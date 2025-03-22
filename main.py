import os
import asyncio
from dotenv import load_dotenv
from typing import Union

from contextlib import asynccontextmanager
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from api import recommendations_router, users_router
from algorithms.collaborative_filter import fetch_and_process_ratings as fetch_cf_ratings
from algorithms.hybrid_filter import fetch_and_process_ratings as fetch_hybrid_ratings

@asynccontextmanager
async def lifespan(app: FastAPI):
    await fetch_cf_ratings()
    await fetch_hybrid_ratings()
    yield

app = FastAPI(title="Social Network based Recommender System for Tourists", lifespan=lifespan)

app.include_router(recommendations_router, prefix="/api")
app.include_router(users_router, prefix="/api")
