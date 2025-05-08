import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class Message(BaseModel):
    """Chat message model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str  # 'user' or 'bot'
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    sessionId: str
    message: str

class SessionResponse(BaseModel):
    """Response model for session creation."""
    sessionId: str
    created: str = Field(default_factory=lambda: datetime.now().isoformat())

class ChatHistory(BaseModel):
    """Chat history model."""
    sessionId: str
    messages: List[Message] = []

class NewsSource(BaseModel):
    """News source model."""
    title: str
    url: str
    description: Optional[str] = None 