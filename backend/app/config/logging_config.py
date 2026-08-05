"""
Logging Configuration Module
Sets up standard logging for the application.
"""
import logging
import sys
import os
from app.config.settings import settings

def setup_logging():
    """
    Configure global logging settings for the application.
    """
    logging_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Disable file logging on Render as it causes directory errors and Render captures stdout automatically.
    # Preserve file logging for local development.
    if not os.environ.get("RENDER") and settings.ENVIRONMENT != "production":
        os.makedirs("logs", exist_ok=True)
        handlers.append(logging.FileHandler("logs/app.log"))
        
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers
    )
    
    # Set levels for noisy libraries if necessary
    logging.getLogger("uvicorn.access").setLevel(logging_level)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return logging.getLogger(__name__)

logger = setup_logging()
