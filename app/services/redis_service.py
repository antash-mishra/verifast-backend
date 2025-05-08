import json
from typing import List, Dict, Any
import redis.asyncio as redis

from app.models.message import Message
from app.config import REDIS_URL, SESSION_TTL

# Initialize Redis client
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def get_redis_connection():
    """Get Redis connection."""
    return redis_client

async def store_message(session_id: str, message: Message, redis_conn=None):
    """Store a message in Redis."""
    if redis_conn is None:
        redis_conn = await get_redis_connection()
    
    key = f"chat_history:{session_id}"
    
    # Get existing messages or initialize empty list
    session_data = await redis_conn.get(key)
    
    if session_data:
        messages = json.loads(session_data)
        messages.append(message.model_dump())
    else:
        messages = [message.model_dump()]
    
    # Store updated messages and set TTL
    await redis_conn.set(key, json.dumps(messages), ex=SESSION_TTL)

async def get_session_history(session_id: str, redis_conn=None) -> List[Message]:
    """Get session chat history from Redis."""
    if redis_conn is None:
        redis_conn = await get_redis_connection()
    
    key = f"chat_history:{session_id}"
    session_data = await redis_conn.get(key)
    
    if session_data:
        messages_data = json.loads(session_data)
        return [Message(**msg) for msg in messages_data]
    
    return []

async def delete_session(session_id: str, redis_conn=None) -> bool:
    """Delete a session from Redis."""
    if redis_conn is None:
        redis_conn = await get_redis_connection()
    
    key = f"chat_history:{session_id}"
    result = await redis_conn.delete(key)
    return result > 0

async def create_session(session_id: str, redis_conn=None) -> bool:
    """Initialize a new session in Redis."""
    if redis_conn is None:
        redis_conn = await get_redis_connection()
    
    key = f"chat_history:{session_id}"
    await redis_conn.set(key, json.dumps([]), ex=SESSION_TTL)
    return True

async def session_exists(session_id: str, redis_conn=None) -> bool:
    """Check if a session exists in Redis."""
    if redis_conn is None:
        redis_conn = await get_redis_connection()
    
    key = f"chat_history:{session_id}"
    return await redis_conn.exists(key) > 0

async def get_all_sessions(redis_conn=None) -> List[Dict[str, Any]]:
    """Get all active sessions with their metadata."""
    if redis_conn is None:
        redis_conn = await get_redis_connection()
    
    # Get all keys matching the chat history pattern
    pattern = "chat_history:*"
    keys = await redis_conn.keys(pattern)
    
    sessions = []
    for key in keys:
        session_id = key.split(":", 1)[1]  # Extract session ID from key
        
        # Get message count and creation time
        session_data = await redis_conn.get(key)
        message_count = 0
        
        if session_data:
            messages = json.loads(session_data)
            message_count = len(messages)
            
            # Get first and last message timestamps if available
            first_timestamp = messages[0].get("timestamp") if messages else None
            last_timestamp = messages[-1].get("timestamp") if messages else None
            
            sessions.append({
                "session_id": session_id,
                "message_count": message_count,
                "created_at": first_timestamp,
                "last_active": last_timestamp
            })
    
    # Sort by last active timestamp, most recent first
    def safe_sort_key(session):
        # Return empty string for None values to ensure consistent comparison
        last_active = session.get("last_active")
        return "" if last_active is None else last_active
    
    sessions.sort(key=safe_sort_key, reverse=True)
    
    return sessions

async def delete_all_sessions(redis_conn=None) -> Dict[str, Any]:
    """Delete all active sessions."""
    if redis_conn is None:
        redis_conn = await get_redis_connection()
    
    # Get all keys matching the chat history pattern
    pattern = "chat_history:*"
    keys = await redis_conn.keys(pattern)
    
    # Delete all session keys
    deleted_count = 0
    if keys:
        deleted_count = await redis_conn.delete(*keys)
    
    return {
        "deleted_count": deleted_count,
        "success": True
    } 