"""
Debug / Config Endpoint

Returns masked environment variable status so production issues can be
diagnosed without exposing secret values. Remove or gate behind auth before
going to a public-facing deployment.
"""
from __future__ import annotations

import os
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["Debug"])


def _mask(value: str | None, show: int = 8) -> str:
    if not value:
        return "<NOT SET>"
    if len(value) <= show:
        return "*" * len(value)
    return value[:show] + "..." + value[-4:]


@router.get("/config")
async def debug_config() -> JSONResponse:
    """
    Returns masked env-var status for production diagnostics.
    Confirms which values Render / the deployed server has loaded.
    """
    from app.config.settings import settings
    import app.api.analyze as _analyze_mod
    import app.services.sql_generator_service as _sqlgen_mod
    import app.database.seeder as _seeder_mod

    groq_key = settings.GROQ_API_KEY or ""
    groq_ok = bool(groq_key) and not groq_key.startswith("your_groq")

    return JSONResponse({
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "groq_model": settings.GROQ_MODEL,
        "groq_api_key_set": groq_ok,
        "groq_api_key_masked": _mask(groq_key),
        "database_url": settings.DATABASE_URL,
        "log_level": settings.LOG_LEVEL,
        "file_paths": {
            "analyze_py": os.path.abspath(_analyze_mod.__file__),
            "sql_generator_py": os.path.abspath(_sqlgen_mod.__file__),
            "seeder_py": os.path.abspath(_seeder_mod.__file__),
        },
        "commit": os.environ.get("RENDER_GIT_COMMIT", "<not on Render>"),
        "render_service": os.environ.get("RENDER_SERVICE_NAME", "<not on Render>"),
    })
