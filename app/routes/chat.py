from fastapi import APIRouter, BackgroundTasks

from app.models.message import Message, ChatRequest
from app.services.redis_service import store_message
from app.services.rag_service import generate_response, get_vector_store_status

router = APIRouter(tags=["chat"])

@router.get("/")
async def root():
    """Root endpoint that returns a welcome message."""
    return {"message": "Welcome to RAG News Chatbot API!"}

@router.post("/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """Process a chat message and return response."""
    session_id = request.sessionId
    user_message = request.message
    
    # Store user message
    user_msg = Message(sender="user", content=user_message)
    await store_message(session_id, user_msg)
    
    # Generate response (non-streaming)
    response_text = await generate_response(user_message, session_id)
    
    # Store bot response
    bot_msg = Message(sender="bot", content=response_text)
    await store_message(session_id, bot_msg)
    
    return {
        "id": bot_msg.id,
        "content": bot_msg.content,
        "timestamp": bot_msg.timestamp
    }

@router.get("/status")
async def get_status():
    """Get system status."""
    vector_store_status = get_vector_store_status()
    
    return {
        "status": "ok",
        "vector_store_ready": vector_store_status["initialized"],
        "news_sources": vector_store_status["sources"]
    } 