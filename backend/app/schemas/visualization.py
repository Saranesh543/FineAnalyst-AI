"""
Visualization Pydantic Schemas

Request and response models for POST /api/v1/visualization/recommend.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.execution import SQLExecutionResponse


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class VisualizationRequest(BaseModel):
    """Incoming request to recommend a visualization."""

    question: str = Field(
        ...,
        min_length=3,
        description="The original natural-language question.",
    )
    execution_result: SQLExecutionResponse = Field(
        ...,
        description="The result of the executed SQL query to be analyzed.",
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class VisualizationRecommendation(BaseModel):
    """Recommended visualization format."""

    chart: str = Field(
        description="The recommended chart type (bar, line, pie, scatter, area, histogram, table)."
    )
    confidence: float = Field(
        description="Confidence score for this recommendation (0.0 to 1.0).",
        ge=0.0,
        le=1.0,
    )
    reason: str = Field(
        description="Human-readable explanation of why this chart was selected."
    )
    x_axis: str | None = Field(
        default=None,
        description="Recommended column for the X-axis.",
    )
    y_axis: str | None = Field(
        default=None,
        description="Recommended column for the Y-axis.",
    )


# ---------------------------------------------------------------------------
# Error response
# ---------------------------------------------------------------------------


class VisualizationErrorResponse(BaseModel):
    """Returned when visualization recommendation fails."""

    error: str = Field(description="Machine-readable error code.")
    message: str = Field(description="Human-readable explanation.")
