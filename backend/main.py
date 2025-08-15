import logging
import asyncio
import os
import time
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

# Performance tracking
pipeline_stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "avg_processing_time": 0.0,
    "stt_avg_time": 0.0,
    "translation_avg_time": 0.0,
    "tts_avg_time": 0.0,
    "last_reset": time.time()
}

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
    """Minimal pipeline: WAV LINEAR16 → STT → Translation → TTS with performance tracking"""
    start_time = time.time()
    pipeline_stats["total_requests"] += 1
    
    try:
        # Skip small chunks (optimized threshold for better responsiveness)
        if len(audio_chunk) < 8000:  # ~0.25 second at 16kHz 16-bit mono
            return None
            
        logging.info(f"🎤 Processing audio: {len(audio_chunk)} bytes")
        
        # Step 1: Speech-to-Text with timing
        stt_start = time.time()
        transcript = await _stt_with_retry(audio_chunk)
        stt_time = time.time() - stt_start
        _update_timing_stat("stt_avg_time", stt_time)
        
        if not transcript:
            return None
            
        logging.info(f"✅ STT Success ({stt_time:.2f}s): '{transcript}'")
        
        # Step 2: Translation with timing
        trans_start = time.time()
        translated_text = await _translation_with_retry(transcript)
        trans_time = time.time() - trans_start
        _update_timing_stat("translation_avg_time", trans_time)
        
        logging.info(f"✅ Translation ({trans_time:.2f}s): '{translated_text}'")
        
        # Step 3: Text-to-Speech with timing
        tts_start = time.time()
        audio_output = await _tts_with_retry(translated_text)
        tts_time = time.time() - tts_start
        _update_timing_stat("tts_avg_time", tts_time)
        
        # Update success stats
        total_time = time.time() - start_time
        pipeline_stats["successful_requests"] += 1
        _update_timing_stat("avg_processing_time", total_time)
        
        logging.info(f"✅ TTS Success ({tts_time:.2f}s): {len(audio_output)} bytes")
        logging.info(f"📊 Total pipeline time: {total_time:.2f}s")
        return audio_output
        
    except Exception as e:
        pipeline_stats["failed_requests"] += 1
        total_time = time.time() - start_time
        logging.error(f"❌ Pipeline error ({total_time:.2f}s): {e}")
        return FALLBACK_AUDIO


def _update_timing_stat(stat_name: str, new_time: float):
    """Update timing statistics with moving average"""
    current_avg = pipeline_stats[stat_name]
    total_requests = pipeline_stats["total_requests"]
    # Simple moving average
    pipeline_stats[stat_name] = ((current_avg * (total_requests - 1)) + new_time) / total_requests


async def _stt_with_retry(audio_chunk: bytes, max_retries: int = 2) -> Optional[str]:
    """STT with simple retry logic and optimized configuration"""
    for attempt in range(max_retries + 1):
        try:
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                audio_channel_count=1,
                language_code="nl-NL",
                enable_automatic_punctuation=True,
                enable_word_time_offsets=False,  # Disable for speed
                model="latest_short",  # Optimized for real-time
                use_enhanced=True,  # Better accuracy
            )
            
            audio = speech.RecognitionAudio(content=audio_chunk)
            response = speech_client.recognize(config=config, audio=audio, timeout=10.0)
            
            if not response.results or not response.results[0].alternatives:
                logging.debug(f"STT attempt {attempt + 1}: No results")
                return None
                
            transcript = response.results[0].alternatives[0].transcript.strip()
            return transcript if transcript else None
            
        except Exception as e:
            if attempt < max_retries:
                logging.warning(f"STT attempt {attempt + 1} failed: {e}, retrying...")
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
            else:
                logging.error(f"STT failed after {max_retries + 1} attempts: {e}")
                raise


async def _translation_with_retry(text: str, max_retries: int = 2) -> str:
    """Translation with simple retry logic"""
    for attempt in range(max_retries + 1):
        try:
            result = translation_client.translate(
                text, source_language='nl', target_language='en'
            )
            return result['translatedText'].strip()
            
        except Exception as e:
            if attempt < max_retries:
                logging.warning(f"Translation attempt {attempt + 1} failed: {e}, retrying...")
                await asyncio.sleep(0.5 * (attempt + 1))
            else:
                logging.error(f"Translation failed after {max_retries + 1} attempts: {e}")
                raise


async def _tts_with_retry(text: str, max_retries: int = 2) -> bytes:
    """TTS with simple retry logic and optimized configuration"""
    for attempt in range(max_retries + 1):
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US", 
                name="en-US-Neural2-D",  # Neural2 voices are faster
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.1,  # Slightly faster speech
                pitch=0.0,
                volume_gain_db=0.0
            )
            
            response = tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config, timeout=10.0
            )
            return response.audio_content
            
        except Exception as e:
            if attempt < max_retries:
                logging.warning(f"TTS attempt {attempt + 1} failed: {e}, retrying...")
                await asyncio.sleep(0.5 * (attempt + 1))
            else:
                logging.error(f"TTS failed after {max_retries + 1} attempts: {e}")
                raise


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


@app.get("/stats")
async def performance_stats():
    """Performance monitoring endpoint"""
    uptime = time.time() - pipeline_stats["last_reset"]
    success_rate = (pipeline_stats["successful_requests"] / max(pipeline_stats["total_requests"], 1)) * 100
    
    return {
        "status": "ok",
        "uptime_seconds": round(uptime, 2),
        "pipeline_stats": {
            "total_requests": pipeline_stats["total_requests"],
            "successful_requests": pipeline_stats["successful_requests"],
            "failed_requests": pipeline_stats["failed_requests"],
            "success_rate_percent": round(success_rate, 2)
        },
        "performance_metrics": {
            "avg_total_time_seconds": round(pipeline_stats["avg_processing_time"], 3),
            "avg_stt_time_seconds": round(pipeline_stats["stt_avg_time"], 3),
            "avg_translation_time_seconds": round(pipeline_stats["translation_avg_time"], 3),
            "avg_tts_time_seconds": round(pipeline_stats["tts_avg_time"], 3)
        },
        "connection_stats": {
            "active_streams": len(connection_manager.listeners),
            "total_listeners": sum(len(listeners) for listeners in connection_manager.listeners.values())
        }
    }