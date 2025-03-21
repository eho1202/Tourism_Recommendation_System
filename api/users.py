import os
import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import RedirectResponse,HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login import LoginManager
from fastapi_login.exceptions import InvalidCredentialsException
from passlib.context import CryptContext

from db.user_db import get_user, add_user, get_last_user, delete_user, get_user_id
from models.users import User

users_router = APIRouter()

SECRET_KEY = os.urandom(16)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta=None): # type: ignore
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=1)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

@users_router.post("/auth/login")
async def login(user: User):
    is_user_exist = await get_user(user.email)
    if not is_user_exist or not pwd_context.verify(user.password, is_user_exist['password']):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user.email})
    return {'access_token': access_token, 'token_type': 'bearer'}
    
@users_router.post("/auth/register")
async def register_user(user: User):
    is_user_exist = get_user(user.email)
    if is_user_exist:
        raise HTTPException(status_code=403, detail="User already exists")
    
    # Grab the userId of the last user
    last_user = await get_last_user()
    if last_user:
        user.userId = last_user['userId'] + 1
    
    # Hash the password
    user.password = hash_password(user.password)
    
    new_user = add_user(user)
    return new_user

@users_router.post("/users/remove-user/{user_id}")
async def remove_user(user_id: int):
    result = delete_user(user_id)
    return result

@users_router.get("/users/get-user-info/{user_id}", response_model=User)
async def get_user_info(user_id: int):
    user = await get_user_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# TODO: Add endpoint to allow user to save destinations
# @users_router.post("/users/append-saved-places")
# async def append_place(user_id: int, saved_places):
    