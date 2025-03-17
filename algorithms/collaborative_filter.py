from fastapi import HTTPException
import joblib
import numpy as np
import pandas as pd
from surprise import Reader, Dataset, KNNBasic, accuracy
from surprise.model_selection import KFold
import requests
from pathlib import Path
import logging

from db import get_ratings
from .datasets.load_data import load_csv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the path to save the trained model
MODEL_PATH = Path(__file__).parent / "collaborative_filter_model.pkl"

def load_tourism_data():
    """
    Load tourism data from a CSV file or another source.
    """
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
        raise HTTPException(status_code=500, detail=f"  Failed to load tourism data: {e}")
    
tourism_data = load_tourism_data()


# Load ratings data into DataFrame
ratings = pd.DataFrame(get_ratings())

# Define the reader object with no rating scale specified (auto-detected)
reader = Reader(rating_scale=(1, 5))

# Load data into Surprise Dataset
data = Dataset.load_from_df(ratings[['userId', 'itemId', 'rating']].copy(), reader)

# Use KNNBasic algorithm for item-based collaborative filtering
sim_options = {
    'name': 'cosine',
    'user_based': False  # Item-based collaborative filtering
}
algo = KNNBasic(sim_options=sim_options)

def filter_by_location(recommendations, location):
    return recommendations[
        recommendations['country'].str.contains(location, case=False, na=False)
    ]

def filter_by_keyword(recommendations, keyword):
    return recommendations[
        recommendations['name'].str.contains(keyword, case=False, na=False) |
        recommendations['category'].str.contains(keyword, case=False, na=False) |
        recommendations['description'].str.contains(keyword, case=False, na=False)
    ]

def is_location(user_input):
    return tourism_data['country'].str.contains(user_input, case=False, na=False).any() 

def is_location_name(user_input):
    return tourism_data['name'].str.lower().eq(user_input.lower()).any()

def get_collaborative_recommendations(user_id, user_input, n):
    try:
        if user_input and is_location_name(user_input):
            # If the user searches for an item, use item-based collaborative filtering
            item_id = tourism_data.loc[tourism_data['name'].str.lower() == user_input.lower(), 'itemId'].values # type: ignore
            if len(item_id) == 0:
                logger.warning(f"No item found with name '{user_input}'.")
                return []  # Return an empty list if no item is found
            item_id = item_id[0]  # Get the first matching item ID
            item_recommendations = get_item_recommendations(item_id, n)  # Returns a list of item IDs
            recommendations = tourism_data[tourism_data['itemId'].isin(item_recommendations)][['name', 'category', 'country', 'description', 'itemRating']]
        else:
            # If the user does not search for an item, recommend top-rated items based on their rating history
            user_items = ratings[ratings['userId'] == user_id]['itemId']
            
            # Get recommendations for each item rated by the user
            all_recommendations = []
            for item_id in user_items:
                item_recommendations = get_item_recommendations(item_id, n)  # Returns a list of item IDs
                all_recommendations.extend(item_recommendations)
            
            # Remove duplicates and items already rated by the user
            unique_recommendations = list(set(all_recommendations) - set(user_items))
            
            # Get details for the recommended items
            recommendations = tourism_data[tourism_data['itemId'].isin(unique_recommendations)][['name', 'category', 'country', 'description', 'itemRating']]

        # Apply location-based filtering if the input is a location
        if user_input and is_location(user_input):
            recommendations = filter_by_location(recommendations, user_input)

        # Apply keyword-based filtering if the input is not a location or location name
        if user_input and not is_location(user_input) and not is_location_name(user_input):
            keyword_filtered = filter_by_keyword(recommendations, user_input)
            if not keyword_filtered.empty:  # Check if keyword filtering returned any results
                recommendations = keyword_filtered
            else:
                logger.info(f"No results found for keyword '{user_input}'. Returning top-rated items.")
                recommendations = recommendations.head(n)  # Fallback to top-rated items

        # Return the top n recommendations
        return recommendations.head(n).to_dict(orient="records")
    except Exception as e:
        logger.error(f"Failed to generate collaborative recommendations: {e}")
        return []  # Return an empty list if an error occurs

def get_item_recommendations(item_id, n):
    try:
        logger.info(f"  Generating recommendations for item {item_id}...")
        
        # Convert the item ID to the inner ID used by the model
        inner_id = algo.trainset.to_inner_iid(item_id)
        
        # Get the nearest neighbors
        neighbors = algo.get_neighbors(inner_id, k=n)
        
        # Convert inner IDs back to raw item IDs
        item_recommendations = [algo.trainset.to_raw_iid(inner_id) for inner_id in neighbors]

        return item_recommendations  # Return a list of item IDs
    except Exception as e:
        logger.error(f" Failed to generate recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {e}")

def train_and_save_model():
    global algo
    try:
        logger.info("   Training the collaborative filtering model...")
        
        # Train the model
        trainset = data.build_full_trainset()
        algo.fit(trainset)
        
        # Save the model
        joblib.dump(algo, MODEL_PATH)
        logger.info("   CF Model trained and saved successfully.")
    except Exception as e:
        logger.error(f" Failed to train and save model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to train the model: {e}")

def load_model():
    global algo
    try:
        if MODEL_PATH.exists():
            logger.info("   Loading pre-trained model...")
            algo = joblib.load(MODEL_PATH)
        else:
            logger.info("   No pre-trained model found. Training a new model...")
            train_and_save_model()
    except Exception as e:
        logger.error(f" Failed to load model: {e}")
        raise HTTPException(status_code=500, detail=f"  Failed to load the model: {e}")

load_model()

# item_id = 8  # Replace with an actual item ID
# recommendations = get_item_recommendations(item_id, 5)
# print("Top 5 item-based recommendations for item", item_id, ":")
# print(recommendations)

