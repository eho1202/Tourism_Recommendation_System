import logging
import traceback
import pandas as pd
from fastapi import HTTPException

from algorithms.collaborative_filter import CollaborativeFilter
from algorithms.content_based_filter import ContentBasedFilter
from algorithms.k_means_cluster import UserClusterer
from .datasets.load_data import load_csv
from db import UserCommands, RecommenderCommands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridFilter:
    def __init__(self):
        self.user_db = UserCommands()
        self.recommender_db = RecommenderCommands()
        self.ratings = pd.DataFrame()
        self.tourism_data = load_csv("tourist_destinations.csv")
        
        self.clusterer = UserClusterer()
        self.cf = CollaborativeFilter()
        self.cb = ContentBasedFilter()


    # Load ratings data
    async def fetch_and_process_ratings(self):
        global ratings
        ratings = pd.DataFrame(await self.recommender_db.get_ratings())
        return ratings

    async def hybrid_recommender(self, user_id, user_input=None, n=10):
        try:
            user_data = await self.user_db.get_user_id(user_id)
            if user_data is None:
                raise HTTPException(status_code=400, detail="User data is not available for the given user_id")

            user_ratings_count = len(ratings[ratings['userId'] == user_id])
            
            if user_id not in ratings['userId'].unique():
                # New user - use clustering
                logger.info(f"  User {user_id} is a new user. Using clustering-based recommendations.")
                
                # Get cluster value
                cluster = await self.clusterer.cluster_user(user_id, user_data)
                # Get cluster peers based on cluster value
                cluster_users = await self.user_db.get_cluster_peers(cluster)
                cluster_pd = pd.DataFrame(cluster_users)
                
                # Get top-rated items from cluster
                cluster_ratings = ratings[ratings['userId'].isin(cluster_pd)]
                if cluster_ratings.empty:
                    logger.warning(f"   No ratings found for cluster {cluster}. Using content-based fallback")
                    return await self.cb.get_content_recommendations(user_input, n)
                    
                top_items = (cluster_ratings.groupby('itemId')['rating']
                            .mean()
                            .sort_values(ascending=False)
                            .head(n))
                
                logger.info(f"  Top rated items from cluster {cluster}: {top_items}")
                
                return self.tourism_data[self.tourism_data['itemId'].isin(top_items.index)].to_dict('records')

            elif user_ratings_count > 15:
                # Item-based collaborative filtering for Users with > 15 ratings
                logger.info(f"  User {user_id} has more than 15 ratings. Using collaborative filtering.")
                return await self.cf.get_collaborative_recommendations(user_id, user_input, n)
            else:
                logger.info(f"  User {user_id} has less than or equal to 15 ratings. Using content based filtering")
                return await self.cb.get_content_recommendations(user_input, n)
        except Exception as e:
            logger.error(f" Failed to generate recommendations for user {user_id}: {e}, {traceback.print_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {e}")
    
# Example usage
# print("Recommendations for userId=45:",hybrid_recommender(userId=45, item_name='London Eye', n=5)) # Should use cb
# print("Recommendations for userId=59:", hybrid_recommender(userId=59, n=5)) # Should use cf
# print("Recommendations for userId=199",hybrid_recommender(userId=199, n=5)) # Should cluster first then cb