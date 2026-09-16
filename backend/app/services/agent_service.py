"""
Agent Service Module

Provides AgentService — the single entry-point for all agent interactions.
Responsibilities:
  - Classify every incoming message via IntentClassifier (Phase 2.1).
  - Return conversational responses (Greeting / Identity / Help) directly,
    bypassing schema discovery and SQL generation entirely.
  - Manage per-session conversation history (in-memory, no DB persistence).
  - Invoke the PydanticAI agent with the appropriate message history.
  - Translate PydanticAI results into structured AgentResponse objects.
  - Emit structured log entries for every request and response.
  - Handle AI provider / network errors gracefully.
"""

from __future__ import annotations

import logging
import time
import uuid
import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart

from app.agents.fineanalyst_agent import get_agent
from app.schemas.agent import (
    AgentErrorResponse,
    AgentResponse,
    AgentStatus,
    UsageInfo,
    MessageTurn,
    MessageRole
)

if TYPE_CHECKING:
    pass  # reserved for future type-only imports

logger = logging.getLogger(__name__)

# Memory is now stateless and managed by the frontend.
# The session endpoints will remain for compatibility or extended to clear backend cache if any.
_SESSION_HISTORY: dict[str, list[ModelMessage]] = defaultdict(list)
_MAX_HISTORY_MESSAGES: int = 100


class AgentService:
    """
    Stateless service class that orchestrates calls to the FineAnalyst agent.

    A single shared instance is created at module level and injected into
    FastAPI route handlers via dependency injection.

    The underlying PydanticAI ``Agent`` is resolved lazily on the first call
    to ``process_message`` so that importing this module never fails due to a
    missing API key.
    """

    def __init__(self) -> None:
        logger.debug("AgentService initialised.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process_message(
        self,
        user_message: str,
        session_id: str | None = None,
        history: list[MessageTurn] | None = None,
        user_id: int | None = None,
    ) -> AgentResponse | AgentErrorResponse:
        """
        Send *user_message* to the agent and return a structured response.

        Args:
            user_message: The raw text from the user.
            session_id:   Optional identifier for conversation continuity.
            history:      List of previous message turns for context.
            user_id:      Optional identifier of the user to fetch attachments.

        Returns:
            AgentResponse on success, AgentErrorResponse on failure.
        """
        request_id = str(uuid.uuid4())
        t_start = time.perf_counter()

        logger.info(
            "[request_id=%s] Received message | session_id=%s | length=%d chars",
            request_id,
            session_id,
            len(user_message),
        )

        from pydantic_ai.messages import UserPromptPart
        
        # Build message history for Pydantic-AI
        model_history: list[ModelMessage] = []
        if history:
            for turn in history:
                if turn.role == MessageRole.USER:
                    model_history.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
                elif turn.role == MessageRole.ASSISTANT:
                    model_history.append(ModelResponse(parts=[TextPart(content=turn.content)]))
                    
        # Inject extracted text from attachments if any
        if session_id and user_id:
            try:
                from sqlalchemy.ext.asyncio import AsyncSession
                from app.database.session import AsyncSessionLocal
                from sqlalchemy import select
                from app.models.chat import FileAttachment
                
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(FileAttachment).where(
                            FileAttachment.session_id == session_id,
                            FileAttachment.user_id == user_id
                        )
                    )
                    attachments = result.scalars().all()
                    
                    if attachments:
                        logger.info("[request_id=%s] Resolved %d uploaded files for session_id=%s", request_id, len(attachments), session_id)
                        file_context = "Context from uploaded files:\n"
                        for att in attachments:
                            logger.info("[request_id=%s] Including attachment: %s (type=%s, table=%s)", request_id, att.filename, att.file_type, att.table_name)
                            if att.table_name:
                                file_context += f"--- {att.filename} ---\nThis structured file was imported into the database table `{att.table_name}`. Query this table to answer questions about this file.\n\n"
                            elif att.extracted_text:
                                file_context += f"--- {att.filename} ---\n{att.extracted_text[:5000]}\n\n"
                        
                        user_message = f"{file_context}\n\nUser Question:\n{user_message}"
                        logger.info("[request_id=%s] Final injected user message:\n%s", request_id, user_message[:500] + ("..." if len(user_message) > 500 else ""))
            except Exception as e:
                logger.error("Failed to fetch attachments for context: %s", e)

        # Intercept database meta-questions deterministically (no LLM call)
        import re
        cleaned_msg = re.sub(r'[^\w\s]', '', user_message.strip().lower())
        
        if re.search(r'\b(what|which|where)\b.*\b(database|db|data)\b.*\b(have|use|using|stored|app|fineanalyst)\b', cleaned_msg):
            logger.info("[request_id=%s] Intercepted database meta-question. Returning deterministic response.", request_id)
            return AgentResponse(
                status=AgentStatus.SUCCESS,
                session_id=session_id,
                message="I use FineAnalyst's application database architecture. My primary backend is a **SQLite database** (`fineanalyst.db`). I also dynamically ingest and query any structured datasets (like CSV or Excel files) that you upload directly into our current conversation.",
                usage=UsageInfo(requests=0, request_tokens=0, response_tokens=0, total_tokens=0)
            )

        if re.search(r'\b(who|what|tell)\b.*\b(created|made|developed|built|behind|creator|creators|team|company|fineworks)\b', cleaned_msg) or 'fineworks' in cleaned_msg:
            logger.info("[request_id=%s] Intercepted creator/FineWorks meta-question. Returning deterministic response.", request_id)
            
            # Dynamically adapt the response string based on what the user asked
            is_who_created_you = bool(re.search(r'\b(who|what|tell)\b.*\b(created|made|developed|built)\b.*\b(you)\b', cleaned_msg))
            is_who_members = bool(re.search(r'\b(who)\b.*\b(members|team)\b', cleaned_msg))
            is_relationship = bool(re.search(r'\b(relationship|are you)\b.*\b(fineworks)\b', cleaned_msg))

            if is_relationship:
                msg = "I'm FineAnalyst, a product developed by FineWorks. FineWorks is the technology team behind me."
            elif is_who_members:
                msg = "FineWorks is made up of Saranesh, Praveen Balaji, Nitish, and Sakthi Saran."
            elif is_who_created_you:
                msg = (
                    "I was created by FineWorks. FineWorks is an innovation-driven technology team founded in 2024 by Saranesh, Praveen Balaji, Nitish, and Sakthi Saran. "
                    "The team builds modern websites, web applications, AI-powered solutions, and digital products. "
                    "I'm FineAnalyst, one of the AI-powered products developed by FineWorks."
                )
            else:
                msg = (
                    "FineWorks is an innovation-driven technology team founded in 2024. The team focuses on building modern websites, web applications, AI-powered solutions, software, and digital products that help startups and businesses grow.\n\n"
                    "Its areas include software development, web development, full-stack development, problem solving, digital transformation, and technology consulting. "
                    "FineWorks also participates in hackathons and innovation challenges, with a focus on turning ideas into practical technology solutions.\n\n"
                    "The team consists of Saranesh, Praveen Balaji, Nitish, and Sakthi Saran.\n\n"
                    "Some of their projects include FineAnalyst-AI (me!), FineFlow, FineGuard, ResQ-Link, and FineFeed. "
                    "You can learn more about FineWorks at https://www.thefineworks.com/"
                )
            
            return AgentResponse(
                status=AgentStatus.SUCCESS,
                session_id=session_id,
                message=msg,
                usage=UsageInfo(requests=0, request_tokens=0, response_tokens=0, total_tokens=0)
            )

        try:
            agent = get_agent()  # lazy — raises ValueError if key is missing
            provider_name = settings.AI_PROVIDER
            
            logger.info("[LLM] [request_id=%s] provider=%s", request_id, provider_name)
            logger.info("[LLM] [request_id=%s] request_started", request_id)
            
            result = await agent.run(
                user_message,
                message_history=model_history if model_history else None,
            )
            
            logger.info("[LLM] [request_id=%s] request_completed", request_id)

            elapsed_ms = (time.perf_counter() - t_start) * 1_000
            # In PydanticAI 2.22, `usage` is a property (RunUsage dataclass),
            # not a callable method. Field names also changed from the older
            # request_tokens/response_tokens to input_tokens/output_tokens.
            _raw_usage = result.usage
            usage_info = UsageInfo(
                requests=getattr(_raw_usage, "requests", 0),
                request_tokens=getattr(_raw_usage, "input_tokens", None),
                response_tokens=getattr(_raw_usage, "output_tokens", None),
                total_tokens=getattr(_raw_usage, "total_tokens", None),
            )

            logger.info(
                "[request_id=%s] Agent response received | elapsed=%.1f ms | "
                "tokens_total=%s",
                request_id,
                elapsed_ms,
                usage_info.total_tokens,
            )

            return AgentResponse(
                status=AgentStatus.SUCCESS,
                session_id=session_id,
                message=result.output,
                usage=usage_info,
            )

        except asyncio.CancelledError as exc:
            elapsed_ms = (time.perf_counter() - t_start) * 1_000
            logger.warning("[request_id=%s] Request cancelled by client (CancelledError) | elapsed=%.1f ms", request_id, elapsed_ms)
            return AgentErrorResponse(
                status=AgentStatus.ERROR,
                error_code="CLIENT_CANCELLED",
                message="The request was cancelled by the client."
            )
        except Exception as exc:  # noqa: BLE001 — intentional broad catch
            elapsed_ms = (time.perf_counter() - t_start) * 1_000
            exc_type = type(exc).__name__

            # 1) Client Cancellation (for older Python or custom CancelledError wrappers)
            if exc_type == "CancelledError":
                logger.warning("[request_id=%s] Request cancelled by client (via Exception) | elapsed=%.1f ms", request_id, elapsed_ms)
                return AgentErrorResponse(
                    status=AgentStatus.ERROR,
                    error_code="CLIENT_CANCELLED",
                    message="The request was cancelled by the client."
                )

            # 2) Rate Limits
            is_429 = (
                exc_type == "RateLimitError" or 
                (hasattr(exc, "status_code") and getattr(exc, "status_code") == 429) or 
                (hasattr(exc, "response") and hasattr(exc.response, "status_code") and getattr(exc.response, "status_code") == 429)
            )
            
            if is_429:
                logger.warning(
                    "[request_id=%s] AI provider rate limit reached (HTTP 429) | elapsed=%.1f ms | exc=%s",
                    request_id,
                    elapsed_ms,
                    exc_type
                )
                return AgentErrorResponse(
                    status=AgentStatus.ERROR,
                    error_code="AI_RATE_LIMITED",
                    message="The AI provider rate limit has been reached. Please try again later."
                )

            # 3) Generic / Other provider errors
            status_code = "UNKNOWN"
            if hasattr(exc, "status_code"):
                status_code = getattr(exc, "status_code")
            elif hasattr(exc, "response") and hasattr(exc.response, "status_code"):
                status_code = getattr(exc.response, "status_code")

            logger.error(
                "[LLM] [request_id=%s] request_failed exception_type=%s status_code=%s",
                request_id,
                exc_type,
                status_code
            )

            logger.exception(
                "[request_id=%s] Agent run failed | elapsed=%.1f ms | "
                "error=%s: %s",
                request_id,
                elapsed_ms,
                exc_type,
                str(exc),
            )

            return AgentErrorResponse(
                status=AgentStatus.ERROR,
                error_code=exc_type,
                message=self._humanise_error(exc)
            )

    # ------------------------------------------------------------------
    # Session Management Helpers
    # ------------------------------------------------------------------

    def clear_session(self, session_id: str) -> bool:
        """
        Clear the conversation history for a given session.

        Returns True if a session existed and was removed, False otherwise.
        """
        if session_id in _SESSION_HISTORY:
            del _SESSION_HISTORY[session_id]
            logger.info("Session history cleared for session_id=%s", session_id)
            return True
        return False

    def session_message_count(self, session_id: str) -> int:
        """Return the number of messages stored for the given session."""
        return len(_SESSION_HISTORY.get(session_id, []))

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _humanise_error(exc: Exception) -> str:
        """
        Convert a raw exception into a user-friendly error string.

        Specific HTTP/provider error classes can be matched here in future
        iterations to provide more actionable messages.
        """
        exc_type = type(exc).__name__

        # Common network / API error patterns
        if any(kw in exc_type.lower() for kw in ("api", "groq", "openai", "omniroute", "http")):
            return (
                "The AI model returned an error. "
                "Please check the provider configuration and try again."
            )
        if "timeout" in exc_type.lower() or "connect" in exc_type.lower():
            return (
                "The request timed out while connecting to the AI service. "
                "Please try again in a moment."
            )

        # Generic fallback
        return (
            "An unexpected error occurred while processing your request. "
            "Please try again."
        )


# ---------------------------------------------------------------------------
# Module-level singleton — shared across all FastAPI requests.
# ---------------------------------------------------------------------------
agent_service = AgentService()
