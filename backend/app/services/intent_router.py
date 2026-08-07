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
Your job is to analyze the user's message, correct any spelling mistakes, and classify it into EXACTLY ONE of four intents.

You must output a structured JSON response matching the IntentResult schema, with two fields:
1. `corrected_message`: The typo-corrected version of the user message. Fix spelling mistakes or expand abbreviations (e.g., 'rev' -> 'revenue'). If no correction is needed, return the original message. Do NOT change the user's intended meaning.
2. `intent`: The detected intent class.

Intents:
1. conversation:
   - Greetings (e.g., "Hi", "Hello", "Good morning")
   - Farewells (e.g., "Bye", "See you later")
   - Polite remarks (e.g., "Thanks", "Thank you")
   - Identity questions (e.g., "Who are you?", "What can you do?", "Nice to meet you")
   - Contextual chat follow-ups that don't query data.

2. knowledge:
   - Educational questions
   - Explanations of concepts
   - Definitions
   - Example: "Explain SQL joins", "What is a primary key?", "What is business intelligence?"

3. database:
   - Requests to analyze data, show metrics, or aggregate data.
   - Any query that requires looking at the actual database tables.
   - Follow-up questions about data (e.g. "and for last year?", "what about the worst?").
   - Example: "Show top customers", "Average salary", "Highest selling products", "Show all employees".

4. schema:
   - Questions about the database metadata, structure, tables, columns, or relationships.
   - Any general question asking what data is available.
   - Example: "What database do you have?", "What tables are available?", "Show me your schema", "What columns exist?", "Describe the database", "What data is stored here?"

Use the conversation history to help disambiguate short messages. For example, if the previous message was "Show top customers", and the current message is "what about the worst?", the intent is `database`, not `conversation`.
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
                output_type=IntentResult
            )
            logger.info("IntentRouterService agent initialised with structured output.")
        return self._agent

    def _heuristic_classify(self, message: str) -> str | None:
        import re
        
        # Normalize message: lowercase, remove punctuation, strip
        cleaned = re.sub(r'[^\w\s]', '', message.strip().lower())
        
        # Remove consecutive duplicate letters (e.g. hiiii -> hi, helloo -> helo, byee -> bye)
        # Note: This will turn "hello" into "helo", "good" into "god".
        deduped = re.sub(r'(.)\1+', r'\1', cleaned)
        
        # Keyword matching (matching on the deduped string where appropriate)
        conversational_keywords = {
            "hi", "helo", "hey", "god morning", "god afternon", "god evening",
            "bye", "god night", "se you", "se ya",
            "thanks", "thank you", "thx", "thnks",
            "ok", "okay", "col", "nice", "great", "awesome",
            "who are you", "what can you do", "help", "how are you", "nice to met you",
            "gm", "gn", "god mrng", "mrng"
        }
        
        if deduped in conversational_keywords:
            return "conversation"
            
        # Short message heuristic (matching on the original cleaned string)
        words = cleaned.split()
        data_terms = {
            "show", "get", "find", "count", "average", "total", "revenue", 
            "sales", "top", "worst", "predict", "compare", "create", "dashboard",
            "anomalies", "customers", "orders", "products", "how many", "what is",
            "list"
        }
        
        if len(words) <= 3:
            if not any(word in data_terms for word in words):
                return "conversation"
                
        return None

    async def classify(self, message: str, history: list[MessageTurn] | None = None) -> IntentResult:
        """
        Classify the intent of the given user message.

        Args:
            message: Raw user message.
            history: Optional list of previous conversation turns.

        Returns:
            IntentResult containing the detected intent.
        """
        
        # 1. Heuristic bypass
        heuristic_intent = self._heuristic_classify(message)
        if heuristic_intent:
            logger.info("Heuristic classified intent: %s", heuristic_intent)
            return IntentResult(intent=heuristic_intent)
            
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
            validated_output: IntentResult = result.output
            logger.info("Parsed intent: %s | Corrected msg: %r", validated_output.intent, validated_output.corrected_message)
            return validated_output
        except Exception as exc:
            logger.exception("LLM Intent Router failed to validate intent output. Exception: %s | Type: %s", exc, type(exc).__name__)
            # Fallback instead of crashing
            return IntentResult(intent="conversation", corrected_message=message)

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

intent_router = IntentRouterService()
