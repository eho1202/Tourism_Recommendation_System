import logging
import traceback
import pandas as pd
from fastapi import HTTPException

from algorithms.collaborative_filter import CollaborativeFilter
from algorithms.content_based_filter import ContentBasedFilter
from algorithms.k_means_cluster import UserClusterer
# from .datasets.load_data import load_csv  # Remove this import
from db import UserCommands, RecommenderCommands, LocationCommands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridFilter:
    def __init__(self):
        self.user_db = UserCommands()
        self.recommender_db = RecommenderCommands()
        self.locations_db = LocationCommands()
        self.ratings = pd.DataFrame()
        self.tourism_data = pd.DataFrame()
        
        self.clusterer = None
        self.cf = None
        self.cb = None

    async def initialize(self):
        self.clusterer = UserClusterer()
        self.cf = CollaborativeFilter()
        self.cb = ContentBasedFilter()
        
        # Initialize components
        await self.clusterer.initialize()
        await self.cf.initialize_data_and_model()
        await self.cb.initialize_data_and_model()
        
        # Load data
        await self.fetch_and_process_ratings()
        await self.load_tourism_data()
        
        logger.info("   Hybrid filter initialized.")
        
    async def fetch_and_process_ratings(self):
        ratings_from_mongodb = pd.DataFrame(await self.recommender_db.get_ratings())
        self.ratings = pd.DataFrame(ratings_from_mongodb)
    
    async def load_tourism_data(self):
        """
        Load tourism data from MongoDB locations collection.
        """
        try:
            logger.info("   Loading tourism data from database...")
            # Get locations from MongoDB
            locations_list = await self.locations_db.get_locations()
            
            # Convert to DataFrame
            self.tourism_data = pd.DataFrame(locations_list)
            
            logger.info("   Tourism data loaded successfully from database.")
        except Exception as e:
            logger.error(f" Failed to load tourism data from database: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load tourism data: {e}")

    async def get_recommendations(self, user_id, user_input=None, n=10):
        try:
            if user_id is None:
                logger.info("   User is guest user, serving guest user recommendations.")
                if not user_input:
                    return self.get_popular_items(n)
                return await self.cb.get_content_recommendations(user_input, n)
            
            user_data = await self.user_db.get_user_by_id(user_id)
            if user_data is None:
                raise HTTPException(status_code=400, detail="User data is not available for the given user_id.")

            user_ratings_count = len(self.ratings[self.ratings['userId'] == user_id])
            
            if user_id not in self.ratings['userId'].unique():
                # New user - use clustering
                logger.info(f"  User {user_id} is a new user. Using clustering-based recommendations.")
                
                # Get cluster value
                cluster = await self.clusterer.cluster_user(user_id, user_data)
                # Get cluster peers based on cluster value
                cluster_users = await self.user_db.get_cluster_peers(cluster)
                cluster_pd = pd.DataFrame(cluster_users)
                
                # Get top-rated items from cluster
                cluster_ratings = self.ratings[self.ratings['userId'].isin(cluster_pd)]
                if cluster_ratings.empty:
                    logger.warning(f"   No ratings found for cluster {cluster}. Using content-based fallback")
                    return await self.cb.get_content_recommendations(user_input, n)
                    
                top_items = (cluster_ratings.groupby('itemId')['rating']
                            .mean()
                            .sort_values(ascending=False)
                            .head(n))
                
                logger.info(f"  Top rated items from cluster {cluster}: {top_items}")
                
                return self.tourism_data[self.tourism_data['locationId'].isin(top_items.index)].to_dict('records')

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
    
    def get_popular_items(self, n):
        if self.ratings.empty:
            return self.tourism_data.head(n).to_dict('records')
            
        popular_items = (self.ratings.groupby('itemId')['rating']
                        .mean()
                        .sort_values(ascending=False)
                        .head(n))
        return self.tourism_data[self.tourism_data['locationId'].isin(popular_items.index)].to_dict('records')