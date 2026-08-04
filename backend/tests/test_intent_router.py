import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic_ai.models.test import TestModel

from app.schemas.intent import Intent, IntentResult
from app.services.intent_router import IntentRouterService

@pytest.fixture
def mock_agent():
    with patch("app.services.intent_router.IntentRouterService._get_agent") as mock_get:
        mock = MagicMock()
        mock_get.return_value = mock
        yield mock

@pytest.mark.asyncio
async def test_classify_conversation(mock_agent):
    mock_agent.run = AsyncMock()
    mock_agent.run.return_value.output = IntentResult(intent=Intent.CONVERSATION)

    router = IntentRouterService()
    result = await router.classify("Hello")

    assert result.intent == Intent.CONVERSATION
    mock_agent.run.assert_called_once_with("Hello")

@pytest.mark.asyncio
async def test_classify_knowledge(mock_agent):
    mock_agent.run = AsyncMock()
    mock_agent.run.return_value.output = IntentResult(intent=Intent.KNOWLEDGE)

    router = IntentRouterService()
    result = await router.classify("What is SQL?")

    assert result.intent == Intent.KNOWLEDGE
    mock_agent.run.assert_called_once_with("What is SQL?")

@pytest.mark.asyncio
async def test_classify_database(mock_agent):
    mock_agent.run = AsyncMock()
    mock_agent.run.return_value.output = IntentResult(intent=Intent.DATABASE)

    router = IntentRouterService()
    result = await router.classify("Show me the top 10 customers by revenue.")

    assert result.intent == Intent.DATABASE
    mock_agent.run.assert_called_once_with("Show me the top 10 customers by revenue.")
