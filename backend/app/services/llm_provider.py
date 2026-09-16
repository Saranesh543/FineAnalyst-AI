"""
LLM Provider Abstraction Module

Provides a factory to instantiate the correct pydantic-ai Model
based on environment configuration, allowing easy swapping between
OmniRoute, Groq, and future providers.

Provider selection is controlled by AI_PROVIDER in the environment:
  - "omniroute"  (default) — routes through OmniRoute's OpenAI-compatible API
  - "groq"       — uses Groq directly via its OpenAI-compatible endpoint

Architecture:
    agent_service / analytics_orchestrator / intent_router /
    query_understanding / sql_generator / business_insight / mermaid_generation
            ↓
    get_llm_model()          ← single provider injection point
            ↓
    OmniRoute  |  Groq       ← provider adapters
            ↓
    Configured Model

OmniRoute is NOT the application. It is the provider.
The FineAnalyst analytical pipeline sits above this layer.
"""

import logging
import json
import urllib.request
from pydantic_ai.models import Model
from app.config.settings import settings

logger = logging.getLogger(__name__)

_OMNIROUTE_DYNAMIC_MODEL: str | None = None


def get_llm_model() -> Model:
    """
    Instantiate and return the configured LLM model based on settings.AI_PROVIDER.

    This is the single provider injection point for all FineAnalyst services.
    Changing AI_PROVIDER in the environment switches the provider globally
    without modifying any service code.

    Returns:
        Model: A pydantic-ai Model instance ready for agent use.

    Raises:
        ValueError: If required API keys/configuration are missing, or if
                    an unknown provider is specified.
    """
    provider = settings.AI_PROVIDER.lower().strip()

    # -------------------------------------------------------------------
    # OmniRoute — Default provider
    # OmniRoute exposes an OpenAI-compatible API so we use OpenAIProvider
    # with OmniRoute's base URL and API key.
    # -------------------------------------------------------------------
    if provider == "omniroute":
        if not settings.OMNIROUTE_API_KEY or settings.OMNIROUTE_API_KEY.startswith("your_"):
            raise ValueError(
                "OMNIROUTE_API_KEY is missing or not configured. "
                "Set AI_PROVIDER=omniroute and provide a valid OMNIROUTE_API_KEY "
                "in the backend .env file."
            )

        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        model_name = settings.OMNIROUTE_MODEL
        if model_name.lower() == "auto":
            global _OMNIROUTE_DYNAMIC_MODEL
            if _OMNIROUTE_DYNAMIC_MODEL is None:
                try:
                    req = urllib.request.Request(f"{settings.OMNIROUTE_BASE_URL}/models")
                    req.add_header("Authorization", f"Bearer {settings.OMNIROUTE_API_KEY}")
                    with urllib.request.urlopen(req, timeout=3.0) as response:
                        data = json.loads(response.read().decode("utf-8"))
                        if "data" in data and len(data["data"]) > 0:
                            # Use the first available model as the routing alias
                            _OMNIROUTE_DYNAMIC_MODEL = data["data"][0]["id"]
                        else:
                            _OMNIROUTE_DYNAMIC_MODEL = "zm/openai/chat-latest"
                except Exception as e:
                    logger.warning("Failed to dynamically fetch models from OmniRoute: %s", e)
                    _OMNIROUTE_DYNAMIC_MODEL = "zm/openai/chat-latest" # safe fallback
            model_name = _OMNIROUTE_DYNAMIC_MODEL

        # Log provider info without exposing the key
        logger.info(
            "AI provider: OmniRoute | base_url=%s | configured_model=%s | actual_model=%s",
            settings.OMNIROUTE_BASE_URL,
            settings.OMNIROUTE_MODEL,
            model_name
        )

        provider_instance = OpenAIProvider(
            base_url=settings.OMNIROUTE_BASE_URL,
            api_key=settings.OMNIROUTE_API_KEY,
        )
        return OpenAIChatModel(
            model_name=model_name,
            provider=provider_instance,
        )

    # -------------------------------------------------------------------
    # Groq — Kept for fallback / testing
    # Uses Groq's OpenAI-compatible endpoint.
    # -------------------------------------------------------------------
    elif provider == "groq":
        if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("your_groq"):
            raise ValueError(
                "GROQ_API_KEY is missing or invalid. "
                "Set AI_PROVIDER=groq and provide a valid GROQ_API_KEY "
                "in the backend .env file."
            )

        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        logger.info(
            "AI provider: Groq | model=%s",
            settings.GROQ_MODEL,
        )

        provider_instance = OpenAIProvider(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.GROQ_API_KEY,
        )
        return OpenAIChatModel(
            model_name=settings.GROQ_MODEL,
            provider=provider_instance,
        )

    # -------------------------------------------------------------------
    # Unknown provider
    # -------------------------------------------------------------------
    else:
        raise ValueError(
            f"Unknown AI_PROVIDER configured: '{provider}'. "
            "Supported providers: 'omniroute', 'groq'."
        )
