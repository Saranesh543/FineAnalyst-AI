"""
Intent Router Service

Classifies an incoming user message into one of the predefined Intent classes
using an LLM (pydantic-ai Agent) to ensure robust and contextual classification.
"""

from __future__ import annotations

import logging

from pydantic_ai import Agent

from app.schemas.intent import IntentResult
from app.schemas.agent import MessageTurn
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

4. schema:
   - Questions about the database metadata, structure, tables, columns, or relationships.
   - Any general question asking what data is available.
   - Example: "What database do you have?", "What tables are available?", "Show me your schema", "What columns exist?", "Describe the database", "What data is stored here?"

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
                system_prompt=SYSTEM_PROMPT,
            )
            logger.info("IntentRouterService agent initialised (plain text mode).")
        return self._agent

    async def classify(self, message: str, history: list[MessageTurn] | None = None) -> IntentResult:
        """
        Classify the intent of the given user message.

        Args:
            message: Raw user message.
            history: Optional list of previous conversation turns.

        Returns:
            IntentResult containing the detected intent.
        """
        agent = self._get_agent()
        
        if history and len(history) > 0:
            prompt_parts = ["Conversation History:"]
            for i, past_msg in enumerate(history):
                prompt_parts.append(f"{past_msg.role.value.capitalize()} (turn {i+1}): {past_msg.content}")
            prompt_parts.append("")
            prompt_parts.append(f"Current Message: {message}")
            prompt = "\n".join(prompt_parts)
        else:
            prompt = message
        
        logger.debug("Classifying intent for prompt: %r", prompt[:100])
        try:
            result = await agent.run(prompt)
            raw_response = result.output.strip().lower()
            logger.info("Raw LLM intent response: %r", raw_response)
            
            # Manual parsing and validation
            if "schema" in raw_response:
                parsed_intent = "schema"
            elif "database" in raw_response:
                parsed_intent = "database"
            elif "knowledge" in raw_response:
                parsed_intent = "knowledge"
            elif "conversation" in raw_response:
                parsed_intent = "conversation"
            else:
                logger.warning("Unrecognized intent format from LLM: %r. Defaulting to conversation.", raw_response)
                parsed_intent = "conversation"
                
            logger.info("Parsed intent: %s", parsed_intent)
            validated_output = IntentResult(intent=parsed_intent)
            logger.info("Final IntentResult: %s", validated_output.model_dump_json())
            return validated_output
        except Exception as exc:
            logger.exception("LLM Intent Router failed to validate intent output. Exception: %s | Type: %s", exc, type(exc).__name__)
            raise

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

intent_router = IntentRouterService()
