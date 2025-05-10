# RAG News Chatbot Backend

A FastAPI backend that powers a Retrieval-Augmented Generation (RAG) chatbot for answering questions about recent news articles.

## Features

- Automatic news ingestion from multiple RSS feeds
- Vector-based semantic search for relevant news content
- Gemini Pro AI integration for natural language responses
- WebSocket support for streaming real-time responses
- Session management with Redis
- Citation tracking to reference source articles

## Setup

### Prerequisites

- Python 3.9+
- Redis server
- Gemini API key

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with required environment variables
echo "REDIS_URL=redis://localhost:6379
GEMINI_API_KEY=your-gemini-api-key" > .env
```

### Running the Application

```bash
python main.py
```

The server will start on http://localhost:8000

## API Endpoints

### Chat

- `POST /chat`: Send a message and get a response
- `WebSocket /ws/chat/{session_id}`: Stream chat messages with real-time responses

### Session Management

- `POST /session`: Create a new chat session
- `GET /sessions`: List available sessions
- `GET /history/{session_id}`: Get chat history for a session
- `DELETE /session/{session_id}`: Clear a session

### System

- `GET /status`: Check system status and news ingestion progress

## Documentation

API documentation is available at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## Environment Variables

- `REDIS_URL`: Connection string for Redis (default: `redis://localhost:6379`)
- `GEMINI_API_KEY`: API key for Google's Gemini AI model
- `PORT`: Server port (default: `8000`)
- `HOST`: Server host (default: `0.0.0.0`)
- `SESSION_TTL`: Session time-to-live in seconds (default: `86400`)