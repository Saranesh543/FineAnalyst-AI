"""
SQL Generation Pydantic Schemas

Request and response models for POST /api/v1/sql/generate.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class SQLGenerationRequest(BaseModel):
    """Incoming natural-language question for SQL generation."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=2_000,
        description="Natural-language question to convert to SQL.",
        examples=["Top 5 products by revenue"],
    )

    model_config = {"str_strip_whitespace": True}


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class SQLGenerationResponse(BaseModel):
    """Successful SQL generation result."""

    sql: str = Field(description="The generated, validated SQL query.")
    question: str = Field(description="The original question echoed back.")
    dialect: str = Field(
        description="The database dialect the SQL was generated for.",
        examples=["sqlite", "postgresql"],
    )


# ---------------------------------------------------------------------------
# Error response
# ---------------------------------------------------------------------------


class SQLGenerationErrorResponse(BaseModel):
    """Returned when SQL generation or validation fails."""

    error: str = Field(description="Machine-readable error code.")
    message: str = Field(description="Human-readable explanation.")
    question: str = Field(description="The original question echoed back.")
