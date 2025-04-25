from pydantic import BaseModel
from typing import Optional, List

class LocationModel(BaseModel):
    locationId: int
    name: str
    category: Optional[List[str]] = None
    address: str
    city: str
    country: str
    description: Optional[str] = None
    rating: Optional[float] = None
    num_ratings: Optional[float] = None
