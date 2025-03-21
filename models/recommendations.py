from pydantic import BaseModel
from typing import List

class Rating(BaseModel):
    userId: int
    itemId: int
    rating: int

class Recommendations(BaseModel):
    name: str
    category: str
    country: str
    itemRating: float