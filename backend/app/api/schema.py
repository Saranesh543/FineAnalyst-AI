"""
Schema API Routes

Exposes GET /schema for database schema discovery.
All heavy lifting is delegated to SchemaService; this module only handles
HTTP concerns (status codes, response shaping, error translation).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.schemas.database_schema import DatabaseSchemaResponse
from app.services.schema_service import SchemaDiscoveryError, schema_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schema", tags=["Schema"])


# ---------------------------------------------------------------------------
# GET /schema
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=DatabaseSchemaResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover the connected database schema",
    description=(
        "Introspects the live database using SQLAlchemy Inspector and returns "
        "a structured description of all tables, columns, primary keys, "
        "foreign keys, and indexes."
    ),
    responses={
        200: {
            "model": DatabaseSchemaResponse,
            "description": "Full schema discovered successfully.",
        },
        500: {
            "description": "Schema discovery failed (database unreachable or inspector error).",
        },
    },
)
async def get_schema() -> JSONResponse:
    """
    Introspect the connected database and return its full schema.

    Returns HTTP 200 with a ``DatabaseSchemaResponse`` on success, or
    HTTP 500 with a structured error body if introspection fails.
    """
    try:
        schema = await schema_service.get_schema()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=schema.model_dump(mode="json"),
        )
    except SchemaDiscoveryError as exc:
        logger.warning("Schema discovery error returned to client: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "schema_discovery_error",
                "message": str(exc),
            },
        )
