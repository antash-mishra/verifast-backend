#!/usr/bin/env python3
"""
Script to test the sessions API endpoint.
This script will:
1. List all active sessions
2. Create a new session
3. List sessions again to verify the new one appears
4. Delete all sessions and verify they're gone
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime

# Base URL for the API
BASE_URL = "http://localhost:8000"

async def test_sessions():
    """Test session management endpoints."""
    async with aiohttp.ClientSession() as session:
        # 1. List all existing sessions
        print("Fetching all sessions...")
        async with session.get(f"{BASE_URL}/sessions") as response:
            response_data = await response.json()
            print(f"Found {response_data['count']} active sessions")
            
            # Print session details in a formatted way
            if response_data['count'] > 0:
                print("\nEXISTING SESSIONS:")
                print("-" * 80)
                print(f"{'SESSION ID':<36} | {'MESSAGES':<8} | {'CREATED':<19} | {'LAST ACTIVE':<19}")
                print("-" * 80)
                
                for s in response_data['sessions']:
                    created = s.get('created_at', 'N/A')
                    if created and created != 'N/A':
                        try:
                            created = datetime.fromisoformat(created.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                        except (ValueError, AttributeError):
                            created = 'N/A'
                    else:
                        created = 'N/A'
                    
                    last_active = s.get('last_active', 'N/A')
                    if last_active and last_active != 'N/A':
                        try:
                            last_active = datetime.fromisoformat(last_active.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                        except (ValueError, AttributeError):
                            last_active = 'N/A'
                    else:
                        last_active = 'N/A'
                    
                    print(f"{s['session_id']:<36} | {s['message_count']:<8} | {created:<19} | {last_active:<19}")
            else:
                print("\nNo active sessions found.")
        
        # 2. Create a new session
        print("\nCreating a new session...")
        async with session.post(f"{BASE_URL}/session") as response:
            new_session = await response.json()
            session_id = new_session['sessionId']
            print(f"Created new session with ID: {session_id}")
            
        # 3. Send a test message to the new session
        print("\nSending a test message...")
        async with session.post(
            f"{BASE_URL}/chat",
            json={"sessionId": session_id, "message": "Test message from session script"}
        ) as response:
            message_response = await response.json()
            print(f"Sent test message, received response: {message_response['content'][:50]}...")
        
        # 4. List sessions again to verify the new one
        print("\nFetching all sessions again...")
        async with session.get(f"{BASE_URL}/sessions") as response:
            response_data = await response.json()
            print(f"Now found {response_data['count']} active sessions")
            
            # Check if our new session is in the list
            new_session_found = any(s['session_id'] == session_id for s in response_data['sessions'])
            print(f"New session {'found' if new_session_found else 'NOT found'} in the list")
            
            # Print session details again
            if response_data['count'] > 0:
                print("\nCURRENT SESSIONS:")
                print("-" * 80)
                print(f"{'SESSION ID':<36} | {'MESSAGES':<8} | {'CREATED':<19} | {'LAST ACTIVE':<19}")
                print("-" * 80)
                
                for s in response_data['sessions']:
                    created = s.get('created_at', 'N/A')
                    if created and created != 'N/A':
                        try:
                            created = datetime.fromisoformat(created.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                        except (ValueError, AttributeError):
                            created = 'N/A'
                    else:
                        created = 'N/A'
                    
                    last_active = s.get('last_active', 'N/A')
                    if last_active and last_active != 'N/A':
                        try:
                            last_active = datetime.fromisoformat(last_active.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                        except (ValueError, AttributeError):
                            last_active = 'N/A'
                    else:
                        last_active = 'N/A'
                    
                    session_marker = " (new)" if s['session_id'] == session_id else ""
                    print(f"{s['session_id']:<36} | {s['message_count']:<8} | {created:<19} | {last_active:<19}{session_marker}")

async def test_delete_all_sessions():
    """Test deleting all sessions."""
    async with aiohttp.ClientSession() as session:
        # 1. List all existing sessions
        print("Fetching current sessions...")
        async with session.get(f"{BASE_URL}/sessions") as response:
            response_data = await response.json()
            initial_count = response_data['count']
            print(f"Found {initial_count} active sessions")
            
        # 2. Delete all sessions
        print("\nDeleting all sessions...")
        async with session.delete(f"{BASE_URL}/sessions") as response:
            delete_result = await response.json()
            print(f"Delete response: {delete_result['message']}")
            
        # 3. Verify sessions are gone
        print("\nVerifying sessions were deleted...")
        async with session.get(f"{BASE_URL}/sessions") as response:
            response_data = await response.json()
            final_count = response_data['count']
            print(f"Found {final_count} active sessions after deletion")
            
            if final_count == 0:
                print("Success! All sessions were deleted.")
            else:
                print(f"Warning: {final_count} sessions remain after deletion.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--delete-all":
        asyncio.run(test_delete_all_sessions())
    else:
        asyncio.run(test_sessions())
        print("\n" + "=" * 80)
        print("To delete all sessions, run with: python3 test_sessions.py --delete-all")
        print("=" * 80) 