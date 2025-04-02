from fastapi import HTTPException
from db.connections import ConnectionManager
from models.recommendations import PreferencesModel
from datetime import datetime, timezone
from typing import Optional

class RecommenderCommands:
    def __init__(self, connection: Optional[ConnectionManager] = None):
        self.connection = connection or ConnectionManager()
        self.recommender_db = self.connection.get_recommender_db()
        self.ratings_collection = self.recommender_db['ratings']
        self.preferences_collection = self.recommender_db['preferences']

    async def get_ratings(self):
        ratings = []
        try:
            cursor = self.ratings_collection.find({}, {'_id': 0})
            async for document in cursor:
                ratings.append(document)
        except Exception as e:
            print({f'Error fetching ratings: {e}'})
            raise
        return ratings

    async def get_user_ratings(self, user_id: int):
        ratings = []
        try:
            cursor = self.ratings_collection.find({'userId': user_id}, {'_id': 0})
            async for document in cursor:
                ratings.append(document)
        except Exception as e:
            print(f'Error retrieving user ratings: {e}')
            raise
        return ratings

    async def update_preferences_collection(self, preferences: PreferencesModel):
        preferences_dict = preferences.model_dump()
        result = await self.preferences_collection.update_one({"userId": preferences_dict["userId"]}, {"$set": preferences_dict}, upsert=True)
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to add user preferences")
        return result
        