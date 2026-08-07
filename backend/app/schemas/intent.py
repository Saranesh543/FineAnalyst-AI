"""
Intent Pydantic Schemas

Defines the Intent enum (all supported intent classes) and IntentResult —
the structured output of the IntentClassifier.
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

    model_config = {"use_enum_values": True}

    @field_validator("intent", mode="before")
    @classmethod
    def lowercase_intent(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower()
        return v
