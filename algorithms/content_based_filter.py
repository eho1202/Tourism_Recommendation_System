import pandas as pd
import numpy as np
import logging
import joblib
import traceback
from pathlib import Path
from fastapi import HTTPException
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from db import LocationCommands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentBasedFilter:
    def __init__(self):
        self.locations_db = LocationCommands()
        self.MODEL_PATH = Path(__file__).parent / "content_based_model.pkl"
        self.tourism_data = pd.DataFrame()
        self.tfidf = None
        self.tfidf_matrix = None
        self.keywords_list = None
        self.cosine_sim = None
        self.indices = None
        
    async def initialize_data_and_model(self):
        await self.initialize()
        try:
            self.load_model()
        except:
            self.train_and_save_model()
            
    # Load the tourism dataset from MongoDB
    async def load_tourism_data(self):
        try:
            logger.info("   Loading tourism data from database...")
            # Get locations from MongoDB
            locations_list = await self.locations_db.get_locations()
            
            # Convert to DataFrame
            tourism_data = pd.DataFrame(locations_list)
            
            # Fill missing values in 'description' and 'category'
            # Process category field safely
            def process_category(x):
                # Handle scalar values
                if isinstance(x, list):
                    return x
                if isinstance(x, str):
                    return [x]
                # Handle None or NaN as a scalar
                if x is None or (isinstance(x, float) and np.isnan(x)):
                    return []
                # Handle unexpected types
                try:
                    return [] if pd.isna(x) else [str(x)]
                except (TypeError, ValueError):
                    return []
                
            # Update: Handle category as a list
            tourism_data['category'] = tourism_data['category'].apply(lambda x: process_category(x))
            tourism_data['description'] = tourism_data['description'].fillna('')
            
            logger.info("   Tourism data loaded successfully from database.")
            return tourism_data
        except Exception as e:
            logger.error(f" Failed to load tourism data from database: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load tourism data: {e}")

    # Function to extract keywords from description
    def extract_keywords(self, text):
        if self.keywords_list is None:
            raise HTTPException(status_code=500, detail="Keywords list not initialized")
        return ', '.join([word for word in text.split() if word in self.keywords_list])

    # Helper function to convert category list to string
    def categories_to_string(self, categories):
        """Convert a list of categories to a space-separated string"""
        if not categories:
            return ""
        if isinstance(categories, list):
            # Filter out any non-string elements
            valid_categories = [cat for cat in categories if isinstance(cat, str)]
            return " ".join(valid_categories)
        if isinstance(categories, str):
            return categories
        # Default fallback
        return ""

    async def initialize(self):
        """Initialize fresh model with database data"""
        try:
            # Load from MongoDB instead of CSV
            self.tourism_data = await self.load_tourism_data()
            
            self.tourism_data = self.tourism_data.apply(
                lambda col: col.fillna('') if col.dtype == 'object' else col.fillna(0)
            )
            
            # Single TF-IDF initialization for metadata
            self.tfidf = TfidfVectorizer(stop_words='english')
            
            # Update: Convert category list to string for TF-IDF
            # Process each field separately to handle any potential errors
            name_col = self.tourism_data['name'].fillna('')
            desc_col = self.tourism_data['description'].fillna('')
            
            # Safely convert categories to strings
            cat_strings = self.tourism_data['category'].apply(self.categories_to_string)
            
            # Combine all fields into metadata
            self.tourism_data['metadata'] = name_col + ' ' + cat_strings + ' ' + desc_col
            
            # Make sure metadata is always a string
            self.tourism_data['metadata'] = self.tourism_data['metadata'].fillna('')
            
            self.tfidf_matrix = self.tfidf.fit_transform(self.tourism_data['metadata'])
            self.keywords_list = self.tfidf.get_feature_names_out()
            
            self.cosine_sim = cosine_similarity(self.tfidf_matrix, self.tfidf_matrix)
            self.tourism_data = self.tourism_data.reset_index()
            self.indices = pd.Series(self.tourism_data.index, index=self.tourism_data['name'])
            
            logger.info("   Content-based filtering module initialized with database data")
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")

    def filter_by_location(self, recommendations, location):
        if self.tourism_data is None:
            raise HTTPException(status_code=500, detail="Tourism data not loaded")
        return recommendations[
            recommendations['country'].str.contains(location, case=False, na=False) |
            recommendations['city'].str.contains(location, case=False, na=False)
        ]

    def filter_by_keyword(self, recommendations, keyword):
        if self.tourism_data is None:
            raise HTTPException(status_code=500, detail="Tourism data not loaded")
        
        keyword_lower = keyword.lower()
        
        # Filter for name and description (still strings)
        name_description_mask = (
            recommendations['name'].str.contains(keyword, case=False, na=False) |
            recommendations['description'].str.contains(keyword, case=False, na=False)
        )
        
        # Filter for category (now a list)
        # Create a mask for items where any category element contains the keyword
        def check_categories(cats):
            if not isinstance(cats, list):
                return False
            if len(cats) == 0:
                return False
            # Explicitly handle each category as a string
            return any(isinstance(cat, str) and keyword_lower in cat.lower() for cat in cats)
        
        # Use the safer category checking function
        category_mask = recommendations['category'].apply(check_categories)
        
        # Combine masks - ensure we're dealing with boolean Series
        return recommendations[name_description_mask | category_mask]

    def is_location(self, user_input):
        if self.tourism_data is None:
            raise HTTPException(status_code=500, detail="Tourism data not loaded")
        return self.tourism_data['country'].str.contains(user_input, case=False, na=False).any()

    def is_location_name(self, user_input):
        if self.tourism_data is None:
            raise HTTPException(status_code=500, detail="Tourism data not loaded")
        return self.tourism_data['name'].str.lower().eq(user_input.lower()).any()

    # Recommendation function
    async def get_content_recommendations(self, user_input, n):
        try:
            if self.tourism_data is None or self.cosine_sim is None or self.indices is None:
                raise HTTPException(status_code=500, detail="Content-based filtering module not initialized")

            if user_input and self.is_location_name(user_input):
                # If the input is an exact location name (e.g., "Louvre Museum"), recommend similar items
                if user_input not in self.indices:
                    logger.warning(f"   No recommendations found for {user_input}.")
                    return []  # Return an empty list if no recommendations are found

                index = self.indices[user_input]
                sim_scores = list(enumerate(self.cosine_sim[index]))
                sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:n+1]  # Exclude the input item itself
                place_indices = [i[0] for i in sim_scores]
                
                recommendations = self.tourism_data.iloc[place_indices][['name', 'category', 'country', 'city', 'rating', 'description']]
                recommendations['keywords'] = recommendations['description'].apply(self.extract_keywords)
            else:
                # If the input is not an exact location name, treat it as a keyword
                recommendations = self.tourism_data.copy()

                # Apply location-based filtering if the input is a location
                if user_input and self.is_location(user_input):
                    recommendations = self.filter_by_location(recommendations, user_input)

                # Apply keyword-based filtering if the input is not a location or location name
                if user_input and not self.is_location(user_input) and not self.is_location_name(user_input):
                    keyword_filtered = self.filter_by_keyword(recommendations, user_input)
                    if not keyword_filtered.empty:  # Check if keyword filtering returned any results
                        recommendations = keyword_filtered
                    else:
                        logger.info(f"  No results found for keyword '{user_input}'. Returning top-rated items.")
                        recommendations = recommendations.head(n)  # Fallback to top-rated items

            # Return the top n recommendations
            return recommendations.head(n).to_dict(orient="records")
        except Exception as e:
            logger.error(f" Failed to generate content-based recommendations: {e}, {traceback.print_exc()}")
            return []  # Return an empty list if an error occurs

    def train_and_save_model(self):
        model_data = {
            "tourism_data": self.tourism_data,
            "cosine_sim": self.cosine_sim,
            "indices": self.indices,
            "tfidf": self.tfidf,
            "keywords_list": self.keywords_list
        }
        joblib.dump(model_data, self.MODEL_PATH)

    def load_model(self):
        if not self.MODEL_PATH.exists():
            raise FileNotFoundError("No saved model found")
            
        model_data = joblib.load(self.MODEL_PATH)
        self.tourism_data = model_data["tourism_data"]
        self.cosine_sim = model_data["cosine_sim"] 
        self.indices = model_data["indices"]
        self.tfidf = model_data["tfidf"]
        self.keywords_list = model_data["keywords_list"]