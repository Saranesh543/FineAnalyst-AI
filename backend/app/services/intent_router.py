"""
Intent Router Service

Classifies an incoming user message into one of the predefined Intent classes
using an LLM (pydantic-ai Agent) to ensure robust and contextual classification.
"""

from __future__ import annotations

import logging

from pydantic_ai import Agent

from app.schemas.intent import IntentResult
from app.services.llm_provider import get_llm_model

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an intent classification routing agent.
Your ONLY job is to classify the user's message into exactly one of three intents.

1. conversation:
   - Greetings (e.g., "Hi", "Hello", "Good morning")
   - Farewells (e.g., "Bye", "See you later")
   - Polite remarks (e.g., "Thanks", "Thank you")
   - Identity questions (e.g., "Who are you?", "What can you do?", "Nice to meet you")

2. knowledge:
   - Educational questions
   - Explanations of concepts
   - Definitions
   - Example: "Explain SQL joins", "What is a primary key?", "What is business intelligence?"

3. database:
   - Requests to analyze data, show metrics, or aggregate data.
   - Any query that requires looking at the actual database tables.
   - Example: "Show top customers", "Average salary", "Highest selling products", "Show all employees".

Respond strictly with the correct intent. Do not include any other text or explanations.
"""

class IntentRouterService:
    """Service to classify user intents using an LLM."""

    def __init__(self) -> None:
        self._agent: Agent | None = None

    def _get_agent(self) -> Agent:
        if self._agent is None:
            self._agent = Agent(
                model=get_llm_model(),
                output_type=IntentResult,
                system_prompt=SYSTEM_PROMPT,
            )
            logger.info("IntentRouterService agent initialised.")
        return self._agent

    async def classify(self, message: str) -> IntentResult:
        """
        Classify the message into an Intent using the LLM.

        Args:
            message: Raw user message.

        Returns:
            IntentResult containing the detected intent.
        """
        agent = self._get_agent()
        logger.debug("Classifying intent for message: %r", message[:100])
        try:
            result = await agent.run(message)
            logger.info("Intent classified successfully. Validated Output: %s", result.output.model_dump_json())
            return result.output
        except Exception as exc:
            logger.error("LLM Intent Router failed to validate intent output. Exception: %s | Type: %s", exc, type(exc).__name__)
            raise

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

intent_router = IntentRouterService()
