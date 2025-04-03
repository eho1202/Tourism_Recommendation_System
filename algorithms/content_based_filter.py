import pandas as pd
import logging
import joblib
import traceback
from pathlib import Path
from fastapi import HTTPException
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .datasets.load_data import load_csv
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
            
    # Load the tourism dataset
    def load_tourism_data(self):
        try:
            logger.info("   Loading tourism data...")
            tourism_data = load_csv("tourist_destinations.csv")
            
            # Fill missing values in 'description' and 'category'
            tourism_data['category'] = tourism_data['category'].fillna('')
            tourism_data['description'] = tourism_data['description'].fillna('')
            
            logger.info("   Tourism data loaded successfully.")
            return tourism_data
        except Exception as e:
            logger.error(f" Failed to load tourism data: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load tourism data: {e}")

    # Function to extract keywords from description
    def extract_keywords(self, text):
        if self.keywords_list is None:
            raise HTTPException(status_code=500, detail="Keywords list not initialized")
        return ', '.join([word for word in text.split() if word in self.keywords_list])

    async def initialize(self):
        """Initialize fresh model"""
        try:
            # TODO: Upate this to load data from MongoDB (await get_locations())
            self.tourism_data = self.load_tourism_data()
            
            # Single TF-IDF initialization for metadata
            self.tfidf = TfidfVectorizer(stop_words='english')
            self.tourism_data['metadata'] = (
                self.tourism_data['name'] + ' ' + 
                self.tourism_data['category'] + ' ' + 
                self.tourism_data['description']
            )
            self.tfidf_matrix = self.tfidf.fit_transform(self.tourism_data['metadata'])
            self.keywords_list = self.tfidf.get_feature_names_out()
            
            self.cosine_sim = cosine_similarity(self.tfidf_matrix, self.tfidf_matrix)
            self.tourism_data = self.tourism_data.reset_index()
            self.indices = pd.Series(self.tourism_data.index, index=self.tourism_data['name'])
            
            logger.info("   Content-based filtering module initialized")
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")

    def filter_by_location(self, recommendations, location):
        if self.tourism_data is None:
            raise HTTPException(status_code=500, detail="Tourism data not loaded")
        return recommendations[
            recommendations['country'].str.contains(location, case=False, na=False)
        ]

    def filter_by_keyword(self, recommendations, keyword):
        if self.tourism_data is None:
            raise HTTPException(status_code=500, detail="Tourism data not loaded")
        return recommendations[
            recommendations['name'].str.contains(keyword, case=False, na=False) |
            recommendations['category'].str.contains(keyword, case=False, na=False) |
            recommendations['description'].str.contains(keyword, case=False, na=False)
        ]

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
                
                recommendations = self.tourism_data.iloc[place_indices][['name', 'category', 'country', 'city', 'itemRating']]
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
