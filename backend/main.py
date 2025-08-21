import logging
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Google Cloud clients - direct imports, no wrappers
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech

# Simple components only
from .connection_manager import ConnectionManager
from .streaming_stt import streaming_stt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Simple Speech-to-Speech Translation",
    description="Dutch → English streaming translation",
    version="2.0.0-simple",
)

# Global clients - simple initialization
translation_client = None
tts_client = None
connection_manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Initialize Google Cloud clients."""
    global translation_client, tts_client
    logger.info("🚀 Starting up streaming STT service...")
    try:
        translation_client = translate.Client()
        tts_client = texttospeech.TextToSpeechClient()
        logger.info("✅ Google Cloud clients initialized")
        logger.info("🔥 Service ready to accept connections")
    except Exception as e:
        logger.error(f"❌ Failed to initialize clients: {e}")
        raise e

@app.websocket("/ws/stream/{stream_id}")
async def websocket_streaming(websocket: WebSocket, stream_id: str):
    """Single streaming endpoint - Dutch speech to English audio."""
    await websocket.accept()
    client_id = f"{websocket.client.host}:{websocket.client.port}"
    message_count = 0
    
    logger.info(f"🎙️ Stream started: {client_id} → {stream_id}")
    
    # Transcript handler - simple pipeline
    async def handle_transcript(text: str, is_final: bool, confidence: float = 1.0):
        nonlocal message_count
        
        if not is_final:
            logger.debug(f"Interim: '{text}'")
            return
        
        if not text.strip():
            return
            
        message_count += 1
        logger.info(f"✅ Transcript #{message_count}: '{text}' (confidence: {confidence:.2f})")
        
        try:
            # Direct translation API call
            result = translation_client.translate(text, target_language='en', source_language='nl')
            translated = result['translatedText']
            logger.info(f"📝 Translation #{message_count}: '{translated}'")
            
            # Direct TTS API call  
            synthesis_input = texttospeech.SynthesisInput(text=translated)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Neural2-F",
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            response = tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            
            # Broadcast to listeners
            await connection_manager.broadcast_to_stream(stream_id, response.audio_content)
            logger.info(f"🔊 Audio broadcast #{message_count}: {len(response.audio_content)} bytes")
            
        except Exception as e:
            logger.error(f"❌ Pipeline error #{message_count}: {e}")

    # Error handler
    async def handle_error(error):
        logger.error(f"❌ STT error: {error}")
    
    try:
        # Start streaming STT - debug the client type
        logger.info(f"🔍 DEBUG: streaming_stt.client type = {type(streaming_stt.client)}")
        logger.info(f"🔍 DEBUG: streaming_stt.client = {streaming_stt.client}")
        await streaming_stt.start_streaming(handle_transcript, handle_error)
        
        # Process audio chunks and handle keepalive
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            elif message["type"] == "websocket.text":
                # Handle text messages (including keepalive)
                try:
                    import json
                    data = json.loads(message.get("text", "{}"))
                    if data.get("type") == "keepalive" and data.get("action") == "pong":
                        # Streaming endpoint doesn't use connection_manager, just log
                        logger.debug(f"Received keepalive pong from streaming client {client_id}")
                except json.JSONDecodeError:
                    # Ignore malformed JSON
                    pass
            elif "bytes" in message and message.get("bytes"):
                audio_chunk = message["bytes"]
                streaming_stt.send_audio_chunk(audio_chunk)
                
    except WebSocketDisconnect:
        logger.info(f"🔌 Stream ended: {client_id} after {message_count} messages")
    except Exception as e:
        logger.error(f"❌ Stream error: {e}")
    finally:
        await streaming_stt.stop_streaming()

@app.websocket("/ws/listen/{stream_id}")
async def websocket_listener(websocket: WebSocket, stream_id: str):
    """Listen to translated audio stream."""
    await websocket.accept()
    client_id = f"{websocket.client.host}:{websocket.client.port}"
    
    logger.info(f"🎧 Listener joined: {client_id} → {stream_id}")
    connection_manager.add_listener(stream_id, websocket)
    
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            elif message["type"] == "websocket.text":
                # Handle text messages (including keepalive)
                try:
                    import json
                    data = json.loads(message.get("text", "{}"))
                    if data.get("type") == "keepalive" and data.get("action") == "pong":
                        await connection_manager.handle_pong(websocket)
                        logger.debug(f"Handled keepalive pong from {client_id}")
                except json.JSONDecodeError:
                    # Ignore malformed JSON
                    pass
            # Ignore other message types for listeners
    except WebSocketDisconnect:
        logger.info(f"🔌 Listener left: {client_id}")
    except Exception as e:
        logger.error(f"❌ Listener error: {e}")
    finally:
        connection_manager.remove_listener(stream_id, websocket)

@app.get("/health")
async def health():
    """Simple health check."""
    return {
        "status": "ok",
        "service": "Simple Speech-to-Speech Translation",
        "translation": "connected" if translation_client else "disconnected",
        "tts": "connected" if tts_client else "disconnected",
        "active_streams": connection_manager.get_active_streams_count()
    }

@app.get("/keepalive/stats")
async def keepalive_stats():
    """Get WebSocket keepalive statistics for monitoring."""
    return connection_manager.get_keepalive_stats()