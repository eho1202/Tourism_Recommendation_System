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
        """Async initialization"""
        self.users_df = await self.load_user_data()
        self.load_or_create_models()
    
    async def load_user_data(self):
        """Load user data from database"""
        users_cursor = self.user_db.get_105_users()
        users_list = await users_cursor.to_list(length=None)
        return pd.DataFrame(users_list)
    
    def load_or_create_models(self):
        """Load existing models or create new ones if they don't exist"""
        try:
            self.preprocessor = load(self.MODEL_PATH / 'feature_pipeline.joblib')
            self.kmeans = load(self.MODEL_PATH / 'cluster_model.joblib')
            self.models_loaded = True
            logger.info("   Loaded existing clustering models")
        except FileNotFoundError:
            logger.info("   No existing models found. Creating new ones...")
            self.create_and_save_models()
            self.models_loaded = True

    def create_and_save_models(self, n_clusters=5):
        """Create new clustering models from training data"""
        if self.users_df is None:
            raise ValueError("User data not loaded. Call initialize() first.")
        
        # Process preferences with fallbacks
        processed_prefs = self.users_df["preferences"].apply(self.process_preferences)
        
        # Create text features
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
        
        # Create and fit KMeans
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        self.kmeans.fit(features)
        
        # Save models
        dump(self.preprocessor, self.MODEL_PATH / 'feature_pipeline.joblib')
        dump(self.kmeans, self.MODEL_PATH / 'cluster_model.joblib')
        logger.info(f"  Created and saved new clustering models with {n_clusters} clusters")

    def process_preferences(self, pref_dict):
        """Ensure preferences dict has all required keys and non-empty values"""
        if not isinstance(pref_dict, dict):
            pref_dict = {}
        
        return {
            "environments": pref_dict.get("environments", ["unknown_environment"]),
            "food": pref_dict.get("food", ["unknown_food"]),
            "activities": pref_dict.get("activities", ["unknown_activity"])
        }

    def prepare_new_user(self, user_data):
        """Convert raw user data to model-ready format"""
        # Ensure preferences exist
        prefs = user_data.get('preferences', {})
        if isinstance(prefs, str):
            try:
                prefs = ast.literal_eval(prefs)
            except:
                prefs = {}
        
        # Build feature DataFrame matching training structure
        return pd.DataFrame([{
            'ageGroup': user_data.get('age_group', 0),
            'location': user_data.get('location', 'unknown'),
            'job': user_data.get('job', 'unknown'),
            'gender': user_data.get('gender', 'unknown'),
            'env_features': ' '.join(prefs.get('environments', ['unknown_env'])),
            'food_features': ' '.join(prefs.get('food', ['unknown_food'])),
            'act_features': ' '.join(prefs.get('activities', ['unknown_act']))
        }])

    async def cluster_user(self, user_id, user_data):
        """Cluster a single new user"""
        if not self.models_loaded:
            self.load_or_create_models()
        
        user_df = self.prepare_new_user(user_data)
        features = self.preprocessor.transform(user_df)
        cluster_val = int(self.kmeans.predict(features)[0])
        result = await self.user_db.update_user_cluster(user_id, cluster_val)
        if result:
            logger.info(f"  User {user_id} clustered to {cluster_val}")
        return cluster_val

# # Example usage
# if __name__ == "__main__":
#     # Initialize clusterer - will create models if they don't exist
#     clusterer = UserClusterer()
    
#     # Example new user
#     new_user = {
#         'userId': 999,
#         'age_group': 3,
#         'location': 'USA',
#         'job': 'Engineer',
#         'gender': 'Male',
#         'preferences': {
#             'environments': ['mountains'],
#             'food': ['italian'],
#             'activities': ['hiking', 'museums']
#         }
#     }
#     cluster = clusterer.cluster_user(new_user)
#     print(f"New user assigned to cluster: {cluster}")