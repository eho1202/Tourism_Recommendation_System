from fastapi import HTTPException
from typing import Optional

from db.connections import ConnectionManager
from models.recommendations import PreferencesModel, RatingModel

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
    
    async def add_user_rating(self, new_rating: RatingModel):
        rating_dict = new_rating.model_dump() 
        result = await self.ratings_collection.insert_one(rating_dict)
        
        if result.inserted_id is None:
            raise HTTPException(status_code=500, detail="Failed to add rating")
        
        return {"message": "Rating added successfully."}


    async def update_user_rating(self, new_rating: RatingModel):
        rating_dict = new_rating.model_dump()
        result = await self.ratings_collection.update_one(
            {"userId": rating_dict["userId"], "locationId": rating_dict["locationId"]},
            {"$set": rating_dict},
            upsert=True
        )

        # Check if the update was successful
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update rating")

        return {"message": "Rating updated successfully."}
    
    async def delete_user_rating(self, user_id: int, item_id: int):
        is_rating_exist = await self.ratings_collection.find_one({"userId": user_id, "locationId": item_id})
        
        if not is_rating_exist:
            raise HTTPException(status_code=404, detail="Could not find rating")
        
        delete_result = await self.ratings_collection.delete_one(is_rating_exist)
        
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=500, detail="Failed to delete rating")
        
        return {"message": "Successfully deleted user's rating."}

    async def update_preferences_collection(self, preferences: PreferencesModel):
        preferences_dict = preferences.model_dump()
        result = await self.preferences_collection.update_one({"userId": preferences_dict["userId"]}, {"$set": preferences_dict}, upsert=True)
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to add user preferences")
        return result
        
    async def get_location_ratings(self, locationId: int):
        ratings = []
        try:
            cursor = self.ratings_collection.find({'locationId': locationId}, {'_id': 0})
            async for document in cursor:
                ratings.append(document)
        except Exception as e:
            print(f'Error retrieving user ratings: {e}')
            raise
        return ratings