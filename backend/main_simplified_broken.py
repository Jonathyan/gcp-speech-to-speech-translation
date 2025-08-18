import logging
import json
import asyncio
import os
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

# Google Cloud clients
from google.cloud import speech
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech
from google.api_core import exceptions as gcp_exceptions

# Keep only essential imports - remove all the complexity
from .connection_manager import ConnectionManager
from .config import settings

# Simplified logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="Simplified Speech Translation Service",
    description="Direct Google Cloud API calls without complex buffering",
    version="3.0.0",
)

# Initialize Google Cloud clients directly
speech_client = None
translation_client = None
tts_client = None
connection_manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    global speech_client, translation_client, tts_client
    try:
        # Load credentials
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        # Initialize clients directly
        speech_client = speech.SpeechClient()
        translation_client = translate.Client()
        tts_client = texttospeech.TextToSpeechClient()
        
        logging.info("✅ All Google Cloud clients initialized successfully")
        
    except Exception as e:
        logging.error(f"❌ Failed to initialize services: {e}")
        speech_client = None
        translation_client = None
        tts_client = None


async def direct_audio_pipeline(audio_chunk: bytes) -> Optional[bytes]:
    """
    PHASE 3: Simplified direct pipeline - no buffering, no complex layers.
    Single, reliable processing path as recommended by brownfield plan.
    """
    try:
        # Step 1: Direct Speech Recognition
        logging.info(f"Direct STT: Processing {len(audio_chunk)} bytes")
        
        # Skip tiny chunks that won't have meaningful audio
        if len(audio_chunk) < 16000:  # ~0.5 second at 16kHz
            logging.debug("Chunk too small, skipping")
            return None
            
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,  # WebM default
            language_code="nl-NL",
            enable_automatic_punctuation=True,
            model="latest_short",
        )
        
        audio = speech.RecognitionAudio(content=audio_chunk)
        
        # Direct synchronous call
        response = speech_client.recognize(config=config, audio=audio, timeout=10.0)
        
        if not response.results or not response.results[0].alternatives:
            logging.debug("No transcription results")
            return None
            
        transcript = response.results[0].alternatives[0].transcript.strip()
        if not transcript:
            return None
            
        logging.info(f"✅ STT Success: '{transcript}'")
        
        # Step 2: Direct Translation
        translation_result = translation_client.translate(
            transcript, 
            source_language='nl', 
            target_language='en'
        )
        translated_text = translation_result['translatedText'].strip()
        logging.info(f"✅ Translation: '{translated_text}'")
        
        # Step 3: Direct Speech Synthesis
        synthesis_input = texttospeech.SynthesisInput(text=translated_text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Wavenet-D"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        tts_response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
            timeout=10.0
        )
        
        logging.info(f"✅ TTS Success: {len(tts_response.audio_content)} bytes")
        return tts_response.audio_content
        
    except Exception as e:
        logging.error(f"❌ Pipeline error: {e}")
        # Return simple fallback beep instead of complex error handling
        return settings.FALLBACK_AUDIO


@app.websocket("/ws/speak/{stream_id}")
async def websocket_speaker_simplified(websocket: WebSocket, stream_id: str):
    """
    Simplified speaker endpoint - no circuit breakers, no complex state management
    """
    await websocket.accept()
    client_id = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "testclient"
    message_count = 0
    
    logging.info(f"✅ Speaker connected: {client_id} → stream '{stream_id}'")
    
    try:
        while True:
            message = await websocket.receive()
            
            if message["type"] == "websocket.disconnect":
                break
            
            if "bytes" in message and message.get("bytes"):
                audio_chunk = message["bytes"]
                message_count += 1
                
                logging.info(f"📦 Message #{message_count}: {len(audio_chunk)} bytes from {client_id}")
                
                # Direct pipeline processing
                try:
                    output_audio = await direct_audio_pipeline(audio_chunk)
                    if output_audio:
                        await connection_manager.broadcast_to_stream(stream_id, output_audio)
                        logging.info(f"✅ Message #{message_count}: Broadcast successful")
                    else:
                        logging.debug(f"⏳ Message #{message_count}: No output (normal for small chunks)")
                        
                except Exception as e:
                    logging.error(f"❌ Message #{message_count}: Pipeline failed: {e}")
                    await connection_manager.broadcast_to_stream(stream_id, settings.FALLBACK_AUDIO)
            
    except WebSocketDisconnect:
        logging.info(f"🔌 Speaker disconnected: {client_id} after {message_count} messages")
    except Exception as e:
        logging.error(f"❌ Speaker error: {e}")
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1011, reason="Speaker error")


@app.websocket("/ws/listen/{stream_id}")
async def websocket_listener_simplified(websocket: WebSocket, stream_id: str):
    """Simplified listener endpoint - just connection management"""
    await websocket.accept()
    client_id = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "testclient"
    
    logging.info(f"🎧 Listener connected: {client_id} → stream '{stream_id}'")
    connection_manager.add_listener(stream_id, websocket)
    
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
                
    except WebSocketDisconnect:
        logging.info(f"🔌 Listener disconnected: {client_id}")
        connection_manager.remove_listener(stream_id, websocket)
    except Exception as e:
        logging.error(f"❌ Listener error: {e}")
        connection_manager.remove_listener(stream_id, websocket)
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1011, reason="Listener error")


@app.get("/health")
async def health():
    """Simple health check"""
    return {
        "status": "ok",
        "version": "3.0.0",
        "service": "Simplified Speech Translation",
        "clients": {
            "speech": "connected" if speech_client else "disconnected",
            "translation": "connected" if translation_client else "disconnected",
            "tts": "connected" if tts_client else "disconnected"
        }
    }


@app.get("/ready")
async def ready():
    """Readiness check"""
    all_ready = all([speech_client, translation_client, tts_client])
    return {
        "status": "ready" if all_ready else "not_ready",
        "clients_ready": all_ready
    }