# RAG News Chatbot Backend API

## Overview
This is a Retrieval-Augmented Generation (RAG) chatbot API built with FastAPI that answers queries over a news corpus. The application uses Redis for in-memory caching of chat history and Qdrant as the vector store for efficient similarity search.

## Features
- RAG pipeline for answering questions about news articles
- Redis caching for session history and message storage
- Gemini Pro AI for generating responses
- Jina Embeddings for vectorizing article content
- WebSocket support for streaming responses
- Automatic news ingestion from multiple RSS feeds
- REST API endpoints for session management and chat

## Getting Started

### Prerequisites
- Python 3.9+
- Redis server (local or remote)
- Gemini API key

### Environment Variables
Create a `.env` file with the following variables:
```
REDIS_URL=redis://localhost:6379
GEMINI_API_KEY=your-gemini-api-key
SESSION_TTL=86400  # 24 hours in seconds
```

### Installation
1. Clone the repository
2. Install dependencies:
```
pip install -r requirements.txt
```

### Running the Application
Start the server with:
```
python main.py
```
The API will be available at `http://localhost:8000`

## API Documentation
Once the server is running, interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints

### Session Management
- `POST /session`: Create a new chat session
- `GET /history/{session_id}`: Get chat history for a session
- `DELETE /session/{session_id}`: Clear a chat session

### Chat
- `POST /chat`: Send a message and get a response
- `WebSocket /ws/chat/{session_id}`: Stream chat messages and responses

### System Status
- `GET /`: Returns a welcome message
- `GET /status`: Get system status including vector store readiness

## Caching and Performance

### Redis TTL Configuration
The application uses Redis to store chat history with configurable Time-To-Live (TTL) values. This helps:

1. **Prevent memory overflow**: Old sessions are automatically evicted
2. **Maintain data freshness**: Expired sessions are cleaned up
3. **Improve response time**: Fast retrieval of session data

The TTL is configured using the `SESSION_TTL` environment variable (default: 24 hours).

### Cache Warming Strategies
For production deployment, consider these cache warming strategies:

1. **Periodic News Ingestion**: Automatically refresh news articles every few hours
   ```python
   # Example scheduler using APScheduler
   from apscheduler.schedulers.asyncio import AsyncIOScheduler
   
   scheduler = AsyncIOScheduler()
   scheduler.add_job(ingest_news, 'interval', hours=4)
   scheduler.start()
   ```

2. **Prefetching Popular Queries**: Store responses for common queries
   ```python
   # Example of prefetching responses for common queries
   common_queries = ["latest world news", "top tech news", "breaking news"]
   for query in common_queries:
       response = await generate_response(query, "system")
       await redis_client.set(f"cached_response:{query}", response, ex=3600)
   ```

3. **Intelligent Redis Eviction Policies**: Configure Redis with the right eviction policy
   ```
   # In redis.conf
   maxmemory 2gb
   maxmemory-policy allkeys-lru  # Least Recently Used
   ```

## Vector Store Details
The application uses an in-memory Qdrant vector store for demo purposes. For production:

1. **Persistent Storage**: Configure Qdrant with a persistent path
   ```python
   vector_store = Qdrant.from_documents(
       documents=splits,
       embedding=embeddings,
       location="./qdrant_data",  # Persistent storage
       collection_name="news_articles"
   )
   ```

2. **Separate Qdrant Server**: Run Qdrant as a separate service
   ```python
   from qdrant_client import QdrantClient
   
   client = QdrantClient(url="http://qdrant-server:6333")
   ```

## Development
During development, the server automatically reloads when code changes are detected.