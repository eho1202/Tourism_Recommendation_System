from fastapi import HTTPException

from db.connections import user_db
from models.users import UserModel

users_collection = user_db['users']

async def get_user_id(user_id):
    return await users_collection.find_one({'userId': user_id}, {'_id': 0})

async def get_user(email):
    user = await users_collection.find_one({'email': email}, {'_id': 0})
    return user

async def get_last_user():
    user = await users_collection.find_one(sort=[("userId", -1)], projection={"userId": 1})
    return user

async def add_user(user: UserModel):
    user_dict = user.model_dump(exclude_unset=True, exclude={"savedPlaces", "preferences"})
    result = await users_collection.insert_one(user_dict)
    if result.inserted_id is None:
        raise HTTPException(status_code=500, detail="Failed to add user")
    return {'message': 'User registered successfully'}

async def update_personal_details(user_id: int, user: UserModel):
    user_dict = user.model_dump(exclude_unset=True, exclude={"userId", "preferences", "savedPlaces"})
    result = await users_collection.update_one({"userId": user_id}, {"$set": user_dict})
    return result

# # TODO: Implement the following functions
# async def update_preferences(user_id: int, preferences: dict):
#     return await users_collection.update_one({"userId": user_id}, {"$set": {"preferences": preferences['preferences']}})

# async def update_user_survey(user_id: int, survey: dict):
#     return await users_collection.update_one({"userId": user_id}, {"$set": {"survey": survey}})

# async def update_saved_places(user_id: int, saved_places: dict):
#     if saved_places["operation"] == "add":
#         await users_collection.update_one({"userId": user_id}, {"$push": {"$each": saved_places["places"]}})
#     elif saved_places["operation"] == "remove":
#         await users_collection.update_one({"userId": user_id}, {"$pull": {"$in": saved_places["places"]}})
#     return {'message': 'Saved places updated successfully'}

# async def add_trip(user_id: int, trip: TripRequest):
#     trip_details = {
#         "name": trip.name,
#         "location": trip.location,
#         "date": trip.date
#     }
#     return await users_collection.update_one({"userId": user_id}, {"$set": {f"trips.{trip.trip_id}": trip_details}})

async def delete_user(user_id):
    await users_collection.delete_one({"userId": user_id})
    return {'message': 'User sucessfully removed'}