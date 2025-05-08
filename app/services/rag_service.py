import asyncio
from typing import Dict, List, Any
from langchain_core.pydantic_v1 import SecretStr
import google.generativeai as genai
import feedparser
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import JinaEmbeddings
from langchain_core.runnables import RunnableConfig

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

# Initialize Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
llm = genai.GenerativeModel(GEMINI_MODEL)
# Initialize embeddings
embeddings = JinaEmbeddings(session=None, jina_api_key=SecretStr(JINA_API_KEY or ""), model_name=EMBEDDINGS_MODEL)

# Initialize vector store (will be populated during ingestion)
vector_store = None

async def generate_response(query: str, session_id: str, task_id: str = None) -> str:
    """Generate response using RAG pattern."""
    global vector_store

    # Ensure vector store is initialized
    if vector_store is None:
        return "I'm not ready yet. Please try again in a few moments while I load the news data."

    # Search for relevant documents
    docs = vector_store.similarity_search(query, k=RAG_NUM_CHUNKS)
    print("docs: ", docs)

    # Construct context from documents
    context = "\n\n".join([doc.page_content for doc in docs])

    # Construct prompt
    prompt = f"""You are a helpful assistant that answers queries about recent news.

CONTEXT:
{context}

QUERY:
{query}

Please answer the query based on the provided context. If you don't find enough information in the context to give a confident answer, say so, but try to provide helpful information based on what's available. Always cite your sources when possible."""

    # Generate response
    try:
        response = llm.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I'm sorry, I encountered an error while processing your request. Please try again."

async def ingest_news() -> Dict[str, Any]:
    """Ingest news articles from RSS feeds and store in vector database."""
    global vector_store

    print("Starting news ingestion...")
    all_texts = []

    for source in NEWS_SOURCES:
        try:
            # Parse RSS feed
            feed = feedparser.parse(source["url"])

            # Process each entry
            for entry in feed.entries[:10]:  # Limit to 10 articles per source
                title = entry.get("title", "")
                link = entry.get("link", "")

                try:
                    # Load article content
                    loader = WebBaseLoader(link)
                    docs = await asyncio.to_thread(loader.load)

                    # Add metadata
                    for doc in docs:
                        doc.metadata["source"] = source["title"]
                        doc.metadata["url"] = link
                        doc.metadata["title"] = title
                        all_texts.append(doc)
                except Exception as e:
                    print(f"Error loading article {link}: {e}")
        except Exception as e:
            print(f"Error processing source {source['url']}: {e}")

    # Split texts into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = text_splitter.split_documents(all_texts)

    # Create vector store
    vector_store = Qdrant.from_documents(
        documents=splits,
        embedding=embeddings,
        location=VECTOR_STORE_PATH,
        collection_name=COLLECTION_NAME
    )

    print(" vector store: ", vector_store, embeddings)

    print(f"Completed ingestion of {len(splits)} text chunks from {len(all_texts)} articles")
    return {"status": "success", "articles_processed": len(all_texts), "chunks_created": len(splits)}

def get_vector_store_status() -> Dict[str, Any]:
    """Get the status of the vector store."""
    return {
        "initialized": vector_store is not None,
        "sources": len(NEWS_SOURCES)
    }
