from fastapi import APIRouter, HTTPException, Path, Query
from db.recommender_db import RecommenderCommands
from models.recommendations import RatingModel, RecommendationsModel
from typing import List, Optional

from algorithms import HybridFilter

recommender_db = RecommenderCommands()
hybrid = HybridFilter()

recommendations_router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
    responses={404: {"description": "No recommendations found."}},
)

# @recommendations_router.get("/", response_model=List[RecommendationsModel])

@recommendations_router.get("/get-user-ratings/{user_id}", response_model=List[RatingModel])
async def fetch_user_ratings(user_id: int):
    ratings = await recommender_db.get_user_ratings(user_id)
    if not ratings:
        raise HTTPException(status_code=404, detail="No ratings found")
    return ratings

@recommendations_router.get("/{user_id}", response_model=List[RecommendationsModel])
async def fetch_user_recommendations(user_id: int, user_input: Optional[str] = Query(None), n: int = Query(10)):
    recommendations = await hybrid.hybrid_recommender(user_id, user_input, n)
    return recommendations