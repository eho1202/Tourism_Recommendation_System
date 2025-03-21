from fastapi import APIRouter, HTTPException
from db.recommender_db import get_user_ratings # type: ignore
from models.recommendations import Rating, Recommendations
from typing import List, Optional

from algorithms import hybrid_recommender

recommendations_router = APIRouter()

@recommendations_router.get("/get-user-ratings", response_model=List[Rating])
def fetch_user_ratings(user_id: int):
    ratings = get_user_ratings(user_id)
    if not ratings:
        raise HTTPException(status_code=404, detail="No ratings found")
    return ratings

@recommendations_router.get("/recommendations", response_model=List[Recommendations])
def fetch_recommendations(user_id: int, user_input: str | None = None, n: int = 10):
    recommendations = hybrid_recommender(user_id, user_input, n) # type: ignore
    return recommendations

# @app.get("/recommend", method=['GET'])
# def get_recommendations():
#     user_id = requests.args.get('user_id')
#     item_id = requests.args.get('item_id')
#     n = requests.args.get('n')
#     recommendations = hybrid_recommender(user_id, item_id, n)
#     return jsonify(recommendations=recommendations.tolist())

# @app.get("/ratings", method=['GET'], response_model=List[RatingResponse])
# async def get_ratings():
#     try:
#         ratings = list(ratings_collection.find({}, {'_id': 0}))
#         if not ratings:
#             return "No ratings found"
#         return ratings
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))