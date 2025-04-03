from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Optional

from db.recommender_db import RecommenderCommands
from models.recommendations import RatingModel, RecommendationsModel, RecommendationsRequest
from algorithms import HybridFilter

recommender_db = RecommenderCommands()
hybrid = HybridFilter()

recommendations_router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
    responses={404: {"description": "No recommendations found."}},
)

@recommendations_router.post("/", response_model=List[RecommendationsModel])
async def fetch_user_recommendations(request: Request, request_body: RecommendationsRequest):
    hybrid = request.app.state.recommender
    recommendations = await hybrid.get_recommendations(request_body.userId, request_body.userInput, request_body.n)
    return recommendations

@recommendations_router.get("/ratings", response_model=List[RatingModel])
async def fetch_user_explicit_ratings(user_id: int):
    ratings = await recommender_db.get_user_ratings(user_id)
    if not ratings:
        raise HTTPException(status_code=404, detail="No ratings found")
    return ratings

# TODO: Add function to add more user ratings if user saves any locations
@recommendations_router.post("/ratings")
async def add_user_rating(new_rating: RatingModel):
    result = await recommender_db.add_user_rating(new_rating)
    return result

@recommendations_router.patch("/ratings")
async def update_user_rating(new_rating: RatingModel):
    result = await recommender_db.update_user_rating(new_rating)
    return result

@recommendations_router.delete("/ratings")
async def delete_user_rating(user_id: int, item_id: int):
    result = await recommender_db.delete_user_rating(user_id, item_id)
    return result