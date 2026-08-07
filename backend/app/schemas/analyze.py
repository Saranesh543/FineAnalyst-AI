"""
Analyze Pydantic Schemas

Request and response models for POST /api/v1/analyze.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from typing import Any
from app.schemas.execution import SQLExecutionResponse
from app.schemas.insight import BusinessInsightResponse
from app.schemas.visualization import VisualizationRecommendation
from app.schemas.agent import MessageTurn


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


class WorkflowStep(BaseModel):
    """Represents a single step in the analytics pipeline."""

    name: str = Field(description="The technical name of the pipeline stage.")
    status: str = Field(description="'done', 'error', 'skipped'")
    duration_ms: float | None = Field(default=None, description="Execution time in milliseconds.")
    detail: str | None = Field(default=None, description="Additional context, like generated SQL or error message.")


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    """Incoming request to execute the full analytics workflow."""

    question: str = Field(
        ...,
        description="The natural-language business question to analyze. Can be short if attachments are provided.",
    )
    session_id: str | None = Field(
        default=None,
        description="The session ID to link to attachments",
    )
    history: list[MessageTurn] | None = Field(
        default=None,
        description="Optional list of previous messages for conversation context.",
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class AnalyzeResponse(BaseModel):
    """Unified response containing the full analytics workflow result."""

    question: str = Field(
        description="The original question."
    )
    intent: str | None = Field(
        default=None,
        description="The classified intent (conversation, knowledge, database).",
    )
    sql: str | None = Field(
        default=None,
        description="The generated SQL query."
    )
    execution: SQLExecutionResponse | None = Field(
        default=None,
        description="The database execution results (columns, rows, execution time)."
    )
    visualization: VisualizationRecommendation | None = Field(
        default=None,
        description="The recommended chart format."
    )
    insight: BusinessInsightResponse | None = Field(
        default=None,
        description="The generated business insights (summary, key findings, etc)."
    )
    chart_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Rich metadata describing the visualization properties for the frontend."
    )
    visualization_confidence: float | None = Field(
        default=None,
        description="Confidence score for the visualization selection."
    )
    confidence_score: str | None = Field(
        default=None,
        description="Overall analytics confidence (High, Medium, Low)."
    )
    steps: list[WorkflowStep] | None = Field(
        default_factory=list,
        description="Chronological log of workflow execution steps."
    )


# ---------------------------------------------------------------------------
# Error response
# ---------------------------------------------------------------------------


class AnalyzeErrorResponse(BaseModel):
    """Returned when any stage of the analytics workflow fails."""

    error: str = Field(description="Machine-readable error code.")
    message: str = Field(description="Human-readable explanation.")
    stage: str = Field(description="The pipeline stage where the failure occurred.")
    steps: list[WorkflowStep] | None = Field(
        default_factory=list,
        description="Chronological log of workflow execution steps up to the point of failure."
    )
