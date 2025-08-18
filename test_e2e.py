#!/usr/bin/env python3
"""
End-to-end test for Dutch → English speech translation
"""
import asyncio
import websockets
import json
import time

async def test_end_to_end_translation():
    """Test the complete Dutch to English pipeline."""
    
    print("🎯 Testing End-to-End Dutch → English Translation")
    print("=" * 60)
    
    # First, let's check if the pipeline is healthy
    import requests
    
    try:
        health = requests.get("http://localhost:8000/health/full")
        if health.json()["status"] == "ok":
            print("✅ Backend pipeline is healthy")
        else:
            print("⚠️  Backend pipeline health check failed")
            return
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        return
    
    # Test WebSocket connection with realistic audio simulation
    uri = "ws://localhost:8000/ws/speak/e2e-test"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected to /ws/speak/e2e-test")
            
            # Simulate realistic Dutch audio chunks
            # This simulates what would come from MediaRecorder in the browser
            simulated_dutch_audio_chunks = [
                # WebM header + simulated audio data for "Hallo, hoe gaat het?"
                b'\x1a\x45\xdf\xa3' + b'\x18\x53\x80\x67' + b'\x11\x4d\x9b\x74' + b'\x00' * 8000,
                b'\x1a\x45\xdf\xa3' + b'\x18\x53\x80\x67' + b'\x11\x4d\x9b\x74' + b'\x01' * 8000,
                b'\x1a\x45\xdf\xa3' + b'\x18\x53\x80\x67' + b'\x11\x4d\x9b\x74' + b'\x02' * 8000,
                # Add more chunks to reach the buffering threshold
                b'\x1a\x45\xdf\xa3' + b'\x18\x53\x80\x67' + b'\x11\x4d\x9b\x74' + b'\x03' * 12000,
            ]
            
            print(f"📤 Sending {len(simulated_dutch_audio_chunks)} audio chunks...")
            
            # Send chunks with realistic timing
            for i, chunk in enumerate(simulated_dutch_audio_chunks):
                print(f"   📤 Chunk {i+1}: {len(chunk)} bytes")
                await websocket.send(chunk)
                await asyncio.sleep(0.25)  # 250ms between chunks (realistic)
            
            print("⏳ Waiting for Phase 1 Enhanced STT processing...")
            print("   • Audio chunks being buffered...")
            print("   • Quality analysis in progress...")
            print("   • Waiting for buffer release trigger...")
            
            # Wait for response with longer timeout for real API processing
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                
                if isinstance(response, bytes):
                    print(f"🎵 SUCCESS! Received English audio: {len(response)} bytes")
                    
                    # Check if it's real translated audio or fallback
                    if len(response) > 5000:  # Real TTS audio is usually larger
                        print("✅ This appears to be real Google Cloud TTS audio!")
                        print("🔊 You should be able to play this as English speech")
                        
                        # Save the audio for inspection
                        with open("output_english.mp3", "wb") as f:
                            f.write(response)
                        print("💾 Saved output as 'output_english.mp3'")
                        
                    else:
                        print("ℹ️  Received fallback audio (pipeline may have failed)")
                        
                else:
                    print(f"📝 Unexpected text response: {response}")
                    
            except asyncio.TimeoutError:
                print("⏰ No response within 30 seconds")
                print("   This might indicate an issue with Google Cloud APIs")
                
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")

async def test_listener_connection():
    """Test the listener side of the connection."""
    print("\n🎧 Testing Listener Connection...")
    
    uri = "ws://localhost:8000/ws/listen/e2e-test"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Listener connected to /ws/listen/e2e-test")
            print("⏳ Waiting for broadcast audio...")
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"🎵 Received broadcast audio: {len(response)} bytes")
            except asyncio.TimeoutError:
                print("ℹ️  No broadcast received (normal if no speaker is active)")
                
    except Exception as e:
        print(f"❌ Listener test failed: {e}")

async def main():
    print("🚀 Starting End-to-End Dutch → English Test")
    print("Backend: http://localhost:8000")
    print("Frontend: http://localhost:3000")
    print("")
    
    await test_end_to_end_translation()
    await test_listener_connection()
    
    print("\n" + "=" * 60)
    print("🎯 END-TO-END TEST COMPLETE")
    print("")
    print("📋 Next Steps:")
    print("1. Check the logs above for success/failure")
    print("2. If successful, try the browser UI at http://localhost:3000")
    print("3. Click 'Start Uitzending' and speak Dutch")
    print("4. Listen for English output")

if __name__ == "__main__":
    asyncio.run(main())