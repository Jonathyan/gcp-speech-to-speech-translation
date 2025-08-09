#!/usr/bin/env python3
"""
Simple WebSocket client to test WAV file translation.
Sends Dutch WAV file, receives English MP3 audio.
"""
import asyncio
import websockets
import os

async def test_wav_translation():
    # Path to your existing test WAV file
    wav_file = "tests/fixtures/hallo_wereld.wav"
    output_file = "output_english.mp3"
    
    print(f"🎵 Reading WAV file: {wav_file}")
    
    # Check if WAV file exists
    if not os.path.exists(wav_file):
        print(f"❌ WAV file not found: {wav_file}")
        return
    
    # Read the WAV file
    with open(wav_file, "rb") as f:
        audio_data = f.read()
    
    print(f"📤 Sending {len(audio_data)} bytes of Dutch audio...")
    
    try:
        # Connect to your WebSocket server
        async with websockets.connect("ws://localhost:8000/ws") as websocket:
            print("🔗 Connected to WebSocket server")
            
            # Send the audio data
            await websocket.send(audio_data)
            print("✅ Audio sent, waiting for translation...")
            
            # Receive the translated audio
            response = await websocket.recv()
            print(f"📥 Received {len(response)} bytes of English audio")
            
            # Save the result
            with open(output_file, "wb") as f:
                f.write(response)
            
            print(f"🎧 Saved translated audio to: {output_file}")
            print("🎉 Test completed successfully!")
            
    except websockets.exceptions.ConnectionRefused:
        print("❌ Could not connect to server. Is it running on localhost:8000?")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Starting WAV translation test...")
    asyncio.run(test_wav_translation())