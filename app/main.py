from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.websocket import websocket_router
from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Multilingual Voice Agent starting...")
    logger.info("Multilingual Voice Agent started.")
    yield
    logger.info("Multilingual Voice Agent stopping...")
    logger.info("Multilingual Voice Agent stopped.")


app = FastAPI(
    title="Multilingual Voice Agent",
    description="Multilingual voice agent with conversation continuity and stable session lifecycle",
    version="1.0.0",
    lifespan=lifespan,
)

# Frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API
app.include_router(router)

# Realtime voice WebSocket
app.include_router(websocket_router)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Multilingual Voice Agent",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }