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


class KPICard(BaseModel):
    """A Key Performance Indicator derived from the data."""
    label: str = Field(description="The title of the KPI (e.g., 'Total Revenue').")
    value: str | float = Field(description="The numeric or string value of the KPI.")
    format: str = Field(
        description="The formatting type: 'currency', 'percentage', 'decimal', 'compact', or 'text'."
    )


class BusinessInsightResponse(BaseModel):
    """Structured insights generated from the data."""

    summary: str = Field(
        description="Executive summary of the data."
    )
    kpi_cards: list[KPICard] = Field(
        default_factory=list,
        description="List of KPI cards derived from the data."
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="Key findings derived from the data (3-6 concise bullet points)."
    )
    anomalies: list[str] = Field(
        default_factory=list,
        description="Anomalies, outliers, or significant differences detected in the data (if any)."
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable business recommendations derived from this data (3-5 bullet points)."
    )
    suggested_questions: list[str] = Field(
        default_factory=list,
        description="Intelligent follow-up analytical questions (3-5 bullet points)."
    )


# ---------------------------------------------------------------------------
# Error response
# ---------------------------------------------------------------------------


class BusinessInsightErrorResponse(BaseModel):
    """Returned when insight generation fails."""

    error: str = Field(description="Machine-readable error code.")
    message: str = Field(description="Human-readable explanation.")
