from db.connections import recommender_db

ratings_collection = recommender_db['ratings']

def get_ratings():
    ratings = []
    cursor = ratings_collection.find({}, {'_id': 0})
    for document in cursor:
        ratings.append(document)
    return ratings