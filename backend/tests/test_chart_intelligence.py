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
    decisions = chart_intelligence_service.select_charts("Show total revenue", resp)
    assert decisions[0].chart == "kpi"

def test_chart_intelligence_pie():
    resp = create_mock_response(3, ["category", "revenue"], [["Category A", 10], ["Category B", 20], ["Category C", 30]])
    decisions = chart_intelligence_service.select_charts("Revenue share by category", resp)
    assert decisions[0].chart == "donut"

def test_chart_intelligence_ranking_horizontal_bar():
    resp = create_mock_response(10, ["customer", "revenue"], [["Customer Name Is Very Long " + str(i), 100-i] for i in range(10)])
    decisions = chart_intelligence_service.select_charts("Top 10 customers by revenue", resp)
    assert decisions[0].chart == "horizontal_bar"

def test_chart_intelligence_trend_area():
    resp = create_mock_response(5, ["month", "revenue"], [["2023-01", 10], ["2023-02", 20], ["2023-03", 30], ["2023-04", 40], ["2023-05", 50]])
    decisions = chart_intelligence_service.select_charts("Revenue growth over time", resp)
    assert decisions[0].chart == "area"
    
def test_chart_intelligence_monthly_line():
    resp = create_mock_response(5, ["month", "revenue"], [["2023-01", 10], ["2023-02", 20], ["2023-03", 30], ["2023-04", 40], ["2023-05", 50]])
    decisions = chart_intelligence_service.select_charts("Show monthly revenue", resp)
    assert decisions[0].chart == "line"
    
def test_chart_intelligence_scatter():
    resp = create_mock_response(10, ["profit", "revenue"], [[10, 100], [20, 200], [30, 300], [40, 400], [50, 500], [60, 600], [70, 700], [80, 800], [90, 900], [100, 1000]])
    decisions = chart_intelligence_service.select_charts("Revenue vs profit", resp)
    assert decisions[0].chart == "scatter"
    
def test_chart_intelligence_map():
    resp = create_mock_response(5, ["country", "sales"], [["US", 10], ["UK", 20], ["FR", 30], ["DE", 40], ["IT", 50]])
    decisions = chart_intelligence_service.select_charts("Sales by country", resp)
    assert decisions[0].chart == "map"
    
def test_chart_intelligence_data_grid():
    resp = create_mock_response(1001, ["id", "order_date"], [[i, "2023-01-01"] for i in range(1001)])
    decisions = chart_intelligence_service.select_charts("Show all orders", resp)
    assert decisions[0].chart == "data_grid"

def test_title_generation():
    resp = create_mock_response(1, ["total_revenue"], [[10000]])
    decisions = chart_intelligence_service.select_charts("Previous Context From Conversation History: Show total revenue", resp)
    # Title generation is now strictly column-based.
    assert decisions[0].metadata.title == "Total Revenue"

