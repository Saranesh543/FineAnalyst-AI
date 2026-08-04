"""
Unit and integration tests for the Visualization Recommendation module.

Covers:
  - ChartRecommenderService logic (Bar, Line, Pie, Scatter, Histogram, Table)
  - Type inference (numeric, datetime, categorical)
  - Edge cases (large dataset, empty data, no columns)
  - API endpoint integration
  - Schema serialization/validation
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from datetime import date, datetime

from app.schemas.execution import SQLExecutionResponse
from app.services.chart_recommender_service import ChartRecommenderService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_exec_response(columns, rows, row_count=None):
    if row_count is None:
        row_count = len(rows)
    return SQLExecutionResponse(
        columns=columns,
        rows=rows,
        row_count=row_count,
        execution_time_ms=10.0,
    )


# ---------------------------------------------------------------------------
# Test Service Recommendation Logic (1-18)
# ---------------------------------------------------------------------------


class TestChartRecommenderService:
    @pytest.fixture
    def service(self):
        return ChartRecommenderService()

    def test_empty_columns_raises_value_error(self, service):
        """Should raise ValueError if no columns are present."""
        data = _make_exec_response([], [])
        with pytest.raises(ValueError, match="empty result set"):
            service.recommend("test", data)

    def test_empty_data_recommends_table(self, service):
        """Empty row data (but has columns) should recommend table."""
        data = _make_exec_response(["id", "name"], [], row_count=0)
        res = service.recommend("show me everything", data)
        assert res.chart == "table"
        assert res.confidence == 1.0

    def test_large_dataset_recommends_table(self, service):
        """Dataset > 1000 rows always recommends a data grid."""
        # Provide only 1 row to avoid huge object, but spoof row_count
        data = _make_exec_response(["id"], [[1]], row_count=1001)
        res = service.recommend("trends", data)
        assert res.chart == "data_grid"
        assert res.confidence == 1.0

    def test_time_series_line_with_explicit_datetime(self, service):
        """Line chart recommended when datetime is present and numeric data."""
        data = _make_exec_response(
            ["created_at", "total_sales"], 
            [[datetime(2023, 1, 1), 100.5]]
        )
        res = service.recommend("what is the trend?", data)
        assert res.chart == "line"
        assert res.x_axis == "created_at"
        assert res.y_axis == "total_sales"
        assert res.confidence == 0.95

    def test_time_series_line_keyword_no_numeric(self, service):
        """Line chart recommended when datetime is present, time keyword, but no numeric."""
        data = _make_exec_response(
            ["login_date", "user_status"], 
            [["2023-01-01", "active"]]
        )
        res = service.recommend("login history", data)
        assert res.chart == "line"
        assert res.x_axis == "login_date"
        assert res.y_axis is None

    def test_pie_chart_recommendation(self, service):
        """Pie chart recommended for category + numeric with percentage intent."""
        data = _make_exec_response(
            ["department", "employee_count"], 
            [["Sales", 45]]
        )
        res = service.recommend("what is the percentage breakdown?", data)
        assert res.chart == "pie"
        assert res.x_axis == "department"
        assert res.y_axis == "employee_count"

    def test_pie_chart_ignored_if_many_rows(self, service):
        """Pie chart not recommended if rows > 20, defaults to bar."""
        data = _make_exec_response(
            ["department", "employee_count"], 
            [["Sales", 45]],
            row_count=25
        )
        res = service.recommend("what is the percentage breakdown?", data)
        assert res.chart == "bar"

    def test_histogram_recommendation(self, service):
        """Histogram recommended for single numeric column with distribution intent."""
        data = _make_exec_response(
            ["age"], 
            [[25], [30], [22]]
        )
        res = service.recommend("show me the age distribution", data)
        assert res.chart == "histogram"
        assert res.x_axis == "age"
        assert res.y_axis is None

    def test_scatter_recommendation_explicit_intent(self, service):
        """Scatter recommended for two numeric columns with correlation intent."""
        data = _make_exec_response(
            ["height", "weight"], 
            [[180.5, 75.0]]
        )
        res = service.recommend("correlation between height and weight", data)
        assert res.chart == "scatter"
        assert res.confidence == 0.9
        assert res.x_axis == "height"
        assert res.y_axis == "weight"

    def test_scatter_recommendation_implicit(self, service):
        """Scatter recommended implicitly if exactly two columns and both are numeric."""
        data = _make_exec_response(
            ["val1", "val2"], 
            [[10.5, 20.1]]
        )
        res = service.recommend("just some data", data)
        assert res.chart == "scatter"
        assert res.confidence == 0.75

    def test_bar_chart_recommendation(self, service):
        """Bar chart recommended for category + numeric."""
        data = _make_exec_response(
            ["product_name", "revenue"], 
            [["Laptop", 1500.0]]
        )
        res = service.recommend("top products by revenue", data)
        assert res.chart == "bar"
        assert res.x_axis == "product_name"
        assert res.y_axis == "revenue"

    def test_fallback_table_recommendation(self, service):
        """Table recommended when nothing else matches (e.g. all categorical)."""
        data = _make_exec_response(
            ["first_name", "last_name"], 
            [["Alice", "Smith"]]
        )
        res = service.recommend("list of users", data)
        assert res.chart == "table"

    def test_infer_datetime_from_iso_string(self, service):
        """String matching YYYY-MM-DD should be inferred as datetime."""
        types = service._infer_types(["my_date"], ["2023-05-12"])
        assert types["my_date"] == "datetime"

    def test_infer_datetime_from_column_name(self, service):
        """String with column name containing 'date' should be inferred as datetime."""
        types = service._infer_types(["birth_date"], ["unknown format"])
        assert types["birth_date"] == "datetime"

    def test_infer_categorical_from_id_column(self, service):
        """Integer column named 'id' should be categorical, not numeric."""
        types = service._infer_types(["user_id"], [42])
        assert types["user_id"] == "categorical"
        types2 = service._infer_types(["id"], [1])
        assert types2["id"] == "categorical"

    def test_infer_datetime_from_year_column(self, service):
        """Integer column named 'year' should be datetime."""
        types = service._infer_types(["year"], [2023])
        assert types["year"] == "datetime"

    def test_infer_categorical_fallback(self, service):
        """Unknown types or random strings should be categorical."""
        types = service._infer_types(["status"], ["active"])
        assert types["status"] == "categorical"
        
    def test_infer_numeric(self, service):
        """Floats and ints should be numeric."""
        types = service._infer_types(["price", "qty"], [19.99, 5])
        assert types["price"] == "numeric"
        assert types["qty"] == "numeric"


# ---------------------------------------------------------------------------
# API Endpoint Tests (19-25)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_recommend_success():
    """API returns 200 and a recommendation."""
    from app.main import app
    
    payload = {
        "question": "monthly sales trend",
        "execution_result": {
            "columns": ["month", "sales"],
            "rows": [["2023-01-01", 100]],
            "row_count": 1,
            "execution_time_ms": 10.0
        }
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/visualization/recommend", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["chart"] == "line"
    assert body["confidence"] > 0
    assert body["x_axis"] == "month"
    assert body["y_axis"] == "sales"


@pytest.mark.asyncio
async def test_api_recommend_validation_error():
    """API returns 422 if service raises ValueError (e.g., empty columns)."""
    from app.main import app
    
    payload = {
        "question": "show nothing",
        "execution_result": {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": 1.0
        }
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/visualization/recommend", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"


@pytest.mark.asyncio
async def test_api_recommend_unexpected_error(monkeypatch):
    """API returns 500 if an unexpected exception occurs."""
    from app.main import app
    from app.services.chart_recommender_service import chart_recommender_service
    
    def mock_recommend(*args, **kwargs):
        raise RuntimeError("BOOM")
        
    monkeypatch.setattr(chart_recommender_service, "recommend", mock_recommend)

    payload = {
        "question": "monthly sales",
        "execution_result": {
            "columns": ["a"],
            "rows": [["b"]],
            "row_count": 1,
            "execution_time_ms": 1.0
        }
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/visualization/recommend", json=payload)

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_server_error"


@pytest.mark.asyncio
async def test_api_recommend_malformed_request():
    """API returns 422 if payload is missing required fields."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/visualization/recommend", json={"question": "only question"})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Schema Tests (26-31)
# ---------------------------------------------------------------------------


def test_visualization_request_schema():
    from app.schemas.visualization import VisualizationRequest
    
    req = VisualizationRequest(
        question="sales",
        execution_result=SQLExecutionResponse(
            columns=["a"], rows=[[1]], row_count=1, execution_time_ms=1.0
        )
    )
    assert req.question == "sales"
    assert req.execution_result.row_count == 1


def test_visualization_request_too_short():
    from app.schemas.visualization import VisualizationRequest
    import pydantic
    
    with pytest.raises(pydantic.ValidationError):
        VisualizationRequest(
            question="a",
            execution_result=SQLExecutionResponse(
                columns=["a"], rows=[[1]], row_count=1, execution_time_ms=1.0
            )
        )


def test_visualization_recommendation_schema():
    from app.schemas.visualization import VisualizationRecommendation
    
    rec = VisualizationRecommendation(
        chart="bar",
        confidence=0.9,
        reason="Because",
        x_axis="x",
        y_axis="y"
    )
    assert rec.chart == "bar"


def test_visualization_recommendation_invalid_confidence():
    from app.schemas.visualization import VisualizationRecommendation
    import pydantic
    
    with pytest.raises(pydantic.ValidationError):
        VisualizationRecommendation(
            chart="bar",
            confidence=1.5,  # Too high
            reason="Because"
        )


def test_visualization_error_response_schema():
    from app.schemas.visualization import VisualizationErrorResponse
    
    err = VisualizationErrorResponse(error="code", message="msg")
    assert err.error == "code"


def test_visualization_recommendation_defaults():
    from app.schemas.visualization import VisualizationRecommendation
    
    rec = VisualizationRecommendation(
        chart="table",
        confidence=1.0,
        reason="Fallback"
    )
    assert rec.x_axis is None
    assert rec.y_axis is None


def test_visualization_error_response_invalid_type():
    from app.schemas.visualization import VisualizationErrorResponse
    import pydantic
    
    with pytest.raises(pydantic.ValidationError):
        # Missing required fields
        VisualizationErrorResponse()


def test_infer_categorical_from_boolean():
    from app.services.chart_recommender_service import ChartRecommenderService
    service = ChartRecommenderService()
    types = service._infer_types(["is_active"], [True])
    # boolean acts as categorical
    assert types["is_active"] == "categorical"


def test_api_recommend_empty_question():
    from app.schemas.visualization import VisualizationRequest
    from app.schemas.execution import SQLExecutionResponse
    import pydantic
    
    with pytest.raises(pydantic.ValidationError):
        VisualizationRequest(
            question="", # min_length=3
            execution_result=SQLExecutionResponse(
                columns=["a"], rows=[[1]], row_count=1, execution_time_ms=1.0
            )
        )
