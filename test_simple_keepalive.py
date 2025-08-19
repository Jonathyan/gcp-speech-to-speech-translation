#!/usr/bin/env python3
"""Simple keepalive test using FastAPI WebSocket client."""

import asyncio
import json
import time
from fastapi.testclient import TestClient
from backend.main import app

async def test_keepalive():
    """Test the keepalive mechanism with a simple WebSocket connection."""
    print("🚀 Testing WebSocket keepalive mechanism")
    
    try:
        # Use the test client to connect
        with TestClient(app) as client:
            with client.websocket_connect("/ws/listen/test-keepalive") as websocket:
                print("✅ WebSocket connected")
                
                # Wait for keepalive ping (should happen within 30 seconds)
                start_time = time.time()
                ping_received = False
                
                for i in range(35):  # Wait up to 35 seconds
                    try:
                        # Check for messages
                        message = websocket.receive_text()
                        print(f"📨 Received: {message}")
                        
                        # Parse keepalive message
                        try:
                            data = json.loads(message)
                            if data.get("type") == "keepalive" and data.get("action") == "ping":
                                print("📡 Keepalive ping received!")
                                ping_received = True
                                
                                # Send pong response
                                pong_response = json.dumps({"type": "keepalive", "action": "pong"})
                                websocket.send_text(pong_response)
                                print("📡 Pong sent!")
                                break
                        except json.JSONDecodeError:
                            # Not JSON, ignore
                            pass
                            
                    except Exception as e:
                        # No message received, wait
                        time.sleep(1)
                        if i % 5 == 0:
                            print(f"⏰ Waiting... {i}s elapsed")
                        continue
                
                if ping_received:
                    print("✅ Keepalive mechanism working correctly!")
                    return True
                else:
                    print("❌ No keepalive ping received in 35 seconds")
                    return False
                    
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_keepalive())
    exit(0 if success else 1)