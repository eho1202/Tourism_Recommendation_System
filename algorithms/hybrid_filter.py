from fastapi import HTTPException
import pandas as pd
import requests
import logging
from surprise import SVD, Dataset, Reader, KNNBasic, accuracy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from surprise.model_selection import KFold

from algorithms.collaborative_filter import get_item_recommendations
from algorithms.content_based_filter import get_content_recommendations
from .datasets.load_data import load_csv
from db import get_ratings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ratings = pd.DataFrame(get_ratings())

# Load data
tourism_data = load_csv("tourist_destinations.csv")
user_metadata = load_csv("user_metadata.csv")

def hybrid_recommender(userId, item_name=None, n=5):
    user_ratings_count = len(ratings[ratings['userId'] == userId])
    try:
        if userId not in ratings['userId'].unique():
            # New user - use clustering
            logger.info(f"  User {userId} is a new user. Using clustering-based recommendations.")
            user_cluster = user_metadata[user_metadata['userId'] == userId]['cluster'].values[0]
            cluster_users = user_metadata[user_metadata['cluster'] == user_cluster]['userId'].values
            cluster_ratings = ratings[ratings['userId'].isin(cluster_users)]
            
            # Get top-rated items from the cluster
            top_items = cluster_ratings.groupby('itemId')['rating'].mean().sort_values(ascending=False).head(n)
            recommendations = tourism_data[tourism_data['itemId'].isin(top_items.index)][['name', 'category', 'country', 'itemRating']]
            return recommendations.to_dict(orient="records")

        elif user_ratings_count > 15:
            # Item-based collaborative filtering for Users with > 15 ratings
            logger.info(f"  User {userId} has more than 15 ratings. Using collaborative filtering.")
            if item_name:
                # Get item-based recommendations for the given item
                item_id = tourism_data.loc[tourism_data['name'] == item_name, 'itemId'].values[0] # type: ignore
                item_recommendations = get_item_recommendations(item_id, n)
                recommendations = tourism_data[tourism_data['itemId'].isin(item_recommendations)][['name', 'category', 'country', 'itemRating']]
                return recommendations.to_dict(orient="records")
            else:
                # Recommend top-rated items for the user based on item-based collaborative filtering
                user_items = ratings[ratings['userId'] == userId]['itemId']
                
                # Get recommendations for each item rated by the user
                all_recommendations = []
                for item_id in user_items:
                    item_recommendations = get_item_recommendations(item_id, n)
                    all_recommendations.extend(item_recommendations)
                
                # Remove duplicates and items already rated by the user
                unique_recommendations = list(set(all_recommendations) - set(user_items))
                
                # Get details for the recommended items
                recommendations = tourism_data[tourism_data['itemId'].isin(unique_recommendations)][['name', 'category', 'country', 'itemRating']]
                return recommendations.to_dict(orient="records")
        else:
            # Content-based filtering
            if item_name:
                # item_id = tourism_data.loc[tourism_data['name'] == item_name, 'itemId'].values[0]
                recommendations = get_content_recommendations(item_name, n)
                return recommendations
            else:
                # Recommend top-rated items based on content similarity
                recommendations = tourism_data.sort_values('itemRating', ascending=False).head(n)[['name', 'category', 'country', 'itemRating']]
                return recommendations.to_dict(orient="records")
    except Exception as e:
        logger.error(f" Failed to generate recommendations for user {userId}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {e}")
    
# Example usage
# print("Recommendations for userId=45:",hybrid_recommender(userId=45, item_name='London Eye', n=5)) # Should use cb
# print("Recommendations for userId=59:", hybrid_recommender(userId=59, n=5)) # Should use cf
# print("Recommendations for userId=199",hybrid_recommender(userId=199, n=5)) # Should cluster first then cb