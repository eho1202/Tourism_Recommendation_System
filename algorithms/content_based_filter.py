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
    return (
        tourism_data['country'].str.contains(user_input, case=False, na=False).any() 
    )

def is_location_name(user_input):
    return tourism_data['name'].str.lower().eq(user_input.lower()).any()


# Recommendation function
def get_content_recommendations(user_input, n, cosine_sim=cosine_sim):
    try:
        if user_input and is_location_name(user_input):
            # If the input is an exact location name (e.g., "Louvre Museum"), recommend similar items
            if user_input not in indices:
                logger.warning(f"   No recommendations found for {user_input}.")
                return []  # Return an empty list if no recommendations are found

            index = indices[user_input]
            sim_scores = list(enumerate(cosine_sim[index]))
            sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:n+1]  # Exclude the input item itself
            place_indices = [i[0] for i in sim_scores]
            
            recommendations = tourism_data.iloc[place_indices][['name', 'category', 'country', 'itemRating']]
        else:
            # If the input is not an exact location name, treat it as a keyword
            recommendations = tourism_data.copy()

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
        logger.error(f" Failed to generate content-based recommendations: {e}")
        return []  # Return an empty list if an error occurs

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