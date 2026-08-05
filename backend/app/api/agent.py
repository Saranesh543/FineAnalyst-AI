"""
Agent API Routes

Exposes HTTP endpoints for interacting with FineAnalyst AI.
All heavy lifting is delegated to AgentService; this module only handles
HTTP concerns (request validation, status codes, response shaping).
"""

from __future__ import annotations

import logging
import traceback

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.schemas.agent import AgentErrorResponse, AgentRequest, AgentResponse
from app.services.agent_service import agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent"])


# ---------------------------------------------------------------------------
# POST /agent/chat
# ---------------------------------------------------------------------------

@router.post(
    "/chat",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to FineAnalyst AI",
    description=(
        "Submit a natural-language message and receive a structured response "
        "from the FineAnalyst AI agent. "
        "Optionally supply a `session_id` to maintain conversation history."
    ),
    responses={
        200: {"model": AgentResponse, "description": "Successful agent response."},
        422: {"description": "Validation error — request body is malformed."},
        500: {"model": AgentErrorResponse, "description": "Agent runtime error."},
    },
)
async def chat(payload: AgentRequest) -> JSONResponse:
    import uuid
    import time
    
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    logger.info("[%s] Chat request received. Message: %r, Session: %s", request_id, payload.message, payload.session_id)
    logger.info("[%s] Request Body: %s", request_id, payload.model_dump_json())

    try:
        result = await agent_service.process_message(
            user_message=payload.message,
            session_id=payload.session_id,
        )

        if isinstance(result, AgentErrorResponse):
            logger.warning(
                "[%s] Returning error response to client | error_code=%s",
                request_id,
                result.error_code,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=result.model_dump(mode="json"),
            )

        response_json = result.model_dump(mode="json")
        logger.info("[%s] Chat completed successfully. HTTP 200.", request_id)
        logger.debug("[%s] Response Body: %s", request_id, response_json)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_json,
        )
    except Exception as e:
        logger.exception("[%s] Unhandled exception in chat endpoint: %s", request_id, e)
        traceback.print_exc()
        raise


# ---------------------------------------------------------------------------
# DELETE /agent/session/{session_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/session/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Clear conversation history for a session",
    description=(
        "Removes the in-memory conversation history associated with the given "
        "`session_id`. After this call, the next message in that session will "
        "start a fresh conversation."
    ),
)
async def clear_session(session_id: str) -> dict:
    """Delete in-memory conversation history for the specified session."""
    cleared = agent_service.clear_session(session_id)
    return {
        "cleared": cleared,
        "session_id": session_id,
        "message": (
            "Session history cleared." if cleared else "No history found for this session."
        ),
    }


# ---------------------------------------------------------------------------
# GET /agent/session/{session_id}/info
# ---------------------------------------------------------------------------

@router.get(
    "/session/{session_id}/info",
    status_code=status.HTTP_200_OK,
    summary="Get session info",
    description="Returns the number of messages stored for a given session.",
)
async def session_info(session_id: str) -> dict:
    """Return message count for the specified session."""
    count = agent_service.session_message_count(session_id)
    return {
        "session_id": session_id,
        "message_count": count,
    }
