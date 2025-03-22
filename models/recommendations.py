from pydantic import BaseModel

class RatingModel(BaseModel):
    userId: int
    itemId: int
    rating: int

class RecommendationsModel(BaseModel):
    name: str
    category: str
    country: str
    itemRating: float