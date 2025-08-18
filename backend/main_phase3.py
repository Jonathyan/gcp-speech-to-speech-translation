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

# Only import connection manager - everything else is simplified away
from .connection_manager import ConnectionManager

# Simplified settings directly in code (no complex config.py)
FALLBACK_AUDIO = b'TEST_AUDIO_BEEP_MARKER:PIPELINE_ERROR_FALLBACK'

# Simplified logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="Phase 3 Simplified Speech Translation",
    description="Direct Google Cloud API calls - no complex layers",
    version="3.0.0-phase3",
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
        
        logging.info("✅ Phase 3 Simplified: All Google Cloud clients initialized")
        
    except Exception as e:
        logging.error(f"❌ Phase 3 Failed to initialize services: {e}")
        speech_client = None
        translation_client = None
        tts_client = None


async def phase3_direct_pipeline(audio_chunk: bytes) -> Optional[bytes]:
    """
    PHASE 3: Completely simplified pipeline - no buffering, no complex layers.
    Exactly as recommended by brownfield plan Section 4.3.
    """
    try:
        # Skip tiny chunks that won't have meaningful audio
        if len(audio_chunk) < 16000:  # ~0.5 second at 16kHz
            logging.debug(f"Phase 3: Skipping small chunk ({len(audio_chunk)} bytes)")
            return None
            
        logging.info(f"Phase 3 Direct STT: Processing {len(audio_chunk)} bytes")
        
        # Step 1: Direct Speech Recognition - try WEBM_OPUS first
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,  # WebM default from browser
            language_code="nl-NL",
            enable_automatic_punctuation=True,
            model="latest_short",
        )
        
        audio = speech.RecognitionAudio(content=audio_chunk)
        
        # Direct synchronous call with timeout
        response = speech_client.recognize(config=config, audio=audio, timeout=10.0)
        
        if not response.results or not response.results[0].alternatives:
            logging.debug("Phase 3: No transcription results")
            return None
            
        transcript = response.results[0].alternatives[0].transcript.strip()
        if not transcript:
            logging.debug("Phase 3: Empty transcript")
            return None
            
        logging.info(f"✅ Phase 3 STT Success: '{transcript}'")
        
        # Step 2: Direct Translation
        translation_result = translation_client.translate(
            transcript, 
            source_language='nl', 
            target_language='en'
        )
        translated_text = translation_result['translatedText'].strip()
        logging.info(f"✅ Phase 3 Translation: '{translated_text}'")
        
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
        
        logging.info(f"✅ Phase 3 TTS Success: {len(tts_response.audio_content)} bytes")
        return tts_response.audio_content
        
    except gcp_exceptions.InvalidArgument as e:
        if "bad encoding" in str(e):
            logging.warning(f"Phase 3: WEBM_OPUS encoding failed, trying LINEAR16 fallback: {e}")
            try:
                # Fallback: Try LINEAR16 (assume 16kHz mono)
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=16000,
                    language_code="nl-NL",
                    enable_automatic_punctuation=True,
                    model="latest_short",
                )
                
                audio = speech.RecognitionAudio(content=audio_chunk)
                response = speech_client.recognize(config=config, audio=audio, timeout=10.0)
                
                if response.results and response.results[0].alternatives:
                    transcript = response.results[0].alternatives[0].transcript.strip()
                    if transcript:
                        logging.info(f"✅ Phase 3 LINEAR16 Fallback Success: '{transcript}'")
                        
                        # Continue with translation and TTS
                        translation_result = translation_client.translate(
                            transcript, source_language='nl', target_language='en'
                        )
                        translated_text = translation_result['translatedText'].strip()
                        
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
                        
                        return tts_response.audio_content
                        
            except Exception as fallback_error:
                logging.error(f"❌ Phase 3 Fallback also failed: {fallback_error}")
        else:
            logging.error(f"❌ Phase 3 STT Invalid argument: {e}")
        
        return FALLBACK_AUDIO
        
    except Exception as e:
        logging.error(f"❌ Phase 3 Pipeline error: {e}")
        return FALLBACK_AUDIO


@app.websocket("/ws/speak/{stream_id}")
async def websocket_speaker_phase3(websocket: WebSocket, stream_id: str):
    """
    Phase 3 speaker endpoint - maximally simplified
    No circuit breakers, no complex state management, no retry logic
    """
    await websocket.accept()
    client_id = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "testclient"
    message_count = 0
    
    logging.info(f"✅ Phase 3 Speaker connected: {client_id} → stream '{stream_id}'")
    
    try:
        while True:
            message = await websocket.receive()
            
            if message["type"] == "websocket.disconnect":
                break
            
            if "bytes" in message and message.get("bytes"):
                audio_chunk = message["bytes"]
                message_count += 1
                
                logging.info(f"📦 Phase 3 Message #{message_count}: {len(audio_chunk)} bytes")
                
                # Direct pipeline processing - no error handling complexity
                output_audio = await phase3_direct_pipeline(audio_chunk)
                if output_audio:
                    await connection_manager.broadcast_to_stream(stream_id, output_audio)
                    logging.info(f"✅ Phase 3 Message #{message_count}: Broadcast successful")
                else:
                    logging.debug(f"⏳ Phase 3 Message #{message_count}: No output")
            
    except WebSocketDisconnect:
        logging.info(f"🔌 Phase 3 Speaker disconnected: {client_id} after {message_count} messages")
    except Exception as e:
        logging.error(f"❌ Phase 3 Speaker error: {e}")
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1011, reason="Phase 3 speaker error")


@app.websocket("/ws/listen/{stream_id}")
async def websocket_listener_phase3(websocket: WebSocket, stream_id: str):
    """Phase 3 listener endpoint - pure connection management only"""
    await websocket.accept()
    client_id = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "testclient"
    
    logging.info(f"🎧 Phase 3 Listener connected: {client_id} → stream '{stream_id}'")
    connection_manager.add_listener(stream_id, websocket)
    
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
                
    except WebSocketDisconnect:
        logging.info(f"🔌 Phase 3 Listener disconnected: {client_id}")
        connection_manager.remove_listener(stream_id, websocket)
    except Exception as e:
        logging.error(f"❌ Phase 3 Listener error: {e}")
        connection_manager.remove_listener(stream_id, websocket)
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1011, reason="Phase 3 listener error")


@app.get("/health")
async def health():
    """Phase 3 simplified health check"""
    return {
        "status": "ok",
        "version": "3.0.0-phase3",
        "service": "Phase 3 Simplified Speech Translation",
        "phase": "3-direct-apis",
        "clients": {
            "speech": "connected" if speech_client else "disconnected",
            "translation": "connected" if translation_client else "disconnected",
            "tts": "connected" if tts_client else "disconnected"
        }
    }


@app.get("/ready")
async def ready():
    """Phase 3 readiness check"""
    all_ready = all([speech_client, translation_client, tts_client])
    return {
        "status": "ready" if all_ready else "not_ready",
        "phase": "3-simplified",
        "clients_ready": all_ready
    }