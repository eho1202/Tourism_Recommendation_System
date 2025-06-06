from fastapi import HTTPException
from pymongo import ReturnDocument
from typing import Optional

from db.connections import ConnectionManager
from models.users import UserModel, CredentialsUpdateModel, TripDetailsModel, FavouritesRequestModel
from models.recommendations import PreferencesModel

class UserCommands:
    def __init__(self, connection: Optional[ConnectionManager] = None):
        self.connection = connection or ConnectionManager()
        self.user_db = self.connection.get_user_db()
        self.users_collection = self.user_db['users']

    def get_105_users(self):
        """Grabs the first 105 users for clustering"""
        users = self.users_collection.find({'userId': {'$gte': 0, '$lte': 104}}, {'_id': 0})
        return users
    
    def get_all_users(self):
        """Grabs all the users in the db for clustering"""
        users = self.users_collection.find({}, {'_id': 0})
        return users
    
    async def get_cluster_peers(self, cluster):
        """Gets cluster peers based on cluster number"""
        user_ids = []
        cursor = self.users_collection.find({'cluster': cluster}, {'_id': 0})
        async for document in cursor:
            user_ids.append(document['userId'])
        return user_ids
    
    async def update_user_cluster(self, user_id, cluster):
        """Adds the cluster value for new users"""
        result = await self.users_collection.update_one({'userId': user_id}, {'$set': {'cluster': cluster}})
        return result

    async def get_user_by_id(self, user_id):
        return await self.users_collection.find_one({'userId': user_id}, {'_id': 0})

    async def get_user_by_email(self, email):
        user = await self.users_collection.find_one({'email': email}, {'_id': 0})
        if user:
            user['userId'] = str(user['userId'])
        return user
    
    async def get_new_user_id(self):
        last_user_id = await self.users_collection.find_one({}, sort=[("userId", -1)], projection={"userId": 1, "_id": 0})
        new_user_id = last_user_id["userId"] + 1 if last_user_id else None
        return new_user_id

    async def add_user(self, user: UserModel):
        user_dict = user.model_dump(exclude_unset=True)
        
        result = await self.users_collection.insert_one(user_dict)
        if result.inserted_id is None:
            raise HTTPException(status_code=500, detail="Failed to add user")
        
        # Check if the user was inserted successfully
        inserted_user = await self.users_collection.find_one({"_id": result.inserted_id}, {"_id": 0})
        if not inserted_user:
            raise HTTPException(status_code=500, detail="Failed to retrieve inserted user")
        
        return inserted_user
    
    async def update_credentials(self, user_id: int, credentials_data: dict):
        current_user = await self.users_collection.find_one({"userId": user_id})
        if not current_user:
            return None
        
        # Perform the update - $set will only modify the specified fields
        update_result = await self.users_collection.find_one_and_update({"userId": user_id}, {"$set": credentials_data}, return_document=ReturnDocument.AFTER)
        return update_result

    async def update_personal_details(self, user_id: int, profile_data: dict) -> Optional[dict]:
        """
        Updates a user's profile with new data (atomic update).
        Args:
            user_id: The user's ID to update.
            profile_data: Fields to update (e.g., {"location": "Canada", "job": "Engineer"}).
        Returns:
            The updated user document (without _id), or None if failed.
        """
        if not profile_data:  # No updates to apply
            return None

        # Atomic update (only modifies provided fields)
        updated_user = await self.users_collection.find_one_and_update(
            {"userId": user_id},
            {"$set": {"profile": profile_data}},  # Overwrites only specified keys in profile
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0}  # Exclude _id in response
        )
        return updated_user

    async def update_preferences(self, user_id: int, preferences: PreferencesModel):
        preferences_dict = preferences.model_dump(exclude={"userId"})
        result = await self.users_collection.update_one({"userId": user_id}, {"$set": {"preferences": preferences_dict}})
        return result

    # TODO: If operation is add, add new rating (rating=random.randint(1, 3))
    async def update_favourites(self, user_id: int, operation_data: dict):
        if operation_data["operation"] == "add":
            await self.users_collection.update_one(
                {"userId": user_id},
                [{
                    "$set": {
                        "favourites": {
                            "$cond": [
                                {"$ifNull": ["$favourites", False]},  # Check if field exists
                                {"$setUnion": ["$favourites", [operation_data["place"]]]},  # Add to existing array
                                [operation_data["place"]]  # Create new array if null/missing
                            ]
                        }
                    }
                }],
                upsert=True  # Optional: create doc if doesn't exist
            )
        elif operation_data["operation"] == "remove":
            await self.users_collection.update_one(
                {"userId": user_id},
                {"$pull": {"favourites": operation_data["place"]}}
            )
        return {'message': 'Saved places updated successfully'}

    async def add_trip(self, user_id: int, trip: TripDetailsModel):
        trip_dict = trip.model_dump()
        trip_id = trip_dict.pop("tripId")
        result = await self.users_collection.update_one({"userId": user_id}, {"$set": {f"savedTrips.{trip_id}": trip_dict}})
        return result

    async def update_trip(self, user_id: int, trip: TripDetailsModel):
        trip_id = trip.tripId
        user = await self.users_collection.find_one({"userId": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="Could not find user.")
        if trip_id not in user["savedTrips"]:
            raise HTTPException(status_code=404, detail=f"Could not find trip_id {trip_id}")
        trip_dict = trip.model_dump(exclude={"tripId"}, exclude_unset=True)
        
        update_query = {"$set": {}}
        for field, value in trip_dict.items():
            update_query["$set"][f"savedTrips.{trip_id}.{field}"] = value
        
        result = await self.users_collection.update_one({"userId": user_id}, update_query)
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail=f"Could not make changes to trip {trip_id}.")
        return {"message": f"Trip {trip_id} updated successfully."}
    
    # TODO: Add function to update savedTripItems, then if operation is add, add new rating (rating=random.randint(4, 5))
    async def update_trip_locations(self, user_id: int, trip_items):
        print("omg")
      
    async def delete_trip(self, user_id, trip_id):
        result = await self.users_collection.update_one({"userId": user_id}, {"$unset": {f"savedTrips.{trip_id}": ""}})
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail=f"Could not delete trip {trip_id}.")
        return{"message": f"Trip {trip_id} deleted successfully."}

    async def delete_user(self, user_id):
        await self.users_collection.delete_one({"userId": user_id})
        return {'message': 'User sucessfully removed'}
