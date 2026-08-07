from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime, timezone
import uuid

from app.database.session import get_db
from app.models.user import User
from app.models.chat import Session, Message
from app.api.deps import get_current_user
from app.schemas.chat import TurnCreate, SessionCreateResponse, SessionUpdate, SessionResponse

router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.get("", response_model=List[SessionResponse])
async def list_sessions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List all sessions for the authenticated user, including messages."""
    result = await db.execute(
        select(Session).where(Session.user_id == user.id).order_by(Session.updated_at.desc())
    )
    sessions = result.scalars().all()
    
    response = []
    for s in sessions:
        # Load messages (we might want eager loading but let's just await lazy load if needed, or query them)
        # Actually sqlalchemy async requires eager loading. Let's do a join or separate query.
        msg_result = await db.execute(select(Message).where(Message.session_id == s.id).order_by(Message.created_at.asc()))
        messages = msg_result.scalars().all()
        
        turn_list = []
        for m in messages:
            turn_list.append(m.turn_metadata or {})
            
        response.append(SessionResponse(
            id=s.id,
            title=s.title,
            isCustomTitle=s.is_custom_title,
            created_at=s.created_at,
            updated_at=s.updated_at,
            messages=turn_list
        ))
        
    return response


@router.post("", response_model=SessionCreateResponse)
async def create_session(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    new_session = Session(
        id=session_id,
        user_id=user.id,
        title="New Chat",
        is_custom_title=False
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return SessionCreateResponse(
        id=new_session.id,
        title=new_session.title,
        created_at=new_session.created_at,
        updated_at=new_session.updated_at
    )


@router.patch("/{session_id}")
async def update_session(session_id: str, payload: SessionUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Update session title."""
    result = await db.execute(select(Session).where(Session.id == session_id, Session.user_id == user.id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session.title = payload.title
    if payload.isCustomTitle is not None:
        session.is_custom_title = payload.isCustomTitle
    session.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    return {"message": "Session updated"}


@router.delete("/{session_id}")
async def delete_session(session_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Delete a session."""
    result = await db.execute(select(Session).where(Session.id == session_id, Session.user_id == user.id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    await db.delete(session)
    await db.commit()
    return {"message": "Session deleted"}


@router.post("/{session_id}/turns")
async def save_turn(session_id: str, turn: TurnCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Upsert a full UI turn (message) into the database."""
    # Verify session belongs to user
    result = await db.execute(select(Session).where(Session.id == session_id, Session.user_id == user.id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Check if message exists
    msg_result = await db.execute(select(Message).where(Message.id == turn.id, Message.session_id == session_id))
    message = msg_result.scalar_one_or_none()
    
    # Store turn as JSON dict
    turn_dict = turn.model_dump(exclude_none=True)
    
    # Text content mapping
    content = turn.answerText if turn.role == 'assistant' else turn.userText
    if content is None:
        content = ""
        
    # SQL mapping
    sql_context = None
    if turn.evidence and len(turn.evidence) > 0 and 'sql' in turn.evidence[0]:
        sql_context = turn.evidence[0]['sql']
        
    if message:
        message.content = content
        message.sql_context = sql_context
        message.turn_metadata = turn_dict
    else:
        new_msg = Message(
            id=turn.id,
            session_id=session_id,
            role=turn.role,
            content=content,
            sql_context=sql_context,
            turn_metadata=turn_dict,
        )
        try:
            # If created_at is provided, try to parse it
            new_msg.created_at = datetime.fromisoformat(turn.createdAt.replace('Z', '+00:00'))
        except Exception:
            pass
        db.add(new_msg)
        
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    
    return {"message": "Turn saved"}
