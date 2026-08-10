import pytest
from app.services.query_understanding_service import query_understanding_service
from app.schemas.intent import QueryPlan, Intent

@pytest.mark.asyncio
async def test_failsafe_returns_database_when_inline_data_present(monkeypatch):
    async def mock_run(*args, **kwargs):
        raise Exception("RateLimitError")
        
    class MockAgent:
        async def run(self, *args, **kwargs):
            return await mock_run(*args, **kwargs)
            
    monkeypatch.setattr(query_understanding_service, '_get_agent', lambda: MockAgent())
    
    plan = await query_understanding_service.understand(
        "Analyze this", 
        inline_columns=["Month", "Revenue"]
    )
    
    assert plan.intent == Intent.DATABASE
    assert plan.requires_database is False


@pytest.mark.asyncio
async def test_normalize_and_parse_valid_json():
    raw = '{"intent": "database", "metrics": ["Revenue"]}'
    plan = query_understanding_service._normalize_and_parse(raw, "Analyze this")
    assert plan.intent == Intent.DATABASE
    assert plan.metrics == ["Revenue"]


@pytest.mark.asyncio
async def test_normalize_and_parse_markdown_json():
    raw = '''Here is your plan:
```json
{
    "intent": "database",
    "metrics": ["Revenue"]
}
```
Good luck!'''
    plan = query_understanding_service._normalize_and_parse(raw, "Analyze this")
    assert plan.intent == Intent.DATABASE
    assert plan.metrics == ["Revenue"]


@pytest.mark.asyncio
async def test_normalize_and_parse_raw_intent_keyword():
    raw = 'DATABASE'
    plan = query_understanding_service._normalize_and_parse(raw, "Analyze this")
    assert plan.intent == Intent.DATABASE


@pytest.mark.asyncio
async def test_normalize_and_parse_fallback_to_conversation_when_junk():
    raw = 'I am sorry, I cannot fulfill this request.'
    plan = query_understanding_service._normalize_and_parse(raw, "Analyze this")
    # Should fallback to conversation
    assert plan.intent == Intent.CONVERSATION
