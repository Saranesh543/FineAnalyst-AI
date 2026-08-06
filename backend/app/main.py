"""
Main Application Module
Initializes the FastAPI application, configures middleware, exception handlers, and routing.
"""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.config.logging_config import setup_logging
from app.api.router import api_router
from app.utils.exceptions import AppException, app_exception_handler, global_exception_handler
from app.database.session import init_db
from app.database.seeder import seed_database

# Initialize logging
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    import app.api.analyze as _analyze_mod
    import app.services.sql_generator_service as _sqlgen_mod
    import app.database.seeder as _seeder_mod

    logger.info("=== FineAnalyst AI Backend Starting ===")
    logger.info("  main.py       : %s", os.path.abspath(__file__))
    logger.info("  analyze.py    : %s", os.path.abspath(_analyze_mod.__file__))
    logger.info("  sql_generator : %s", os.path.abspath(_sqlgen_mod.__file__))
    logger.info("  seeder        : %s", os.path.abspath(_seeder_mod.__file__))
    logger.info("  GROQ_MODEL    : %s", settings.GROQ_MODEL)
    logger.info("  DATABASE_URL  : %s", settings.DATABASE_URL)
    logger.info("  ENVIRONMENT   : %s", settings.ENVIRONMENT)

    # Step 1: Create ORM tables (no-op if already exist)
    await init_db()

    # Step 2: Seed demo data if database is empty (handles fresh Render deployments)
    seed_database()

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
    allow_origins=[
        "http://localhost:3000",
        "https://fine-analyst-ai.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register global exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Include main API router
app.include_router(api_router, prefix="/api/v1")
