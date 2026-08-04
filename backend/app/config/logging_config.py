"""
Logging Configuration Module
Sets up standard logging for the application.
"""
import logging
import sys
from app.config.settings import settings

def setup_logging():
    """
    Configure global logging settings for the application.
    """
    logging_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            # Optional: Add FileHandler to write to logs/ directory
            logging.FileHandler("logs/app.log")
        ]
    )
    
    # Set levels for noisy libraries if necessary
    logging.getLogger("uvicorn.access").setLevel(logging_level)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return logging.getLogger(__name__)

logger = setup_logging()
