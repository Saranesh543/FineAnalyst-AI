"""
Unit and integration tests for the SQL Generation module.

Covers:
  - validate_sql()             — allow-list and deny-list cases
  - _strip_markdown()          — markdown fence removal
  - _build_schema_section()    — prompt construction
  - SQLGeneratorService.generate() — mocked AI agent
  - POST /api/v1/sql/generate  — full endpoint happy-path and error paths

Run with:
    pytest tests/test_sql_generator.py -v
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_schema(tables=True):
    """Return a DatabaseSchemaResponse with one table (or empty)."""
    from app.schemas.database_schema import (
        ColumnInfo,
        DatabaseSchemaResponse,
        ForeignKeyInfo,
        TableInfo,
    )

    if not tables:
        return DatabaseSchemaResponse(
            database="test.db",
            dialect="sqlite",
            table_count=0,
            tables=[],
            is_empty=True,
            message="No tables were found in the connected database.",
        )

    return DatabaseSchemaResponse(
        database="test.db",
        dialect="sqlite",
        table_count=2,
        is_empty=False,
        tables=[
            TableInfo(
                name="orders",
                columns=[
                    ColumnInfo(name="id", type="INTEGER", nullable=False, autoincrement=True),
                    ColumnInfo(name="customer_id", type="INTEGER", nullable=False),
                    ColumnInfo(name="total", type="REAL", nullable=True),
                ],
                primary_keys=["id"],
                foreign_keys=[
                    ForeignKeyInfo(
                        constrained_columns=["customer_id"],
                        referred_table="customers",
                        referred_columns=["id"],
                    )
                ],
            ),
            TableInfo(
                name="customers",
                columns=[
                    ColumnInfo(name="id", type="INTEGER", nullable=False, autoincrement=True),
                    ColumnInfo(name="name", type="VARCHAR(255)", nullable=True),
                ],
                primary_keys=["id"],
                foreign_keys=[],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# validate_sql — allow-list cases
# ---------------------------------------------------------------------------


class TestValidateSqlAllowed:
    """SQL that should pass the safety validator."""

    def test_simple_select(self):
        from app.services.sql_generator_service import validate_sql
        sql = validate_sql("SELECT id, name FROM customers")
        assert sql.startswith("SELECT")
        assert sql.endswith(";")

    def test_select_with_where(self):
        from app.services.sql_generator_service import validate_sql
        sql = validate_sql("SELECT * FROM orders WHERE total > 100 ORDER BY total DESC LIMIT 10")
        assert "WHERE" in sql

    def test_select_with_join(self):
        from app.services.sql_generator_service import validate_sql
        sql = validate_sql(
            "SELECT c.name, SUM(o.total) "
            "FROM customers c JOIN orders o ON c.id = o.customer_id "
            "GROUP BY c.name"
        )
        assert "JOIN" in sql

    def test_with_cte(self):
        from app.services.sql_generator_service import validate_sql
        sql = validate_sql(
            "WITH ranked AS (SELECT id, total FROM orders) SELECT * FROM ranked"
        )
        assert sql.startswith("WITH")

    def test_semicolon_appended(self):
        from app.services.sql_generator_service import validate_sql
        sql = validate_sql("SELECT 1")
        assert sql == "SELECT 1;"

    def test_existing_semicolon_not_doubled(self):
        from app.services.sql_generator_service import validate_sql
        sql = validate_sql("SELECT 1;")
        assert sql == "SELECT 1;"

    def test_case_insensitive_select(self):
        from app.services.sql_generator_service import validate_sql
        sql = validate_sql("select id from customers")
        assert sql.lower().startswith("select")

    def test_group_by_having(self):
        from app.services.sql_generator_service import validate_sql
        sql = validate_sql(
            "SELECT customer_id, COUNT(*) AS cnt FROM orders "
            "GROUP BY customer_id HAVING cnt > 5"
        )
        assert "HAVING" in sql.upper()


# ---------------------------------------------------------------------------
# validate_sql — deny-list cases
# ---------------------------------------------------------------------------


class TestValidateSqlForbidden:
    """SQL that must be rejected by the safety validator."""

    @pytest.mark.parametrize("bad_sql", [
        "INSERT INTO orders VALUES (1, 2, 99.9)",
        "UPDATE orders SET total = 0",
        "DELETE FROM orders",
        "DROP TABLE orders",
        "ALTER TABLE orders ADD COLUMN flag INT",
        "CREATE TABLE foo (id INT)",
        "TRUNCATE TABLE orders",
        "MERGE INTO orders USING ...",
        "EXEC sp_help 'orders'",
        "EXECUTE sp_help",
    ])
    def test_forbidden_statement(self, bad_sql):
        from app.services.sql_generator_service import validate_sql, SQLValidationError
        with pytest.raises(SQLValidationError):
            validate_sql(bad_sql)

    def test_select_with_hidden_drop(self):
        """Deny-list must catch dangerous keywords even inside SELECT."""
        from app.services.sql_generator_service import validate_sql, SQLValidationError
        with pytest.raises(SQLValidationError):
            validate_sql("SELECT * FROM orders; DROP TABLE orders;")

    def test_empty_sql_raises(self):
        from app.services.sql_generator_service import validate_sql, SQLValidationError
        with pytest.raises(SQLValidationError, match="empty"):
            validate_sql("   ")

    def test_unknown_leading_keyword_raises(self):
        from app.services.sql_generator_service import validate_sql, SQLValidationError
        with pytest.raises(SQLValidationError, match="not allowed"):
            validate_sql("SHOW TABLES")


# ---------------------------------------------------------------------------
# _strip_markdown
# ---------------------------------------------------------------------------


class TestStripMarkdown:
    def test_sql_fence_removed(self):
        from app.services.sql_generator_service import _strip_markdown
        raw = "```sql\nSELECT 1;\n```"
        assert _strip_markdown(raw) == "SELECT 1;"

    def test_plain_fence_removed(self):
        from app.services.sql_generator_service import _strip_markdown
        raw = "```\nSELECT 1;\n```"
        assert _strip_markdown(raw) == "SELECT 1;"

    def test_no_fence_unchanged(self):
        from app.services.sql_generator_service import _strip_markdown
        raw = "SELECT 1;"
        assert _strip_markdown(raw) == "SELECT 1;"

    def test_whitespace_stripped(self):
        from app.services.sql_generator_service import _strip_markdown
        raw = "  SELECT 1;  "
        assert _strip_markdown(raw) == "SELECT 1;"


# ---------------------------------------------------------------------------
# _build_schema_section
# ---------------------------------------------------------------------------


class TestBuildSchemaSection:
    def test_contains_table_name(self):
        from app.services.sql_generator_service import _build_schema_section
        schema = _make_schema()
        text = _build_schema_section(schema)
        assert "orders" in text
        assert "customers" in text

    def test_contains_column_names(self):
        from app.services.sql_generator_service import _build_schema_section
        schema = _make_schema()
        text = _build_schema_section(schema)
        assert "customer_id" in text
        assert "total" in text

    def test_contains_foreign_key(self):
        from app.services.sql_generator_service import _build_schema_section
        schema = _make_schema()
        text = _build_schema_section(schema)
        assert "customers" in text
        assert "->" in text

    def test_contains_pk_marker(self):
        from app.services.sql_generator_service import _build_schema_section
        schema = _make_schema()
        text = _build_schema_section(schema)
        assert "PK" in text

    def test_contains_dialect(self):
        from app.services.sql_generator_service import _build_schema_section
        schema = _make_schema()
        text = _build_schema_section(schema)
        assert "sqlite" in text


# ---------------------------------------------------------------------------
# SQLGeneratorService.generate — mocked agent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_returns_sql_response():
    """generate() should return SQLGenerationResponse when the model returns clean SQL."""
    mock_result = MagicMock()
    mock_result.output = "SELECT id, name FROM customers ORDER BY name LIMIT 5;"

    with patch(
        "app.services.sql_generator_service.SQLGeneratorService._get_agent"
    ) as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_get_agent.return_value = mock_agent

        from app.services.sql_generator_service import sql_generator_service

        schema = _make_schema()
        result = await sql_generator_service.generate(
            question="List customers by name", schema=schema
        )

    assert result.sql.startswith("SELECT")
    assert result.sql.endswith(";")
    assert result.question == "List customers by name"
    assert result.dialect == "sqlite"


@pytest.mark.asyncio
async def test_generate_strips_markdown_fences():
    """generate() should strip ```sql ... ``` wrappers before validation."""
    mock_result = MagicMock()
    mock_result.output = "```sql\nSELECT * FROM orders;\n```"

    with patch(
        "app.services.sql_generator_service.SQLGeneratorService._get_agent"
    ) as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_get_agent.return_value = mock_agent

        from app.services.sql_generator_service import sql_generator_service

        result = await sql_generator_service.generate(
            question="All orders", schema=_make_schema()
        )

    assert result.sql == "SELECT * FROM orders;"


@pytest.mark.asyncio
async def test_generate_raises_validation_error_on_forbidden_sql():
    """generate() must raise SQLValidationError when model returns a forbidden statement."""
    from app.services.sql_generator_service import SQLValidationError

    mock_result = MagicMock()
    mock_result.output = "DROP TABLE orders;"

    with patch(
        "app.services.sql_generator_service.SQLGeneratorService._get_agent"
    ) as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_get_agent.return_value = mock_agent

        from app.services.sql_generator_service import sql_generator_service

        with pytest.raises(SQLValidationError):
            await sql_generator_service.generate(
                question="Drop the orders table", schema=_make_schema()
            )


@pytest.mark.asyncio
async def test_generate_raises_sql_generation_error_on_api_failure():
    """generate() must raise SQLGenerationError when the AI call fails."""
    from app.services.sql_generator_service import SQLGenerationError

    with patch(
        "app.services.sql_generator_service.SQLGeneratorService._get_agent"
    ) as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("Provider unavailable"))
        mock_get_agent.return_value = mock_agent

        from app.services.sql_generator_service import sql_generator_service

        with pytest.raises(SQLGenerationError, match="Provider unavailable"):
            await sql_generator_service.generate(
                question="Sales total", schema=_make_schema()
            )


# ---------------------------------------------------------------------------
# POST /api/v1/sql/generate — endpoint integration
# ---------------------------------------------------------------------------


def _mock_schema_and_sql(sql_output: str):
    """Context-manager factory that mocks schema_service and sql_generator_service."""
    from app.schemas.sql import SQLGenerationResponse

    schema = _make_schema()

    mock_response = SQLGenerationResponse(
        sql=sql_output,
        question="Top 5 products by revenue",
        dialect="sqlite",
    )

    schema_patch = patch(
        "app.services.schema_service.schema_service.get_schema",
        new=AsyncMock(return_value=schema),
    )
    sql_patch = patch(
        "app.services.sql_generator_service.sql_generator_service.generate",
        new=AsyncMock(return_value=mock_response),
    )
    return schema_patch, sql_patch


@pytest.mark.asyncio
async def test_sql_generate_endpoint_returns_200():
    """POST /api/v1/sql/generate should return HTTP 200 with sql field."""
    schema_patch, sql_patch = _mock_schema_and_sql(
        "SELECT name, SUM(total) AS revenue FROM orders "
        "JOIN customers ON orders.customer_id = customers.id "
        "GROUP BY name ORDER BY revenue DESC LIMIT 5;"
    )

    with schema_patch, sql_patch:
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/sql/generate",
                json={"question": "Top 5 products by revenue"},
            )

    assert response.status_code == 200, response.text
    body = response.json()
    assert "sql" in body
    assert body["sql"].upper().startswith("SELECT")
    assert body["question"] == "Top 5 products by revenue"
    assert body["dialect"] == "sqlite"


@pytest.mark.asyncio
async def test_sql_generate_endpoint_returns_422_on_empty_question():
    """Empty question must be rejected by Pydantic validation (HTTP 422)."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/sql/generate",
            json={"question": ""},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sql_generate_endpoint_returns_422_on_validation_error():
    """SQLValidationError from the service must map to HTTP 422."""
    from app.services.sql_generator_service import SQLValidationError

    schema = _make_schema()

    with (
        patch(
            "app.services.schema_service.schema_service.get_schema",
            new=AsyncMock(return_value=schema),
        ),
        patch(
            "app.services.sql_generator_service.sql_generator_service.generate",
            new=AsyncMock(side_effect=SQLValidationError("Forbidden keyword DROP")),
        ),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/sql/generate",
                json={"question": "Drop the orders table"},
            )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "sql_validation_error"
    assert "DROP" in body["message"]


@pytest.mark.asyncio
async def test_sql_generate_endpoint_returns_500_on_model_error():
    """SQLGenerationError from the service must map to HTTP 500."""
    from app.services.sql_generator_service import SQLGenerationError

    schema = _make_schema()

    with (
        patch(
            "app.services.schema_service.schema_service.get_schema",
            new=AsyncMock(return_value=schema),
        ),
        patch(
            "app.services.sql_generator_service.sql_generator_service.generate",
            new=AsyncMock(side_effect=SQLGenerationError("Model timeout")),
        ),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/sql/generate",
                json={"question": "Sales total"},
            )

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "sql_generation_error"


@pytest.mark.asyncio
async def test_sql_generate_endpoint_returns_422_on_empty_schema():
    """When the DB has no tables the endpoint must return 422, not 500."""
    empty_schema = _make_schema(tables=False)

    with patch(
        "app.services.schema_service.schema_service.get_schema",
        new=AsyncMock(return_value=empty_schema),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/sql/generate",
                json={"question": "Show me all data"},
            )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "empty_schema"


@pytest.mark.asyncio
async def test_sql_generate_endpoint_returns_500_on_schema_error():
    """SchemaDiscoveryError must map to HTTP 500."""
    from app.services.schema_service import SchemaDiscoveryError

    with patch(
        "app.services.schema_service.schema_service.get_schema",
        new=AsyncMock(side_effect=SchemaDiscoveryError("DB unreachable")),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/sql/generate",
                json={"question": "Any question"},
            )

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "schema_discovery_error"


# ---------------------------------------------------------------------------
# Schema model validation
# ---------------------------------------------------------------------------


def test_sql_generation_request_strips_whitespace():
    from app.schemas.sql import SQLGenerationRequest
    req = SQLGenerationRequest(question="  Top 5 products  ")
    assert req.question == "Top 5 products"


def test_sql_generation_request_rejects_too_short():
    from app.schemas.sql import SQLGenerationRequest
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        SQLGenerationRequest(question="ab")


def test_sql_generation_response_fields():
    from app.schemas.sql import SQLGenerationResponse
    resp = SQLGenerationResponse(
        sql="SELECT 1;",
        question="test",
        dialect="sqlite",
    )
    data = resp.model_dump(mode="json")
    assert "sql" in data
    assert "question" in data
    assert "dialect" in data
