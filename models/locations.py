from pydantic import BaseModel
from typing import Optional

class LocationModel(BaseModel):
    locationId: int
    name: str
    category: str
    address: str
    city: str
    country: str
    description: str
    rating: Optional[float] = None
