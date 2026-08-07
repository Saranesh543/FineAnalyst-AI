"""
FineAnalyst AI Agent Module

Defines the singleton PydanticAI agent powered by the configured LLM Provider (e.g. Groq).
Tools are NOT registered here — this module only establishes the agent
architecture so tools can be attached in future iterations.

The agent is initialised lazily on the first call to ``get_agent()`` so the
server can start (and pass health checks) even before API keys are set.
"""

import logging
from typing import Optional

from pydantic_ai import Agent
from app.services.llm_provider import get_llm_model

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are FineAnalyst AI, an autonomous Business Intelligence agent. "
    "Your responsibility is to understand user requests, plan investigations, "
    "call available tools when required, explain results clearly, and provide "
    "business insights. "
    "If the user says a greeting or expresses gratitude, reply politely and casually. "
    "If the user asks an out-of-domain question or something you cannot answer, gracefully explain your limitations "
    "as a business intelligence agent and suggest an analytical task you CAN do (e.g., 'I can help you analyze your database and find insights.'). "
    "Never crash or output generic error messages; always maintain a helpful, conversational tone."
)

# ---------------------------------------------------------------------------
# Internal singleton cache
# ---------------------------------------------------------------------------
_agent_instance: Optional[Agent] = None


def _build_agent() -> Agent:
    """
    Construct and return a new PydanticAI Agent instance.
    """

    # Construct the model using the provider factory
    model = get_llm_model()

    agent: Agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
    )

    # -----------------------------------------------------------------------
    # Tool Registration Hook
    # -----------------------------------------------------------------------
    # Future tools should be registered here using:
    #
    #   @agent.tool
    #   async def my_tool(ctx: RunContext, ...) -> ...:
    #       ...
    #
    # This section is intentionally empty for this iteration.
    # -----------------------------------------------------------------------

    logger.info("FineAnalyst AI agent initialised.")
    return agent


def get_agent() -> Agent:
    """
    Return the module-level singleton agent, building it on first call.

    This lazy pattern keeps import-time side-effects minimal:
    the server starts and passes health checks even before the API key
    is set. The ``ValueError`` surfaces only at the first real chat request.
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = _build_agent()
    return _agent_instance


# Convenience alias kept for backward-compatibility with existing imports.
# Resolves to the same lazy getter result.
def fineanalyst_agent_factory() -> Agent:  # noqa: D401
    """Alias for ``get_agent()``."""
    return get_agent()

