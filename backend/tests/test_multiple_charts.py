import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_multiple_charts_generation(monkeypatch):
    from app.main import app
    from app.schemas.intent import QueryPlan, Intent
    from app.schemas.execution import SQLExecutionResponse

    payload = {
        "question": "Analyze this dataset",
        "session_id": "test-session"
    }

    class MockQueryUnderstanding:
        async def understand(self, q, history=None, inline_columns=None, previous_query_plan=None):
            return QueryPlan(intent=Intent.DATABASE, requires_database=True)

    class MockSchemaService:
        async def get_schema(self, user_id=None, session_id=None, custom_engine=None):
            from app.schemas.database_schema import DatabaseSchemaResponse
            return DatabaseSchemaResponse(database="test", dialect="sqlite", tables=[], table_count=0)

    class MockSqlGenerator:
        async def generate(self, q, schema, query_plan=None, history=None):
            class FakeRes:
                sql = "SELECT * FROM data"
            return FakeRes()

    class MockSqlExecutor:
        async def execute_sql(self, sql, user_id=None, custom_engine=None, user_question=""):
            return SQLExecutionResponse(
                columns=["month", "revenue", "customers", "conversion_rate"],
                rows=[
                    ["Jan", 1000, 50, 0.05],
                    ["Feb", 1200, 60, 0.05]
                ],
                row_count=2,
                execution_time_ms=10
            )

    class MockBusinessInsight:
        async def generate_insight(self, question, execution_result, visualizations):
            from app.schemas.insight import BusinessInsightResponse
            return BusinessInsightResponse(summary="test", kpi_cards=[], key_findings=[], detailed_analysis="", anomalies=[], recommendations=[], suggested_questions=[], conclusion="")

    monkeypatch.setattr("app.services.analytics_orchestrator.query_understanding_service", MockQueryUnderstanding())
    monkeypatch.setattr("app.services.analytics_orchestrator.schema_service", MockSchemaService())
    monkeypatch.setattr("app.services.analytics_orchestrator.sql_generator_service", MockSqlGenerator())
    monkeypatch.setattr("app.services.analytics_orchestrator.sql_executor_service", MockSqlExecutor())
    monkeypatch.setattr("app.services.analytics_orchestrator.business_insight_service", MockBusinessInsight())
    # Note: We do NOT mock chart_intelligence_service because we want to test its output

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    
    assert "visualizations" in data
    visualizations = data["visualizations"]
    assert len(visualizations) == 3

    y_axes = [v["metadata"]["y_axis"] for v in visualizations]
    assert "revenue" in y_axes
    assert "customers" in y_axes
    assert "conversion_rate" in y_axes
