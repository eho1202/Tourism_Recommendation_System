import pandas as pd
import logging
import joblib
import traceback
from pathlib import Path
from fastapi import HTTPException
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .datasets.load_data import load_csv
from db import LocationsCommands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentBasedFilter:
    def __init__(self):
        self.locations_db = LocationsCommands()
        self.MODEL_PATH = Path(__file__).parent / "content_based_model.pkl"
        self.tourism_data = pd.DataFrame()
        self.tfidf = None
        self.tfidf_matrix = None
        self.keywords_list = None
        self.cosine_sim = None
        self.indices = None
        
    async def initialize_data_and_model(self):
        await self.initialize()
        self.load_model()

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
        if keywords_list is None:
            raise HTTPException(status_code=500, detail="Keywords list not initialized")
        return ', '.join([word for word in text.split() if word in keywords_list])

    async def initialize(self):
        """
        Initialize the content-based filtering module.
        """
        global tourism_data, tfidf, tfidf_matrix, keywords_list, cosine_sim, indices

        try:
            # Load tourism data
            # TODO: Upate this to load data from MongoDB (await get_locations())
            tourism_data = self.load_tourism_data()

            # Initialize TF-IDF Vectorizer for keyword extraction
            tfidf = TfidfVectorizer(stop_words='english', max_features=10)  # Extract top 10 keywords
            tfidf_matrix = tfidf.fit_transform(tourism_data['description'])

            # Get feature names (keywords)
            keywords_list = tfidf.get_feature_names_out()

            # Create 'keywords' column
            tourism_data['keywords'] = tourism_data['description'].apply(self.extract_keywords)

            # Create metadata column for content-based filtering
            tourism_data['metadata'] = tourism_data['name'] + ' ' + tourism_data['category'] + ' ' + tourism_data['keywords']

            # Apply TF-IDF to metadata
            tfidf_matrix = TfidfVectorizer(stop_words='english').fit_transform(tourism_data['metadata'])

            # Compute cosine similarity
            cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

            # Reset index for lookup
            tourism_data = tourism_data.reset_index()
            indices = pd.Series(tourism_data.index, index=tourism_data['name']).drop_duplicates()

            logger.info("   Content-based filtering module initialized successfully.")
        except Exception as e:
            logger.error(f" Failed to initialize content-based filtering module: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to initialize module: {e}, {traceback.print_exc()}")

    def filter_by_location(self, recommendations, location):
        if tourism_data is None:
            raise HTTPException(status_code=500, detail="Tourism data not loaded")
        return recommendations[
            recommendations['country'].str.contains(location, case=False, na=False)
        ]

    def filter_by_keyword(self, recommendations, keyword):
        if tourism_data is None:
            raise HTTPException(status_code=500, detail="Tourism data not loaded")
        return recommendations[
            recommendations['name'].str.contains(keyword, case=False, na=False) |
            recommendations['category'].str.contains(keyword, case=False, na=False) |
            recommendations['description'].str.contains(keyword, case=False, na=False)
        ]

    def is_location(self, user_input):
        if tourism_data is None:
            raise HTTPException(status_code=500, detail="Tourism data not loaded")
        return tourism_data['country'].str.contains(user_input, case=False, na=False).any()

    def is_location_name(self, user_input):
        if tourism_data is None:
            raise HTTPException(status_code=500, detail="Tourism data not loaded")
        return tourism_data['name'].str.lower().eq(user_input.lower()).any()

    # Recommendation function
    async def get_content_recommendations(self, user_input, n):
        try:
            if tourism_data is None or cosine_sim is None or indices is None:
                raise HTTPException(status_code=500, detail="Content-based filtering module not initialized")

            if user_input and self.is_location_name(user_input):
                # If the input is an exact location name (e.g., "Louvre Museum"), recommend similar items
                if user_input not in indices:
                    logger.warning(f"   No recommendations found for {user_input}.")
                    return []  # Return an empty list if no recommendations are found

                index = indices[user_input]
                sim_scores = list(enumerate(cosine_sim[index]))
                sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:n+1]  # Exclude the input item itself
                place_indices = [i[0] for i in sim_scores]
                
                recommendations = tourism_data.iloc[place_indices][['name', 'category', 'country', 'city', 'itemRating']]
            else:
                # If the input is not an exact location name, treat it as a keyword
                recommendations = tourism_data.copy()

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
        try:
            logger.info("   Training the content-based filtering model...")
            
            model_data = {
                "tourism_data": tourism_data,
                "cosine_sim": cosine_sim,
                "indices": indices
            }
            
            joblib.dump(model_data, self.MODEL_PATH)
            logger.info("   CB Model trained and saved successfully.")
        except Exception as e:
            logger.error(f" Failed to train and save model: {e}, {traceback.print_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to train the model: {e}")

    def load_model(self):
        global tourism_data, cosine_sim, indices
        try:
            if self.MODEL_PATH.exists():
                logger.info("   Loading pre-trained model...")
                model_data = joblib.load(self.MODEL_PATH)
                tourism_data = model_data["tourism_data"]
                cosine_sim = model_data["cosine_sim"]
                indices = model_data["indices"]
            else:
                logger.info("   No pre-trained model found. Training a new model...")
                self.train_and_save_model()
        except Exception as e:
            logger.error(f" Failed to load model: {e}, {traceback.print_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to load the model: {e}")
