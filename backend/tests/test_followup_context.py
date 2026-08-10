import pytest
from app.schemas.agent import MessageTurn, MessageRole
from app.services.analytics_orchestrator import analytics_orchestrator

@pytest.mark.asyncio
async def test_followup_query_inherits_inline_context_12_rows(monkeypatch):
    """
    1. Analyze the inline 12-row dataset.
    2. Follow up: 'create a chart for this'.
    3. It must reuse the same table and return the 12 rows successfully.
    """
    
    # --- Step 1: Initial Query with Inline Data ---
    inline_data = """
| Month | Shipments | Delivered | Delayed | Cancelled | Revenue | Avg Delivery Days |
|---|---|---|---|---|---|---|
| Jan | 100 | 90 | 5 | 5 | 10000 | 2.5 |
| Feb | 110 | 100 | 6 | 4 | 11000 | 2.4 |
| Mar | 120 | 110 | 7 | 3 | 12000 | 2.3 |
| Apr | 130 | 120 | 5 | 5 | 13000 | 2.2 |
| May | 140 | 130 | 6 | 4 | 14000 | 2.1 |
| Jun | 150 | 140 | 5 | 5 | 15000 | 2.0 |
| Jul | 160 | 150 | 4 | 6 | 16000 | 1.9 |
| Aug | 170 | 160 | 5 | 5 | 17000 | 1.8 |
| Sep | 180 | 170 | 6 | 4 | 18000 | 1.7 |
| Oct | 190 | 180 | 7 | 3 | 19000 | 1.6 |
| Nov | 200 | 190 | 5 | 5 | 20000 | 1.5 |
| Dec | 210 | 200 | 4 | 6 | 21000 | 1.4 |
"""
    initial_question = inline_data + "\nShow all data"
    
    class MockQueryUnderstanding:
        async def understand(self, q, history=None, inline_columns=None, previous_query_plan=None):
            from app.schemas.intent import QueryPlan, Intent
            # Simulating intent router appending the history context
            return QueryPlan(intent=Intent.DATABASE, requires_database=True)

    class MockSchemaService:
        async def get_schema(self, user_id=None, session_id=None, custom_engine=None):
            from app.schemas.database_schema import DatabaseSchemaResponse
            return DatabaseSchemaResponse(database="test", dialect="sqlite", tables=[], table_count=0)

    class MockSqlGenerator:
        async def generate(self, q, schema, query_plan=None, history=None):
            class FakeRes:
                sql = "SELECT * FROM user_inline_data"
            return FakeRes()

    class MockSqlExecutor:
        async def execute_sql(self, sql, user_id=None, custom_engine=None, user_question=""):
            from app.schemas.execution import SQLExecutionResponse
            return SQLExecutionResponse(
                columns=["Month"],
                rows=[["Jan"] for _ in range(12)],
                row_count=12,
                execution_time_ms=10
            )

    class MockChartIntelligence:
        def select_charts(self, question, execution_result, query_plan):
            return []

    class MockBusinessInsight:
        async def generate_insight(self, question, execution_result, visualizations):
            from app.schemas.insight import BusinessInsightResponse
            return BusinessInsightResponse(summary="test", kpi_cards=[], key_findings=[], detailed_analysis="", anomalies=[], recommendations=[], suggested_questions=[], conclusion="")

    monkeypatch.setattr("app.services.analytics_orchestrator.query_understanding_service", MockQueryUnderstanding())
    monkeypatch.setattr("app.services.analytics_orchestrator.schema_service", MockSchemaService())
    monkeypatch.setattr("app.services.analytics_orchestrator.sql_generator_service", MockSqlGenerator())
    monkeypatch.setattr("app.services.analytics_orchestrator.sql_executor_service", MockSqlExecutor())
    monkeypatch.setattr("app.services.analytics_orchestrator.chart_intelligence_service", MockChartIntelligence())
    monkeypatch.setattr("app.services.analytics_orchestrator.business_insight_service", MockBusinessInsight())

    # We don't have a full frontend running in this test, so we pass an empty history
    response_1 = await analytics_orchestrator.analyze(
        question=initial_question,
        history=[],
        user_id=1,
        session_id="test_session"
    )
    
    assert response_1.execution is not None, "Execution should not be None"
    assert response_1.execution.row_count == 12, f"Expected 12 rows from inline data, got {response_1.execution.row_count}"
    assert "user_inline_data" in response_1.sql.lower(), "SQL must query the inline data table"
    
    # Extract the query plan from response_1 steps
    intent_step = next((s for s in response_1.steps if s.name == "intent_routing"), None)
    assert intent_step is not None, "Missing intent_routing step"
    
    # Simulate what the frontend does: construct history for step 2
    history = [
        MessageTurn(role=MessageRole.USER, content=initial_question),
        MessageTurn(role=MessageRole.ASSISTANT, content=f"Here is the analysis.\n\n[Previous QueryPlan: {intent_step.detail}]")
    ]
    
    # --- Step 2: Follow-up Query ---
    followup_question = "create a chart for this"
    
    response_2 = await analytics_orchestrator.analyze(
        question=followup_question,
        history=history,
        user_id=1,
        session_id="test_session"
    )
    
    assert response_2.execution is not None, "Execution should not be None for follow-up"
    assert response_2.execution.row_count == 12, f"Follow-up must still query inline dataset of 12 rows, got {response_2.execution.row_count}"
    assert "user_inline_data" in response_2.sql.lower(), "Follow-up SQL must query the inline data table, not default DB"

