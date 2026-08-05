"""
SQL Generator Service

Converts a natural-language question into a validated SQL query using the
FineAnalyst AI agent and the live database schema.

Responsibilities:
  - Build a structured schema-aware prompt from a DatabaseSchemaResponse.
  - Invoke PydanticAI with strict output instructions.
  - Strip residual markdown fences from the model output.
  - Validate the generated SQL against an allow-list of safe read-only
    statement types and a deny-list of destructive keywords.
  - Raise SQLValidationError for any policy violation.
  - Emit structured log entries for every request.

Usage::

    from app.services.sql_generator_service import sql_generator_service

    result = await sql_generator_service.generate(
        question="Top 5 products by revenue",
        schema=schema_response,
    )
    print(result.sql)
"""

from __future__ import annotations

import logging
import re
import time

from pydantic_ai import Agent
from app.services.llm_provider import get_llm_model

from app.config.settings import settings
from app.schemas.database_schema import DatabaseSchemaResponse
from app.schemas.sql import SQLGenerationResponse

logger = logging.getLogger(__name__)


from app.services.sql_validator_service import SQLValidationError, SQLSchemaValidationError, validate_sql_schema

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SQLGenerationError(RuntimeError):
    """Raised when the AI model call fails unexpectedly."""


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a SQL expert. "
    "Your ONLY job is to generate a single, syntactically correct SQL query "
    "that answers the user's question using ONLY the tables and columns "
    "described in the schema below. "
    "\n\n"
    "STRICT RULES — violating any rule makes the response invalid:\n"
    "1. Return ONLY the raw SQL statement. No explanations.\n"
    "2. Do NOT wrap the SQL in markdown code fences (``` or ```sql).\n"
    "3. Do NOT include any text before or after the SQL.\n"
    "4. Use ONLY SELECT or WITH as the top-level statement.\n"
    "5. Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, "
    "MERGE, or EXEC.\n"
    "6. Reference only tables and columns that appear in the provided schema.\n"
    "7. Always end the statement with a semicolon.\n"
)


def _build_schema_section(schema: DatabaseSchemaResponse) -> str:
    """
    Render a DatabaseSchemaResponse into a compact, prompt-friendly text block.

    Example output::

        Database: fineanalyst.db  (sqlite)

        Table: orders
          Columns: id (INTEGER, NOT NULL, PK), customer_id (INTEGER, NOT NULL), total (REAL, NULL)
          Primary Keys: id
          Foreign Keys: customer_id -> customers.id

        Table: customers
          Columns: id (INTEGER, NOT NULL, PK), name (VARCHAR(255), NULL)
          Primary Keys: id
    """
    lines: list[str] = [
        f"Database: {schema.database}  (dialect: {schema.dialect})",
        "",
    ]

    for table in schema.tables:
        lines.append(f"Table: {table.name}")

        # Columns
        col_parts: list[str] = []
        pk_set = set(table.primary_keys)
        for col in table.columns:
            null_flag = "NULL" if col.nullable else "NOT NULL"
            pk_flag = ", PK" if col.name in pk_set else ""
            col_parts.append(f"  {col.name} ({col.type}, {null_flag}{pk_flag})")
        lines.append("  Columns:")
        lines.extend(col_parts)

        # Primary keys
        if table.primary_keys:
            lines.append(f"  Primary Keys: {', '.join(table.primary_keys)}")

        # Foreign keys
        for fk in table.foreign_keys:
            src = ", ".join(fk.constrained_columns)
            dst_cols = ", ".join(fk.referred_columns)
            lines.append(f"  Foreign Key: {src} -> {fk.referred_table}.{dst_cols}")

        lines.append("")  # blank line between tables

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Safety validator (now handled by app.services.sql_validator_service)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Markdown fence stripper
# ---------------------------------------------------------------------------


_FENCE_RE = re.compile(
    r"^\s*```(?:sql)?\s*\n?(.*?)\n?\s*```\s*$",
    re.DOTALL | re.IGNORECASE,
)


def _strip_markdown(text: str) -> str:
    """Remove ```sql … ``` or ``` … ``` wrappers if the model adds them."""
    match = _FENCE_RE.match(text.strip())
    if match:
        return match.group(1).strip()
    return text.strip()


def _expand_wildcards(sql: str, schema: DatabaseSchemaResponse) -> str:
    """
    Expands SELECT * or table.* into explicit column lists.
    """
    import sqlglot
    from sqlglot import exp
    try:
        ast = sqlglot.parse_one(sql, dialect=schema.dialect)
    except Exception:
        return sql
    
    schema_tables = {t.name.lower(): [c.name for c in t.columns] for t in schema.tables}

    for select in ast.find_all(exp.Select):
        table_aliases = {}
        for table in select.find_all(exp.Table):
            alias = table.alias.lower() if table.alias else table.name.lower()
            table_aliases[alias] = table.name.lower()
            
        new_exprs = []
        for projection in select.expressions:
            if isinstance(projection, exp.Star):
                for alias, table_name in table_aliases.items():
                    cols = schema_tables.get(table_name, [])
                    for col in cols:
                        new_exprs.append(exp.column(col, table=alias))
            elif isinstance(projection, exp.Column) and isinstance(projection.this, exp.Star):
                prefix_node = projection.args.get("table")
                if prefix_node:
                    prefix = prefix_node.name.lower()
                    table_name = table_aliases.get(prefix, prefix)
                    cols = schema_tables.get(table_name, [])
                    if cols:
                        for col in cols:
                            new_exprs.append(exp.column(col, table=prefix))
                    else:
                        new_exprs.append(projection)
                else:
                    new_exprs.append(projection)
            else:
                new_exprs.append(projection)
        select.set("expressions", new_exprs)
        
    return ast.sql(dialect=schema.dialect)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SQLGeneratorService:
    """
    Stateless service that translates natural-language questions into SQL.

    A dedicated PydanticAI Agent is constructed lazily on first use so that
    import-time failures (missing API key) surface only at request time,
    consistent with the rest of the application.
    """

    def __init__(self) -> None:
        self._agent: Agent | None = None
        logger.debug("SQLGeneratorService initialised.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        question: str,
        schema: DatabaseSchemaResponse,
        history: list[str] | None = None,
    ) -> SQLGenerationResponse:
        """
        Generate a validated SQL query from a natural-language question.

        Args:
            question: The user's natural-language question.
            schema:   The live database schema to constrain generation.
            history:  Optional list of previous questions to provide context.

        Returns:
            SQLGenerationResponse containing the validated SQL.

        Raises:
            SQLValidationError:  If the generated SQL fails the safety policy.
            SQLGenerationError:  If the AI model call fails.
            ValueError:          If the API key is not configured.
        """
        request_id = f"sql-{int(time.time() * 1000)}"
        t_start = time.perf_counter()

        logger.info(
            "[%s] SQL generation request | question_len=%d | tables=%d | dialect=%s",
            request_id,
            len(question),
            schema.table_count,
            schema.dialect,
        )

        agent = self._get_agent()
        schema_text = _build_schema_section(schema)
        
        prompt_parts = [
            f"Database Schema:\n{schema_text}",
        ]
        
        if history and len(history) > 0:
            prompt_parts.append("Conversation History:")
            for i, past_q in enumerate(history):
                prompt_parts.append(f"Q{i+1}: {past_q}")
            prompt_parts.append("")
            
        prompt_parts.append(f"Question: {question}")
        prompt_parts.append("Return only the SQL query. No explanation. No markdown.")
        
        user_prompt = "\n".join(prompt_parts)

        try:
            result = await agent.run(user_prompt)
            raw_output: str = result.output
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t_start) * 1_000
            logger.exception(
                "[%s] AI model call failed | elapsed=%.1f ms | error=%s: %s",
                request_id,
                elapsed_ms,
                type(exc).__name__,
                exc,
            )
            raise SQLGenerationError(
                f"AI model call failed: {exc}"
            ) from exc

        # Strip any markdown fences the model may have added despite instructions.
        cleaned = _strip_markdown(raw_output)
        
        # Expand wildcards into explicit columns if present
        cleaned = _expand_wildcards(cleaned, schema)

        # Validate safety and schema via sqlglot.
        try:
            validated_sql = validate_sql_schema(cleaned, schema)
        except (SQLValidationError, SQLSchemaValidationError) as exc:
            exc.sql = cleaned
            elapsed_ms = (time.perf_counter() - t_start) * 1_000
            logger.warning(
                "[%s] SQL validation failed | elapsed=%.1f ms | raw_output=%r",
                request_id,
                elapsed_ms,
                raw_output[:200],
            )
            raise exc

        elapsed_ms = (time.perf_counter() - t_start) * 1_000
        logger.info(
            "[%s] SQL generated successfully | elapsed=%.1f ms | sql_len=%d",
            request_id,
            elapsed_ms,
            len(validated_sql),
        )

        return SQLGenerationResponse(
            sql=validated_sql,
            question=question,
            dialect=schema.dialect,
        )

    async def generate_retry(
        self,
        question: str,
        schema: DatabaseSchemaResponse,
        previous_sql: str,
        validation_error: SQLSchemaValidationError,
    ) -> SQLGenerationResponse:
        """
        Generate a validated SQL query attempting to fix a previous schema error.
        """
        request_id = f"sql-retry-{int(time.time() * 1000)}"
        t_start = time.perf_counter()

        logger.info(
            "[%s] SQL retry generation request | error_type=%s | table=%s",
            request_id,
            validation_error.type,
            validation_error.table,
        )

        agent = self._get_agent()
        schema_text = _build_schema_section(schema)
        
        # Build structured feedback
        feedback = f"Validation Error:\n{validation_error.args[0]}\n"
        if validation_error.suggestions:
            feedback += f"Allowed/Suggested alternatives:\n"
            for s in validation_error.suggestions[:20]: # Limit to 20 to avoid context bloat
                feedback += f"- {s}\n"
        
        user_prompt = (
            f"Database Schema:\n{schema_text}\n\n"
            f"Question: {question}\n\n"
            f"Previous SQL:\n{previous_sql}\n\n"
            f"{feedback}\n"
            "Generate ONLY the corrected SQL. Do not invent tables or columns. "
            "Return SQL only. No explanation. No markdown."
        )

        try:
            result = await agent.run(user_prompt)
            raw_output: str = result.output
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t_start) * 1_000
            logger.exception(
                "[%s] AI model call failed on retry | elapsed=%.1f ms | error=%s: %s",
                request_id,
                elapsed_ms,
                type(exc).__name__,
                exc,
            )
            raise SQLGenerationError(f"AI model call failed: {exc}") from exc

        cleaned = _strip_markdown(raw_output)

        try:
            validated_sql = validate_sql_schema(cleaned, schema)
        except (SQLValidationError, SQLSchemaValidationError) as exc:
            exc.sql = cleaned
            elapsed_ms = (time.perf_counter() - t_start) * 1_000
            logger.warning(
                "[%s] SQL validation failed on retry | elapsed=%.1f ms | raw_output=%r",
                request_id,
                elapsed_ms,
                raw_output[:200],
            )
            raise exc

        elapsed_ms = (time.perf_counter() - t_start) * 1_000
        logger.info(
            "[%s] SQL generated successfully on retry | elapsed=%.1f ms",
            request_id,
            elapsed_ms,
        )

        return SQLGenerationResponse(
            sql=validated_sql,
            question=question,
            dialect=schema.dialect,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_agent(self) -> Agent:
        """
        Return the lazily-constructed dedicated SQL generation agent.

        This agent uses the same underlying model as the main chat agent but
        carries a SQL-specific system prompt to maximise output quality.
        """
        if self._agent is None:
            # Instantiate the LLM model from the provider factory
            model = get_llm_model()
            self._agent = Agent(model=model, system_prompt=_SYSTEM_PROMPT)
            logger.info(
                "SQL generation agent initialised with model '%s'.",
                settings.GROQ_MODEL,
            )
        return self._agent


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
sql_generator_service = SQLGeneratorService()
