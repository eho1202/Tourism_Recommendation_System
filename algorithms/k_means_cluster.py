import ast
import logging
import pandas as pd
from joblib import load, dump
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from typing import Dict, Optional

from db.user_db import UserCommands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserClusterer:
    def __init__(self):
        self.models_loaded = False
        self.MODEL_PATH = Path(__file__).parent
        self.users_df = None
        self.user_db = UserCommands()
    
    async def initialize(self):
        """Async initialization that handles nested profile structure"""
        self.users_df = await self.load_users_data()
        self.load_or_create_models()
    
    async def load_users_data(self) -> pd.DataFrame:
        """Load user data from database and flatten profile structure"""
        users_cursor = self.user_db.get_105_users()
        users_list = await users_cursor.to_list(length=None)
        
        if not users_list:
            logger.warning("No users found in database")
            return pd.DataFrame()
        
        # Convert to DataFrame and handle nested profile
        df = pd.DataFrame(users_list)
        
        # Extract profile fields if they exist
        if 'profile' in df.columns:
            profile_df = pd.json_normalize(df['profile'])
            # Merge profile fields into main dataframe
            df = pd.concat([df.drop(['profile'], axis=1), profile_df], axis=1)
        
        return df
    
    def load_or_create_models(self):
        """Load existing models or create new ones if they don't exist"""
        try:
            self.preprocessor = load(self.MODEL_PATH / 'feature_pipeline.joblib')
            self.kmeans = load(self.MODEL_PATH / 'cluster_model.joblib')
            self.models_loaded = True
            logger.info("Loaded existing clustering models")
        except FileNotFoundError:
            logger.info("No existing models found. Creating new ones...")
            self.create_and_save_models()
            self.models_loaded = True

    def create_and_save_models(self, n_clusters: int = 5):
        """Create new clustering models from training data"""
        if self.users_df is None or self.users_df.empty:
            raise ValueError("User data not loaded or empty. Call initialize() first.")
        
        # Process preferences with fallbacks
        processed_prefs = self.users_df["preferences"].apply(self.process_preferences)
        
        # Create text features from preferences
        self.users_df["env_features"] = processed_prefs.apply(lambda x: " ".join(x["environments"]))
        self.users_df["food_features"] = processed_prefs.apply(lambda x: " ".join(x["food"]))
        self.users_df["act_features"] = processed_prefs.apply(lambda x: " ".join(x["activities"]))
        
        # Configure vectorizers
        vectorizer_params = {
            'min_df': 1,
            'max_df': 1.0,
            'stop_words': None,
            'token_pattern': r'(?u)\b\w+\b'
        }
        
        # Define preprocessing pipeline
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('env_tfidf', TfidfVectorizer(**vectorizer_params), 'env_features'),
                ('food_tfidf', TfidfVectorizer(**vectorizer_params), 'food_features'),
                ('act_tfidf', TfidfVectorizer(**vectorizer_params), 'act_features'),
                ('demographics', Pipeline([
                    ('onehot', OneHotEncoder(handle_unknown='ignore')),
                    ('scaler', StandardScaler(with_mean=False))
                ]), ['ageGroup', 'location', 'job', 'gender'])
            ],
            remainder='drop'
        )
        
        # Fit the preprocessor
        features = self.preprocessor.fit_transform(self.users_df)
        
        # Create and fit KMeans model
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        self.kmeans.fit(features)
        
        # Save models
        dump(self.preprocessor, self.MODEL_PATH / 'feature_pipeline.joblib')
        dump(self.kmeans, self.MODEL_PATH / 'cluster_model.joblib')
        logger.info(f"Created and saved new clustering models with {n_clusters} clusters")

    def process_preferences(self, pref_dict: Optional[Dict]) -> Dict:
        """Ensure preferences dict has all required keys and non-empty values"""
        if not isinstance(pref_dict, dict):
            pref_dict = {}
        
        return {
            "environments": pref_dict.get("environments", ["unknown_environment"]),
            "food": pref_dict.get("food", ["unknown_food"]),
            "activities": pref_dict.get("activities", ["unknown_activity"])
        }

    def prepare_new_user(self, user_data: Dict) -> pd.DataFrame:
        """Convert raw user data to model-ready format, handling nested profile"""
        # Extract profile data (default to empty dict if not present)
        profile_data = user_data.get('profile', {})
        
        # Process preferences with fallbacks
        prefs = user_data.get('preferences', {})
        if isinstance(prefs, str):
            try:
                prefs = ast.literal_eval(prefs)
            except (ValueError, SyntaxError):
                prefs = {}
        
        # Build feature DataFrame matching training structure
        return pd.DataFrame([{
            'ageGroup': profile_data.get('ageGroup', 0),
            'location': profile_data.get('location', 'unknown'),
            'job': profile_data.get('job', 'unknown'),
            'gender': profile_data.get('gender', 'unknown'),
            'env_features': ' '.join(prefs.get('environments', ['unknown_env'])),
            'food_features': ' '.join(prefs.get('food', ['unknown_food'])),
            'act_features': ' '.join(prefs.get('activities', ['unknown_act']))
        }])

    async def cluster_user(self, user_id: int, user_data: Dict) -> int:
        """Cluster a single new user and update database"""
        if not self.models_loaded:
            await self.initialize()
        
        try:
            user_df = self.prepare_new_user(user_data)
            features = self.preprocessor.transform(user_df)
            cluster_val = int(self.kmeans.predict(features)[0])
            
            # Update user cluster in database
            result = await self.user_db.update_user_cluster(user_id, cluster_val)
            if result:
                logger.info(f"User {user_id} assigned to cluster {cluster_val}")
            else:
                logger.warning(f"Failed to update cluster for user {user_id}")
            
            return cluster_val
        except Exception as e:
            logger.error(f"Error clustering user {user_id}: {str(e)}")
            raise

    async def recluster_all_users(self) -> Dict[int, int]:
        """Recluster all users in the database"""
        if not self.models_loaded:
            await self.initialize()
        
        users_cursor = self.user_db.get_all_users()
        users_list = await users_cursor.to_list(length=None)
        
        results = {}
        for user in users_list:
            try:
                cluster = await self.cluster_user(user['userId'], user)
                results[user['userId']] = cluster
            except Exception as e:
                logger.error(f"Failed to cluster user {user.get('userId')}: {str(e)}")
                continue
        
        logger.info(f"Completed reclustering of {len(results)} users")
        return results