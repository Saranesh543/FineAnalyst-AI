"""
Intent Pydantic Schemas

Defines the Intent enum (all supported intent classes) and IntentResult —
the structured output of the IntentClassifier.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


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


# ---------------------------------------------------------------------------
# Result Model
# ---------------------------------------------------------------------------


class IntentResult(BaseModel):
    """Structured output of a single intent classification run."""

    intent: Intent = Field(
        description="The detected intent class."
    )

    model_config = {"use_enum_values": True}
