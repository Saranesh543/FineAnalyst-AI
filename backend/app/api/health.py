"""
Health Check API Module
Provides a simple endpoint to verify the API is running.
"""
from fastapi import APIRouter
from app.config.settings import settings

router = APIRouter()

@router.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.
    Returns the status and current environment.
    """
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT
    }
