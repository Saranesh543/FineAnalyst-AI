"""
Integration tests for the Agent API endpoint.

Run with:
    pytest tests/test_agent.py -v

These tests use FastAPI's async TestClient so they exercise the full
request/response cycle without starting a real server.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

# Patch the agent before importing the app so we don't call Gemini.
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_agent_result():
    """Return a fake PydanticAI RunResult matching the 2.22 API.

    In PydanticAI 2.22, ``result.usage`` is a property that returns a
    ``RunUsage`` dataclass directly — it is no longer a callable method.
    Field names also changed: request_tokens -> input_tokens,
    response_tokens -> output_tokens.
    """
    result = MagicMock()
    result.output = "Hello! I'm FineAnalyst AI. How can I assist you today?"
    result.all_messages.return_value = []
    usage = MagicMock()
    usage.requests = 1
    usage.input_tokens = 10
    usage.output_tokens = 20
    usage.total_tokens = 30
    # Property access — assign directly, NOT as a return_value.
    result.usage = usage
    return result


@pytest.fixture
def app_with_mocked_agent(mock_agent_result):
    """
    Import the FastAPI app with the PydanticAI agent's `run` method mocked
    so no real Gemini API calls are made during tests.
    """
    with patch(
        "app.agents.fineanalyst_agent._build_agent"
    ) as mock_build:
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_agent_result)
        mock_build.return_value = mock_agent_instance

        # Import app AFTER patching to ensure the mock is used.
        from app.main import app  # noqa: PLC0415
        return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_returns_200_on_hello(mock_agent_result):
    """
    Sending 'Hello' to POST /api/v1/agent/chat should return HTTP 200 with
    a non-empty message and status='success'.
    """
    with patch(
        "app.services.agent_service.get_agent"
    ) as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_agent_result)
        mock_get_agent.return_value = mock_agent

        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/agent/chat",
                json={"message": "Hello"},
            )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    assert len(body["message"]) > 0
    assert body["usage"]["total_tokens"] == 30


@pytest.mark.asyncio
async def test_chat_with_session_id(mock_agent_result):
    """Session ID is echoed back in the response."""
    with patch(
        "app.services.agent_service.get_agent"
    ) as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_agent_result)
        mock_get_agent.return_value = mock_agent

        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/agent/chat",
                json={"message": "Hello", "session_id": "test-session-42"},
            )

    assert response.status_code == 200
    assert response.json()["session_id"] == "test-session-42"


@pytest.mark.asyncio
async def test_chat_empty_message_returns_422():
    """An empty string message must be rejected by Pydantic validation."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/agent/chat",
            json={"message": ""},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_agent_error_returns_500(mock_agent_result):
    """If the agent raises an exception the endpoint should return HTTP 500."""
    with patch(
        "app.services.agent_service.get_agent"
    ) as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("Simulated API failure"))
        mock_get_agent.return_value = mock_agent

        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/agent/chat",
                json={"message": "Crash test"},
            )

    assert response.status_code == 500
    body = response.json()
    assert body["status"] == "error"
    assert "error_code" in body


@pytest.mark.asyncio
async def test_clear_session_endpoint():
    """DELETE /api/v1/agent/session/{id} should respond 200."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.delete("/api/v1/agent/session/some-session")

    assert response.status_code == 200
    assert "cleared" in response.json()


@pytest.mark.asyncio
async def test_session_info_endpoint():
    """GET /api/v1/agent/session/{id}/info should return a message_count."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/agent/session/some-session/info")

    assert response.status_code == 200
    assert "message_count" in response.json()
