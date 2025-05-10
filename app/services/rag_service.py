import asyncio
from typing import Dict, List, Any, Optional
from langchain_core.pydantic_v1 import SecretStr
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.generativeai.types import BlockedPromptException
import feedparser
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import JinaEmbeddings
from langchain_core.runnables import RunnableConfig
import time

from app.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    EMBEDDINGS_MODEL,
    VECTOR_STORE_PATH,
    COLLECTION_NAME,
    NEWS_SOURCES,
    RAG_NUM_CHUNKS,
    JINA_API_KEY
)
from app.services.redis_service import get_session_history
from app.models.message import Message # Added for type hinting

# Initialize Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
# Configuration for safety settings - adjust as needed
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}
llm = genai.GenerativeModel(GEMINI_MODEL, safety_settings=safety_settings)

# Initialize embeddings
embeddings = JinaEmbeddings(session=None, jina_api_key=SecretStr(JINA_API_KEY or ""), model_name=EMBEDDINGS_MODEL)

# Initialize vector store (will be populated during ingestion)
vector_store = None

# Ingestion status tracking
ingestion_status = {
    "is_ingesting": False,
    "started_at": None,
    "completed_at": None,
    "sources_processed": 0,
    "total_sources": len(NEWS_SOURCES),
    "articles_processed": 0,
    "articles_failed": 0,
    "chunks_created": 0,
    "status": "not_started",  # not_started, in_progress, completed, failed
    "progress_percentage": 0,
    "error_message": None
}

async def generate_response(query: str, session_id: str, task_id: Optional[str] = None) -> str:
    """Generate response using RAG pattern with citations, incorporating chat history correctly."""
    global vector_store

    if vector_store is None:
        return "I'm not ready yet. Please try again in a few moments while I load the news data."

    # 1. Fetch and format chat history for Gemini API
    raw_chat_history: List[Message] = await get_session_history(session_id)
    gemini_chat_history = []
    if raw_chat_history:
        for msg in raw_chat_history[-10:]: # Keep last 10 messages for history
            role = "user" if msg.sender == "user" else "model"
            gemini_chat_history.append({"role": role, "parts": [msg.content]})

    # 2. RAG: Search for relevant documents for the current query
    docs = vector_store.similarity_search(query, k=RAG_NUM_CHUNKS)
    
    context_with_citations = []
    citations = []
    for i, doc in enumerate(docs):
        citation_id = f"[{i+1}]"
        context_with_citations.append(f"{doc.page_content} {citation_id}")
        url = doc.metadata.get("url", "Unknown source")
        title = doc.metadata.get("title", "Untitled")
        source = doc.metadata.get("source", "Unknown")
        citations.append(f"{citation_id} {title} - {source} ({url})")
    
    context = "\n\n".join(context_with_citations)
    citations_text = "\n".join(citations)

    # 3. Construct the full prompt for the current turn, including RAG context and instructions
    # The system prompt aspects (persona, instructions) are part of the user's turn content.
    # Chat history is handled by the ChatSession.
    
    system_instructions = f"""FORMATTING RULES (FOLLOW EXACTLY):
1. Start your response with a brief introductory sentence summarizing the key information.
2. Then present your answer as a SINGLE LIST of bullet points using this exact format:
   * Point 1 about **key term** with citation [1].
   * Point 2 about another **important fact** with citation [2].
   * Point 3 with more information about the topic [3].

3. IMPORTANT RULES:
   - Use ONLY the asterisk (*) for bullet points, never use numbers, dashes or other symbols.
   - Put ONE SPACE after each asterisk.
   - Make each bullet point a COMPLETE sentence that can stand alone.
   - Bold important terms using double asterisks like **this**.
   - Add citation numbers in square brackets [1] at the end of relevant points.
   - NEVER place bullet points on separate lines without content.
   - ALWAYS end each bullet point with proper punctuation.

4. End with a "Sources:" section formatted exactly like this:
   **Sources:**
   * [1] First source with details
   * [2] Second source with details

BASE YOUR RESPONSE ONLY ON THE CONTEXT PROVIDED. DO NOT ADD INFORMATION FROM OTHER SOURCES.
"""

    # The user's current query, augmented with RAG context and instructions.
    # This is what gets sent as the "user" part of the current turn.
    current_turn_prompt = f"""{system_instructions}

CONTEXT:
{context}

CITATIONS:
{citations_text}

QUERY:
{query}
"""

    try:
        # Start a new chat session with the fetched history
        chat = llm.start_chat(history=gemini_chat_history)
        
        # Send the current query (with RAG context and instructions) to the model
        response_obj = await asyncio.to_thread(chat.send_message, current_turn_prompt)
        
        # Check for blocking at the response object level if not raised as an exception
        # The response_obj from send_message should have prompt_feedback if applicable.
        if hasattr(response_obj, 'prompt_feedback') and response_obj.prompt_feedback and \
           hasattr(response_obj.prompt_feedback, 'block_reason') and response_obj.prompt_feedback.block_reason:
            reason = response_obj.prompt_feedback.block_reason_message or response_obj.prompt_feedback.block_reason
            print(f"Prompt blocked after generation. Reason: {reason}")
            return f"I'm sorry, your request was blocked. Reason: {reason}. Please rephrase your query or try a different topic."
            
        return response_obj.text

    except BlockedPromptException as bpe:
        error_message = f"BlockedPromptException: Prompt was blocked by Google safety filters before generation."
        print(error_message)
        print(f"Details of BlockedPromptException: {bpe}") 
        return "I'm sorry, your request was blocked by content safety filters before it could be processed. Please rephrase your query or try a different topic."
        
    except Exception as e:
        error_message = f"Error generating response: {type(e).__name__} - {e}"
        print(error_message)
        return "I'm sorry, I encountered an error while processing your request. Please try again."

async def ingest_news() -> Dict[str, Any]:
    """Ingest news articles from RSS feeds and store in vector database."""
    global vector_store, ingestion_status
    
    # Update ingestion status to "in progress"
    ingestion_status["is_ingesting"] = True
    ingestion_status["started_at"] = time.time()
    ingestion_status["status"] = "in_progress"
    ingestion_status["sources_processed"] = 0
    ingestion_status["articles_processed"] = 0
    ingestion_status["articles_failed"] = 0
    ingestion_status["chunks_created"] = 0
    ingestion_status["progress_percentage"] = 0
    ingestion_status["error_message"] = None

    print("Starting news ingestion...")
    all_texts = []

    for i, source_info in enumerate(NEWS_SOURCES): # Renamed 'source' to 'source_info' to avoid conflict
        try:
            feed = feedparser.parse(source_info["url"])
            
            # Update source progress
            ingestion_status["sources_processed"] += 1
            ingestion_status["progress_percentage"] = int((ingestion_status["sources_processed"] / ingestion_status["total_sources"]) * 100)
            
            successful_articles = 0
            failed_articles = 0
            
            for entry in feed.entries[:10]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                try:
                    loader = WebBaseLoader(link)
                    docs = await asyncio.to_thread(loader.load)
                    for doc in docs:
                        doc.metadata["source"] = source_info["title"]
                        doc.metadata["url"] = link
                        doc.metadata["title"] = title
                        all_texts.append(doc)
                    successful_articles += 1
                    ingestion_status["articles_processed"] += 1
                except Exception as e:
                    print(f"Error loading article {link}: {e}")
                    failed_articles += 1
                    ingestion_status["articles_failed"] += 1
            
            print(f"Processed source {source_info['title']}: {successful_articles} articles loaded, {failed_articles} failed")
            
        except Exception as e:
            print(f"Error processing source {source_info['url']}: {e}")
            ingestion_status["articles_failed"] += 1

    if not all_texts:
        print("No articles were successfully loaded. Ingestion cannot proceed.")
        ingestion_status["status"] = "failed"
        ingestion_status["error_message"] = "No articles were successfully loaded."
        ingestion_status["is_ingesting"] = False
        ingestion_status["completed_at"] = time.time()
        return {"status": "failure", "message": "No articles loaded."}

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = text_splitter.split_documents(all_texts)
    ingestion_status["chunks_created"] = len(splits)

    if not splits:
        print("No text chunks were created after splitting. Ingestion cannot proceed.")
        ingestion_status["status"] = "failed"
        ingestion_status["error_message"] = "No text chunks were created after splitting."
        ingestion_status["is_ingesting"] = False
        ingestion_status["completed_at"] = time.time()
        return {"status": "failure", "message": "No text chunks created."}

    try:
        vector_store = Qdrant.from_documents(
            documents=splits,
            embedding=embeddings,
            location=VECTOR_STORE_PATH,
            collection_name=COLLECTION_NAME
        )
        ingestion_status["status"] = "completed"
        ingestion_status["is_ingesting"] = False
        ingestion_status["completed_at"] = time.time()
        ingestion_status["progress_percentage"] = 100
        
        print(f"Completed ingestion of {len(splits)} text chunks from {len(all_texts)} articles. Vector store initialized.")
        return {"status": "success", "articles_processed": len(all_texts), "chunks_created": len(splits)}
    except Exception as e:
        print(f"Error creating vector store: {e}")
        ingestion_status["status"] = "failed"
        ingestion_status["error_message"] = f"Error creating vector store: {e}"
        ingestion_status["is_ingesting"] = False
        ingestion_status["completed_at"] = time.time()
        return {"status": "failure", "message": f"Error creating vector store: {e}"}

def get_vector_store_status() -> Dict[str, Any]:
    """Get the status of the vector store."""
    global ingestion_status
    
    elapsed_time = None
    if ingestion_status["started_at"]:
        if ingestion_status["completed_at"]:
            elapsed_time = round(ingestion_status["completed_at"] - ingestion_status["started_at"], 2)
        else:
            elapsed_time = round(time.time() - ingestion_status["started_at"], 2)
    
    return {
        "initialized": vector_store is not None,
        "sources": len(NEWS_SOURCES),
        "ingestion": {
            "status": ingestion_status["status"],
            "is_ingesting": ingestion_status["is_ingesting"],
            "progress_percentage": ingestion_status["progress_percentage"],
            "sources_processed": ingestion_status["sources_processed"],
            "total_sources": ingestion_status["total_sources"],
            "articles_processed": ingestion_status["articles_processed"],
            "articles_failed": ingestion_status["articles_failed"],
            "chunks_created": ingestion_status["chunks_created"],
            "started_at": ingestion_status["started_at"],
            "completed_at": ingestion_status["completed_at"],
            "elapsed_time_seconds": elapsed_time,
            "error_message": ingestion_status["error_message"]
        }
    }
