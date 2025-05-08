import uuid
from fastapi import APIRouter, HTTPException

from app.models.message import SessionResponse
from app.services.redis_service import (
    create_session, 
    get_session_history, 
    delete_session, 
    session_exists
)

router = APIRouter(tags=["session"])

@router.post("/session", response_model=SessionResponse)
async def create_new_session():
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    
    # Initialize empty session in Redis
    await create_session(session_id)
    
    return SessionResponse(sessionId=session_id)

@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get chat history for a specific session."""
    messages = await get_session_history(session_id)
    
    if not messages and not await session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"sessionId": session_id, "messages": messages}

@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a chat session."""
    # Check if session exists
    if not await session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete session data
    await delete_session(session_id)
    
    return {"message": "Session cleared successfully"} 