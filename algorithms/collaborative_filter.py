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

def get_item_recommendations(item_id, n):
    try:
        logger.info(f"  Generating recommendations for item {item_id}...")
        
        # Convert the item ID to the inner ID used by the model
        inner_id = algo.trainset.to_inner_iid(item_id)
        
        # Get the nearest neighbors
        neighbors = algo.get_neighbors(inner_id, k=n)
        
        # Convert inner IDs back to raw item IDs
        item_recommendations = [algo.trainset.to_raw_iid(inner_id) for inner_id in neighbors]
        
        logger.info(f"  Recommendations generated successfully: {item_recommendations}")
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

