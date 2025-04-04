from fastapi import HTTPException
import joblib
import pandas as pd
from surprise import Reader, Dataset, KNNBasic
from pathlib import Path
import logging

from db import RecommenderCommands, LocationCommands
# from .datasets.load_data import load_csv  # We won't need this anymore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CollaborativeFilter:
    def __init__(self):
        self.recommender_db = RecommenderCommands()
        self.locations_db = LocationCommands()
        self.MODEL_PATH = Path(__file__).parent / "collaborative_filter_model.pkl"
        self.reader = Reader(rating_scale=(1, 5))
        self.sim_options = {'name': 'cosine', 'user_based': False}  # Item-based CF
        self.algo = KNNBasic(sim_options=self.sim_options)
        self.ratings = pd.DataFrame()
        self.tourism_data = pd.DataFrame()
    
    # main.py calls this 
    async def initialize_data_and_model(self):
        await self.fetch_and_process_ratings()
        await self.load_tourism_data()
        self.load_model()

    async def load_tourism_data(self):
        """
        Load tourism data from MongoDB locations collection.
        """
        try:
            logger.info("   Loading tourism data from database...")
            # Get locations from MongoDB
            locations_list = await self.locations_db.get_locations()
            
            # Convert to DataFrame
            tourism_data = pd.DataFrame(locations_list)
            
            # Fill missing values in 'description' and 'category'
            tourism_data['category'] = tourism_data['category'].fillna('')
            tourism_data['description'] = tourism_data['description'].fillna('')
            
            self.tourism_data = tourism_data
            self.tourism_data = self.tourism_data.apply(
                lambda col: col.fillna('') if col.dtype == 'object' else col.fillna(0)
            )
            logger.info("   Tourism data loaded successfully from database.")
            return tourism_data
        except Exception as e:
            logger.error(f" Failed to load tourism data from database: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load tourism data: {e}")

    # Load ratings data into Surprise Dataset
    async def fetch_and_process_ratings(self):
        self.ratings = pd.DataFrame(await self.recommender_db.get_ratings())

    def filter_by_location(self, recommendations, location):
        return recommendations[
            recommendations['country'].str.contains(location, case=False, na=False)
        ]

    def filter_by_keyword(self, recommendations, keyword):
        return recommendations[
            recommendations['name'].str.contains(keyword, case=False, na=False) |
            recommendations['category'].str.contains(keyword, case=False, na=False) |
            recommendations['description'].str.contains(keyword, case=False, na=False)
        ]

    def is_country(self, user_input):
        return self.tourism_data['country'].str.contains(user_input, case=False, na=False).any() 

    def is_location_name(self, user_input):
        return self.tourism_data['name'].str.lower().eq(user_input.lower()).any()

    async def get_collaborative_recommendations(self, user_id, user_input, n):
        try:
            if user_input and self.is_location_name(user_input):
                # If the user searches for an item, use item-based collaborative filtering
                item_id = self.tourism_data.loc[self.tourism_data['name'].str.lower() == user_input.lower(), 'locationId'].values
                if len(item_id) == 0:
                    logger.warning(f"No item found with name '{user_input}'.")
                    return []  # Return an empty list if no item is found
                item_id = item_id[0]  # Get the first matching item ID
                item_recommendations = self.get_item_recommendations(item_id, n)  # Returns a list of item IDs
                recommendations = self.tourism_data[self.tourism_data['locationId'].isin(item_recommendations)][['name', 'category', 'country', 'city', 'description', 'rating']]
            else:
                # If the user does not search for an item, recommend top-rated items based on their rating history
                user_items = self.ratings[self.ratings['userId'] == user_id]['locationId']
                
                # Get recommendations for each item rated by the user
                all_recommendations = []
                for item_id in user_items:
                    item_recommendations = self.get_item_recommendations(item_id, n)  # Returns a list of item IDs
                    all_recommendations.extend(item_recommendations)
                
                # Remove duplicates and items already rated by the user
                unique_recommendations = list(set(all_recommendations) - set(user_items))
                
                # Get details for the recommended items
                recommendations = self.tourism_data[self.tourism_data['locationId'].isin(unique_recommendations)][['name', 'category', 'city', 'country', 'description']]

            # Apply location-based filtering if the input is a location
            if user_input and self.is_country(user_input):
                recommendations = self.filter_by_location(recommendations, user_input)

            # Apply keyword-based filtering if the input is not a location or location name
            if user_input and not self.is_country(user_input) and not self.is_location_name(user_input):
                keyword_filtered = self.filter_by_keyword(recommendations, user_input)
                if not keyword_filtered.empty:  # Check if keyword filtering returned any results
                    recommendations = keyword_filtered
                else:
                    logger.info(f"No results found for keyword '{user_input}'. Returning top-rated items.")
                    recommendations = recommendations.head(n)  # Fallback to top-rated items

            # Return the top n recommendations
            return recommendations.head(n).to_dict(orient="records")
        except Exception as e:
            logger.error(f"Failed to generate collaborative recommendations: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate collaborative recommendations.")

    def get_item_recommendations(self, item_id, n):
        try:
            logger.info(f"  Generating recommendations for item {item_id}...")
            
            # Convert the item ID to the inner ID used by the model
            inner_id = self.algo.trainset.to_inner_iid(item_id)
            
            # Get the nearest neighbors
            neighbors = self.algo.get_neighbors(inner_id, k=n)
            
            # Convert inner IDs back to raw item IDs
            item_recommendations = [self.algo.trainset.to_raw_iid(inner_id) for inner_id in neighbors]

            return item_recommendations  # Return a list of item IDs
        except Exception as e:
            logger.error(f" Failed to generate recommendations: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {e}")

    def train_and_save_model(self):
        try:
            logger.info("   Training the collaborative filtering model...")
            
            # Train the model
            data = Dataset.load_from_df(self.ratings[['userId', 'locationId', 'rating']].copy(), self.reader)
            trainset = data.build_full_trainset()
            self.algo.fit(trainset)
            
            # Save the model
            joblib.dump(self.algo, self.MODEL_PATH)
            logger.info("   CF Model trained and saved successfully.")
        except Exception as e:
            logger.error(f" Failed to train and save model: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to train the model: {e}")

    def load_model(self):
        try:
            if self.MODEL_PATH.exists():
                logger.info("   Loading pre-trained model...")
                self.algo = joblib.load(self.MODEL_PATH)
            else:
                logger.info("   No pre-trained model found. Training a new model...")
                self.train_and_save_model()
        except Exception as e:
            logger.error(f" Failed to load model: {e}")
            raise HTTPException(status_code=500, detail=f"  Failed to load the model: {e}")

# item_id = 8  # Replace with an actual item ID
# recommendations = get_item_recommendations(item_id, 5)
# print("Top 5 item-based recommendations for item", item_id, ":")
# print(recommendations)
