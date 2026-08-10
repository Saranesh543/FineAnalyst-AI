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
def mock_intent():
    from app.schemas.intent import QueryPlan, Intent
    return QueryPlan(intent=Intent.DATABASE, requires_database=True, corrected_message="test question")

@pytest.fixture
def mock_all_services(mock_schema, mock_sql, mock_exec, mock_vis, mock_insight, mock_intent):
    with patch("app.services.analytics_orchestrator.schema_service.get_schema", new_callable=AsyncMock) as m_schema, \
         patch("app.services.analytics_orchestrator.sql_generator_service.generate", new_callable=AsyncMock) as m_sql, \
         patch("app.services.analytics_orchestrator.sql_generator_service.generate_retry", new_callable=AsyncMock) as m_retry, \
         patch("app.services.analytics_orchestrator.sql_executor_service.execute_sql", new_callable=AsyncMock) as m_exec, \
         patch("app.services.analytics_orchestrator.chart_intelligence_service.select_charts") as m_vis, \
         patch("app.services.analytics_orchestrator.business_insight_service.generate_insight", new_callable=AsyncMock) as m_insight, \
         patch("app.services.analytics_orchestrator.query_understanding_service.understand", new_callable=AsyncMock) as m_intent:
        
        m_schema.return_value = mock_schema
        m_sql.return_value = mock_sql
        
        # Make m_retry behave exactly like m_sql for failures
        def retry_side_effect(*args, **kwargs):
            if hasattr(m_sql, "side_effect") and m_sql.side_effect:
                if isinstance(m_sql.side_effect, Exception):
                    raise m_sql.side_effect
                return m_sql.side_effect(*args, **kwargs)
            return mock_sql
        m_retry.side_effect = retry_side_effect
        
        m_exec.return_value = mock_exec
        m_vis.return_value = [mock_vis]
        m_insight.return_value = mock_insight
        m_intent.return_value = mock_intent
        
        yield (m_schema, m_sql, m_exec, m_vis, m_insight, m_intent)


# ---------------------------------------------------------------------------
# Service Tests (1-14)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAnalyticsOrchestratorService:
    async def test_analyze_success_path(self, mock_all_services, mock_sql, mock_exec, mock_vis, mock_insight):
        m_schema, m_sql_mock, m_exec_mock, m_vis_mock, m_insight_mock, m_intent_mock = mock_all_services
        service = AnalyticsOrchestratorService()
        
        res = await service.analyze("test question")
        
        assert res.question == "test question"
        assert res.sql == mock_sql.sql
        assert res.execution == mock_exec
        assert res.visualizations == [mock_vis]
        assert res.insight == mock_insight
        
        m_schema.assert_called_once()
        m_sql_mock.assert_called_once()
        m_exec_mock.assert_called_once()
        m_vis_mock.assert_called_once()
        m_insight_mock.assert_called_once()

    async def test_schema_failure(self, mock_all_services):
        m_schema, m_sql, m_exec, m_vis, m_insight, m_intent = mock_all_services
        m_schema.side_effect = RuntimeError("DB down")
        
        service = AnalyticsOrchestratorService()
        with pytest.raises(AnalyticsWorkflowError) as exc:
            await service.analyze("Q")
            
        assert exc.value.stage == "schema"
        assert "DB down" in str(exc.value)

    async def test_sql_generation_failure(self, mock_all_services):
        m_schema, m_sql, m_exec, m_vis, m_insight, m_intent = mock_all_services
        m_sql.side_effect = ValueError("Invalid prompt")
        m_exec.side_effect = ValueError("Fallback failed")
        
        service = AnalyticsOrchestratorService()
        with pytest.raises(AnalyticsWorkflowError) as exc:
            await service.analyze("Q")
            
        assert exc.value.stage == "sql_execution"

    async def test_sql_execution_failure(self, mock_all_services):
        m_schema, m_sql, m_exec, m_vis, m_insight, m_intent = mock_all_services
        m_exec.side_effect = ValueError("Syntax error")
        
        service = AnalyticsOrchestratorService()
        with pytest.raises(AnalyticsWorkflowError) as exc:
            await service.analyze("Q")
            
        assert exc.value.stage == "sql_execution"

    async def test_visualization_failure(self, mock_all_services):
        m_schema, m_sql, m_exec, m_vis, m_insight, m_intent = mock_all_services
        m_vis.side_effect = TypeError("Bad data")
        
        service = AnalyticsOrchestratorService()
        with pytest.raises(AnalyticsWorkflowError) as exc:
            await service.analyze("Q")
            
        assert exc.value.stage == "visualization"

    async def test_insight_failure(self, mock_all_services):
        m_schema, m_sql, m_exec, m_vis, m_insight, m_intent = mock_all_services
        m_insight.side_effect = RuntimeError("AI offline")
        
        service = AnalyticsOrchestratorService()
        with pytest.raises(AnalyticsWorkflowError) as exc:
            await service.analyze("Q")
            
        assert exc.value.stage == "insight"

    async def test_empty_schema_handled(self, mock_all_services, mock_schema):
        m_schema, m_sql, m_exec, m_vis, m_insight, m_intent = mock_all_services
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
        assert "QueryPlan intent:" in caplog.text

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
        assert "Discovered" in caplog.text

    async def test_logger_insight_generated(self, mock_all_services, caplog):
        import logging
        caplog.set_level(logging.INFO)
        service = AnalyticsOrchestratorService()
        await service.analyze("what")
        assert "Finished" in caplog.text


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
    assert "visualizations" in body
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
    _, m_sql, m_exec, *_ = mock_all_services
    m_sql.side_effect = ValueError("Unsafe")
    m_exec.side_effect = ValueError("Fallback Failed")
    
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/analyze", json=valid_analyze_payload)

    assert response.status_code == 500
    body = response.json()
    assert body["stage"] == "sql_execution"


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
    _, _, _, m_vis, _, _ = mock_all_services
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
    *_, m_insight, _ = mock_all_services
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
    
    assert "Analytics workflow failed | stage=schema" in caplog.text
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


def test_analyze_response_schema(mock_exec, mock_vis, mock_insight):
    res = AnalyzeResponse(
        question="q",
        sql="s",
        execution=mock_exec,
        visualizations=[mock_vis],
        insight=mock_insight
    )
    assert res.question == "q"
    assert res.sql == "s"

def test_analyze_response_serialization(mock_exec, mock_vis, mock_insight):
    res = AnalyzeResponse(
        question="q",
        sql="s",
        execution=mock_exec,
        visualizations=[mock_vis],
        insight=mock_insight
    )
    data = res.model_dump(mode="json")
    assert data["question"] == "q"
    assert "execution" in data
    assert "visualizations" in data
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


@pytest.mark.asyncio
async def test_visualization_pipeline_strict_mapping():
    from app.schemas.execution import SQLExecutionResponse
    from app.schemas.intent import QueryPlan, Intent
    from app.services.chart_intelligence_service import chart_intelligence_service

    # 1. Provide exact test dataset
    mock_execution = SQLExecutionResponse(
        columns=['Month', 'Revenue', 'Expenses', 'Customers', 'Refunds', 'Complaints'],
        rows=[
            ['Jan', 100, 50, 10, 1, 0],
            ['Feb', 150, 60, 15, 2, 1],
        ],
        row_count=2,
        execution_time_ms=10
    )

    mock_query_plan = QueryPlan(
        intent=Intent.DATABASE,
        requires_database=True,
        corrected_message="Analyze data"
    )

    # 2. Run Chart Intelligence
    vis_recommendations = chart_intelligence_service.select_charts(
        question="Analyze data",
        execution_result=mock_execution,
        query_plan=mock_query_plan
    )

    # 3. Assertions
    # Should produce distinct charts for financial (Revenue, Expenses) and counts (Customers, Refunds, Complaints)
    assert len(vis_recommendations) >= 2, "Should produce multiple distinct charts"
    
    seen_signatures = set()
    for vis in vis_recommendations:
        y_keys = vis.metadata.y_axis.split(',') if vis.metadata.y_axis else []
        x_key = vis.metadata.x_axis
        
        # No zero-yKey charts (unless data_grid fallback)
        if vis.chart != "data_grid":
            assert len(y_keys) > 0, "Charts must have at least one yKey"
            assert x_key is not None, "Charts must have an xKey"
        
        # No duplicate charts
        sig = f"{x_key}|{vis.metadata.y_axis}|{vis.chart}"
        assert sig not in seen_signatures, f"Duplicate chart signature found: {sig}"
        seen_signatures.add(sig)
        
        # No invalid columns
        if x_key:
            assert x_key in mock_execution.columns
        for y in y_keys:
            assert y in mock_execution.columns
            
        # Verify title does not contain the original prompt
        assert "Analyze data" not in vis.metadata.title

    # Verify Financial Chart isolation
    financial_chart = next((v for v in vis_recommendations if 'Revenue' in v.metadata.y_axis), None)
    assert financial_chart is not None
    assert 'Expenses' in financial_chart.metadata.y_axis
    assert 'Customers' not in financial_chart.metadata.y_axis, "Unrelated metrics mixed"

    # Verify Count Chart isolation
    count_chart = next((v for v in vis_recommendations if 'Customers' in v.metadata.y_axis), None)
    assert count_chart is not None
    assert 'Refunds' in count_chart.metadata.y_axis
    assert 'Revenue' not in count_chart.metadata.y_axis, "Unrelated metrics mixed"




@pytest.mark.asyncio
async def test_followup_context_success(mock_all_services):
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.schemas.intent import QueryPlan, Intent
    
    payload = {
        "question": "What about December?",
        "session_id": "test-session",
        "history": [
            {"role": "user", "content": "Analyze this dataset"},
            {"role": "assistant", "content": "Analysis complete.\n\n[Previous QueryPlan: {\"intent\": \"database\", \"metrics\": [\"Revenue\"], \"time_range\": \"all\"}]"}
        ]
    }
    
    m_schema, m_sql_gen, m_sql_exec, m_chart_intel, m_insight_gen, m_query_understand = mock_all_services
    m_query_understand.return_value = QueryPlan(
        intent=Intent.DATABASE,
        requires_database=True,
        metrics=["Revenue"],
        time_range="December"
    )
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/analyze", json=payload)
        
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "database"
    
    # Verify the orchestrator parsed the previous query plan and passed it to the intent router
    call_args = m_query_understand.call_args[1]
    assert call_args["previous_query_plan"] is not None
    assert call_args["previous_query_plan"].metrics == ["Revenue"]


@pytest.mark.asyncio
async def test_failed_request_does_not_poison_context(mock_all_services):
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.schemas.intent import QueryPlan, Intent
    
    payload = {
        "question": "What about December?",
        "session_id": "test-session",
        "history": [
            {"role": "user", "content": "Analyze this dataset"},
            {"role": "assistant", "content": "Analysis complete.\n\n[Previous QueryPlan: {\"intent\": \"database\", \"metrics\": [\"Revenue\"], \"time_range\": \"all\"}]"},
            {"role": "user", "content": "Bad query"},
            {"role": "assistant", "content": "Error executing query."}
        ]
    }
    
    m_schema, m_sql_gen, m_sql_exec, m_chart_intel, m_insight_gen, m_query_understand = mock_all_services
    m_query_understand.return_value = QueryPlan(
        intent=Intent.DATABASE,
        requires_database=True,
        metrics=["Revenue"],
        time_range="December"
    )
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/analyze", json=payload)
        
    assert response.status_code == 200
    # It should skip the failed turn and still find the successful one
    call_args = m_query_understand.call_args[1]
    assert call_args["previous_query_plan"] is not None
    assert call_args["previous_query_plan"].metrics == ["Revenue"]


@pytest.mark.asyncio
async def test_conversational_request_bypass(mock_all_services):
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.schemas.intent import QueryPlan, Intent
    
    payload = {
        "question": "What database do you have?",
        "session_id": "test-session",
    }
    
    m_schema, m_sql_gen, m_sql_exec, m_chart_intel, m_insight_gen, m_query_understand = mock_all_services
    # It should hit the heuristic bypass, but let's say the LLM caught it
    m_query_understand.return_value = QueryPlan(
        intent=Intent.CONVERSATION,
        requires_database=False,
        corrected_message="what database do you have"
    )
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/analyze", json=payload)
        
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "conversation"
    # SQL generator should NEVER be called for conversational intent
    m_sql_gen.assert_not_called()
    m_sql_exec.assert_not_called()
    m_chart_intel.assert_not_called()
    m_insight_gen.assert_not_called()


@pytest.mark.asyncio
async def test_conversational_preserves_analytical_context(mock_all_services):
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.schemas.intent import QueryPlan, Intent
    
    payload = {
        "question": "What about December?",
        "session_id": "test-session",
        "history": [
            {"role": "user", "content": "Analyze this dataset"},
            {"role": "assistant", "content": "Analysis complete.\n\n[Previous QueryPlan: {\"intent\": \"database\", \"metrics\": [\"Revenue\"], \"time_range\": \"all\"}]"},
            {"role": "user", "content": "What database do you have?"},
            {"role": "assistant", "content": "I have SQLite."} 
        ]
    }
    
    m_schema, m_sql_gen, m_sql_exec, m_chart_intel, m_insight_gen, m_query_understand = mock_all_services
    m_query_understand.return_value = QueryPlan(
        intent=Intent.DATABASE,
        requires_database=True,
        metrics=["Revenue"],
        time_range="December"
    )
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/analyze", json=payload)
        
    assert response.status_code == 200
    call_args = m_query_understand.call_args[1]
    assert call_args["previous_query_plan"] is not None
    assert call_args["previous_query_plan"].metrics == ["Revenue"]

