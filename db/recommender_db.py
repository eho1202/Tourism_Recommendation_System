from db.connections import recommender_db

ratings_collection = recommender_db['ratings']

async def get_ratings():
    ratings = []
    try:
        cursor = ratings_collection.find({}, {'_id': 0})
        async for document in cursor:
            ratings.append(document)
    except Exception as e:
        print({f'Error fetching ratings: {e}'})
        raise
    return ratings

async def get_user_ratings(user_id: int):
    ratings = []
    try:
        cursor = ratings_collection.find({'userId': user_id}, {'_id': 0})
        async for document in cursor:
            ratings.append(document)
    except Exception as e:
        print(f'Error retrieving user ratings: {e}')
        raise
    return ratings
