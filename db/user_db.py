from db.connections import user_db
from models.users import UserModel

users_collection = user_db['users']

def get_user_id(user_id):
    return users_collection.find_one({'userId': user_id}, {'_id': 0})

def get_user(email):
    return users_collection.find_one({'email': email}, {'_id': 0})

def get_last_user():
    return users_collection.find_one(sort=[("userId", -1)], projection={"userId": 1})

async def add_user(user: UserModel):
    await users_collection.insert_one(user.model_dump())
    return {'message': 'User registered successfully'}

async def update_user(user_id: int, user: UserModel):
    user_dict = user.model_dump(exclude_unset=True, exclude={"userId"})
    result = await users_collection.update_one({"userId": user_id}, {"$set": user_dict})
    return result

async def delete_user(user_id):
    await users_collection.delete_one({"userId": user_id})
    return {'message': 'User sucessfully removed'}