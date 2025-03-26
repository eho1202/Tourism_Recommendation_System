from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class TripRequest(BaseModel):
    trip_id: str
    name: str
    location: str
    date: str

class TripDetails(BaseModel):
    trip_id: str
    name: Optional[str] = None
    location: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None

class UserModel(BaseModel):
    userId: int
    name: str
    email: str
    password: str
    preferences: Optional[List[str]]
    savedPlaces: Optional[List[str]]
    # trips: Dict[str, TripDetails] = Field(default_factory=dict)

class LoginRequestModel(BaseModel):
    email: str
    password: str

class UserResponseModel(BaseModel):
    userId: int
    name: str
    email: str
    password: str
    preferences: Optional[List[str]]
    savedPlaces: Optional[List[str]]
    trips: Dict[str, TripDetails] = Field(default_factory=dict)
