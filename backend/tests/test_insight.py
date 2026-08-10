"""
Unit and integration tests for the Business Insight Engine module.

Covers:
  - BusinessInsightService logic (LLM abstraction via mock)
  - Edge cases (empty results, single row, max row truncation)
  - Prompt construction testing
  - API endpoint integration (success, 422, 500)
  - Schema serialization/validation
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from app.schemas.execution import SQLExecutionResponse
from app.schemas.visualization import VisualizationRecommendation
from app.schemas.insight import BusinessInsightResponse


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

def _make_vis_recommendation():
    return VisualizationRecommendation(
        chart="line",
        confidence=0.9,
        reason="Trend analysis",
        x_axis="month",
        y_axis="sales"
    )

def _make_mock_insight():
    return BusinessInsightResponse(
        summary="Sales are growing.",
        key_findings=["January was strong.", "February dipped."],
        anomalies=[],
        recommendations=["What happened in March?"]
    )


# ---------------------------------------------------------------------------
# Test Prompt Construction (1-4)
# ---------------------------------------------------------------------------

class TestBusinessInsightPromptBuilder:
    def test_build_prompt_includes_all_context(self):
        from app.services.business_insight_service import _build_insight_prompt
        
        exec_res = _make_exec_response(["id", "val"], [[1, 100], [2, 200]])
        vis_res = [_make_vis_recommendation()]
        
        prompt = _build_insight_prompt("Show sales", exec_res, vis_res)
        assert "Show sales" in prompt
        assert "line" in prompt
        assert "Trend analysis" in prompt
        assert "val" in prompt
        assert "200" in prompt

    def test_build_prompt_truncates_large_results(self):
        from app.services.business_insight_service import _build_insight_prompt
        
        rows = [[i] for i in range(1000)]
        exec_res = _make_exec_response(["id"], rows)
        vis_res = [_make_vis_recommendation()]
        
        prompt = _build_insight_prompt("Big data", exec_res, vis_res)
        assert "Showing first 10" in prompt
        # Ensure only 10 rows are rendered
        assert prompt.count("[") <= 13  # +1 for columns bracket if any

    def test_build_prompt_empty_rows(self):
        from app.services.business_insight_service import _build_insight_prompt
        
        exec_res = _make_exec_response(["id"], [])
        vis_res = [_make_vis_recommendation()]
        
        prompt = _build_insight_prompt("Empty", exec_res, vis_res)
        assert "Total Rows: 0" in prompt

    def test_build_prompt_includes_visualization(self):
        from app.services.business_insight_service import _build_insight_prompt
        exec_res = _make_exec_response(["id"], [[1]])
        vis_res = [_make_vis_recommendation()]
        vis_res[0].chart = "pie"
        
        prompt = _build_insight_prompt("Pie chart?", exec_res, vis_res)
        assert "pie" in prompt


# ---------------------------------------------------------------------------
# Test Service Execution Logic (5-14)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestBusinessInsightService:
    @patch("app.services.business_insight_service._get_insight_agent")
    async def test_generate_insight_success(self, mock_get_agent):
        mock_agent = AsyncMock()
        mock_agent.run.return_value.output = _make_mock_insight().model_dump_json()
        mock_get_agent.return_value = mock_agent

        from app.services.business_insight_service import BusinessInsightService
        service = BusinessInsightService()
        
        exec_res = _make_exec_response(["id"], [[1]])
        vis_res = [_make_vis_recommendation()]
        
        res = await service.generate_insight("Q", exec_res, vis_res)
        assert res.summary == "Sales are growing."
        assert len(res.key_findings) == 2
        mock_agent.run.assert_called_once()

    async def test_generate_insight_empty_result_bypasses_llm(self):
        from app.services.business_insight_service import BusinessInsightService
        service = BusinessInsightService()
        
        # Bypass agent creation completely
        service._agent = AsyncMock() # Should not be called
        
        exec_res = _make_exec_response(["id"], []) # Empty
        vis_res = [_make_vis_recommendation()]
        
        res = await service.generate_insight("Q", exec_res, vis_res)
        assert "no data" in res.summary.lower()
        assert len(res.key_findings) == 1
        service._agent.run.assert_not_called()

    @patch("app.services.business_insight_service._get_insight_agent")
    async def test_generate_insight_single_row(self, mock_get_agent):
        mock_agent = AsyncMock()
        mock_agent.run.return_value.output = _make_mock_insight().model_dump_json()
        mock_get_agent.return_value = mock_agent

        from app.services.business_insight_service import BusinessInsightService
        service = BusinessInsightService()
        
        exec_res = _make_exec_response(["total"], [[1000]])
        vis_res = [_make_vis_recommendation()]
        
        res = await service.generate_insight("Total?", exec_res, vis_res)
        assert res.summary == "Sales are growing."

    @patch("app.services.business_insight_service._get_insight_agent")
    async def test_generate_insight_multiple_rows(self, mock_get_agent):
        mock_agent = AsyncMock()
        mock_agent.run.return_value.output = _make_mock_insight().model_dump_json()
        mock_get_agent.return_value = mock_agent

        from app.services.business_insight_service import BusinessInsightService
        service = BusinessInsightService()
        
        exec_res = _make_exec_response(["a"], [[1], [2], [3]])
        vis_res = [_make_vis_recommendation()]
        
        res = await service.generate_insight("Trend?", exec_res, vis_res)
        assert len(res.key_findings) > 0

    @patch("app.services.business_insight_service._get_insight_agent")
    async def test_generate_insight_raises_business_error_on_failure(self, mock_get_agent):
        mock_agent = AsyncMock()
        mock_agent.run.side_effect = RuntimeError("API down")
        mock_get_agent.return_value = mock_agent

        from app.services.business_insight_service import BusinessInsightService, BusinessInsightError
        service = BusinessInsightService()
        
        exec_res = _make_exec_response(["a"], [[1]])
        vis_res = [_make_vis_recommendation()]
        
        res = await service.generate_insight("question", exec_res, vis_res)
        assert res.key_findings == ["AI analysis is temporarily unavailable."]
    

    def test_get_insight_agent_creates_agent_once(self):
        from app.services.business_insight_service import BusinessInsightService
        with patch("app.services.business_insight_service._get_insight_agent") as mock_get:
            mock_get.return_value = "fake_agent"
            service = BusinessInsightService()
            a1 = service.agent
            a2 = service.agent
            assert a1 == a2 == "fake_agent"
            mock_get.assert_called_once()
            
    def test_get_insight_agent_raises_if_no_api_key(self, monkeypatch):
        from app.config.settings import settings
        from app.services.business_insight_service import _get_insight_agent
        monkeypatch.setattr(settings, "GROQ_API_KEY", "")
        # Force a fresh service instance so it picks up the patched setting
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            _get_insight_agent()

    @patch("app.services.business_insight_service._get_insight_agent")
    async def test_generate_insight_trend_analysis(self, mock_get_agent):
        # Specific mock for a trend response
        mock_agent = AsyncMock()
        mock_agent.run.return_value.output = BusinessInsightResponse(
            summary="Trend is going up.",
            key_findings=[], anomalies=[], recommendations=[]
        ).model_dump_json()
        mock_get_agent.return_value = mock_agent

        from app.services.business_insight_service import BusinessInsightService
        service = BusinessInsightService()
        exec_res = _make_exec_response(["a"], [[1]])
        res = await service.generate_insight("Trend?", exec_res, [_make_vis_recommendation()])
        assert "Trend" in res.summary

    @patch("app.services.business_insight_service._get_insight_agent")
    async def test_generate_insight_recommendation_generation(self, mock_get_agent):
        mock_agent = AsyncMock()
        mock_agent.run.return_value.output = BusinessInsightResponse(
            summary="x", key_findings=[], anomalies=[],
            recommendations=["Check this out.", "Look closer."]
        ).model_dump_json()
        mock_get_agent.return_value = mock_agent

        from app.services.business_insight_service import BusinessInsightService
        service = BusinessInsightService()
        exec_res = _make_exec_response(["a"], [[1]])
        res = await service.generate_insight("Q", exec_res, [_make_vis_recommendation()])
        assert len(res.recommendations) == 2

    @patch("app.services.business_insight_service._get_insight_agent")
    async def test_generate_insight_anomalies_detected(self, mock_get_agent):
        mock_agent = AsyncMock()
        mock_agent.run.return_value.output = BusinessInsightResponse(
            summary="x", key_findings=[],
            anomalies=["Spike on Jan 5th."], recommendations=[]
        ).model_dump_json()
        mock_get_agent.return_value = mock_agent

        from app.services.business_insight_service import BusinessInsightService
        service = BusinessInsightService()
        exec_res = _make_exec_response(["a"], [[1]])
        res = await service.generate_insight("Q", exec_res, [_make_vis_recommendation()])
        assert len(res.anomalies) == 1


# ---------------------------------------------------------------------------
# API Endpoint Tests (15-20)
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_insight_payload():
    return {
        "question": "What is the revenue?",
        "execution_result": {
            "columns": ["revenue"],
            "rows": [[100]],
            "row_count": 1,
            "execution_time_ms": 1.0
        },
        "visualizations": [{
            "chart": "table",
            "confidence": 1.0,
            "reason": "fallback"
        }]
    }


@pytest.mark.asyncio
async def test_api_insight_success(valid_insight_payload):
    """API returns 200 and structured insight."""
    from app.main import app
    
    with patch(
        "app.services.business_insight_service.business_insight_service.generate_insight",
        new=AsyncMock(return_value=_make_mock_insight()),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/insight", json=valid_insight_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == "Sales are growing."
    assert "January was strong." in body["key_findings"]
    assert len(body["recommendations"]) == 1


@pytest.mark.asyncio
async def test_api_insight_malformed_request():
    """API returns 422 if payload is missing required fields."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/insight", json={"question": "only question"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_insight_business_error(valid_insight_payload):
    """API returns 500 if BusinessInsightError is raised."""
    from app.main import app
    from app.services.business_insight_service import BusinessInsightError
    
    with patch(
        "app.services.business_insight_service.business_insight_service.generate_insight",
        new=AsyncMock(side_effect=BusinessInsightError("Model failed")),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/insight", json=valid_insight_payload)

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "insight_generation_failed"
    assert "Model failed" in body["message"]


@pytest.mark.asyncio
async def test_api_insight_unexpected_error(valid_insight_payload):
    """API returns 500 if an unexpected exception occurs."""
    from app.main import app
    
    with patch(
        "app.services.business_insight_service.business_insight_service.generate_insight",
        new=AsyncMock(side_effect=RuntimeError("BOOM")),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/insight", json=valid_insight_payload)

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_server_error"


@pytest.mark.asyncio
async def test_api_insight_empty_result_success():
    """API successfully handles empty database results."""
    from app.main import app
    
    payload = {
        "question": "What is the revenue?",
        "execution_result": {
            "columns": ["revenue"],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": 1.0
        },
        "visualizations": [{
            "chart": "table",
            "confidence": 1.0,
            "reason": "fallback"
        }]
    }
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Actually run the service logic (it bypasses LLM)
        response = await client.post("/api/v1/insight", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert "no data" in body["summary"].lower()


@pytest.mark.asyncio
async def test_api_insight_question_too_short(valid_insight_payload):
    """API returns 422 if question is < 3 chars."""
    from app.main import app
    
    payload = valid_insight_payload.copy()
    payload["question"] = "Q"
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/insight", json=payload)

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Schema Tests (21-31)
# ---------------------------------------------------------------------------

def test_insight_request_schema():
    from app.schemas.insight import BusinessInsightRequest
    
    req = BusinessInsightRequest(
        question="sales",
        execution_result=_make_exec_response(["a"], [[1]]),
        visualizations=[_make_vis_recommendation()]
    )
    assert req.question == "sales"
    assert req.execution_result.row_count == 1
    assert req.visualizations[0].chart == "line"

def test_insight_request_invalid():
    from app.schemas.insight import BusinessInsightRequest
    import pydantic
    
    with pytest.raises(pydantic.ValidationError):
        BusinessInsightRequest(
            question="a",  # too short
            execution_result=_make_exec_response(["a"], [[1]]),
            visualizations=[_make_vis_recommendation()]
        )

def test_insight_response_schema():
    from app.schemas.insight import BusinessInsightResponse
    
    res = BusinessInsightResponse(
        summary="A summary.",
        key_findings=["Finding 1", "Finding 2"],
        anomalies=[],
        recommendations=["Rec 1"]
    )
    assert res.summary == "A summary."
    assert len(res.key_findings) == 2

def test_insight_response_defaults():
    from app.schemas.insight import BusinessInsightResponse
    
    res = BusinessInsightResponse(
        summary="A summary."
    )
    assert res.key_findings == []
    assert res.anomalies == []
    assert res.recommendations == []

def test_insight_error_response_schema():
    from app.schemas.insight import BusinessInsightErrorResponse
    
    err = BusinessInsightErrorResponse(error="E", message="M")
    assert err.error == "E"

def test_insight_error_response_invalid():
    from app.schemas.insight import BusinessInsightErrorResponse
    import pydantic
    
    with pytest.raises(pydantic.ValidationError):
        BusinessInsightErrorResponse()

def test_insight_request_serialization():
    from app.schemas.insight import BusinessInsightRequest
    req = BusinessInsightRequest(
        question="sales",
        execution_result=_make_exec_response(["a"], [[1]]),
        visualizations=[_make_vis_recommendation()]
    )
    data = req.model_dump(mode="json")
    assert data["question"] == "sales"
    assert data["execution_result"]["row_count"] == 1
    assert data["visualizations"][0]["chart"] == "line"

def test_insight_response_serialization():
    from app.schemas.insight import BusinessInsightResponse
    res = BusinessInsightResponse(summary="S")
    data = res.model_dump(mode="json")
    assert data["summary"] == "S"
    assert data["key_findings"] == []

def test_insight_error_response_serialization():
    from app.schemas.insight import BusinessInsightErrorResponse
    err = BusinessInsightErrorResponse(error="E", message="M")
    data = err.model_dump(mode="json")
    assert data["error"] == "E"

def test_insight_response_from_json():
    from app.schemas.insight import BusinessInsightResponse
    data = {
        "summary": "Sum",
        "key_findings": ["1"],
        "anomalies": [],
        "recommendations": []
    }
    res = BusinessInsightResponse.model_validate(data)
    assert res.summary == "Sum"

def test_insight_request_from_json():
    from app.schemas.insight import BusinessInsightRequest
    data = {
        "question": "test",
        "execution_result": {
            "columns": ["a"],
            "rows": [[1]],
            "row_count": 1,
            "execution_time_ms": 1.0
        },
        "visualizations": [{
            "chart": "line",
            "confidence": 1.0,
            "reason": "test",
            "x_axis": None,
            "y_axis": None
        }]
    }
    req = BusinessInsightRequest.model_validate(data)
    assert req.question == "test"

