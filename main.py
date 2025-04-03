import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import recommendations_router, users_router
from algorithms.collaborative_filter import CollaborativeFilter
from algorithms.content_based_filter import ContentBasedFilter
from algorithms.hybrid_filter import HybridFilter
from algorithms.k_means_cluster import UserClusterer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

clusterer = UserClusterer()
cf = CollaborativeFilter()
cb = ContentBasedFilter()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("   Starting Lifespan...")
    hybrid = HybridFilter()
    await hybrid.initialize()
    
    app.state.recommender = hybrid
    yield

app = FastAPI(title="Social Network based Recommender System for Tourists", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

app.include_router(recommendations_router)
app.include_router(users_router)
