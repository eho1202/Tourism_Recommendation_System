from fastapi import HTTPException
import pandas as pd
import requests
import logging
from surprise import SVD, Dataset, Reader, KNNBasic, accuracy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from surprise.model_selection import KFold

from algorithms.collaborative_filter import get_collaborative_recommendations
from algorithms.content_based_filter import get_content_recommendations
from .datasets.load_data import load_csv
from db import get_ratings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ratings = pd.DataFrame(get_ratings())

# Load data
tourism_data = load_csv("tourist_destinations.csv")
user_metadata = load_csv("user_metadata.csv")

def hybrid_recommender(user_id, user_input=None, n=10):
    try:
        user_ratings_count = len(ratings[ratings['userId'] == user_id])
        
        if user_id not in ratings['userId'].unique():
            # New user - use clustering
            logger.info(f"  User {user_id} is a new user. Using clustering-based recommendations.")
            user_cluster = user_metadata[user_metadata['userId'] == user_id]['cluster'].values[0]
            cluster_users = user_metadata[user_metadata['cluster'] == user_cluster]['userId'].values
            cluster_ratings = ratings[ratings['userId'].isin(cluster_users)]
            
            # Get top-rated items from the cluster
            top_items = cluster_ratings.groupby('itemId')['rating'].mean().sort_values(ascending=False).head(n)
            recommendations = tourism_data[tourism_data['itemId'].isin(top_items.index)][['name', 'category', 'country', 'itemRating']]
            return recommendations.to_dict(orient="records")

        elif user_ratings_count > 15:
            # Item-based collaborative filtering for Users with > 15 ratings
            logger.info(f"  User {user_id} has more than 15 ratings. Using collaborative filtering.")
            return get_collaborative_recommendations(user_id, user_input, n)
        else:
            return get_content_recommendations(user_input, n)
    except Exception as e:
        logger.error(f" Failed to generate recommendations for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {e}")
    
# Example usage
# print("Recommendations for userId=45:",hybrid_recommender(userId=45, item_name='London Eye', n=5)) # Should use cb
# print("Recommendations for userId=59:", hybrid_recommender(userId=59, n=5)) # Should use cf
# print("Recommendations for userId=199",hybrid_recommender(userId=199, n=5)) # Should cluster first then cb