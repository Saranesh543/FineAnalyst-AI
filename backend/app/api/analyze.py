"""
Analytics Workflow API Routes

Exposes POST /api/v1/analyze — the primary endpoint for the end-to-end
FineAnalyst AI pipeline.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
import pydantic_ai.exceptions

from app.schemas.analyze import (
    AnalyzeErrorResponse,
    AnalyzeRequest,
    AnalyzeResponse,
)
from app.services.analytics_orchestrator import (
    AnalyticsWorkflowError,
    analytics_orchestrator,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["Analytics Workflow"])


# ---------------------------------------------------------------------------
# POST /analyze
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Run full analytics workflow",
    description=(
        "Executes the complete FineAnalyst AI pipeline: Schema Discovery -> "
        "SQL Generation -> SQL Execution -> Visualization Recommendation -> "
        "Business Insight Generation."
    ),
    responses={
        200: {"model": AnalyzeResponse, "description": "Full analysis successfully generated."},
        422: {
            "description": "Validation failed (e.g., malformed payload or invalid SQL execution).",
        },
        500: {
            "model": AnalyzeErrorResponse,
            "description": "Pipeline failure at any stage.",
        },
    },
)
async def analyze_workflow(payload: AnalyzeRequest) -> JSONResponse:
    """
    Execute the full end-to-end workflow based on a natural language question.

    Returns:
      - HTTP 200 with AnalyzeResponse on success.
      - HTTP 422 with AnalyzeErrorResponse for user/data errors (e.g., unsafe SQL).
      - HTTP 500 with AnalyzeErrorResponse for server/model errors.
    """
    logger.info("Analyze request received for question: %r", payload.question)

    try:
        response = await analytics_orchestrator.analyze(question=payload.question)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response.model_dump(mode="json"),
        )
    except AnalyticsWorkflowError as exc:
        logger.warning("Analytics workflow failed at stage '%s': %s", exc.stage, exc)
        
        # If the failure is a known validation error (e.g., empty DB, unsafe SQL) from 
        # a downstream service, it typically inherits ValueError or is raised as such,
        # but to keep it simple, we use 422 if it's schema or sql_generation or sql_execution 
        # related to user inputs, else 500. However, the requirements say "Return structured error"
        # and "Do not expose internal exceptions." Let's map stage-specific errors broadly:
        
        # Determine status code by stage/underlying error
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if exc.stage in ("sql_execution", "sql_generation", "schema", "visualization", "insight"):
            pass
            
        # Log the full stack trace internally, but do not expose it to the client
        logger.exception("Analytics workflow failed with full trace:", exc_info=exc)
        
        error_code = "workflow_failed"
        message = "An unexpected error occurred during the analytics workflow."

        if exc.original_error:
            from app.services.sql_validator_service import SQLSchemaValidationError, SQLValidationError
            if isinstance(exc.original_error, SQLSchemaValidationError):
                status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
                error_code = "schema_validation_error"
                message = "I couldn't generate a valid database query. The generated SQL referenced database fields that do not exist. Please try rephrasing your request."
            elif isinstance(exc.original_error, SQLValidationError):
                status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
                error_code = "sql_validation_error"
                message = f"I couldn't generate a safe or valid database query: {exc.original_error}"
            elif isinstance(exc.original_error, pydantic_ai.exceptions.UnexpectedModelBehavior):
                status_code = status.HTTP_502_BAD_GATEWAY
                message = "The AI provider is currently unavailable or returned an invalid response."
            
        return JSONResponse(
            status_code=status_code,
            content=AnalyzeErrorResponse(
                error=error_code,
                message=message,
                stage=exc.stage,
            ).model_dump(mode="json"),
        )
    except pydantic_ai.exceptions.UnexpectedModelBehavior as exc:
        logger.error("LLM Provider failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=AnalyzeErrorResponse(
                error="llm_provider_error",
                message="The AI provider is currently unavailable or returned an invalid response.",
                stage="ai_inference",
            ).model_dump(mode="json"),
        )
    except Exception as exc:
        logger.exception("Unexpected error during analyze workflow: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=AnalyzeErrorResponse(
                error="internal_server_error",
                message="An unexpected error occurred during the analytics workflow.",
                stage="unknown",
            ).model_dump(mode="json"),
        )
