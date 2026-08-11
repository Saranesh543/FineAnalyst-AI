"""
Analytics Workflow API Routes

Exposes POST /api/v1/analyze — the primary endpoint for the end-to-end
FineAnalyst AI pipeline.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status, Depends, Request
from fastapi.responses import JSONResponse
import asyncio
import pydantic_ai.exceptions

from app.api.deps import get_current_user
from app.models.user import User

from app.schemas.analyze import (
    AnalyzeErrorResponse,
    AnalyzeRequest,
    AnalyzeResponse,
)
from app.services.analytics_orchestrator import (
    AnalyticsWorkflowError,
    analytics_orchestrator,
)
from pydantic_ai.exceptions import ModelHTTPError

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
async def analyze_workflow(
    payload: AnalyzeRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    import uuid
    import time
    
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    logger.info("[%s] Analyze request received. Question: %r", request_id, payload.question)
    logger.info("[%s] Request Body: %s", request_id, payload.model_dump_json())

    try:
        response = await analytics_orchestrator.analyze(
            question=payload.question,
            history=payload.history,
            user_id=current_user.id,
            session_id=payload.session_id
        )
        # Reconstruct query_plan and sql from response if available
        query_plan_str = "N/A"
        sql_str = "N/A"
        if response.query_plan:
            import json
            query_plan_str = json.dumps(response.query_plan)
        if response.sql:
            sql_str = response.sql

        logger.info(
            "\n[Analytics] Question: %s\n"
            "[Analytics] QueryPlan: %s\n"
            "[Analytics] Stage: success\n"
            "[Analytics] SQL: %s\n"
            "[Analytics] Error: None",
            payload.question,
            query_plan_str,
            sql_str
        )
        
        response_json = response.model_dump(mode="json")
        logger.info("[%s] Analyze completed successfully. HTTP 200.", request_id)
        logger.debug("[%s] Response Body: %s", request_id, response_json)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_json,
        )
    except AnalyticsWorkflowError as exc:
        # Log the required formatted analytics error
        # Reconstruct query_plan and sql if they exist in the steps
        query_plan_str = "N/A"
        sql_str = "N/A"
        for step in exc.steps:
            if step.name == "intent_routing" and step.detail:
                query_plan_str = step.detail
            if step.name == "sql_generation" and step.detail:
                sql_str = step.detail

        logger.error(
            "\n[Analytics] Question: %s\n"
            "[Analytics] QueryPlan: %s\n"
            "[Analytics] Stage: %s\n"
            "[Analytics] SQL: %s\n"
            "[Analytics] Error: %s",
            payload.question,
            query_plan_str,
            exc.stage,
            sql_str,
            str(exc)
        )

        # Log the full internal traceback first — visible in backend logs
        logger.exception(
            "Analytics workflow failed | stage=%s | exc_type=%s | exc=%s",
            exc.stage,
            type(exc.original_error).__name__ if exc.original_error else type(exc).__name__,
            exc,
        )

        # --- Determine HTTP status code and user-facing message ---
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_code = "workflow_failed"
        message = f"The analytics pipeline failed at stage '{exc.stage}'."

        original = exc.original_error
        
        # Traverse the exception chain to find the true root cause
        # This prevents exceptions hidden inside wrappers (like SQLGenerationError)
        # from falling through to the generic 500 handler.
        root_cause = original
        while root_cause and getattr(root_cause, "__cause__", None) is not None:
            root_cause = root_cause.__cause__

        original_str = str(root_cause) if root_cause else str(exc)

        # Priority 1: Rate limit (429)
        if "429" in original_str or "rate limit" in original_str.lower() or "rate_limit_exceeded" in original_str.lower():
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
            error_code = "rate_limit_exceeded"
            message = "The AI provider rate limit was reached. Please wait a moment and try again."

        # Priority 2: Known typed exceptions
        elif root_cause is not None:
            from app.services.sql_validator_service import SQLSchemaValidationError, SQLValidationError
            from app.services.sql_executor_service import SQLExecutionFailedError
            import pydantic_ai.exceptions as _pai_exc

            if isinstance(root_cause, SQLSchemaValidationError):
                status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
                error_code = "schema_validation_error"
                message = "The AI generated a query referencing columns that don't exist. Please rephrase your question."
            elif isinstance(root_cause, SQLValidationError):
                status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
                error_code = "sql_validation_error"
                message = f"Generated an invalid or unsafe SQL query: {root_cause}"
            elif isinstance(root_cause, SQLExecutionFailedError):
                status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
                error_code = "sql_execution_error"
                message = f"The database rejected the query: {root_cause}"
            elif isinstance(root_cause, _pai_exc.UnexpectedModelBehavior) or isinstance(root_cause, ModelHTTPError):
                status_code = status.HTTP_502_BAD_GATEWAY
                error_code = "llm_provider_error"
                message = "The AI provider returned an unexpected response. Please try again."
            elif isinstance(root_cause, ValueError) and "GROQ_API_KEY" in original_str:
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                error_code = "configuration_error"
                message = "The AI provider API key is not configured. Contact the administrator."

        return JSONResponse(
            status_code=status_code,
            content=AnalyzeErrorResponse(
                error=error_code,
                message=message,
                stage=exc.stage,
                steps=exc.steps,
            ).model_dump(mode="json"),
        )
    except asyncio.CancelledError:
        logger.warning("[%s] Client cancelled the request. HTTP 499.", request_id)
        return JSONResponse(
            status_code=499,
            content=AnalyzeErrorResponse(
                error="CLIENT_CANCELLED",
                message="Request was cancelled by the client.",
                stage="unknown"
            ).model_dump(mode="json"),
        )
    except pydantic_ai.exceptions.UnexpectedModelBehavior as exc:
        logger.exception("LLM Provider failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=AnalyzeErrorResponse(
                error="llm_provider_error",
                message="The AI provider is currently unavailable or returned an invalid response.",
                stage="ai_inference",
            ).model_dump(mode="json"),
        )
    except ModelHTTPError as exc:
        logger.exception("LLM HTTP Error: %s", exc)
        if exc.status_code == 429 or "rate_limit_exceeded" in str(exc).lower():
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=AnalyzeErrorResponse(
                    error="rate_limit_exceeded",
                    message="The AI provider rate limit was reached. Please wait a moment and try again.",
                    stage="rate_limited",
                ).model_dump(mode="json"),
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=AnalyzeErrorResponse(
                error="model_http_error",
                message=f"The AI provider returned an HTTP error {exc.status_code}.",
                stage="unknown",
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
