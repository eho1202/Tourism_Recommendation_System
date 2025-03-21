from pydantic import BaseModel

class Location(BaseModel):
    locationId: int
    name: str
    country: str
    city: str
    description: str
    category: str
