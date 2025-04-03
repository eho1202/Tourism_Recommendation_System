from pydantic import BaseModel

class LocationModel(BaseModel):
    locationId: int
    name: str
    country: str
    city: str
    description: str
    category: str
