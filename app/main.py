from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.websocket import websocket_router
from app.core.logger import logger


app = FastAPI(
    title="Multilingual Voice Agent",
    description="Multilingual voice agent with conversation continuity",
    version="1.0.0",
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


@app.on_event("startup")
async def startup_event():
    logger.info("Multilingual Voice Agent started")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Multilingual Voice Agent stopped")


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