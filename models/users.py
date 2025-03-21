from pydantic import BaseModel

class User(BaseModel):
    userId: int
    name: str
    email: str
    password: str
    preferences: list = []
    savedPlaces: list = []