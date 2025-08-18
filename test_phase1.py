#!/usr/bin/env python3
"""
Simple test script for Phase 1 Enhanced STT Service
"""
import asyncio
import websockets
import json

async def test_websocket_connection():
    """Test WebSocket connection and basic functionality."""
    uri = "ws://localhost:8000/ws/speak/test-stream-1"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected successfully")
            
            # Send a small test audio chunk (simulated WebM header + data)
            test_audio = b'\x1a\x45\xdf\xa3' + b'\x18\x53\x80\x67' + b'\x00' * 5000
            
            print(f"📤 Sending test audio chunk ({len(test_audio)} bytes)")
            await websocket.send(test_audio)
            
            print("⏳ Waiting for response...")
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                print(f"✅ Received response ({len(response)} bytes)")
                
                # Check if it's the fallback audio or real audio
                if isinstance(response, bytes):
                    if len(response) < 1000:
                        print("ℹ️  Received fallback/test audio")
                    else:
                        print("🎵 Received processed audio!")
                else:
                    print(f"📝 Received text response: {response}")
                    
            except asyncio.TimeoutError:
                print("⏰ No response received within timeout")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")

async def test_multiple_chunks():
    """Test sending multiple chunks to trigger buffering."""
    uri = "ws://localhost:8000/ws/speak/test-stream-2"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Multi-chunk test connected")
            
            # Send multiple small chunks to test buffering
            for i in range(5):
                test_audio = b'\x1a\x45\xdf\xa3' + b'\x18\x53\x80\x67' + (f"chunk{i}".encode() + b'\x00' * 2000)
                print(f"📤 Sending chunk {i+1}/5 ({len(test_audio)} bytes)")
                await websocket.send(test_audio)
                await asyncio.sleep(0.2)  # Small delay between chunks
            
            print("⏳ Waiting for buffered response...")
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                print(f"✅ Received buffered response ({len(response)} bytes)")
            except asyncio.TimeoutError:
                print("⏰ No response received within timeout")
                
    except Exception as e:
        print(f"❌ Multi-chunk test failed: {e}")

async def main():
    print("🚀 Starting Phase 1 Enhanced STT Testing")
    print("=" * 50)
    
    print("\n1️⃣ Testing single WebSocket connection...")
    await test_websocket_connection()
    
    print("\n2️⃣ Testing multi-chunk buffering...")
    await test_multiple_chunks()
    
    print("\n✅ Testing complete!")

if __name__ == "__main__":
    asyncio.run(main())