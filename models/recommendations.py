from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class RatingModel(BaseModel):
    userId: int
    itemId: int
    rating: int
    
class RecommendationsRequest(BaseModel):
    userId: Optional[int] = None
    userInput: Optional[str] = None
    n: int = 10

class RecommendationsModel(BaseModel):
    name: str
    category: str
    country: str
    itemRating: float

class PreferencesModel(BaseModel):
    userId: int
    environments: List[str]
    food: List[str]
    activities: List[str]