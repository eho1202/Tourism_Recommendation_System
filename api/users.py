from fastapi import APIRouter, HTTPException
from db.user_db import get_user
from models.users import User

users_router = APIRouter()

@users_router.get("/users/{user_id}", response_model=User)
async def get_user_info(user_id: int):
    user = get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user