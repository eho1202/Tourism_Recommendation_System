import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext

from db.recommender_db import RecommenderCommands
from db.user_db import UserCommands
from models.users import UserModel, CredentialsUpdateModel, UserResponseModel, LoginRequestModel, RegisterRequestModel, TripDetails, FavouritesRequestModel, ProfileModel, ProfileUpdateModel
from models.recommendations import PreferencesModel

users_router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "User does not exist."}},
)

SECRET_KEY = os.urandom(16)

user_db = UserCommands()
recommender_db = RecommenderCommands()

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
    is_user_exist = await user_db.get_user_by_email(user.email)
    if not is_user_exist or not pwd_context.verify(user.password, is_user_exist['password']):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user.email})
    return {'access_token': access_token, 'token_type': 'bearer', 'user_id': is_user_exist['userId']}
    
@users_router.post("/auth/register")
async def register_user(user: RegisterRequestModel):
    """_Register new users_

    Args:
        user (RegisterRequestModel): Takes `userId`, `email`, and `password` as input

    Raises:
        HTTPException: status_code=`403`, detail=`User already exists`

    Returns:
        _type_: _description_
    """
    is_user_exist = await user_db.get_user_by_email(user.email)
    if is_user_exist is not None:
        raise HTTPException(status_code=403, detail="User already exists")
    # Grab the userId of the last user
    last_user = await user_db.get_last_user()
    if last_user:
        user.userId = last_user['userId'] + 1
    
    # Hash the password
    hashed_password = hash_password(user.password)
    
    new_user = UserModel(
        userId=user.userId,
        email=user.email,
        password=hashed_password,
        profile=ProfileModel(
            firstName=None,
            lastName=None,
            gender=None,
            ageGroup=None,
            location=None,
            job=None,   
        ),
        preferences=None,
        favourites=None,
        savedTrips=None,
        cluster=None,
    )
    
    confirm_user = await user_db.add_user(new_user)
    return confirm_user

@users_router.get("/get-user-details", response_model=UserModel)
async def get_user_info(user_id: int):
    user_data = await user_db.get_user_by_id(user_id)
    if user_data is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = UserModel(**user_data)
    return user

@users_router.patch("/credentials", response_model=UserResponseModel)
async def update_user_credentials(credentials: CredentialsUpdateModel):
    update_data = credentials.model_dump(exclude_unset=True, exclude_none=True)
    
    # Hash password if provided
    if 'password' in update_data:
        update_data['password'] = hash_password(update_data['password'])
    
    # Check for email uniqueness if email is being updated
    if 'email' in update_data:
        existing = await user_db.get_user_by_email(update_data['email'])
        if existing and existing['userId'] != credentials.userId:
            raise HTTPException(
                status_code=409,
                detail="Email already in use by another account"
            )
    
    # Perform update
    result = await user_db.update_credentials(credentials.userId, update_data)
    
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result

@users_router.patch("/profile", response_model=UserResponseModel)
async def update_user_details(profile: ProfileUpdateModel):
    """Updates user information in Profiles"""
    existing_user = await user_db.get_user_by_id(profile.userId)
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prepare update data
    update_data = profile.model_dump(exclude_unset=True, exclude_none=True, exclude={"userId"})
    
    # Perform update
    updated_user = await user_db.update_personal_details(user_id=profile.userId, profile_data=update_data)
    
    if not updated_user:
        raise HTTPException(status_code=500, detail="Failed to update profile")
    
    # Ensure profile exists in response
    if "profile" not in updated_user:
        updated_user["profile"] = {}
    
    return UserResponseModel(**updated_user)

@users_router.delete("/remove-user")
async def remove_user(user_id: int):
    result = await user_db.delete_user(user_id)
    return result

@users_router.patch("/update-preferences")
async def update_user_preferences(user_id: int, preferences: PreferencesModel):
    """Updates user's preferences
    
        Example request body:\n
        Requires `user_id`
        ```
        {
            "userId": 0,
            "environments": [
                "cold"
            ],
            "food": [
                "japanese"
            ],
            "activities": [
                "museums",
                "skiing"
            ]
        }
        ```
    """
    preferences.userId = user_id
    user_result = await user_db.update_preferences(user_id, preferences)
    preferences_result = await recommender_db.update_preferences_collection(preferences)
    
    if user_result and preferences_result:
        return {"message": "User's preferences have been successfully updated."}
    elif not user_result:
        raise HTTPException(status_code=400, detail="Failed to update user information.")
    elif not preferences_result:
        raise HTTPException(status_code=400, detail="Failed to update preferences collection.")

@users_router.patch("/update-favourites")
async def update_user_favourites(user_id: int, favourites: FavouritesRequestModel):
    """_Update user's saved places, not in trips_

    Args:
    
        user_id (int): User ID
        
        saved_places (dict): Includes operations of what places to add or remove

    Example request body:\n
    ```
    {
        "operations": [
            {"operation": "add", "place": "London Eye"},
            {"operation": "add", "place": "Eiffel Tower"},
            {"operation": "remove", "place": "Statue of Liberty"}
        ]
    }
    ```
    Raises:
        HTTPException: status_code=`400`, detail=`Failed to update user saved places.`
    """
    for operation in favourites.operations:
        result = await user_db.update_favourites(user_id, {"operation": operation.operation, "place": operation.place})
    if not result:
        raise HTTPException(status_code=400, detail="Failed to update user saved places.")
    return {"message": "All operations completed successfully."}

@users_router.post("/add-trip")
async def add_user_trip(user_id: int, trip: TripDetails):
    """Add user trip when user creates a trip
    
        Example request body:\n
        Requires `user_id`
        ```
        {
            tripId: "trip_[randomized_numbers]",
            name: "Toronto Adventure",
            destination: "Toronto",
            startDate: "2025-04-01",
            endDate: "2025-04-15"
        }
        ```
    """
    result = await user_db.add_trip(user_id, trip)
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Failed to add trip. Use may not exist.")
    return {"message": f"Trip {trip.tripId} added successfully"}
        

@users_router.patch("/update-trip")
async def update_user_trip(user_id: int, trip: TripDetails):
    """Update user trip when user changes trip information
    
        Example request body:\n
        Requires `user_id`
        Note: This example changes the startDate and endDate, it always requires the `tripId` inside body
        ```
        {
            tripId: "trip_[randomized_numbers]",
            startDate: "2025-05-02",
            endDate: "2025-06-02"
        }
        ```
    """
    result = await user_db.update_trip(user_id, trip)
    return result

@users_router.delete("/delete-trip")
async def delete_user_trip(user_id: int, trip_id: str):
    """Deletes user's trip"""
    result = await user_db.delete_trip(user_id, trip_id)
    return result
    