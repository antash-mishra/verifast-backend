import json
import asyncio
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.message import Message
from app.services.redis_service import store_message
from app.services.rag_service import generate_response

router = APIRouter(tags=["websocket"])

# WebSocket for streaming responses
@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            # Store user message
            user_msg = Message(sender="user", content=user_message)
            await store_message(session_id, user_msg)
            
            # Generate response
            task_id = str(uuid.uuid4())
            
            # Send typing indicator
            await websocket.send_json({"type": "typing_start", "taskId": task_id})
            
            # Stream response (simulated)
            response_text = await generate_response(user_message, session_id, task_id)
            bot_msg = Message(sender="bot", content=response_text)
            
            # For demo, we'll stream character by character
            for i in range(len(response_text)):
                partial_text = response_text[:i+1]
                await websocket.send_json({
                    "type": "partial_response",
                    "taskId": task_id,
                    "content": partial_text
                })
                await asyncio.sleep(0.02)  # Adjust speed as needed
            
            # Send complete message
            await websocket.send_json({
                "type": "complete_response",
                "id": bot_msg.id,
                "content": bot_msg.content,
                "timestamp": bot_msg.timestamp
            })
            
            # Store complete bot response
            await store_message(session_id, bot_msg)
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}") 