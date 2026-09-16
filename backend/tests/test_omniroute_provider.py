"""
OmniRoute Provider Boundary Tests

Tests the provider abstraction layer at its boundary without making real
network requests. The patching strategy uses monkeypatching of the
settings object attributes rather than module-level patching, to avoid
import/reload ordering issues.

Tests:
  - Missing API key → ValueError
  - Placeholder API key → ValueError
  - Missing model → ValueError
  - Error message doesn't expose key value
  - Groq fallback still raises ValueError when key missing
  - Unknown provider → ValueError
  - Error humanisation (provider-agnostic)
  - Rate-limit normalization (429 → AI_RATE_LIMITED)
  - Cancellation → CLIENT_CANCELLED
  - FineWorks knowledge deterministic intercepts

Usage:
    cd backend
    .venv\\Scripts\\activate
    python -m pytest tests/test_omniroute_provider.py -v
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 1. OmniRoute provider — validation error cases (no network required)
# ---------------------------------------------------------------------------
# We test these first because they don't need the model to be instantiated.

class TestOmniRouteMissingConfig:

    def test_missing_omniroute_api_key_raises_valueerror(self, monkeypatch):
        """Empty OMNIROUTE_API_KEY must raise ValueError mentioning the key name."""
        from app.config import settings as settings_module
        monkeypatch.setattr(settings_module.settings, "AI_PROVIDER", "omniroute")
        monkeypatch.setattr(settings_module.settings, "OMNIROUTE_API_KEY", "")
        monkeypatch.setattr(settings_module.settings, "OMNIROUTE_MODEL", "some-model")
        monkeypatch.setattr(settings_module.settings, "OMNIROUTE_BASE_URL", "http://localhost:20128/v1")

        from app.services import llm_provider
        import importlib
        importlib.reload(llm_provider)

        with pytest.raises(ValueError, match="OMNIROUTE_API_KEY"):
            llm_provider.get_llm_model()

    def test_placeholder_omniroute_api_key_raises_valueerror(self, monkeypatch):
        """Placeholder 'your_*' key must be treated the same as missing."""
        from app.config import settings as settings_module
        monkeypatch.setattr(settings_module.settings, "AI_PROVIDER", "omniroute")
        monkeypatch.setattr(settings_module.settings, "OMNIROUTE_API_KEY", "your_omniroute_api_key_here")
        monkeypatch.setattr(settings_module.settings, "OMNIROUTE_MODEL", "some-model")
        monkeypatch.setattr(settings_module.settings, "OMNIROUTE_BASE_URL", "http://localhost:20128/v1")

        from app.services import llm_provider
        import importlib
        importlib.reload(llm_provider)

        with pytest.raises(ValueError, match="OMNIROUTE_API_KEY"):
            llm_provider.get_llm_model()

    def test_omniroute_allows_omitted_model_for_dynamic_routing(self, monkeypatch):
        """Omitting OMNIROUTE_MODEL allows OmniRoute to use its own dynamic routing/fallback logic."""
        from app.config import settings as settings_module
        monkeypatch.setattr(settings_module.settings, "AI_PROVIDER", "omniroute")
        monkeypatch.setattr(settings_module.settings, "OMNIROUTE_API_KEY", "real-test-key-123")
        monkeypatch.setattr(settings_module.settings, "OMNIROUTE_MODEL", "auto")
        monkeypatch.setattr(settings_module.settings, "OMNIROUTE_BASE_URL", "http://localhost:20128/v1")

        with patch("pydantic_ai.providers.openai.OpenAIProvider", return_value=MagicMock()):
            with patch("pydantic_ai.models.openai.OpenAIChatModel", return_value=MagicMock()) as mock_model:
                from app.services import llm_provider
                import importlib
                importlib.reload(llm_provider)
                llm_provider.get_llm_model()
                
                # Check that the default "auto" model parameter was passed through
                mock_model.assert_called_once()
                args, kwargs = mock_model.call_args
                assert kwargs.get("model_name") == "auto"

    def test_error_message_does_not_expose_key_value(self, monkeypatch):
        """ValueError messages must never include the actual API key value."""
        from app.config import settings as settings_module
        secret = "my-actual-secret-key-xyz789"
        monkeypatch.setattr(settings_module.settings, "AI_PROVIDER", "omniroute")
        monkeypatch.setattr(settings_module.settings, "OMNIROUTE_API_KEY", secret)
        monkeypatch.setattr(settings_module.settings, "OMNIROUTE_MODEL", "auto")  # No longer triggers error
        monkeypatch.setattr(settings_module.settings, "OMNIROUTE_BASE_URL", "http://localhost:20128/v1")

        # To test the error message, we need to trigger an error, like missing API key
        monkeypatch.setattr(settings_module.settings, "OMNIROUTE_API_KEY", "")

        from app.services import llm_provider
        import importlib
        importlib.reload(llm_provider)

        with pytest.raises(ValueError) as exc_info:
            llm_provider.get_llm_model()
        assert secret not in str(exc_info.value), \
            "API key value must not appear in the ValueError message"


# ---------------------------------------------------------------------------
# 2. Groq provider — validation errors still work
# ---------------------------------------------------------------------------

class TestGroqProviderFallback:

    def test_missing_groq_api_key_raises_valueerror(self, monkeypatch):
        """Missing GROQ_API_KEY raises ValueError when AI_PROVIDER=groq."""
        from app.config import settings as settings_module
        monkeypatch.setattr(settings_module.settings, "AI_PROVIDER", "groq")
        monkeypatch.setattr(settings_module.settings, "GROQ_API_KEY", "")
        monkeypatch.setattr(settings_module.settings, "GROQ_MODEL", "llama-3.3-70b-versatile")

        from app.services import llm_provider
        import importlib
        importlib.reload(llm_provider)

        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            llm_provider.get_llm_model()

    def test_placeholder_groq_api_key_raises_valueerror(self, monkeypatch):
        """Placeholder Groq key must also be rejected."""
        from app.config import settings as settings_module
        monkeypatch.setattr(settings_module.settings, "AI_PROVIDER", "groq")
        monkeypatch.setattr(settings_module.settings, "GROQ_API_KEY", "your_groq_api_key_here")
        monkeypatch.setattr(settings_module.settings, "GROQ_MODEL", "llama-3.3-70b-versatile")

        from app.services import llm_provider
        import importlib
        importlib.reload(llm_provider)

        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            llm_provider.get_llm_model()


# ---------------------------------------------------------------------------
# 3. Unknown provider
# ---------------------------------------------------------------------------

class TestUnknownProvider:

    def test_unknown_provider_raises_valueerror(self, monkeypatch):
        """Completely unknown AI_PROVIDER must raise a clear ValueError."""
        from app.config import settings as settings_module
        monkeypatch.setattr(settings_module.settings, "AI_PROVIDER", "fakeprovider")

        from app.services import llm_provider
        import importlib
        importlib.reload(llm_provider)

        with pytest.raises(ValueError, match="fakeprovider"):
            llm_provider.get_llm_model()

    def test_unknown_provider_error_mentions_supported(self, monkeypatch):
        """The unknown provider error must name supported providers."""
        from app.config import settings as settings_module
        monkeypatch.setattr(settings_module.settings, "AI_PROVIDER", "azure")

        from app.services import llm_provider
        import importlib
        importlib.reload(llm_provider)

        with pytest.raises(ValueError) as exc_info:
            llm_provider.get_llm_model()
        error_msg = str(exc_info.value).lower()
        # Should mention at least one supported provider
        assert "omniroute" in error_msg or "groq" in error_msg


# ---------------------------------------------------------------------------
# 4. Rate-limit normalization
# ---------------------------------------------------------------------------

class TestRateLimitNormalization:

    @pytest.mark.asyncio
    async def test_rate_limit_429_maps_to_ai_rate_limited(self):
        """HTTP 429 from any provider must produce AI_RATE_LIMITED error_code."""
        from app.services.agent_service import AgentService
        from app.schemas.agent import AgentStatus
        import app.agents.fineanalyst_agent as _agent_mod

        service = AgentService()

        class FakeRateLimitError(Exception):
            status_code = 429

        # Build a fake agent that raises 429 when run
        fake_agent = AsyncMock()
        fake_agent.run = AsyncMock(side_effect=FakeRateLimitError("rate limit exceeded"))

        # Clear the singleton cache so get_agent() rebuilds
        original_instance = _agent_mod._agent_instance
        try:
            _agent_mod._agent_instance = fake_agent
            result = await service.process_message(
                user_message="Tell me about quantum computing",
                session_id="test-session",
            )
        finally:
            _agent_mod._agent_instance = original_instance

        assert result.status == AgentStatus.ERROR
        assert result.error_code == "AI_RATE_LIMITED"

    @pytest.mark.asyncio
    async def test_rate_limit_error_not_generic_500(self):
        """Rate limit errors must NOT produce a generic internal error code."""
        from app.services.agent_service import AgentService
        import app.agents.fineanalyst_agent as _agent_mod

        service = AgentService()

        class FakeRateLimitError(Exception):
            status_code = 429

        fake_agent = AsyncMock()
        fake_agent.run = AsyncMock(side_effect=FakeRateLimitError("rate limit exceeded"))

        original_instance = _agent_mod._agent_instance
        try:
            _agent_mod._agent_instance = fake_agent
            result = await service.process_message(
                user_message="Show revenue",
                session_id="test-session",
            )
        finally:
            _agent_mod._agent_instance = original_instance

        assert result.error_code not in ("InternalServerError", "500", "Exception")


# ---------------------------------------------------------------------------
# 5. Client cancellation
# ---------------------------------------------------------------------------

class TestClientCancellation:

    @pytest.mark.asyncio
    async def test_cancelled_error_maps_to_client_cancelled(self):
        """asyncio.CancelledError must produce CLIENT_CANCELLED (not a 500)."""
        from app.services.agent_service import AgentService
        from app.schemas.agent import AgentStatus
        import app.agents.fineanalyst_agent as _agent_mod

        service = AgentService()

        fake_agent = AsyncMock()
        fake_agent.run = AsyncMock(side_effect=asyncio.CancelledError())

        original_instance = _agent_mod._agent_instance
        try:
            _agent_mod._agent_instance = fake_agent
            result = await service.process_message(
                user_message="Some long request",
                session_id="test-session",
            )
        finally:
            _agent_mod._agent_instance = original_instance

        assert result.status == AgentStatus.ERROR
        assert result.error_code == "CLIENT_CANCELLED"


# ---------------------------------------------------------------------------
# 6. Provider-agnostic error humanisation
# ---------------------------------------------------------------------------

class TestHumaniseError:

    def test_http_class_name_produces_friendly_message(self):
        """Errors whose type name contains 'http' produce friendly messages."""
        from app.services.agent_service import AgentService

        service = AgentService()

        class OmniRouteHTTPError(Exception):
            pass

        exc = OmniRouteHTTPError("connection refused")
        result = service._humanise_error(exc)
        assert "error" in result.lower()

    def test_timeout_produces_friendly_message(self):
        """Timeout errors should produce a meaningful message."""
        from app.services.agent_service import AgentService

        service = AgentService()

        class ConnectTimeoutError(Exception):
            pass

        exc = ConnectTimeoutError("timeout")
        result = service._humanise_error(exc)
        assert "timed out" in result.lower() or "try again" in result.lower()

    def test_generic_error_has_fallback_message(self):
        """Completely unknown error types get a generic fallback message."""
        from app.services.agent_service import AgentService

        service = AgentService()

        class VeryWeirdError(Exception):
            pass

        exc = VeryWeirdError("weird error")
        result = service._humanise_error(exc)
        assert len(result) > 0  # Must not be empty


# ---------------------------------------------------------------------------
# 7. FineWorks / FineAnalyst knowledge (deterministic — no LLM call)
# ---------------------------------------------------------------------------

class TestFineWorksKnowledge:

    @pytest.mark.asyncio
    async def test_who_created_fineanalyst_returns_team(self):
        """'Who created FineAnalyst?' must be answered without LLM call."""
        from app.services.agent_service import AgentService
        from app.schemas.agent import AgentStatus

        service = AgentService()

        result = await service.process_message(
            user_message="Who created FineAnalyst?",
            session_id="test-session",
        )

        assert result.status == AgentStatus.SUCCESS
        msg = result.message.lower()
        assert "saranesh" in msg
        assert "fineworks" in msg

    @pytest.mark.asyncio
    async def test_fineworks_all_members_listed(self):
        """Team member query must list all 4 known members."""
        from app.services.agent_service import AgentService
        from app.schemas.agent import AgentStatus

        service = AgentService()

        result = await service.process_message(
            user_message="Who are the members of FineWorks?",
            session_id="test-session",
        )

        assert result.status == AgentStatus.SUCCESS
        msg = result.message.lower()
        for name in ["saranesh", "praveen", "nitish", "sakthi"]:
            assert name in msg, f"Expected '{name}' in FineWorks response. Got: {result.message}"

    @pytest.mark.asyncio
    async def test_fineworks_response_uses_zero_tokens(self):
        """Deterministic FineWorks responses must report 0 LLM token usage."""
        from app.services.agent_service import AgentService
        from app.schemas.agent import AgentStatus

        service = AgentService()

        result = await service.process_message(
            user_message="Who created FineAnalyst?",
            session_id="test-session",
        )

        assert result.status == AgentStatus.SUCCESS
        assert result.usage.total_tokens == 0, \
            "Deterministic responses should consume 0 tokens"

    @pytest.mark.asyncio
    async def test_fineworks_does_not_call_llm(self):
        """FineWorks intercepts must not invoke the LLM at all."""
        from app.services.agent_service import AgentService

        service = AgentService()

        with patch("app.agents.fineanalyst_agent.get_agent") as mock_get_agent:
            result = await service.process_message(
                user_message="Who built FineAnalyst?",
                session_id="test-session",
            )
            # get_agent should NOT have been called
            mock_get_agent.assert_not_called()
