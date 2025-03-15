from pydantic import BaseModel
from typing import List

class Rating(BaseModel):
    user_id: int
    item_name: str
    rating: int

class Recommendations(BaseModel):
    name: str
    category: str
    country: str
    itemRating: float