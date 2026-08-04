"""
SQL Execution Pydantic Schemas

Request and response models for POST /api/v1/sql/execute.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class SQLExecutionRequest(BaseModel):
    """Incoming request to execute a SQL query."""

    sql: str = Field(
        ...,
        min_length=5,
        description="The SQL query to execute. Must be read-only (SELECT or WITH).",
        examples=["SELECT * FROM customers LIMIT 10;"],
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class SQLExecutionResponse(BaseModel):
    """Successful SQL execution result."""

    columns: list[str] = Field(
        description="List of column names returned by the query."
    )
    rows: list[list[Any]] = Field(
        description="Query results, where each row is a list of values matching the column order."
    )
    row_count: int = Field(
        description="Total number of rows returned."
    )
    execution_time_ms: float = Field(
        description="Time taken to execute the query and fetch results, in milliseconds."
    )


# ---------------------------------------------------------------------------
# Error response
# ---------------------------------------------------------------------------


class SQLExecutionErrorResponse(BaseModel):
    """Returned when SQL execution or validation fails."""

    error: str = Field(description="Machine-readable error code.")
    message: str = Field(description="Human-readable explanation.")
