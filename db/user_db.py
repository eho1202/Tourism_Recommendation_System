from db.connections import user_db
from models.users import User

users_collection = user_db['users']

def get_user_id(user_id):
    return users_collection.find_one({'userId': user_id}, {'_id': 0})

def get_user(email):
    return users_collection.find_one({'email': email}, {'_id': 0})

def get_last_user():
    return users_collection.find_one(sort=[("userId", -1)], projection={"userId": 1})

# TODO: Add function to update saved places
async def add_user(user: User):
    await users_collection.insert_one(user.model_dump())
    return {'message': 'User registered successfully'}

async def delete_user(user_id):
    await users_collection.delete_one({"userId": user_id})
    return {'message': 'User sucessfully removed'}