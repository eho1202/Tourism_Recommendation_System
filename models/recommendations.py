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
    locationId: int
    name: str
    category: str
    address: str
    city: str
    country: str
    description: str
    rating: Optional[float] = None

class PreferencesModel(BaseModel):
    userId: int
    environments: List[str]
    food: List[str]
    activities: List[str]