import uuid
import logging
import os
from fastapi import APIRouter, HTTPException

from app.models.message import SessionResponse
from app.services.redis_service import (
    create_session, 
    get_session_history, 
    delete_session, 
    session_exists,
    get_all_sessions,
    delete_all_sessions
)

logger = logging.getLogger("session_routes")

router = APIRouter(tags=["session"])

@router.post("/session", response_model=SessionResponse)
async def create_new_session():
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    redis_url = os.getenv("REDIS_URL")
    logger.info(f"Creating session {session_id} in Redis: {redis_url}")
    try:
        await create_session(session_id)
    except Exception as e:
        logger.error(f"Error creating session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")
    return SessionResponse(sessionId=session_id)

@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get chat history for a specific session."""
    redis_url = os.getenv("REDIS_URL")
    logger.info(f"Retrieving history for session {session_id} from Redis: {redis_url}")
    try:
        messages = await get_session_history(session_id)
        if not messages and not await session_exists(session_id):
            logger.warning(f"Session {session_id} not found in Redis: {redis_url}")
            raise HTTPException(status_code=404, detail="Session not found")
        return {"sessionId": session_id, "messages": messages}
    except Exception as e:
        logger.error(f"Error retrieving history for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session history")

@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a chat session."""
    redis_url = os.getenv("REDIS_URL")
    logger.info(f"Attempting to delete session {session_id} from Redis: {redis_url}")
    try:
        if not await session_exists(session_id):
            logger.warning(f"Session {session_id} not found in Redis: {redis_url}")
            raise HTTPException(status_code=404, detail="Session not found")
        await delete_session(session_id)
        logger.info(f"Session {session_id} deleted from Redis: {redis_url}")
        return {"message": "Session cleared successfully"}
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")

@router.get("/sessions")
async def list_sessions():
    redis_url = os.getenv("REDIS_URL")
    logger.info(f"Listing all sessions from Redis: {redis_url}")
    try:
        sessions = await get_all_sessions()
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to list sessions")

@router.delete("/sessions")
async def delete_sessions():
    redis_url = os.getenv("REDIS_URL")
    logger.info(f"Deleting all sessions from Redis: {redis_url}")
    try:
        result = await delete_all_sessions()
        logger.info(f"Deleted {result['deleted_count']} sessions from Redis: {redis_url}")
        return {
            "message": f"Successfully deleted {result['deleted_count']} sessions",
            "deleted_count": result["deleted_count"]
        }
    except Exception as e:
        logger.error(f"Error deleting all sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete all sessions") 