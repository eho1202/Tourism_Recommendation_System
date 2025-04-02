from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class TripDetails(BaseModel):
    tripId: str
    name: Optional[str] = None
    destination: Optional[str] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None

class UserModel(BaseModel):
    userId: int
    email: str
    password: str
    firstName: Optional[str]
    lastName: Optional[str]
    gender: Optional[str]
    ageGroup: Optional[int]
    location: Optional[str]
    job: Optional[str]
    preferences: Optional[Dict[str, List[str]]]
    savedPlaces: Optional[List[str]]
    savedTrips: Optional[Dict[str, TripDetails]]
    cluster: Optional[int]

class LoginRequestModel(BaseModel):
    email: str
    password: str
    
class RegisterRequestModel(BaseModel):
    userId: int
    email: str
    password: str

class SavedPlaceOperation(BaseModel):
    operation: str
    place: str

class SavedPlacesRequestModel(BaseModel):
    operations: List[SavedPlaceOperation]

class UserUpdateModel(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None

class UserResponseModel(BaseModel):
    userId: int
    email: str
    password: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    gender: Optional[str] = None
    ageGroup: Optional[int] = None
    location: Optional[str] = None
    job: Optional[str] = None
    preferences: Optional[Dict[str, List[str]]] = None
    savedPlaces: Optional[List[str]] = None
    savedTrips: Optional[Dict[str, TripDetails]] = None
    cluster: Optional[int]
