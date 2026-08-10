"""
Unit and integration tests for the SQL Execution module.

Covers:
  - validate_execution_sql()   — allow-list and deny-list cases (must be strict)
  - SQLExecutorService.execute_sql() — DB execution (mocked and actual)
  - POST /api/v1/sql/execute   — endpoint integration, errors, structure

Run with:
    pytest tests/test_sql_executor.py -v
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.execution import (
    SQLExecutionRequest,
    SQLExecutionResponse,
)


# ---------------------------------------------------------------------------
# Validation Tests (1-15)
# ---------------------------------------------------------------------------

class TestValidateExecutionSqlAllowed:
    def test_valid_select(self):
        from app.services.sql_executor_service import validate_execution_sql
        sql = validate_execution_sql("SELECT * FROM users")
        assert sql.startswith("SELECT")
        assert sql.endswith(";")

    def test_valid_with(self):
        from app.services.sql_executor_service import validate_execution_sql
        sql = validate_execution_sql("WITH data AS (SELECT 1) SELECT * FROM data")
        assert sql.startswith("WITH")

    def test_case_insensitive_select(self):
        from app.services.sql_executor_service import validate_execution_sql
        sql = validate_execution_sql("select id from orders")
        assert sql.lower().startswith("select")

    def test_whitespace_trimmed(self):
        from app.services.sql_executor_service import validate_execution_sql
        sql = validate_execution_sql("   SELECT 1;   ")
        assert sql == "SELECT 1;"

    def test_valid_complex_select(self):
        from app.services.sql_executor_service import validate_execution_sql
        sql = validate_execution_sql(
            "SELECT a.id, b.name FROM a JOIN b ON a.b_id = b.id WHERE a.id > 10 ORDER BY b.name LIMIT 5"
        )
        assert "JOIN" in sql


class TestValidateExecutionSqlForbidden:
    @pytest.mark.parametrize("bad_sql", [
        "INSERT INTO users (name) VALUES ('test')",
        "UPDATE users SET name = 'test'",
        "DELETE FROM users",
        "DROP TABLE users",
        "ALTER TABLE users ADD email TEXT",
        "CREATE TABLE logs (id INT)",
        "TRUNCATE TABLE users",
        "ATTACH DATABASE 'test.db' AS test",
        "DETACH DATABASE test",
        "PRAGMA foreign_keys = ON",
        "VACUUM",
        "REINDEX users",
    ])
    def test_forbidden_keywords_rejected(self, bad_sql):
        from app.services.sql_executor_service import validate_execution_sql, SQLExecutionValidationError
        with pytest.raises(SQLExecutionValidationError):
            validate_execution_sql(bad_sql)

    def test_forbidden_keyword_in_subquery_rejected(self):
        from app.services.sql_executor_service import validate_execution_sql, SQLExecutionValidationError
        with pytest.raises(SQLExecutionValidationError):
            validate_execution_sql("SELECT * FROM (DROP TABLE users)")

    def test_empty_sql_rejected(self):
        from app.services.sql_executor_service import validate_execution_sql, SQLExecutionValidationError
        with pytest.raises(SQLExecutionValidationError):
            validate_execution_sql("   ")

    def test_unknown_statement_rejected(self):
        from app.services.sql_executor_service import validate_execution_sql, SQLExecutionValidationError
        with pytest.raises(SQLExecutionValidationError, match="not allowed"):
            validate_execution_sql("SHOW TABLES")


# ---------------------------------------------------------------------------
# Executor Service Tests (16-22)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_sql_success_multiple_rows():
    """Execution returns structured multiple rows."""
    mock_result = MagicMock()
    mock_result.returns_rows = True
    mock_result.keys.return_value = ["id", "name"]
    mock_result.all.return_value = [(1, "Alice"), (2, "Bob")]

    engine = MagicMock()
    conn_ctx = MagicMock()
    conn_ctx.__aenter__ = AsyncMock(return_value=conn_ctx)
    conn_ctx.__aexit__ = AsyncMock()
    conn_ctx.execute = AsyncMock(return_value=mock_result)
    engine.connect.return_value = conn_ctx

    from app.services.sql_executor_service import SQLExecutorService
    service = SQLExecutorService(engine)
    
    response = await service.execute_sql("SELECT * FROM users")
    assert response.row_count == 2
    assert response.columns == ["Id", "Name"]
    assert response.rows == [[1, "Alice"], [2, "Bob"]]
    assert response.execution_time_ms >= 0


@pytest.mark.asyncio
async def test_execute_sql_success_one_row():
    """Execution returns one row correctly."""
    mock_result = MagicMock()
    mock_result.returns_rows = True
    mock_result.keys.return_value = ["count"]
    mock_result.all.return_value = [(42,)]

    engine = MagicMock()
    conn_mock = AsyncMock()
    conn_mock.execute.return_value = mock_result
    engine.connect.return_value.__aenter__.return_value = conn_mock

    from app.services.sql_executor_service import SQLExecutorService
    service = SQLExecutorService(engine)
    
    response = await service.execute_sql("SELECT COUNT(*) as count FROM users")
    assert response.row_count == 1
    assert response.columns == ["Count"]
    assert response.rows == [[42]]


@pytest.mark.asyncio
async def test_execute_sql_success_empty_result():
    """Execution returns empty result correctly."""
    mock_result = MagicMock()
    mock_result.returns_rows = True
    mock_result.keys.return_value = ["Id", "Name"]
    mock_result.all.return_value = []

    engine = MagicMock()
    conn_ctx = MagicMock()
    conn_ctx.__aenter__ = AsyncMock(return_value=conn_ctx)
    conn_ctx.__aexit__ = AsyncMock()
    conn_ctx.execute = AsyncMock(return_value=mock_result)
    engine.connect.return_value = conn_ctx

    from app.services.sql_executor_service import SQLExecutorService
    service = SQLExecutorService(engine)
    
    response = await service.execute_sql("SELECT * FROM users WHERE id = -1")
    assert response.row_count == 0
    assert response.columns == ["Id", "Name"]
    assert response.rows == []


@pytest.mark.asyncio
async def test_execute_sql_database_failure():
    """Database exception maps to SQLExecutionFailedError."""
    engine = MagicMock()
    # Create an AsyncMock for the connection context manager
    conn_mock = AsyncMock()
    conn_mock.execute.side_effect = RuntimeError("DB timeout")
    
    # When engine.connect() is used in 'async with', it will return conn_mock
    engine.connect.return_value.__aenter__.return_value = conn_mock

    from app.services.sql_executor_service import SQLExecutorService, SQLExecutionFailedError
    service = SQLExecutorService(engine)
    
    with pytest.raises(SQLExecutionFailedError, match="DB timeout"):
        await service.execute_sql("SELECT * FROM users")


@pytest.mark.asyncio
async def test_execute_sql_validation_failure_before_execution():
    """Execution intercepts bad SQL before hitting DB."""
    engine = MagicMock()
    from app.services.sql_executor_service import SQLExecutorService, SQLExecutionValidationError
    service = SQLExecutorService(engine)
    
    with pytest.raises(SQLExecutionValidationError):
        await service.execute_sql("DROP TABLE users")
    
    engine.connect.assert_not_called()


def test_singleton_behaviour():
    from app.services.sql_executor_service import sql_executor_service, SQLExecutorService
    assert isinstance(sql_executor_service, SQLExecutorService)
    assert sql_executor_service is not None


# ---------------------------------------------------------------------------
# API Endpoint Tests (23-32)
# ---------------------------------------------------------------------------

def _mock_execute_success():
    """Return a success execution response."""
    return SQLExecutionResponse(
        columns=["id", "name"],
        rows=[[1, "Alice"], [2, "Bob"]],
        row_count=2,
        execution_time_ms=1.23,
    )

@pytest.mark.asyncio
async def test_api_execute_success():
    """API returns 200 and correct structure for valid SQL."""
    with patch(
        "app.services.sql_executor_service.sql_executor_service.execute_sql",
        new=AsyncMock(return_value=_mock_execute_success()),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/sql/execute",
                json={"sql": "SELECT * FROM users"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["columns"] == ["id", "name"]
    assert body["rows"] == [[1, "Alice"], [2, "Bob"]]
    assert body["row_count"] == 2
    assert body["execution_time_ms"] == 1.23


@pytest.mark.asyncio
async def test_api_execute_validation_error():
    """API returns 422 for unsafe SQL."""
    from app.services.sql_executor_service import SQLExecutionValidationError
    
    with patch(
        "app.services.sql_executor_service.sql_executor_service.execute_sql",
        new=AsyncMock(side_effect=SQLExecutionValidationError("DROP is forbidden")),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/sql/execute",
                json={"sql": "DROP TABLE users"},
            )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "sql_validation_error"
    assert "DROP is forbidden" in body["message"]


@pytest.mark.asyncio
async def test_api_execute_db_error():
    """API returns 500 for DB failure."""
    from app.services.sql_executor_service import SQLExecutionFailedError
    
    with patch(
        "app.services.sql_executor_service.sql_executor_service.execute_sql",
        new=AsyncMock(side_effect=SQLExecutionFailedError("Connection lost")),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/sql/execute",
                json={"sql": "SELECT * FROM big_table"},
            )

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "sql_execution_failed"


@pytest.mark.asyncio
async def test_api_execute_unexpected_error():
    """API returns 500 for unexpected unhandled errors."""
    with patch(
        "app.services.sql_executor_service.sql_executor_service.execute_sql",
        new=AsyncMock(side_effect=Exception("Something weird")),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/sql/execute",
                json={"sql": "SELECT 1"},
            )

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_server_error"


@pytest.mark.asyncio
async def test_api_execute_malformed_request():
    """API returns 422 from Pydantic (or 400 conceptually) if sql field missing."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/sql/execute",
            json={"wrong_field": "SELECT 1"},
        )

    # FastAPI naturally returns 422 Unprocessable Entity for missing required body fields
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


@pytest.mark.asyncio
async def test_api_execute_too_short_sql():
    """API returns 422 from Pydantic for sql < 5 chars."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/sql/execute",
            json={"sql": "SEL"},
        )

    assert response.status_code == 422


def test_sql_execution_request_schema():
    """Validate request schema attributes."""
    req = SQLExecutionRequest(sql="SELECT 1;")
    assert req.sql == "SELECT 1;"


def test_sql_execution_response_schema():
    """Validate response schema serialization."""
    resp = SQLExecutionResponse(
        columns=["a"], rows=[[1]], row_count=1, execution_time_ms=5.0
    )
    data = resp.model_dump(mode="json")
    assert data["columns"] == ["a"]
    assert data["rows"] == [[1]]
    assert data["row_count"] == 1
    assert data["execution_time_ms"] == 5.0
