from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import setup_logging
from app.core.config import settings
from app.api.routes import router

setup_logging()

app = FastAPI(
    title="TripPilot AI",
    description="Agentic Travel Operations Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "service": "trippilot-api"}
