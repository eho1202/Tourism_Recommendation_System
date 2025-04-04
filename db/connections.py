import os
import logging
from typing import Optional
import motor.motor_asyncio as motor
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionManager:
    _instance = None  # For singleton pattern
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConnectionManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize database connections"""
        logger.info("   Connecting to MongoDB...")
        
        self.DB_USERNAME = os.getenv('DB_USERNAME')
        self.DB_PASSWORD_USER = os.getenv('DB_PASSWORD_USERS')
        self.DB_PASSWORD_LOCATION = os.getenv('DB_PASSWORD_LOCATION')
        self.USER_MONGO_URI = os.getenv('USER_MONGO_URI')
        self.LOCATION_MONGO_URI = os.getenv('LOCATION_MONGO_URI')
        
        self.MONGO_USER_URI = f"mongodb+srv://{self.DB_USERNAME}:{self.DB_PASSWORD_USER}@{self.USER_MONGO_URI}"
        self.MONGO_LOCATION_URI = f"mongodb+srv://{self.DB_USERNAME}:{self.DB_PASSWORD_LOCATION}@{self.LOCATION_MONGO_URI}"
        
        # Initialize clients
        self.user_client: Optional[motor.AsyncIOMotorClient] = None
        self.location_client: Optional[motor.AsyncIOMotorClient] = None
        
        # Initialize databases
        self.user_db: Optional[motor.AsyncIOMotorDatabase] = None
        self.recommender_db: Optional[motor.AsyncIOMotorDatabase] = None
        self.location_db: Optional[motor.AsyncIOMotorDatabase] = None
        
        self._connect()
    
    def _connect(self):
        """Establish database connections"""
        try:
            self.user_client = motor.AsyncIOMotorClient(self.MONGO_USER_URI)
            self.location_client = motor.AsyncIOMotorClient(self.MONGO_LOCATION_URI)
            
            self.user_db = self.user_client["users_db"]
            self.recommender_db = self.user_client["recommender_system"]
            self.location_db = self.location_client["LocationData"]
            
            logger.info("   Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f" Failed to connect to MongoDB: {e}")
            raise
    
    async def close(self):
        """Close all database connections"""
        if self.user_client:
            self.user_client.close()
        if self.location_client:
            self.location_client.close()
        logger.info("   MongoDB connections closed")
    
    def get_user_db(self):
        if self.user_db is None:
            raise RuntimeError("User database not initialized")
        return self.user_db
    
    def get_recommender_db(self):
        if self.recommender_db is None:
            raise RuntimeError("Recommender database not initialized")
        return self.recommender_db
    
    def get_location_db(self):
        if self.location_db is None:
            raise RuntimeError("Location database not initialized")
        return self.location_db