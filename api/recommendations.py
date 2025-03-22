from fastapi import APIRouter, HTTPException, Path, Query
from db.recommender_db import get_user_ratings # type: ignore
from models.recommendations import Rating, Recommendations
from typing import Dict, List, Optional

from algorithms import hybrid_recommender
from db import get_ratings

recommendations_router = APIRouter()

@recommendations_router.get("/get-user-ratings", response_model=List[Rating])
async def fetch_user_ratings(user_id: int):
    ratings = await get_user_ratings(user_id)
    if not ratings:
        raise HTTPException(status_code=404, detail="No ratings found")
    return ratings

@recommendations_router.get("/users/{user_id}/recommendations", response_model=List[Recommendations])
async def fetch_recommendations(
    user_id: int = Path(..., description="User ID"), 
    user_input: Optional[str] = Query(None, description="User input for recommendations (optional)"), 
    n: int = Query(10, description="Number of recommendations to return")
):
    recommendations = hybrid_recommender(user_id, user_input, n) # type: ignore
    return recommendations

# @app.get("/recommend", method=['GET'])
# def get_recommendations():
#     user_id = requests.args.get('user_id')
#     item_id = requests.args.get('item_id')
#     n = requests.args.get('n')
#     recommendations = hybrid_recommender(user_id, item_id, n)
#     return jsonify(recommendations=recommendations.tolist())

# async def get_all_ratings() -> List[Dict]:
#     try:
#         ratings = []
#         ratings = await get_ratings()
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#     return ratings