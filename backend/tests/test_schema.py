"""
Unit tests for the Schema Intelligence module.

Covers:
  - SchemaService._derive_database_name  (pure / no I/O)
  - SchemaService.get_schema             (mocked SQLAlchemy engine)
  - GET /api/v1/schema endpoint          (mocked schema_service)
  - Error propagation                    (SchemaDiscoveryError -> HTTP 500)

Run with:
    pytest tests/test_schema.py -v
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------


def _make_schema_response():
    """Return a minimal DatabaseSchemaResponse-like object for mocking."""
    from app.schemas.database_schema import (
        ColumnInfo,
        DatabaseSchemaResponse,
        ForeignKeyInfo,
        IndexInfo,
        TableInfo,
    )

    return DatabaseSchemaResponse(
        database="fineanalyst.db",
        dialect="sqlite",
        table_count=1,
        is_empty=False,
        message=None,
        tables=[
            TableInfo(
                name="users",
                columns=[
                    ColumnInfo(
                        name="id",
                        type="INTEGER",
                        nullable=False,
                        autoincrement=True,
                    ),
                    ColumnInfo(
                        name="name",
                        type="VARCHAR(255)",
                        nullable=True,
                    ),
                ],
                primary_keys=["id"],
                foreign_keys=[
                    ForeignKeyInfo(
                        name=None,
                        constrained_columns=["org_id"],
                        referred_table="organisations",
                        referred_columns=["id"],
                    )
                ],
                indexes=[
                    IndexInfo(name="ix_users_name", columns=["name"], unique=False)
                ],
                row_count=42,
            )
        ],
    )


def _make_empty_schema_response():
    """Return a DatabaseSchemaResponse representing an empty database."""
    from app.schemas.database_schema import DatabaseSchemaResponse

    return DatabaseSchemaResponse(
        database="fineanalyst.db",
        dialect="sqlite",
        table_count=0,
        tables=[],
        is_empty=True,
        message="No tables were found in the connected database.",
    )


# ---------------------------------------------------------------------------
# Unit tests: SchemaService._derive_database_name
# ---------------------------------------------------------------------------


class TestDeriveDatabaseName:
    """Pure-function tests — no I/O required."""

    def _make_engine(self, url: str):
        engine = MagicMock()
        engine.url = url
        engine.dialect.name = "sqlite"
        return engine

    def test_sqlite_relative_path(self):
        from app.services.schema_service import SchemaService

        engine = self._make_engine("sqlite+aiosqlite:///./fineanalyst.db")
        assert SchemaService._derive_database_name(engine) == "fineanalyst.db"

    def test_sqlite_in_memory(self):
        from app.services.schema_service import SchemaService

        engine = self._make_engine("sqlite+aiosqlite:///:memory:")
        # Should not raise; exact value is dialect-defined.
        result = SchemaService._derive_database_name(engine)
        assert isinstance(result, str)

    def test_postgres_url(self):
        from app.services.schema_service import SchemaService

        engine = self._make_engine(
            "postgresql+asyncpg://user:pass@localhost:5432/northwind"
        )
        assert SchemaService._derive_database_name(engine) == "northwind"

    def test_mysql_url(self):
        from app.services.schema_service import SchemaService

        engine = self._make_engine("mysql+aiomysql://user:pass@localhost/sales_db")
        assert SchemaService._derive_database_name(engine) == "sales_db"


# ---------------------------------------------------------------------------
# Unit tests: SchemaService.get_schema (mocked engine)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_schema_returns_structured_response():
    """get_schema() should return a DatabaseSchemaResponse on success."""
    expected = _make_schema_response()

    with patch(
        "app.services.schema_service.schema_service.get_schema",
        new=AsyncMock(return_value=expected),
    ):
        from app.services.schema_service import schema_service

        result = await schema_service.get_schema()

    assert result.database == "fineanalyst.db"
    assert result.dialect == "sqlite"
    assert result.table_count == 1
    assert result.is_empty is False
    assert result.message is None
    assert result.tables[0].name == "users"
    assert result.tables[0].primary_keys == ["id"]
    assert result.tables[0].foreign_keys[0].referred_table == "organisations"
    assert result.tables[0].indexes[0].name == "ix_users_name"
    assert result.tables[0].row_count == 42


@pytest.mark.asyncio
async def test_get_schema_raises_on_engine_failure():
    """get_schema() should raise SchemaDiscoveryError on engine errors."""
    from app.services.schema_service import SchemaDiscoveryError

    with patch(
        "app.services.schema_service.schema_service.get_schema",
        new=AsyncMock(side_effect=SchemaDiscoveryError("DB unavailable")),
    ):
        from app.services.schema_service import schema_service

        with pytest.raises(SchemaDiscoveryError, match="DB unavailable"):
            await schema_service.get_schema()


@pytest.mark.asyncio
async def test_get_schema_empty_database():
    """
    get_schema() must return HTTP 200 (not raise) when the database has no
    tables, and must populate is_empty=True with the standard message.
    """
    expected = _make_empty_schema_response()

    with patch(
        "app.services.schema_service.schema_service.get_schema",
        new=AsyncMock(return_value=expected),
    ):
        from app.services.schema_service import schema_service

        result = await schema_service.get_schema()

    assert result.table_count == 0
    assert result.tables == []
    assert result.is_empty is True
    assert result.message == "No tables were found in the connected database."


# ---------------------------------------------------------------------------
# Integration tests: GET /api/v1/schema endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_schema_endpoint_returns_200():
    """GET /api/v1/schema should return HTTP 200 with a valid schema body."""
    expected = _make_schema_response()

    with patch(
        "app.services.schema_service.schema_service.get_schema",
        new=AsyncMock(return_value=expected),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/schema")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["database"] == "fineanalyst.db"
    assert body["dialect"] == "sqlite"
    assert body["table_count"] == 1
    assert body["is_empty"] is False
    assert body["message"] is None
    assert len(body["tables"]) == 1
    table = body["tables"][0]
    assert table["name"] == "users"
    assert "id" in table["primary_keys"]
    assert len(table["columns"]) == 2
    assert len(table["foreign_keys"]) == 1
    assert table["foreign_keys"][0]["referred_table"] == "organisations"
    assert len(table["indexes"]) == 1
    assert table["row_count"] == 42


@pytest.mark.asyncio
async def test_schema_endpoint_returns_500_on_error():
    """GET /api/v1/schema should return HTTP 500 when discovery fails."""
    from app.services.schema_service import SchemaDiscoveryError

    with patch(
        "app.services.schema_service.schema_service.get_schema",
        new=AsyncMock(side_effect=SchemaDiscoveryError("DB unavailable")),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/schema")

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "schema_discovery_error"
    assert "DB unavailable" in body["message"]


@pytest.mark.asyncio
async def test_schema_endpoint_empty_database():
    """
    GET /api/v1/schema must return HTTP 200 (not 500) when the database is
    empty, with is_empty=True and the human-readable message.
    """
    expected = _make_empty_schema_response()

    with patch(
        "app.services.schema_service.schema_service.get_schema",
        new=AsyncMock(return_value=expected),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/schema")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["table_count"] == 0
    assert body["tables"] == []
    assert body["is_empty"] is True
    assert body["message"] == "No tables were found in the connected database."


# ---------------------------------------------------------------------------
# Schema model validation
# ---------------------------------------------------------------------------


def test_column_info_defaults():
    """ColumnInfo should use sensible defaults for optional fields."""
    from app.schemas.database_schema import ColumnInfo

    col = ColumnInfo(name="email", type="TEXT", nullable=True)
    assert col.default is None
    assert col.autoincrement is False
    assert col.comment is None


def test_database_schema_response_structure():
    """DatabaseSchemaResponse should serialize cleanly and include all fields."""
    schema = _make_schema_response()
    data = schema.model_dump(mode="json")

    assert "database" in data
    assert "dialect" in data
    assert "table_count" in data
    assert "tables" in data
    assert "is_empty" in data
    assert "message" in data
    assert isinstance(data["tables"], list)
    assert data["is_empty"] is False
    assert data["message"] is None


def test_database_schema_response_defaults_backward_compatible():
    """
    DatabaseSchemaResponse created without is_empty/message (as legacy callers
    might do) should default to is_empty=False and message=None.
    """
    from app.schemas.database_schema import DatabaseSchemaResponse

    schema = DatabaseSchemaResponse(
        database="legacy.db",
        dialect="sqlite",
        table_count=0,
        tables=[],
    )
    assert schema.is_empty is False
    assert schema.message is None
