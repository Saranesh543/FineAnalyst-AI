"""
Query Understanding Service

Classifies and understands an incoming user message, extracting a structured QueryPlan.
Replaces the intent router to provide a deep understanding of analytical intent.
"""

from __future__ import annotations

import logging
import re

from pydantic_ai import Agent

from app.schemas.intent import QueryPlan, Intent
from app.schemas.agent import MessageTurn
from app.services.llm_provider import get_llm_model

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an expert Query Understanding agent for a Business Intelligence platform.
Your job is to analyze the user's message, correct any spelling mistakes, and extract a structured QueryPlan.

You must output a structured JSON response matching the QueryPlan schema.

Intent classes:
1. conversation: Greetings (e.g. "hi", "thanks"), Farewells, or non-analytical chat.
2. knowledge: Educational questions (e.g. "What is a primary key?", "What is the weather today?"). Use this for out-of-domain questions too.
3. database: Requests to analyze data, compare metrics, or show charts (e.g. "Show top customers", "Create a chart").
4. schema: Questions about database metadata, tables, or columns (e.g. "What tables exist?", "Draw ER diagram").

Rules for QueryPlan extraction:
1. If the query is ambiguous (e.g. "Show sales", "Create a chart" with no context), set `clarification_needed = true` and provide a `clarification_question`. DO NOT GUESS missing parameters.
2. If the user asks "Create a chart for this" or says "Now show it for last year", use the provided Conversation History to inherit context (entities, metric, dimensions) and update the plan.
3. Extract `metrics`, `dimensions`, `entities`, `time_range`, `filters`. Do NOT invent them from thin air. If multiple metrics are asked (e.g., 'compare sales and profit'), include both in the `metrics` array.
4. If a visualization is explicitly requested (e.g. "bar chart", "trend line") or strongly implied (trend -> line, compare -> bar, distribution -> pie, correlation -> scatter, flow/process/hierarchy/relationship -> mermaid), set `requested_visualization`.
5. Fix spelling mistakes or expand abbreviations in `corrected_message` (e.g., 'rev' -> 'revenue'). If no correction is needed, set to the original message.

Use the conversation history carefully.
If previous request was: "Customer count by segment"
And current request is: "Create a chart for this"
Then intent is `database`, metrics is ["Customer count"], dimensions is ["segment"], clarification_needed is false, requested_visualization is "bar".

If a Previous QueryPlan is provided, you must MERGE the new question's intent with the previous QueryPlan to produce a Merged QueryPlan. Preserve the previous entities, dataset references, and time range unless explicitly changed. Never fall back to defaults if previous context exists.
CRITICAL RULE: You may ONLY use columns present in the current dataset schema or context. Never invent columns. Never reuse columns from previous conversations or previous datasets if they are not in the current schema. If the requested concept is unavailable, explain that it cannot be calculated from the current dataset.
CRITICAL RULE: Follow-up queries containing pronouns like "this", "that", "it", "these", "them" along with analytical verbs (create, show, compare, chart) MUST be classified as `database` intent. NEVER classify a request to chart or compare data as `conversation`.
CRITICAL RULE: If the user asks "what database do you have?", "who are you?", "how does this work?", or asks questions ABOUT the system itself, you MUST classify it as `conversation` or `knowledge`. DO NOT classify it as `database`.
"""

class QueryUnderstandingService:
    """Service to understand user queries and extract a QueryPlan using an LLM."""

    def __init__(self) -> None:
        self._agent: Agent | None = None

    def _get_agent(self) -> Agent:
        if self._agent is None:
            self._agent = Agent(
                model=get_llm_model(),
                system_prompt=SYSTEM_PROMPT
            )
            logger.info("QueryUnderstandingService agent initialised with string output.")
        return self._agent

    def _heuristic_classify(self, message: str) -> QueryPlan | None:
        # Normalize message: lowercase, remove punctuation, strip
        cleaned = re.sub(r'[^\w\s]', '', message.strip().lower())
        
        # Remove consecutive duplicate letters (e.g. hiiii -> hi)
        deduped = re.sub(r'(.)\1+', r'\1', cleaned)
        
        conversational_keywords = {
            "hi", "helo", "hey", "god morning", "god afternon", "god evening",
            "bye", "god night", "se you", "se ya",
            "thanks", "thank you", "thx", "thnks",
            "ok", "okay", "col", "nice", "great", "awesome",
            "who are you", "what can you do", "help", "how are you", "nice to met you",
            "gm", "gn", "god mrng", "mrng",
            "what database do you have", "what database", "what databases", "which database"
        }
        
        if deduped in conversational_keywords:
            return QueryPlan(
                intent=Intent.CONVERSATION,
                requires_database=False,
                corrected_message=message
            )
            
        words = cleaned.split()
        data_terms = {
            "show", "get", "find", "count", "average", "total", "revenue", 
            "sales", "top", "worst", "predict", "compare", "create", "dashboard",
            "anomalies", "customers", "orders", "products", "how many", "what is",
            "list", "chart", "analyze", "plot", "graph", "trend", "visualize"
        }
        
        if len(words) <= 3:
            if not any(word in data_terms for word in words):
                return QueryPlan(
                    intent=Intent.CONVERSATION,
                    requires_database=False,
                    corrected_message=message
                )
                
        return None

    async def understand(self, message: str, history: list[MessageTurn] | None = None, inline_columns: list[str] | None = None, previous_query_plan: QueryPlan | None = None) -> QueryPlan:
        """
        Extract the query plan for the given user message.
        """
        # 1. Heuristic bypass
        heuristic_plan = self._heuristic_classify(message)
        if heuristic_plan:
            logger.info("Heuristic classified intent: %s", heuristic_plan.intent)
            return heuristic_plan
            
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
        
        if inline_columns is not None:
            prompt += f"\n\n[System Note: The user has explicitly provided the required dataset inline. The columns in this dataset are: {', '.join(inline_columns)}. Use these columns to understand the analytical request. You MUST set requires_database = false.]"
            
        if previous_query_plan:
            prompt += f"\n\n[System Note: Previous QueryPlan: {previous_query_plan.model_dump_json()}]\nMerge this with the current question."
        
        try:
            logger.debug("Understanding query for prompt: %r", prompt[:100])
            result = await agent.run(prompt)
            raw_output = result.data if hasattr(result, 'data') else result.output
            plan = self._normalize_and_parse(raw_output, message)
            logger.info("Extracted QueryPlan intent: %s | Clarification: %s", plan.intent, plan.clarification_needed)
            return plan
        except Exception as e:
            logger.error("Intent routing model failed: %s", e)
            if inline_columns:
                logger.warning("Fail-safe triggered: Fallback to DATABASE intent because inline data was provided.")
                return QueryPlan(
                    intent=Intent.DATABASE,
                    requires_database=False,
                    corrected_message=message
                )
            raise e

    def _normalize_and_parse(self, raw_output: str, original_message: str) -> QueryPlan:
        import json
        text = raw_output.strip()
        
        # 1. Check if the output is just a raw intent keyword
        upper_text = text.upper()
        if upper_text in [i.value.upper() for i in Intent]:
            intent_val = next(i for i in Intent if i.value.upper() == upper_text)
            return QueryPlan(intent=intent_val, requires_database=False, corrected_message=original_message)
            
        # 2. Extract JSON if wrapped in markdown blocks
        json_str = text
        import re
        match = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Maybe it starts with { and ends with } without markdown
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = text[start:end+1]
                
        # 3. Parse JSON
        try:
            data = json.loads(json_str)
            return QueryPlan(**data)
        except Exception as e:
            logger.warning("Failed to parse intent output as JSON: %s. Raw: %s", e, text)
            
        # 4. Fallback keyword matching
        if "DATABASE" in upper_text:
            return QueryPlan(intent=Intent.DATABASE, requires_database=False, corrected_message=original_message)
        
        return QueryPlan(intent=Intent.CONVERSATION, requires_database=False, corrected_message=original_message)

# Singleton
query_understanding_service = QueryUnderstandingService()
