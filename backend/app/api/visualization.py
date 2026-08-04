"""
Visualization API Routes

Exposes POST /api/v1/visualization/recommend — Recommends a chart format
based on a user question and a SQL execution result.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.schemas.visualization import (
    VisualizationErrorResponse,
    VisualizationRecommendation,
    VisualizationRequest,
)
from app.services.chart_recommender_service import chart_recommender_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/visualization", tags=["Visualization"])


# ---------------------------------------------------------------------------
# POST /visualization/recommend
# ---------------------------------------------------------------------------


@router.post(
    "/recommend",
    response_model=VisualizationRecommendation,
    status_code=status.HTTP_200_OK,
    summary="Recommend a chart type",
    description=(
        "Analyzes the given natural-language question and SQL execution result "
        "to recommend the most appropriate visualization format (e.g., bar, line, pie). "
        "Does NOT generate the chart."
    ),
    responses={
        200: {"model": VisualizationRecommendation, "description": "Recommendation generated."},
        422: {
            "model": VisualizationErrorResponse,
            "description": "Validation failed (e.g., empty execution result).",
        },
        500: {
            "model": VisualizationErrorResponse,
            "description": "Unexpected server error.",
        },
    },
)
async def recommend_visualization(payload: VisualizationRequest) -> JSONResponse:
    """
    Recommend a visualization.

    Returns:
      - HTTP 200 with VisualizationRecommendation on success.
      - HTTP 422 with VisualizationErrorResponse for empty data.
      - HTTP 500 with VisualizationErrorResponse on unexpected errors.
    """
    logger.info("Visualization recommendation request received for question: %r", payload.question)

    try:
        recommendation = chart_recommender_service.recommend(
            question=payload.question,
            execution_result=payload.execution_result,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=recommendation.model_dump(mode="json"),
        )
    except ValueError as exc:
        logger.warning("Visualization recommendation validation failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=VisualizationErrorResponse(
                error="validation_error",
                message=str(exc),
            ).model_dump(mode="json"),
        )
    except Exception as exc:
        logger.exception("Unexpected error during visualization recommendation: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=VisualizationErrorResponse(
                error="internal_server_error",
                message="An unexpected error occurred while recommending a visualization.",
            ).model_dump(mode="json"),
        )
