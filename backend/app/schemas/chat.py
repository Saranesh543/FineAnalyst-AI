from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

class TurnCreate(BaseModel):
    id: str
    role: str
    userText: Optional[str] = None
    answerText: Optional[str] = None
    status: str
    createdAt: str
    thinkingSteps: Optional[List[Dict[str, Any]]] = None
    evidence: Optional[List[Dict[str, Any]]] = None
    followUpSuggestions: Optional[List[str]] = None

class SessionCreateResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

class SessionUpdate(BaseModel):
    title: str
    isCustomTitle: Optional[bool] = None

class SessionResponse(BaseModel):
    id: str
    title: str
    isCustomTitle: bool
    created_at: datetime
    updated_at: datetime
    messages: List[Dict[str, Any]] = []

class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
