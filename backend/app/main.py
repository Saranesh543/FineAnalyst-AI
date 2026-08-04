"""
Main Application Module
Initializes the FastAPI application, configures middleware, exception handlers, and routing.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.config.logging_config import setup_logging
from app.api.router import api_router
from app.utils.exceptions import AppException, app_exception_handler, global_exception_handler
from app.database.session import init_db

# Initialize logging
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    logger.info("Starting up FineAnalyst AI Backend...")
    # Initialize database tables
    await init_db()
    yield
    logger.info("Shutting down FineAnalyst AI Backend...")

# Create FastAPI application instance
app = FastAPI(
    title="FineAnalyst AI",
    description="Backend foundation for FineAnalyst AI.",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register global exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Include main API router
app.include_router(api_router, prefix="/api/v1")
