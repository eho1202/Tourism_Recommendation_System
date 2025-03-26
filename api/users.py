import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext

from db.user_db import get_user, add_user, get_last_user, delete_user, get_user_id, update_personal_details
from models.users import UserModel, UserResponseModel, LoginRequestModel

users_router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "User does not exist."}},
)

SECRET_KEY = os.urandom(16)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta=None): # type: ignore
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

@users_router.post("/auth/login")
async def login(user: LoginRequestModel):
    is_user_exist = await get_user(user.email)
    if not is_user_exist or not pwd_context.verify(user.password, is_user_exist['password']):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user.email})
    return {'access_token': access_token, 'token_type': 'bearer'}
    
@users_router.post("/auth/register")
async def register_user(user: UserModel):
    is_user_exist = await get_user(user.email)
    if is_user_exist is not None:
        raise HTTPException(status_code=403, detail="User already exists")
    # Grab the userId of the last user
    last_user = await get_last_user()
    if last_user:
        user.userId = last_user['userId'] + 1
    
    # Hash the password
    user.password = hash_password(user.password)
    
    new_user = await add_user(user)
    return new_user

@users_router.get("/get-user-details/{user_id}", response_model=UserModel)
async def get_user_info(user_id: int):
    user = await get_user_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@users_router.patch("/{user_id}", response_model=UserResponseModel)
async def update_user_details(user_id: int, user: UserModel):
    result = await update_personal_details(user_id, user)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    return result

# # TODO: Implement functions for updating preferences, saved places, survey, and trips
# @users_router.patch("/{user_id}/update-preferences")
# async def update_user_preferences(user_id: int, preferences: dict):
#     result = await update_preferences(user_id, preferences)
#     return result

# @users_router.patch("/{user_id}/update-saved-places")
# async def update_user_saved_places(user_id: int, saved_places: dict):
#     result = await update_saved_places(user_id, saved_places)
#     return result

@users_router.delete("/remove-user/{user_id}")
async def remove_user(user_id: int):
    result = await delete_user(user_id)
    return result
