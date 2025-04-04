from pydantic import BaseModel

class LocationModel(BaseModel):
    locationId: int
    name: str
    address: str
    city: str
    country: str
    description: str
    category: str
