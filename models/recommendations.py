from pydantic import BaseModel, field_validator
import math
from typing import List, Optional
from datetime import datetime

class RatingModel(BaseModel):
    userId: int
    locationId: int
    rating: int
    
class RecommendationsRequest(BaseModel):
    userId: Optional[int] = None
    userInput: Optional[str] = None
    n: int = 20

class RecommendationsModel(BaseModel):
    locationId: int
    name: str
    category: Optional[List[str]] = None
    address: str
    city: str
    country: str
    description: Optional[str] = None
    rating: Optional[float] = None
    num_ratings: Optional[int] = None

class PreferencesModel(BaseModel):
    userId: int
    environments: List[str]
    food: List[str]
    activities: List[str]