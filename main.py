import os
from dotenv import load_dotenv
from typing import Union

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import requests
import jsonify

from api import recommendations_router, users_router

app = FastAPI(title="Social Network based Recommender System for Tourists")

app.include_router(recommendations_router, prefix="/api")
app.include_router(users_router, prefix="/api")
