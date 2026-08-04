"""
LLM Provider Abstraction Module

Provides a factory to instantiate the correct pydantic-ai Model
based on environment configuration, allowing easy swapping between
Groq and others.
"""

import logging
from pydantic_ai.models import Model
from app.config.settings import settings

logger = logging.getLogger(__name__)

def get_llm_model() -> Model:
    """
    Instantiates and returns the configured LLM model based on settings.LLM_PROVIDER.
    
    Returns:
        Model: A pydantic-ai Model instance.
        
    Raises:
        ValueError: If the required API keys are missing or an unknown provider is specified.
    """
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "groq":
        if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("your_groq"):
            raise ValueError("GROQ_API_KEY is missing or invalid. Calls to LLM will fail.")
        
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
        
        logger.info("Using Groq with model: %s", settings.GROQ_MODEL)
        
        provider_instance = OpenAIProvider(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.GROQ_API_KEY,
        )
        return OpenAIChatModel(
            model_name=settings.GROQ_MODEL,
            provider=provider_instance,
        )
        
    else:
        raise ValueError(f"Unknown LLM_PROVIDER configured: '{provider}'. Supported providers: 'groq'.")
