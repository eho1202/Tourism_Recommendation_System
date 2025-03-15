from db.connections import user_db

users_collection = user_db['users']

def get_user(user_id):
    return users_collection.find_one({'user_id': user_id}, {'_id': 0})