"""
SQL Executor Service

Executes read-only SQL queries against the live database securely.

Responsibilities:
  - Strictly validate incoming SQL (allow only SELECT/WITH, reject mutations).
  - Execute the SQL asynchronously using SQLAlchemy.
  - Measure execution time.
  - Return a structured SQLExecutionResponse containing columns and rows.
  - Handle exceptions and emit structured logs.

Usage::

    from app.services.sql_executor_service import sql_executor_service

    result = await sql_executor_service.execute_sql("SELECT * FROM users")
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.database.session import analytics_engine
from app.schemas.execution import SQLExecutionResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SQLExecutionValidationError(ValueError):
    """Raised when SQL fails the safety validation policy prior to execution."""


class SQLExecutionFailedError(RuntimeError):
    """Raised when the database fails to execute the query."""


# ---------------------------------------------------------------------------
# Safety policy
# ---------------------------------------------------------------------------

_ALLOWED_STATEMENT_PREFIXES: frozenset[str] = frozenset(
    {"SELECT", "WITH"}
)

_FORBIDDEN_KEYWORDS: frozenset[str] = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "ATTACH",
        "DETACH",
        "PRAGMA",
        "VACUUM",
        "REINDEX",
    }
)


def _clean_column_name(col: str) -> str:
    """
    Converts raw SQL column names into explicit display labels.
    Ensures safe strings for frontend charting libraries by removing brackets/dots.
    """
    clean = col.replace("_", " ")
    clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean.title() if clean else "Column"


def validate_execution_sql(sql: str) -> str:
    """
    Validate that *sql* is safe to execute.
    
    Steps:
    1. Strip whitespace.
    2. Ensure the first keyword is SELECT or WITH.
    3. Ensure no forbidden keyword appears anywhere in the statement.

    Returns the stripped SQL if safe.

    Raises:
        SQLExecutionValidationError: If any policy is violated.
    """
    stripped = sql.strip().rstrip(";").strip()

    if not stripped:
        raise SQLExecutionValidationError("SQL query is empty.")

    first_word = stripped.split()[0].upper()
    if first_word not in _ALLOWED_STATEMENT_PREFIXES:
        raise SQLExecutionValidationError(
            f"SQL statement type '{first_word}' is not allowed. "
            f"Only {sorted(_ALLOWED_STATEMENT_PREFIXES)} statements are permitted."
        )

    upper_sql = stripped.upper()
    for keyword in _FORBIDDEN_KEYWORDS:
        pattern = rf"\b{re.escape(keyword)}\b"
        if re.search(pattern, upper_sql):
            raise SQLExecutionValidationError(
                f"SQL contains forbidden keyword '{keyword}'. "
                "Only read-only SELECT/WITH queries are permitted."
            )

    return stripped + ";"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SQLExecutorService:
    """
    Stateless service that safely executes SQL queries.

    A single shared instance is exposed at the module level.
    """

    def __init__(self, db_engine: AsyncEngine) -> None:
        self._engine = db_engine
        logger.debug("SQLExecutorService initialised.")

    async def execute_sql(self, sql: str) -> SQLExecutionResponse:
        """
        Validate and execute the SQL query.

        Args:
            sql: The raw SQL query string to execute.

        Returns:
            SQLExecutionResponse containing the columns, rows, row count,
            and execution time.

        Raises:
            SQLExecutionValidationError: If the SQL is unsafe.
            SQLExecutionFailedError: If the database execution fails.
        """
        request_id = f"exec-{int(time.time() * 1000)}"
        
        logger.info(
            "[%s] SQL execution request received | sql_len=%d",
            request_id,
            len(sql),
        )

        try:
            validated_sql = validate_execution_sql(sql)
        except SQLExecutionValidationError as exc:
            logger.warning(
                "[%s] SQL execution validation failed | error=%s | raw_sql=%r",
                request_id,
                exc,
                sql[:200],
            )
            raise

        logger.info("[%s] SQL validation successful. Starting execution.", request_id)

        t_start = time.perf_counter()
        columns: list[str] = []
        rows: list[list[Any]] = []

        try:
            async with self._engine.connect() as conn:
                result = await conn.execute(text(validated_sql))
                
                # Extract column names (if result yields rows)
                if result.returns_rows:
                    raw_columns = list(result.keys())
                    
                    # Deduplicate cleaned column names
                    seen = set()
                    for c in raw_columns:
                        cleaned = _clean_column_name(c)
                        base_cleaned = cleaned
                        counter = 1
                        while cleaned in seen:
                            cleaned = f"{base_cleaned} {counter}"
                            counter += 1
                        seen.add(cleaned)
                        columns.append(cleaned)
                    
                    # Fetch all rows and convert each tuple to a list
                    for row in result.all():
                        rows.append(list(row))
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t_start) * 1_000
            db_path = str(self._engine.url)
            logger.exception(
                "[%s] SQL execution failed\n"
                "  SQL: %s\n"
                "  DB Path: %s\n"
                "  Elapsed: %.1f ms\n"
                "  Error: %s: %s",
                request_id,
                validated_sql,
                db_path,
                elapsed_ms,
                type(exc).__name__,
                exc,
                exc_info=True,
            )
            raise SQLExecutionFailedError(f"Database execution failed: {exc}") from exc

        elapsed_ms = (time.perf_counter() - t_start) * 1_000
        row_count = len(rows)

        logger.info(
            "[%s] SQL execution completed | elapsed=%.1f ms | rows=%d",
            request_id,
            elapsed_ms,
            row_count,
        )

        return SQLExecutionResponse(
            columns=columns,
            rows=rows,
            row_count=row_count,
            execution_time_ms=elapsed_ms,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
sql_executor_service = SQLExecutorService(db_engine=analytics_engine)
