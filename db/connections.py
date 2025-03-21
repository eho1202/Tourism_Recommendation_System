from pymongo import MongoClient
import os
import logging

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("   Connecting to MongoDB...")

DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD_USERS')
USER_MONGO_URI = os.getenv('USER_MONGO_URI')
MONGO_URI = f"mongodb+srv://{DB_USERNAME}:{DB_PASSWORD}@{USER_MONGO_URI}"

client = MongoClient(MONGO_URI)

user_db = client["users_db"]
recommender_db = client["recommender_system"]
