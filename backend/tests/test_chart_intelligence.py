import pytest
from app.services.chart_intelligence_service import chart_intelligence_service
from app.schemas.execution import SQLExecutionResponse

def create_mock_response(row_count: int, columns: list[str], rows: list[list | dict]) -> SQLExecutionResponse:
    # Handle dict rows conversion for consistency if needed, but schema allows dicts
    return SQLExecutionResponse(
        columns=columns,
        rows=rows,
        row_count=row_count,
        execution_time_ms=10.0
    )

def test_chart_intelligence_kpi():
    resp = create_mock_response(1, ["total_revenue"], [[10000]])
    decision = chart_intelligence_service.select_chart("Show total revenue", resp)
    assert decision.chart == "kpi"

def test_chart_intelligence_pie():
    resp = create_mock_response(3, ["category", "revenue"], [["A", 10], ["B", 20], ["C", 30]])
    decision = chart_intelligence_service.select_chart("Revenue share by category", resp)
    assert decision.chart == "donut"

def test_chart_intelligence_ranking_horizontal_bar():
    resp = create_mock_response(10, ["customer", "revenue"], [["Cust" + str(i), 100-i] for i in range(10)])
    decision = chart_intelligence_service.select_chart("Top 10 customers by revenue", resp)
    assert decision.chart == "horizontal_bar"

def test_chart_intelligence_trend_area():
    resp = create_mock_response(5, ["month", "revenue"], [["2023-01", 10], ["2023-02", 20], ["2023-03", 30], ["2023-04", 40], ["2023-05", 50]])
    decision = chart_intelligence_service.select_chart("Revenue trend", resp)
    assert decision.chart == "area"
    
def test_chart_intelligence_monthly_line():
    resp = create_mock_response(5, ["month", "revenue"], [["2023-01", 10], ["2023-02", 20], ["2023-03", 30], ["2023-04", 40], ["2023-05", 50]])
    decision = chart_intelligence_service.select_chart("Show monthly revenue", resp)
    assert decision.chart == "line"
    
def test_chart_intelligence_scatter():
    resp = create_mock_response(10, ["profit", "revenue"], [[10, 100], [20, 200], [30, 300], [40, 400], [50, 500], [60, 600], [70, 700], [80, 800], [90, 900], [100, 1000]])
    decision = chart_intelligence_service.select_chart("Revenue vs profit", resp)
    assert decision.chart == "scatter"
    
def test_chart_intelligence_map():
    resp = create_mock_response(5, ["country", "sales"], [["US", 10], ["UK", 20], ["FR", 30], ["DE", 40], ["IT", 50]])
    decision = chart_intelligence_service.select_chart("Sales by country", resp)
    assert decision.chart == "map"
    
def test_chart_intelligence_data_grid():
    resp = create_mock_response(1001, ["id", "order_date"], [[i, "2023-01-01"] for i in range(1001)])
    decision = chart_intelligence_service.select_chart("Show all orders", resp)
    assert decision.chart == "data_grid"

def test_title_generation():
    resp = create_mock_response(1, ["total_revenue"], [[10000]])
    decision = chart_intelligence_service.select_chart("Previous Context From Conversation History: Show total revenue", resp)
    # The title should be cleaned to "Total Revenue"
    assert decision.metadata.title == "Total Revenue"
