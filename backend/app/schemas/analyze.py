"""
Analyze Pydantic Schemas

Request and response models for POST /api/v1/analyze.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.execution import SQLExecutionResponse
from app.schemas.insight import BusinessInsightResponse
from app.schemas.visualization import VisualizationRecommendation


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    """Incoming request to execute the full analytics workflow."""

    question: str = Field(
        ...,
        min_length=3,
        description="The natural-language business question to analyze.",
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class AnalyzeResponse(BaseModel):
    """Unified response containing the full analytics workflow result."""

    question: str = Field(
        description="The original question."
    )
    sql: str = Field(
        description="The generated SQL query."
    )
    execution: SQLExecutionResponse = Field(
        description="The database execution results (columns, rows, execution time)."
    )
    visualization: VisualizationRecommendation = Field(
        description="The recommended chart format."
    )
    insight: BusinessInsightResponse = Field(
        description="The generated business insights (summary, key findings, etc)."
    )


# ---------------------------------------------------------------------------
# Error response
# ---------------------------------------------------------------------------


class AnalyzeErrorResponse(BaseModel):
    """Returned when any stage of the analytics workflow fails."""

    error: str = Field(description="Machine-readable error code.")
    message: str = Field(description="Human-readable explanation.")
    stage: str = Field(description="The pipeline stage where the failure occurred.")
