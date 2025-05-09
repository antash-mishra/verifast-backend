import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import APP_TITLE, APP_DESCRIPTION, APP_VERSION
from app.routes import chat, session, websocket
from app.services.rag_service import ingest_news

# Initialize FastAPI app
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)
app.include_router(session.router)
# WebSocket routes are already defined in the router
app.include_router(websocket.router)

@app.get("/status", tags=["Health"])
async def status():
    """Health check endpoint for the application."""
    return {"status": "ok", "service": APP_TITLE, "version": APP_VERSION}

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    # Start news ingestion in background
    asyncio.create_task(ingest_news()) 