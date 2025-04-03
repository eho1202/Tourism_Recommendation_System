from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime

class TripDetails(BaseModel):
    tripId: str
    name: Optional[str] = None
    destination: Optional[str] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    itinerary: Optional[List] = None

class ProfileModel(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    gender: Optional[str] = None
    ageGroup: Optional[int] = None
    location: Optional[str] = None
    job: Optional[str] = None

class UserModel(BaseModel):
    userId: int
    email: EmailStr
    password: str
    profile: Optional[ProfileModel] = None
    preferences: Optional[Dict[str, List[str]]] = None
    favourites: Optional[List[str]] = None
    savedTrips: Optional[Dict[str, TripDetails]] = None
    cluster: Optional[int] = None

class LoginRequestModel(BaseModel):
    email: EmailStr
    password: str
    
class RegisterRequestModel(BaseModel):
    userId: int
    email: EmailStr
    password: str

class SavedPlaceOperation(BaseModel):
    operation: str
    place: str

class FavouritesRequestModel(BaseModel):
    operations: List[SavedPlaceOperation]

class CredentialsUpdateModel(BaseModel):
    userId: int
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class ProfileUpdateModel(BaseModel):
    userId: int
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    gender: Optional[str] = None
    ageGroup: Optional[int] = None
    location: Optional[str] = None
    job: Optional[str] = None

class UserResponseModel(BaseModel):
    userId: int
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    profile: Optional[ProfileModel] = None
    preferences: Optional[Dict[str, List[str]]] = None
    favourites: Optional[List[str]] = None
    savedTrips: Optional[Dict[str, TripDetails]] = None
    cluster: Optional[int] = None
