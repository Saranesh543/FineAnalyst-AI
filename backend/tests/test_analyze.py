"""
Unit and integration tests for the Analytics Workflow Orchestrator.

Covers:
  - E2E Success path (mocked)
  - Failure at every stage (schema, sql_gen, sql_exec, vis, insight)
  - API endpoint integration
  - Schema serialization/validation
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.analyze import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalyzeErrorResponse,
)
from app.schemas.database_schema import DatabaseSchemaResponse
from app.schemas.execution import SQLExecutionResponse
from app.schemas.insight import BusinessInsightResponse
from app.schemas.sql import SQLGenerationResponse
from app.schemas.visualization import VisualizationRecommendation
from app.services.analytics_orchestrator import AnalyticsWorkflowError, AnalyticsOrchestratorService


# ---------------------------------------------------------------------------
# Mocks & Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_schema():
    return DatabaseSchemaResponse(database="test", dialect="sqlite", tables=[], table_count=0)

@pytest.fixture
def mock_sql():
    return SQLGenerationResponse(sql="SELECT 1", question="test question", dialect="sqlite")

@pytest.fixture
def mock_exec():
    return SQLExecutionResponse(columns=["a"], rows=[[1]], row_count=1, execution_time_ms=1.0)

@pytest.fixture
def mock_vis():
    return VisualizationRecommendation(chart="table", confidence=1.0, reason="test")

@pytest.fixture
def mock_insight():
    return BusinessInsightResponse(summary="sum", key_findings=[], anomalies=[], recommendations=[])

@pytest.fixture
def mock_all_services(mock_schema, mock_sql, mock_exec, mock_vis, mock_insight):
    with patch("app.services.analytics_orchestrator.schema_service.get_schema", new_callable=AsyncMock) as m_schema, \
         patch("app.services.analytics_orchestrator.sql_generator_service.generate", new_callable=AsyncMock) as m_sql, \
         patch("app.services.analytics_orchestrator.sql_executor_service.execute_sql", new_callable=AsyncMock) as m_exec, \
         patch("app.services.analytics_orchestrator.chart_recommender_service.recommend") as m_vis, \
         patch("app.services.analytics_orchestrator.business_insight_service.generate_insight", new_callable=AsyncMock) as m_insight:
        
        m_schema.return_value = mock_schema
        m_sql.return_value = mock_sql
        m_exec.return_value = mock_exec
        m_vis.return_value = mock_vis
        m_insight.return_value = mock_insight
        
        yield (m_schema, m_sql, m_exec, m_vis, m_insight)


# ---------------------------------------------------------------------------
# Service Tests (1-14)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAnalyticsOrchestratorService:
    async def test_analyze_success_path(self, mock_all_services, mock_sql, mock_exec, mock_vis, mock_insight):
        m_schema, m_sql_mock, m_exec_mock, m_vis_mock, m_insight_mock = mock_all_services
        service = AnalyticsOrchestratorService()
        
        res = await service.analyze("test question")
        
        assert res.question == "test question"
        assert res.sql == mock_sql.sql
        assert res.execution == mock_exec
        assert res.visualization == mock_vis
        assert res.insight == mock_insight
        
        m_schema.assert_called_once()
        m_sql_mock.assert_called_once()
        m_exec_mock.assert_called_once()
        m_vis_mock.assert_called_once()
        m_insight_mock.assert_called_once()

    async def test_schema_failure(self, mock_all_services):
        m_schema, m_sql, m_exec, m_vis, m_insight = mock_all_services
        m_schema.side_effect = RuntimeError("DB down")
        
        service = AnalyticsOrchestratorService()
        with pytest.raises(AnalyticsWorkflowError) as exc:
            await service.analyze("Q")
            
        assert exc.value.stage == "schema"
        assert "DB down" in str(exc.value)

    async def test_sql_generation_failure(self, mock_all_services):
        m_schema, m_sql, m_exec, m_vis, m_insight = mock_all_services
        m_sql.side_effect = ValueError("Invalid prompt")
        
        service = AnalyticsOrchestratorService()
        with pytest.raises(AnalyticsWorkflowError) as exc:
            await service.analyze("Q")
            
        assert exc.value.stage == "sql_generation"

    async def test_sql_execution_failure(self, mock_all_services):
        m_schema, m_sql, m_exec, m_vis, m_insight = mock_all_services
        m_exec.side_effect = ValueError("Syntax error")
        
        service = AnalyticsOrchestratorService()
        with pytest.raises(AnalyticsWorkflowError) as exc:
            await service.analyze("Q")
            
        assert exc.value.stage == "sql_execution"

    async def test_visualization_failure(self, mock_all_services):
        m_schema, m_sql, m_exec, m_vis, m_insight = mock_all_services
        m_vis.side_effect = TypeError("Bad data")
        
        service = AnalyticsOrchestratorService()
        with pytest.raises(AnalyticsWorkflowError) as exc:
            await service.analyze("Q")
            
        assert exc.value.stage == "visualization"

    async def test_insight_failure(self, mock_all_services):
        m_schema, m_sql, m_exec, m_vis, m_insight = mock_all_services
        m_insight.side_effect = RuntimeError("AI offline")
        
        service = AnalyticsOrchestratorService()
        with pytest.raises(AnalyticsWorkflowError) as exc:
            await service.analyze("Q")
            
        assert exc.value.stage == "insight"

    async def test_empty_schema_handled(self, mock_all_services, mock_schema):
        m_schema, m_sql, m_exec, m_vis, m_insight = mock_all_services
        mock_schema.table_count = 0
        mock_schema.is_empty = True
        
        service = AnalyticsOrchestratorService()
        res = await service.analyze("Q")
        assert res.question == "Q"

    def test_singleton_behaviour(self):
        from app.services.analytics_orchestrator import analytics_orchestrator as obj1
        from app.services.analytics_orchestrator import AnalyticsOrchestratorService
        obj2 = AnalyticsOrchestratorService()
        # Ensure obj1 exists and is the same type
        assert isinstance(obj1, AnalyticsOrchestratorService)
        assert type(obj1) is type(obj2)

    def test_error_wraps_original_exception(self, mock_all_services):
        from app.services.analytics_orchestrator import AnalyticsWorkflowError
        err = AnalyticsWorkflowError("Test", stage="test", original_error=ValueError("orig"))
        assert isinstance(err.original_error, ValueError)

    def test_error_without_original(self):
        from app.services.analytics_orchestrator import AnalyticsWorkflowError
        err = AnalyticsWorkflowError("Test", stage="test")
        assert err.original_error is None
        
    async def test_logger_workflow_started(self, mock_all_services, caplog):
        import logging
        caplog.set_level(logging.INFO)
        service = AnalyticsOrchestratorService()
        await service.analyze("what")
        assert "Analytics workflow started" in caplog.text

    async def test_logger_workflow_completed(self, mock_all_services, caplog):
        import logging
        caplog.set_level(logging.INFO)
        service = AnalyticsOrchestratorService()
        await service.analyze("what")
        assert "Workflow completed" in caplog.text

    async def test_logger_schema_completed(self, mock_all_services, caplog):
        import logging
        caplog.set_level(logging.INFO)
        service = AnalyticsOrchestratorService()
        await service.analyze("what")
        assert "Schema completed" in caplog.text

    async def test_logger_insight_generated(self, mock_all_services, caplog):
        import logging
        caplog.set_level(logging.INFO)
        service = AnalyticsOrchestratorService()
        await service.analyze("what")
        assert "Insight generated" in caplog.text


# ---------------------------------------------------------------------------
# API Tests (15-28)
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_analyze_payload():
    return {"question": "What is the total revenue?"}


@pytest.mark.asyncio
async def test_api_analyze_success(mock_all_services, valid_analyze_payload):
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/analyze", json=valid_analyze_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["question"] == "What is the total revenue?"
    assert "sql" in body
    assert "execution" in body
    assert "visualization" in body
    assert "insight" in body


@pytest.mark.asyncio
async def test_api_analyze_malformed_request():
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/analyze", json={})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_analyze_question_too_short():
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/analyze", json={"question": "Q"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_analyze_schema_failure(mock_all_services, valid_analyze_payload):
    m_schema, *_ = mock_all_services
    m_schema.side_effect = RuntimeError("Fail")
    
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/analyze", json=valid_analyze_payload)

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "workflow_failed"
    assert body["stage"] == "schema"


@pytest.mark.asyncio
async def test_api_analyze_sql_generation_failure(mock_all_services, valid_analyze_payload):
    _, m_sql, *_ = mock_all_services
    m_sql.side_effect = ValueError("Unsafe")
    
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/analyze", json=valid_analyze_payload)

    assert response.status_code == 500
    body = response.json()
    assert body["stage"] == "sql_generation"


@pytest.mark.asyncio
async def test_api_analyze_sql_execution_failure(mock_all_services, valid_analyze_payload):
    _, _, m_exec, *_ = mock_all_services
    m_exec.side_effect = ValueError("Syntax Error")
    
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/analyze", json=valid_analyze_payload)

    assert response.status_code == 500
    body = response.json()
    assert body["stage"] == "sql_execution"


@pytest.mark.asyncio
async def test_api_analyze_visualization_failure(mock_all_services, valid_analyze_payload):
    _, _, _, m_vis, _ = mock_all_services
    m_vis.side_effect = ValueError("Bad data")
    
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/analyze", json=valid_analyze_payload)

    assert response.status_code == 500
    body = response.json()
    assert body["stage"] == "visualization"


@pytest.mark.asyncio
async def test_api_analyze_insight_failure(mock_all_services, valid_analyze_payload):
    *_, m_insight = mock_all_services
    m_insight.side_effect = RuntimeError("AI Error")
    
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/analyze", json=valid_analyze_payload)

    assert response.status_code == 500
    body = response.json()
    assert body["stage"] == "insight"


@pytest.mark.asyncio
async def test_api_analyze_unexpected_error(valid_analyze_payload):
    from app.main import app
    with patch("app.services.analytics_orchestrator.analytics_orchestrator.analyze") as m_analyze:
        m_analyze.side_effect = RuntimeError("BOOM")
        
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/analyze", json=valid_analyze_payload)

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_server_error"
    assert body["stage"] == "unknown"


@pytest.mark.asyncio
async def test_api_analyze_swagger_docs_exist():
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/openapi.json")
    
    assert response.status_code == 200
    docs = response.json()
    assert "/api/v1/analyze" in docs["paths"]
    
@pytest.mark.asyncio
async def test_api_analyze_logs_request(mock_all_services, valid_analyze_payload, caplog):
    import logging
    caplog.set_level(logging.INFO)
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/api/v1/analyze", json=valid_analyze_payload)
    
    assert "Analyze request received" in caplog.text

@pytest.mark.asyncio
async def test_api_analyze_logs_workflow_failure(mock_all_services, valid_analyze_payload, caplog):
    import logging
    caplog.set_level(logging.INFO)
    m_schema, *_ = mock_all_services
    m_schema.side_effect = RuntimeError("Fail")
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/api/v1/analyze", json=valid_analyze_payload)
    
    assert "Analytics workflow failed at stage 'schema'" in caplog.text

@pytest.mark.asyncio
async def test_api_analyze_logs_unexpected_failure(valid_analyze_payload, caplog):
    import logging
    caplog.set_level(logging.INFO)
    from app.main import app
    with patch("app.services.analytics_orchestrator.analytics_orchestrator.analyze") as m_analyze:
        m_analyze.side_effect = RuntimeError("BOOM")
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post("/api/v1/analyze", json=valid_analyze_payload)
    
    assert "Unexpected error during analyze workflow" in caplog.text

@pytest.mark.asyncio
async def test_api_analyze_response_headers(mock_all_services, valid_analyze_payload):
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/analyze", json=valid_analyze_payload)
    assert response.headers["content-type"] == "application/json"


# ---------------------------------------------------------------------------
# Schema Tests (29-37)
# ---------------------------------------------------------------------------

def test_analyze_request_schema():
    req = AnalyzeRequest(question="show sales")
    assert req.question == "show sales"

def test_analyze_request_invalid():
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        AnalyzeRequest(question="a")

def test_analyze_response_schema(mock_exec, mock_vis, mock_insight):
    res = AnalyzeResponse(
        question="q",
        sql="s",
        execution=mock_exec,
        visualization=mock_vis,
        insight=mock_insight
    )
    assert res.question == "q"
    assert res.sql == "s"

def test_analyze_response_serialization(mock_exec, mock_vis, mock_insight):
    res = AnalyzeResponse(
        question="q",
        sql="s",
        execution=mock_exec,
        visualization=mock_vis,
        insight=mock_insight
    )
    data = res.model_dump(mode="json")
    assert data["question"] == "q"
    assert "execution" in data
    assert "visualization" in data
    assert "insight" in data

def test_analyze_error_response_schema():
    err = AnalyzeErrorResponse(error="E", message="M", stage="S")
    assert err.error == "E"
    assert err.stage == "S"

def test_analyze_error_response_invalid():
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        AnalyzeErrorResponse(error="E")

def test_analyze_error_response_serialization():
    err = AnalyzeErrorResponse(error="E", message="M", stage="S")
    data = err.model_dump(mode="json")
    assert data["stage"] == "S"

def test_analyze_request_from_json():
    req = AnalyzeRequest.model_validate({"question": "hello world"})
    assert req.question == "hello world"

def test_analyze_response_from_json(mock_exec, mock_vis, mock_insight):
    data = {
        "question": "Q",
        "sql": "S",
        "execution": mock_exec.model_dump(mode="json"),
        "visualization": mock_vis.model_dump(mode="json"),
        "insight": mock_insight.model_dump(mode="json"),
    }
    res = AnalyzeResponse.model_validate(data)
    assert res.question == "Q"
