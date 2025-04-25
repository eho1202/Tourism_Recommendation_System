import logging
import traceback
import pandas as pd
import numpy as np
from fastapi import HTTPException

from algorithms.collaborative_filter import CollaborativeFilter
from algorithms.content_based_filter import ContentBasedFilter
from algorithms.k_means_cluster import UserClusterer
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
            
            # Process category field safely
            def process_category(x):
                # Handle scalar values
                if isinstance(x, list):
                    return x
                if isinstance(x, str):
                    return [x]
                # Handle None or NaN as a scalar
                if x is None or (isinstance(x, float) and np.isnan(x)):
                    return []
                # Handle unexpected types
                try:
                    return [] if pd.isna(x) else [str(x)]
                except (TypeError, ValueError):
                    return []
                
            # Update: Handle category as a list
            self.tourism_data['category'] = self.tourism_data['category'].apply(lambda x: process_category(x))
            
            # Process other fields
            for col in self.tourism_data.columns:
                if col != 'category':
                    if self.tourism_data[col].dtype == 'object':
                        self.tourism_data[col] = self.tourism_data[col].fillna('')
                    else:
                        self.tourism_data[col] = self.tourism_data[col].fillna(0)
            
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
                    
                top_items = (cluster_ratings.groupby('locationId')['rating']
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
            # Return tourism data with null ratings converted to None (which becomes null in JSON)
            return [self._clean_dict(item) for item in self.tourism_data.head(n).to_dict('records')]
            
        popular_items = (self.ratings.groupby('locationId')['rating']
                        .mean()
                        .sort_values(ascending=False)
                        .head(n))
        
        # Get the tourism data for popular items
        result = self.tourism_data[self.tourism_data['locationId'].isin(popular_items.index)]
        
        # Add the average rating to each item
        result = result.merge(
            popular_items.rename('averageRating'), 
            left_on='locationId', 
            right_index=True
        )
        
        # Convert to dict and clean NaN values
        return [self._clean_dict(item) for item in result.to_dict('records')]

    def _clean_dict(self, item):
        """Helper method to convert NaN/None values to None (which becomes null in JSON)"""
        cleaned = {}
        for key, value in item.items():
            if pd.isna(value):
                cleaned[key] = None
            elif key == 'category' and not value:  # Empty list check for category
                cleaned[key] = []
            else:
                cleaned[key] = value
        return cleaned