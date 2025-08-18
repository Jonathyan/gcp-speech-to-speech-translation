import logging
import asyncio
import os
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

# Google Cloud clients
from google.cloud import speech
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech

# Only import connection manager - minimal dependencies
from .connection_manager import ConnectionManager

# Minimal settings
FALLBACK_AUDIO = b'TEST_AUDIO_BEEP_MARKER:PIPELINE_ERROR_FALLBACK'

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Minimal Audio Test Service",
    description="Testing audio encoding fix - WAV LINEAR16",
    version="1.0.0-minimal",
)

# Initialize clients
speech_client = None
translation_client = None
tts_client = None
connection_manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    global speech_client, translation_client, tts_client
    try:
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        speech_client = speech.SpeechClient()
        translation_client = translate.Client()
        tts_client = texttospeech.TextToSpeechClient()
        
        logging.info("✅ Minimal service: All Google Cloud clients initialized")
        
    except Exception as e:
        logging.error(f"❌ Minimal service startup failed: {e}")


async def minimal_audio_pipeline(audio_chunk: bytes) -> Optional[bytes]:
    """Minimal pipeline to test WAV LINEAR16 → translation → TTS"""
    try:
        # Skip tiny chunks
        if len(audio_chunk) < 16000:  # ~0.5 second
            return None
            
        logging.info(f"🎤 Processing audio: {len(audio_chunk)} bytes")
        
        # Direct STT with LINEAR16 (for WAV from frontend)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="nl-NL",
            enable_automatic_punctuation=True,
            model="latest_short",
        )
        
        audio = speech.RecognitionAudio(content=audio_chunk)
        response = speech_client.recognize(config=config, audio=audio, timeout=10.0)
        
        if not response.results or not response.results[0].alternatives:
            logging.debug("No STT results")
            return None
            
        transcript = response.results[0].alternatives[0].transcript.strip()
        if not transcript:
            return None
            
        logging.info(f"✅ STT Success: '{transcript}'")
        
        # Direct Translation
        translation_result = translation_client.translate(
            transcript, source_language='nl', target_language='en'
        )
        translated_text = translation_result['translatedText'].strip()
        logging.info(f"✅ Translation: '{translated_text}'")
        
        # Direct TTS
        synthesis_input = texttospeech.SynthesisInput(text=translated_text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", name="en-US-Wavenet-D"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        tts_response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config, timeout=10.0
        )
        
        logging.info(f"✅ TTS Success: {len(tts_response.audio_content)} bytes")
        return tts_response.audio_content
        
    except Exception as e:
        logging.error(f"❌ Pipeline error: {e}")
        return FALLBACK_AUDIO


@app.websocket("/ws/speak/{stream_id}")
async def websocket_speaker(websocket: WebSocket, stream_id: str):
    await websocket.accept()
    client_id = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "testclient"
    message_count = 0
    
    logging.info(f"🎙️ Speaker connected: {client_id} → stream '{stream_id}'")
    
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            
            if "bytes" in message and message.get("bytes"):
                audio_chunk = message["bytes"]
                message_count += 1
                
                logging.info(f"📦 Message #{message_count}: {len(audio_chunk)} bytes from {client_id}")
                
                output_audio = await minimal_audio_pipeline(audio_chunk)
                if output_audio:
                    await connection_manager.broadcast_to_stream(stream_id, output_audio)
                    logging.info(f"✅ Message #{message_count}: Broadcast successful")
                else:
                    logging.debug(f"⏳ Message #{message_count}: No output (normal)")
            
    except WebSocketDisconnect:
        logging.info(f"🔌 Speaker disconnected: {client_id} after {message_count} messages")
    except Exception as e:
        logging.error(f"❌ Speaker error: {e}")


@app.websocket("/ws/listen/{stream_id}")
async def websocket_listener(websocket: WebSocket, stream_id: str):
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


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0-minimal",
        "service": "Minimal Audio Test Service - WAV LINEAR16 Fix",
        "clients": {
            "speech": "connected" if speech_client else "disconnected",
            "translation": "connected" if translation_client else "disconnected",
            "tts": "connected" if tts_client else "disconnected"
        }
    }