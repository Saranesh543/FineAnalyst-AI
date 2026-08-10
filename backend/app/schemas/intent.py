"""
Intent Pydantic Schemas

Defines the Intent enum (all supported intent classes) and QueryPlan —
the structured output of the QueryUnderstandingService.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Intent Enum
# ---------------------------------------------------------------------------


class Intent(str, Enum):
    """All recognised intent classes.

    Add new intents here to extend routing.
    """

    CONVERSATION = "conversation"
    KNOWLEDGE = "knowledge"
    DATABASE = "database"
    SCHEMA = "schema"


# ---------------------------------------------------------------------------
# Result Model
# ---------------------------------------------------------------------------


class IntentResult(BaseModel):
    """Structured output of a single intent classification run."""

    intent: Intent = Field(
        description="The detected intent class."
    )
    corrected_message: str | None = Field(
        default=None,
        description="The typo-corrected version of the user message. Fix spelling mistakes or expand abbreviations (e.g., 'rev' -> 'revenue'). If no correction is needed, return the original message or leave empty."
    )

    model_config = {"use_enum_values": True}

    @field_validator("intent", mode="before")
    @classmethod
    def lowercase_intent(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower()
        return v

class QueryPlan(BaseModel):
    """Structured output representing the user's analytical query intent."""
    
    intent: Intent = Field(
        description="The detected intent class."
    )
    operation: str | None = Field(
        default=None,
        description="The analytical operation requested (e.g., comparison, trend, ranking, aggregation, distribution, lookup, filter, explanation)."
    )
    entities: list[str] | None = Field(
        default_factory=list,
        description="Specific entities mentioned in the query (e.g., 'Laptop', 'Smartphone', 'Q3', specific names)."
    )
    metrics: list[str] | None = Field(
        default_factory=list,
        description="The metrics being queried (e.g., 'total sales', 'revenue', 'delayed delivery', 'cancelled delivery')."
    )
    dimensions: list[str] | None = Field(
        default_factory=list,
        description="The dimensions to group or cut the metric by (e.g., 'product', 'category', 'country')."
    )
    time_range: str | None = Field(
        default=None,
        description="Any specific time range mentioned (e.g., 'last year', '2023', 'last 6 months')."
    )
    filters: list[str] | None = Field(
        default_factory=list,
        description="Any specific filtering conditions applied (e.g., 'revenue > 1000', 'status is active')."
    )
    requested_visualization: str | None = Field(
        default=None,
        description="Visualization explicitly requested or strongly implied by the operation (e.g., bar, line, pie, scatter, flowchart, er, None)."
    )
    requires_database: bool = Field(
        default=True,
        description="True if the request actually requires fetching data from the database."
    )
    clarification_needed: bool = Field(
        default=False,
        description="Set to true if the query is too ambiguous to determine the requested analysis without asking the user."
    )
    clarification_question: str | None = Field(
        default=None,
        description="The question to ask the user to clarify their intent, if clarification_needed is true."
    )
    corrected_message: str | None = Field(
        default=None,
        description="The typo-corrected version of the user message."
    )

    model_config = {"use_enum_values": True}

    @field_validator("intent", mode="before")
    @classmethod
    def lowercase_intent(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower()
        return v
