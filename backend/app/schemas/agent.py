"""
Agent Pydantic Schemas

Defines the request and response models used by the agent API and service.
All fields are typed and validated by Pydantic v2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MessageRole(str, Enum):
    """Role of a participant in a conversation turn."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class MessageTurn(BaseModel):
    role: MessageRole
    content: str


class AgentStatus(str, Enum):
    """High-level outcome of an agent run."""
    SUCCESS = "success"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class AgentRequest(BaseModel):
    """Incoming message from the user to the agent."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=32_000,
        description="The user message to send to FineAnalyst AI.",
        examples=["What are the top 5 products by revenue this quarter?"],
    )
    session_id: str | None = Field(
        default=None,
        description=(
            "Optional session identifier for conversation continuity. "
            "If omitted, a stateless single-turn exchange is performed."
        ),
        examples=["session-abc-123"],
    )
    history: list[MessageTurn] | None = Field(
        default=None,
        description="Optional list of previous messages for conversation context."
    )

    model_config = {"str_strip_whitespace": True}


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class UsageInfo(BaseModel):
    """Token usage reported by the model for a single run."""

    requests: int = Field(default=0, description="Number of model API calls made.")
    request_tokens: int | None = Field(
        default=None, description="Input tokens consumed."
    )
    response_tokens: int | None = Field(
        default=None, description="Output tokens generated."
    )
    total_tokens: int | None = Field(
        default=None, description="Total tokens (input + output)."
    )

    @classmethod
    def from_pydantic_usage(cls, usage: Any) -> "UsageInfo":
        """
        Build a UsageInfo from a pydantic_ai.usage.Usage object.

        The Usage object may not always populate all fields (e.g. cached runs),
        so every attribute is accessed with getattr and a safe default.
        """
        return cls(
            requests=getattr(usage, "requests", 0),
            request_tokens=getattr(usage, "request_tokens", None),
            response_tokens=getattr(usage, "response_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        )


class AgentResponse(BaseModel):
    """Structured response returned by the AgentService."""

    status: AgentStatus = Field(
        description="Whether the agent run succeeded or failed."
    )
    session_id: str | None = Field(
        default=None,
        description="Echoed session ID (if provided in the request).",
    )
    message: str = Field(
        description="The agent's natural-language reply."
    )
    usage: UsageInfo | None = Field(
        default=None,
        description="Token-usage statistics for this run.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the response was generated.",
    )

    model_config = {"use_enum_values": True}


class AgentErrorResponse(BaseModel):
    """Returned when the agent encounters an unrecoverable error."""

    status: AgentStatus = AgentStatus.ERROR
    session_id: str | None = None
    error_code: str = Field(description="Machine-readable error category.")
    message: str = Field(description="Human-readable error description.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
