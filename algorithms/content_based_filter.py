import pandas as pd
import numpy as np
import logging
import joblib
from pathlib import Path
from fastapi import HTTPException
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import linear_kernel, cosine_similarity

from .datasets.load_data import load_csv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "content_based_model.pkl"

# Load the tourism dataset
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
        raise HTTPException(status_code=500, detail=f"Failed to load tourism data: {e}")

# Function to extract keywords from description
def extract_keywords(text):
    return ', '.join([word for word in text.split() if word in keywords_list])


tourism_data = load_tourism_data()

# Initialize TF-IDF Vectorizer for keyword extraction
tfidf = TfidfVectorizer(stop_words='english', max_features=10)  # Extract top 10 keywords
tfidf_matrix = tfidf.fit_transform(tourism_data['description'])

# Get feature names (keywords)
keywords_list = tfidf.get_feature_names_out()

# Create 'keywords' column
tourism_data['keywords'] = tourism_data['description'].apply(extract_keywords)

# Create metadata column for content-based filtering
tourism_data['metadata'] = tourism_data['name'] + ' ' + tourism_data['category'] + ' ' + tourism_data['keywords']

# Apply TF-IDF to metadata
tfidf_matrix = TfidfVectorizer(stop_words='english').fit_transform(tourism_data['metadata'])

# Compute cosine similarity
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

# Reset index for lookup
tourism_data = tourism_data.reset_index()
indices = pd.Series(tourism_data.index, index=tourism_data['name']).drop_duplicates()

# Recommendation function
def get_content_recommendations(item_name, n=5, cosine_sim=cosine_sim):
    try:
        logger.info(f"  Generating recommendations for item {item_name}...")
        
        if item_name not in indices:
            return f"   No recommendations found for {item_name}"

        index = indices[item_name]
        sim_scores = list(enumerate(cosine_sim[index]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:n+1]  # Top n similar places
        place_indices = [i[0] for i in sim_scores]
        
        recommendations = tourism_data.iloc[place_indices][['name', 'category', 'country', 'itemRating']]
        
        logger.info(f"  Recommendations generated successfully: {recommendations}")
        return recommendations.to_dict(orient="records")
    except Exception as e:
        logger.error(f" Failed to generate recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {e}")

def train_and_save_model():
    try:
        logger.info("   Training the content-based filtering model...")
        
        model_data = {
            "tourism_data": tourism_data,
            "cosine_sim": cosine_sim,
            "indices": indices
        }
        
        joblib.dump(model_data, MODEL_PATH)
        logger.info("   CB Model trained and saved sucessfully.")
    except Exception as e:
        logger.error(f" Failed to train and save model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to train the model: {e}")

def load_model():
    global tourism_data, cosine_sim, indices
    try:
        if MODEL_PATH.exists():
            logger.info("   Loading pre-trained model...")
            model_data = joblib.load(MODEL_PATH)
            tourism_data = model_data["tourism_data"]
            cosine_sim = model_data["cosine_sim"]
            indices = model_data["indices"]
        else:
            logger.info("   No pre-trained model found. Training a new model...")
            train_and_save_model()
    except Exception as e:
        logger.error(f" Failed to load model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load the model: {e}")

load_model()

# Example usage
# print(get_content_recommendations('London Eye'))