"""
SQL API Routes

Exposes POST /sql/generate — converts a natural-language question into a
validated SQL query using the live database schema.

HTTP concerns only; all logic is delegated to SQLGeneratorService and
SchemaService.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.schemas.sql import (
    SQLGenerationErrorResponse,
    SQLGenerationRequest,
    SQLGenerationResponse,
)
from app.services.schema_service import SchemaDiscoveryError, schema_service
from app.services.sql_generator_service import (
    SQLGenerationError,
    SQLValidationError,
    sql_generator_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sql", tags=["SQL Generation"])


# ---------------------------------------------------------------------------
# POST /sql/generate
# ---------------------------------------------------------------------------


@router.post(
    "/generate",
    response_model=SQLGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate SQL from a natural-language question",
    description=(
        "Introspects the live database schema, builds a schema-aware prompt, "
        "and asks the AI agent to produce a validated read-only SQL query. "
        "Only SELECT/WITH statements are returned. Destructive keywords "
        "(INSERT, UPDATE, DELETE, DROP, …) are rejected with HTTP 422."
    ),
    responses={
        200: {"model": SQLGenerationResponse, "description": "SQL generated successfully."},
        422: {
            "model": SQLGenerationErrorResponse,
            "description": "SQL validation failed — generated query is not safe.",
        },
        500: {
            "model": SQLGenerationErrorResponse,
            "description": "AI model call or schema discovery failed.",
        },
    },
)
async def generate_sql(payload: SQLGenerationRequest) -> JSONResponse:
    """
    Translate *payload.question* into a SQL query constrained by the
    live database schema.

    Returns:
      - HTTP 200  with ``SQLGenerationResponse``   on success.
      - HTTP 422  with ``SQLGenerationErrorResponse`` when the generated SQL
                  fails the safety policy.
      - HTTP 500  with ``SQLGenerationErrorResponse`` on model or schema errors.
    """
    question = payload.question

    # --- Step 1: Discover live schema ------------------------------------
    try:
        schema = await schema_service.get_schema()
    except SchemaDiscoveryError as exc:
        logger.warning("Schema discovery failed during SQL generation: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=SQLGenerationErrorResponse(
                error="schema_discovery_error",
                message=str(exc),
                question=question,
            ).model_dump(mode="json"),
        )

    # Guard: cannot generate SQL without any tables.
    if schema.is_empty:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=SQLGenerationErrorResponse(
                error="empty_schema",
                message=(
                    "No tables were found in the connected database. "
                    "SQL cannot be generated without a schema."
                ),
                question=question,
            ).model_dump(mode="json"),
        )

    # --- Step 2: Generate & validate SQL ---------------------------------
    try:
        response = await sql_generator_service.generate(
            question=question,
            schema=schema,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response.model_dump(mode="json"),
        )

    except SQLValidationError as exc:
        logger.warning(
            "SQL validation rejected generated query | question=%r | error=%s",
            question,
            exc,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=SQLGenerationErrorResponse(
                error="sql_validation_error",
                message=str(exc),
                question=question,
            ).model_dump(mode="json"),
        )

    except (SQLGenerationError, ValueError) as exc:
        logger.exception(
            "SQL generation model error | question=%r | error=%s: %s",
            question,
            type(exc).__name__,
            exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=SQLGenerationErrorResponse(
                error="sql_generation_error",
                message=str(exc),
                question=question,
            ).model_dump(mode="json"),
        )
