"""
Schema Service Module

Provides SchemaService — the entry-point for all database schema discovery
operations.

Responsibilities:
  - Use SQLAlchemy's async Inspector to introspect the live database.
  - Discover tables, columns (name, type, nullable, default, autoincrement),
    primary keys, foreign keys, and indexes.
  - Derive a human-readable database name from the connection URL.
  - Return a fully-typed DatabaseSchemaResponse without exposing raw
    SQLAlchemy internals to callers.
  - Emit structured log entries for every discovery run.
  - Handle inspector errors gracefully (re-raise as SchemaDiscoveryError).

Usage::

    from app.services.schema_service import schema_service

    schema = await schema_service.get_schema()
"""

from __future__ import annotations

import logging
import time
from urllib.parse import urlparse

from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.database.session import engine
from app.schemas.database_schema import (
    ColumnInfo,
    DatabaseSchemaResponse,
    ForeignKeyInfo,
    IndexInfo,
    TableInfo,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class SchemaDiscoveryError(RuntimeError):
    """Raised when schema introspection fails unexpectedly."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SchemaService:
    """
    Stateless service that introspects the connected database.

    A single shared instance (``schema_service``) is created at module level
    and injected into FastAPI route handlers.  The underlying SQLAlchemy
    engine is resolved from ``app.database.session.engine`` so there is
    no engine duplication.
    """

    def __init__(self, db_engine: AsyncEngine) -> None:
        self._engine = db_engine
        logger.debug("SchemaService initialised with engine: %s", db_engine.url)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_schema(self) -> DatabaseSchemaResponse:
        """
        Discover and return the full database schema.

        Returns:
            DatabaseSchemaResponse containing all table metadata.

        Raises:
            SchemaDiscoveryError: On any inspector-level failure.
        """
        t_start = time.perf_counter()
        logger.info("Schema discovery started | url=%s", self._engine.url)

        try:
            async with self._engine.connect() as conn:
                schema = await self._introspect(conn)

            elapsed_ms = (time.perf_counter() - t_start) * 1_000
            logger.info(
                "Schema discovery complete | tables=%d | elapsed=%.1f ms",
                schema.table_count,
                elapsed_ms,
            )
            return schema

        except SchemaDiscoveryError:
            raise
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t_start) * 1_000
            logger.exception(
                "Schema discovery failed | elapsed=%.1f ms | error=%s: %s",
                elapsed_ms,
                type(exc).__name__,
                exc,
            )
            raise SchemaDiscoveryError(
                f"Failed to discover database schema: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    async def _introspect(self, conn: AsyncConnection) -> DatabaseSchemaResponse:
        """Run the full introspection against an open connection."""
        # --- Database name -------------------------------------------------
        database_name = self._derive_database_name(self._engine)
        dialect = self._engine.dialect.name

        # --- Table list ----------------------------------------------------
        table_names: list[str] = await conn.run_sync(
            lambda sync_conn: sa_inspect(sync_conn).get_table_names()
        )
        logger.debug("Discovered tables: %s", table_names)

        # ---- Empty-database fast path ------------------------------------
        if not table_names:
            logger.info(
                "No tables found in database '%s' — returning empty schema.",
                database_name,
            )
            return DatabaseSchemaResponse(
                database=database_name,
                dialect=dialect,
                table_count=0,
                tables=[],
                is_empty=True,
                message="No tables were found in the connected database.",
            )

        tables: list[TableInfo] = []
        for table_name in sorted(table_names):
            table_info = await self._introspect_table(conn, table_name)
            tables.append(table_info)

        return DatabaseSchemaResponse(
            database=database_name,
            dialect=dialect,
            table_count=len(tables),
            tables=tables,
            is_empty=False,
        )

    async def _introspect_table(
        self, conn: AsyncConnection, table_name: str
    ) -> TableInfo:
        """Collect all metadata for a single table."""

        def _sync_introspect(sync_conn):
            insp = sa_inspect(sync_conn)
            columns_raw = insp.get_columns(table_name)
            pk_constraint = insp.get_pk_constraint(table_name)
            fk_list = insp.get_foreign_keys(table_name)
            index_list = insp.get_indexes(table_name)
            return columns_raw, pk_constraint, fk_list, index_list

        columns_raw, pk_constraint, fk_list, index_list = await conn.run_sync(
            _sync_introspect
        )

        # Columns -----------------------------------------------------------
        columns = [
            ColumnInfo(
                name=col["name"],
                type=str(col["type"]),
                nullable=col.get("nullable", True),
                default=col.get("default"),
                autoincrement=col.get("autoincrement", False) is True,
                comment=col.get("comment"),
            )
            for col in columns_raw
        ]

        # Primary keys ------------------------------------------------------
        primary_keys: list[str] = pk_constraint.get("constrained_columns", [])

        # Foreign keys -------------------------------------------------------
        foreign_keys = [
            ForeignKeyInfo(
                name=fk.get("name"),
                constrained_columns=fk.get("constrained_columns", []),
                referred_table=fk.get("referred_table", ""),
                referred_columns=fk.get("referred_columns", []),
            )
            for fk in fk_list
        ]

        # Indexes ------------------------------------------------------------
        # Exclude any index that is simply the primary-key constraint.
        pk_set = set(primary_keys)
        indexes = [
            IndexInfo(
                name=idx.get("name"),
                columns=idx.get("column_names", []),
                unique=idx.get("unique", False),
            )
            for idx in index_list
            if set(idx.get("column_names", [])) != pk_set
        ]

        # Row count (best-effort — silently omit if the query fails) ---------
        row_count: int | None = None
        try:
            result = await conn.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")  # noqa: S608
            )
            row_count = result.scalar()
        except Exception:  # noqa: BLE001
            logger.debug(
                "Row-count query failed for table '%s' — skipping.", table_name
            )

        logger.debug(
            "Introspected table '%s' | columns=%d | pks=%s | fks=%d | indexes=%d | rows=%s",
            table_name,
            len(columns),
            primary_keys,
            len(foreign_keys),
            len(indexes),
            row_count,
        )

        return TableInfo(
            name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            indexes=indexes,
            row_count=row_count,
        )

    @staticmethod
    def _derive_database_name(db_engine: AsyncEngine) -> str:
        """
        Derive a human-readable database name from the engine URL.

        - SQLite: returns the filename (e.g. ``fineanalyst.db``).
        - PostgreSQL / MySQL: returns the database name component.
        - Fallback: the raw URL string (credentials stripped).
        """
        url = str(db_engine.url)
        parsed = urlparse(url)

        # SQLite: path looks like ``///./fineanalyst.db``
        if "sqlite" in url:
            path = parsed.path.lstrip("/").lstrip("./")
            return path or "sqlite"

        # Standard RDBMS: last path segment is the DB name.
        db_name = parsed.path.lstrip("/")
        return db_name or parsed.netloc or url


# ---------------------------------------------------------------------------
# Module-level singleton — shared across all FastAPI requests.
# ---------------------------------------------------------------------------
schema_service = SchemaService(db_engine=engine)
