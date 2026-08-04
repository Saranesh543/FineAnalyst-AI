"""
Global Exception Handling Module
Defines custom exceptions and exception handlers for FastAPI.
"""
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

class AppException(Exception):
    """Base exception for application-specific errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code

async def app_exception_handler(request: Request, exc: AppException):
    """
    Handler for application-specific exceptions.
    """
    logger.error(f"AppException at {request.url}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )

async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unhandled exceptions.
    """
    logger.exception(f"Unhandled exception at {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal Server Error"},
    )
