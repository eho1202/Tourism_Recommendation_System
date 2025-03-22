from pydantic import BaseModel
from typing import Optional, List

class UserModel(BaseModel):
    userId: int
    name: str
    email: str
    password: str
    preferences: Optional[List[str]]
    savedPlaces: Optional[List[str]]

class UserResponseModel(BaseModel):
    userId: int
    name: str
    email: str
    password: str
    preferences: Optional[List[str]]
    savedPlaces: Optional[List[str]]
