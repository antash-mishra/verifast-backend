import os
import sys
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
import argparse
import json
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import JinaEmbeddings
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def check_qdrant_collection(collection_name="news_articles", limit=5):
    """
    Check if a Qdrant collection exists and has embeddings
    """
    try:
        # Try to connect to local Qdrant instance first
        try:
            client = QdrantClient(url="http://localhost:6333")
            collections = client.get_collections().collections
            logger.info(f"Connected to Qdrant at http://localhost:6333")
        except Exception:
            # If local connection fails, try in-memory Qdrant
            logger.info("Local Qdrant connection failed, trying in-memory Qdrant")
            client = QdrantClient(":memory:")
            collections = client.get_collections().collections
            logger.info("Connected to in-memory Qdrant")
            
        # Check if our collection exists
        collection_names = [collection.name for collection in collections]
        logger.info(f"Available collections: {collection_names}")
        
        if collection_name not in collection_names:
            logger.error(f"Collection '{collection_name}' not found")
            return False
            
        # Get collection info
        collection_info = client.get_collection(collection_name=collection_name)
        logger.info(f"Collection '{collection_name}' info: {collection_info}")
        
        # Count points in the collection
        count_result = client.count(collection_name=collection_name)
        count = count_result.count
        logger.info(f"Collection '{collection_name}' contains {count} points")
        
        if count == 0:
            logger.warning("Vector store is empty - no embeddings found")
            return False
            
        # Retrieve sample points to check content
        if count > 0:
            logger.info(f"Retrieving {min(limit, count)} sample points:")
            points = client.scroll(
                collection_name=collection_name,
                limit=min(limit, count)
            )[0]
            
            for i, point in enumerate(points):
                logger.info(f"Point {i+1}:")
                # Display point ID
                logger.info(f"  ID: {point.id}")
                
                # Display metadata (condensed view of key fields)
                if hasattr(point, 'payload') and point.payload:
                    metadata = point.payload
                    text = metadata.get('text', metadata.get('page_content', 'No text content'))
                    source = metadata.get('source', 'Unknown source')
                    timestamp = metadata.get('timestamp', metadata.get('created_at', 'No timestamp'))
                    
                    # Truncate text if it's too long
                    if text and len(text) > 100:
                        text = text[:100] + "..."
                        
                    logger.info(f"  Source: {source}")
                    logger.info(f"  Timestamp: {timestamp}")
                    logger.info(f"  Text snippet: {text}")
                    
                    # Count keys in metadata
                    logger.info(f"  Metadata keys: {list(metadata.keys())}")
                else:
                    logger.info("  No payload/metadata found")
                
                # Check if vector exists and show its dimension
                if hasattr(point, 'vector') and point.vector:
                    vector_dim = len(point.vector)
                    logger.info(f"  Vector dimension: {vector_dim}")
                else:
                    logger.info("  No vector found")
                    
                logger.info("-" * 40)
            
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error checking Qdrant collection: {str(e)}")
        return False

def perform_test_query(collection_name="news_articles", query="latest news"):
    """
    Perform a test query against the vector store to check if it returns relevant results
    """
    try:
        # Initialize Jina embeddings
        embedding = JinaEmbeddings(
            jina_api_key=os.getenv("JINA_API_KEY"),
            model_name="jina-embeddings-v2-base-en"
        )
        
        # Try to connect to local Qdrant instance first
        try:
            client = QdrantClient(url="http://localhost:6333")
            logger.info("Connected to Qdrant at http://localhost:6333")
        except Exception:
            # If local connection fails, try in-memory Qdrant
            logger.info("Local Qdrant connection failed, trying in-memory Qdrant")
            client = QdrantClient(":memory:")
            logger.info("Connected to in-memory Qdrant")
        
        # Create Qdrant store object
        vector_store = Qdrant(
            client=client,
            collection_name=collection_name,
            embeddings=embedding
        )
        
        # Perform similarity search
        logger.info(f"Performing test query: '{query}'")
        results = vector_store.similarity_search(query, k=3)
        
        if not results:
            logger.warning("No results found for the test query")
            return False
            
        logger.info(f"Found {len(results)} results for query: '{query}'")
        
        # Display results
        for i, doc in enumerate(results):
            logger.info(f"Result {i+1}:")
            # Truncate text if it's too long
            content = doc.page_content
            if len(content) > 100:
                content = content[:100] + "..."
            logger.info(f"  Content: {content}")
            logger.info(f"  Metadata: {doc.metadata}")
            logger.info("-" * 40)
            
        return True
        
    except Exception as e:
        logger.error(f"Error performing test query: {str(e)}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check Qdrant vector store")
    parser.add_argument("--collection", default="news_articles", help="Collection name to check")
    parser.add_argument("--limit", type=int, default=5, help="Number of sample points to retrieve")
    parser.add_argument("--query", default="latest news", help="Test query to run against the vector store")
    parser.add_argument("--test-query", action="store_true", help="Run a test query against the vector store")
    
    args = parser.parse_args()
    
    # Check if collection exists and has embeddings
    success = check_qdrant_collection(args.collection, args.limit)
    
    # Run test query if requested
    if success and args.test_query:
        perform_test_query(args.collection, args.query)
    
    sys.exit(0 if success else 1)