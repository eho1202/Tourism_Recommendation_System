import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import recommendations_router, users_router
from algorithms.collaborative_filter import fetch_and_process_ratings as fetch_cf_ratings
from algorithms.collaborative_filter import load_model as load_cf_model
from algorithms.collaborative_filter import load_tourism_data as load_cf_tourism_data
from algorithms.content_based_filter import load_model as load_cb_model
from algorithms.content_based_filter import initialize
from algorithms.hybrid_filter import fetch_and_process_ratings as fetch_hybrid_ratings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("   Starting Lifespan...")
    load_cf_tourism_data()
    await initialize()
    await fetch_cf_ratings()
    load_cf_model()
    load_cb_model()
    await fetch_hybrid_ratings()
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
