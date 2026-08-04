"""
Business Insight Pydantic Schemas

Request and response models for POST /api/v1/insight.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.execution import SQLExecutionResponse
from app.schemas.visualization import VisualizationRecommendation


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class BusinessInsightRequest(BaseModel):
    """Incoming request to generate business insights."""

    question: str = Field(
        ...,
        min_length=3,
        description="The original natural-language question.",
    )
    execution_result: SQLExecutionResponse = Field(
        ...,
        description="The result of the executed SQL query.",
    )
    visualization: VisualizationRecommendation = Field(
        ...,
        description="The recommended visualization format for this data.",
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class BusinessInsightResponse(BaseModel):
    """Structured insights generated from the data."""

    summary: str = Field(
        description="Executive summary of the data (2-4 sentences)."
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="Key findings derived from the data (3-5 bullet points)."
    )
    anomalies: list[str] = Field(
        default_factory=list,
        description="Anomalies detected in the data (if any)."
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommended next questions to ask based on this data (2-3)."
    )


# ---------------------------------------------------------------------------
# Error response
# ---------------------------------------------------------------------------


class BusinessInsightErrorResponse(BaseModel):
    """Returned when insight generation fails."""

    error: str = Field(description="Machine-readable error code.")
    message: str = Field(description="Human-readable explanation.")
