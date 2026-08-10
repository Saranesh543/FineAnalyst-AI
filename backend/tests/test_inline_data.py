import pytest
import asyncio
from unittest.mock import MagicMock
from app.services.inline_data_extractor import extract_inline_data
from app.schemas.intent import QueryPlan, Intent
from app.services.analytics_orchestrator import AnalyticsOrchestratorService
import pandas as pd

def test_inline_data_extractor_markdown_table():
    message = """Here is some data:
| Month | Revenue |
| Jan | 450000 |
| Feb | 475000 |
Analyze the trend in revenue."""
    
    clean_q, df, detected = extract_inline_data(message)
    
    assert detected is True
    assert "Analyze the trend in revenue" in clean_q
    assert "Here is some data" in clean_q
    assert "| Month |" not in clean_q
    
    assert df is not None
    assert len(df) == 2
    assert "Month" in df.columns
    assert "Revenue" in df.columns
    assert df.iloc[0]["Revenue"] == 450000

def test_inline_data_extractor_no_table():
    message = "Show total shipments for this year."
    
    clean_q, df, detected = extract_inline_data(message)
    
    assert detected is False
    assert df is None
    assert clean_q == message

@pytest.mark.asyncio
async def test_analytics_orchestrator_inline_data_flow(monkeypatch):
    orchestrator = AnalyticsOrchestratorService()
    
    message = """| Month | Shipments |
| Jan | 820 |
| Feb | 870 |
Analyze shipments."""
    
    # We will mock the subsequent services to just check if custom_engine is correctly initialized and passed.
    class MockQueryUnderstanding:
        async def understand(self, q, history=None, inline_columns=None, previous_query_plan=None):
            assert inline_columns is not None, "inline_columns list was not passed correctly"
            return QueryPlan(intent=Intent.DATABASE, corrected_message="Analyze shipments", requires_database=False)
            
    class MockSchemaService:
        async def get_schema(self, user_id=None, session_id=None, custom_engine=None):
            assert custom_engine is not None, "custom_engine was not passed to schema_service"
            from app.schemas.database_schema import DatabaseSchemaResponse, TableInfo, ColumnInfo
            return DatabaseSchemaResponse(tables=[], table_count=1, database="sqlite", dialect="sqlite")
            
    class MockSqlGenerator:
        async def generate(self, q, schema, query_plan=None, history=None):
            class FakeRes:
                sql = "SELECT * FROM user_inline_data"
            return FakeRes()
            
    class MockSqlExecutor:
        async def execute_sql(self, sql, user_id=None, custom_engine=None, user_question=""):
            assert custom_engine is not None, "custom_engine was not passed to sql_executor"
            from app.schemas.execution import SQLExecutionResponse
            return SQLExecutionResponse(columns=["Month", "Shipments"], rows=[["Jan", 820], ["Feb", 870]], row_count=2, execution_time_ms=5.0)

    class MockChartIntelligence:
        def select_charts(self, question, execution_result, query_plan=None):
            from app.schemas.visualization import VisualizationRecommendation, VisualizationMetadata
            return [VisualizationRecommendation(chart="line", confidence=1.0, reason="test", metadata=VisualizationMetadata(chart_type="line", title="test"))]
            
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

    res = await orchestrator.analyze(message, user_id=1, session_id="test")
    assert res is not None
    assert res.execution.row_count == 2
    assert res.intent == Intent.DATABASE

if __name__ == "__main__":
    pytest.main(["-v", __file__])
