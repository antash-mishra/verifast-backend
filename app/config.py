import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Application settings
APP_TITLE = "RAG Chatbot API"
APP_DESCRIPTION = "Backend API for RAG News Chatbot with Redis caching"
APP_VERSION = "0.1.0"

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# Redis settings
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SESSION_TTL = int(os.getenv("SESSION_TTL", 86400))  # Default: 24 hours

# Gemini API settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash-preview-04-17"

# Vector DB settings
EMBEDDINGS_MODEL = "jina-embeddings-v3"
JINA_API_KEY = os.getenv("JINA_API_KEY")
VECTOR_STORE_PATH = ":memory:"  # Use memory for development
COLLECTION_NAME = "news_articles"

# News sources for ingestion
NEWS_SOURCES = [
    {"title": "BBC News", "url": "http://feeds.bbci.co.uk/news/rss.xml", "description": "Latest news from BBC"},
    {"title": "CNN", "url": "http://rss.cnn.com/rss/edition.rss", "description": "Breaking news from CNN"},
    {"title": "The New York Times", "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "description": "Latest from NYT"},
    {"title": "Reuters", "url": "http://feeds.reuters.com/reuters/topNews", "description": "Top news from Reuters"},
    {"title": "NPR", "url": "https://feeds.npr.org/1001/rss.xml", "description": "National Public Radio news"},
]

# Chat settings
RAG_NUM_CHUNKS = 3  # Number of chunks to retrieve

# Check if Gemini API key is provided
if not GEMINI_API_KEY or GEMINI_API_KEY == "your-gemini-api-key":
    print("Warning: GEMINI_API_KEY not set or using default value. API calls to Gemini will fail.")
    print("Please set a valid API key in the .env file or environment variables.")
