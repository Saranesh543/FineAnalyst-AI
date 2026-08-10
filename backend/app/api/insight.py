"""
Business Insight API Routes

Exposes POST /api/v1/insight — Generates business insights from SQL results
using the AI agent.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.schemas.insight import (
    BusinessInsightErrorResponse,
    BusinessInsightRequest,
    BusinessInsightResponse,
)
from app.services.business_insight_service import (
    BusinessInsightError,
    business_insight_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insight", tags=["Business Insight"])


# ---------------------------------------------------------------------------
# POST /insight
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=BusinessInsightResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Business Insights",
    description=(
        "Analyzes raw data (SQL execution result) alongside the recommended "
        "visualization format to generate a short executive summary, key findings, "
        "anomalies, and recommended next questions."
    ),
    responses={
        200: {"model": BusinessInsightResponse, "description": "Insights successfully generated."},
        422: {
            "description": "Validation failed (e.g., malformed payload).",
        },
        500: {
            "model": BusinessInsightErrorResponse,
            "description": "Unexpected server error or AI model failure.",
        },
    },
)
async def generate_insight(payload: BusinessInsightRequest) -> JSONResponse:
    """
    Generate business insights from data.

    Returns:
      - HTTP 200 with BusinessInsightResponse on success.
      - HTTP 500 with BusinessInsightErrorResponse on model failure.
    """
    logger.info("Business insight request received for question: %r", payload.question)

    try:
        response = await business_insight_service.generate_insight(
            question=payload.question,
            execution_result=payload.execution_result,
            visualizations=payload.visualizations,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response.model_dump(mode="json"),
        )
    except BusinessInsightError as exc:
        logger.warning("Business insight generation failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=BusinessInsightErrorResponse(
                error="insight_generation_failed",
                message=str(exc),
            ).model_dump(mode="json"),
        )
    except Exception as exc:
        logger.exception("Unexpected error during insight generation: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=BusinessInsightErrorResponse(
                error="internal_server_error",
                message="An unexpected error occurred while generating insights.",
            ).model_dump(mode="json"),
        )
