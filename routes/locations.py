from fastapi import APIRouter, HTTPException
from typing import List, Optional

from models.locations import LocationModel
from db.location_db import LocationCommands

locations_router = APIRouter(
    prefix="/locations",
    tags=["locations"],
    responses={404: {"description": "Location does not exist."}},
)

location_db = LocationCommands()

@locations_router.get("/", response_model=LocationModel)
async def fetch_location_by_id(locationId: int):
    location_detail = await location_db.get_location_by_id(locationId)
    if location_detail is None:
        raise HTTPException(status_code=404, detail="Location not found")
    
    location = LocationModel(**location_detail)
    return location