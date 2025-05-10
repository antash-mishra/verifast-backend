import redis
import sys
import socket
import time
import logging
import os
from urllib.parse import urlparse
import redis.exceptions
import inspect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_REDIS_URL = "redis://default:cd28530fd7d047cab18f88137ca13940@fly-verifast-backend-sparkling-sea-4629-redis.upstash.io:6379"

def parse_redis_url(redis_url):
    parsed = urlparse(redis_url)
    host = parsed.hostname
    port = parsed.port or 6379
    password = parsed.password
    return host, port, password

def resolve(val):
    # Helper to resolve awaitables if any (should not be needed for redis-py)
    if inspect.isawaitable(val):
        import asyncio
        return asyncio.get_event_loop().run_until_complete(val)
    return val

def check_redis_connection(host="localhost", port=6379, password=None, max_retries=5, retry_delay=1):
    """Check if Redis server is running and accessible.
    
    Args:
        host: Redis host address (default: localhost)
        port: Redis port (default: 6379)
        password: Redis password if authentication is enabled (default: None)
        max_retries: Maximum number of connection attempts (default: 5)
        retry_delay: Delay between retries in seconds (default: 1)
        
    Returns:
        bool: True if connection is successful, False otherwise
    """
    retry_count = 0
    redis_client = redis.Redis(host=host, port=port, password=password, socket_timeout=5)
    
    while retry_count < max_retries:
        try:
            # Try to ping Redis
            response = resolve(redis_client.ping())
            if response:
                # Get Redis info
                info = resolve(redis_client.info())
                logger.info(f"Successfully connected to Redis at {host}:{port}")
                logger.info(f"Redis version: {info.get('redis_version')}")
                logger.info(f"Redis mode: {info.get('redis_mode', 'standalone')}")
                logger.info(f"Connected clients: {info.get('connected_clients')}")
                logger.info(f"Memory used: {info.get('used_memory_human')}")
                
                # Test basic operations
                redis_client.set("test_key", "test_value")
                value = resolve(redis_client.get("test_key"))
                logger.info(f"Test key value: {value.decode('utf-8') if value else None}")
                redis_client.delete("test_key")
                
                return True
        except redis.exceptions.ConnectionError as e:
            logger.warning(f"Failed to connect to Redis at {host}:{port}: {str(e)}")
            logger.info(f"Retrying in {retry_delay} seconds... (Attempt {retry_count + 1}/{max_retries})")
            time.sleep(retry_delay)
            retry_count += 1
        except redis.exceptions.ResponseError as e:
            logger.error(f"Redis server error: {str(e)}")
            # If authentication is required but not provided
            if "NOAUTH" in str(e):
                logger.error("Authentication required. Please provide a password.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return False
    
    logger.error(f"Failed to connect to Redis after {max_retries} attempts")
    return False

def scan_for_redis(start_port=6379, end_port=6389):
    """Scan a range of ports to find Redis servers"""
    logger.info(f"Scanning for Redis servers on ports {start_port}-{end_port}...")
    found_servers = []
    
    for port in range(start_port, end_port + 1):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            result = s.connect_ex(('localhost', port))
            s.close()
            
            if result == 0:
                # Try to connect to Redis at this port
                try:
                    r = redis.Redis(host='localhost', port=port, socket_timeout=1)
                    if resolve(r.ping()):
                        found_servers.append(port)
                        logger.info(f"Found Redis server at port {port}")
                except:
                    pass
        except:
            pass
    
    return found_servers

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Redis Connection Tester")
    parser.add_argument("--host", help="Redis host address")
    parser.add_argument("--port", type=int, help="Redis port")
    parser.add_argument("--password", help="Redis password")
    parser.add_argument("--url", help="Full Redis URL (overrides host/port/password)")
    parser.add_argument("--scan", action="store_true", help="Scan for Redis servers on common ports")
    
    args = parser.parse_args()
    
    if args.url:
        host, port, password = parse_redis_url(args.url)
    elif args.host:
        host = args.host
        port = args.port or 6379
        password = args.password
    else:
        # Default to Upstash Redis URL
        host, port, password = parse_redis_url(DEFAULT_REDIS_URL)

    if args.scan:
        found_servers = scan_for_redis()
        if found_servers:
            logger.info(f"Found Redis servers at ports: {', '.join(map(str, found_servers))}")
        else:
            logger.info("No Redis servers found on common ports")
    else:
        success = check_redis_connection(host, port, password)
        sys.exit(0 if success else 1)