"""
SQL Execution API Routes

Exposes POST /api/v1/sql/execute — safely executes a read-only SQL query
and returns the structured results.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.schemas.execution import (
    SQLExecutionErrorResponse,
    SQLExecutionRequest,
    SQLExecutionResponse,
)
from app.services.sql_executor_service import (
    SQLExecutionFailedError,
    SQLExecutionValidationError,
    sql_executor_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sql", tags=["SQL Execution"])


# ---------------------------------------------------------------------------
# POST /sql/execute
# ---------------------------------------------------------------------------


@router.post(
    "/execute",
    response_model=SQLExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute a generated SQL query securely",
    description=(
        "Executes a read-only SQL query (SELECT or WITH) against the live database "
        "and returns the column names, rows, row count, and execution time. "
        "Any attempt to execute a mutating query will be rejected."
    ),
    responses={
        200: {"model": SQLExecutionResponse, "description": "SQL executed successfully."},
        400: {
            "description": "Malformed request.",
        },
        422: {
            "model": SQLExecutionErrorResponse,
            "description": "SQL validation failed (e.g., attempt to mutate data).",
        },
        500: {
            "model": SQLExecutionErrorResponse,
            "description": "Database execution failure or unexpected error.",
        },
    },
)
async def execute_sql(payload: SQLExecutionRequest) -> JSONResponse:
    """
    Validate and execute the SQL query provided in the payload.

    Returns:
      - HTTP 200 with SQLExecutionResponse on success.
      - HTTP 422 with SQLExecutionErrorResponse for unsafe SQL.
      - HTTP 500 with SQLExecutionErrorResponse for database failures.
    """
    try:
        response = await sql_executor_service.execute_sql(payload.sql)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response.model_dump(mode="json"),
        )
    except SQLExecutionValidationError as exc:
        # Handled as HTTP 422 for Unprocessable Content (unsafe SQL)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=SQLExecutionErrorResponse(
                error="sql_validation_error",
                message=str(exc),
            ).model_dump(mode="json"),
        )
    except SQLExecutionFailedError as exc:
        # DB execution failures
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=SQLExecutionErrorResponse(
                error="sql_execution_failed",
                message=str(exc),
            ).model_dump(mode="json"),
        )
    except Exception as exc:
        # Unexpected exceptions
        logger.exception("Unexpected error during SQL execution: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=SQLExecutionErrorResponse(
                error="internal_server_error",
                message="An unexpected error occurred during execution.",
            ).model_dump(mode="json"),
        )
