import logging
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Google Cloud clients - direct imports, no wrappers
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech

# Simple components only
from backend.connection_manager import ConnectionManager
from backend.streaming_stt import streaming_stt

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
        
        # Debug: Log registered routes
        logger.info("📋 Registered routes:")
        for route in app.routes:
            logger.info(f"  - {route.path} ({route.methods if hasattr(route, 'methods') else 'WebSocket' if hasattr(route, 'endpoint') else 'Unknown'})")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize clients: {e}")
        raise e

@app.get("/test")
async def test_route():
    """Test route to verify route registration works."""
    return {"message": "Test route works", "routes_registered": len(app.routes)}

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
                logger.info(f"📡 Received WebSocket audio chunk: {len(audio_chunk)} bytes from {client_id}")
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
        # Use receive_json with mode='text' and a timeout to handle both receiving and allow background tasks
        logger.info(f"🎧 Starting listener receive loop for {client_id}")
        iteration_count = 0
        while True:
            try:
                iteration_count += 1
                if iteration_count % 30 == 0:  # Log every 30 iterations (30 seconds)
                    logger.info(f"🎧 Listener {client_id} receive loop iteration {iteration_count}")
                
                # Use a short timeout to periodically check for disconnection
                # This allows the background keepalive task to send pings
                import asyncio
                
                # Create a receive task with timeout
                logger.debug(f"🎧 Creating receive task for {client_id}")
                receive_task = asyncio.create_task(websocket.receive())
                
                try:
                    # Wait for message with 1 second timeout
                    logger.debug(f"🎧 Waiting for message from {client_id} with 1s timeout")
                    message = await asyncio.wait_for(receive_task, timeout=1.0)
                    logger.info(f"🎧 RECEIVED MESSAGE from {client_id}: {message}")
                    
                    if message["type"] == "websocket.disconnect":
                        logger.info(f"🔌 Listener disconnect signal: {client_id}")
                        break
                    elif message["type"] == "websocket.receive" and "text" in message:
                        # Handle text messages (including keepalive)
                        try:
                            import json
                            text_data = message.get("text", "{}")
                            logger.info(f"🏓 Listener {client_id} sent text message: {text_data}")
                            data = json.loads(text_data)
                            if data.get("type") == "keepalive" and data.get("action") == "pong":
                                logger.info(f"✅ Processing keepalive pong from listener {client_id}")
                                await connection_manager.handle_pong(websocket)
                                logger.info(f"✅ Keepalive pong handled for {client_id}")
                            elif data.get("type") == "connection" and data.get("action") == "confirm":
                                logger.info(f"🔗 Listener {client_id} confirmed connection: {data}")
                            else:
                                logger.info(f"📝 Listener message type: {data.get('type')}, action: {data.get('action')}")
                        except json.JSONDecodeError as e:
                            logger.warning(f"⚠️ Malformed JSON from listener {client_id}: {text_data}, error: {e}")
                        except Exception as e:
                            logger.error(f"❌ Error processing listener message from {client_id}: {e}")
                            logger.error(f"❌ Message content: {message}")
                            logger.error(f"❌ Text data: {message.get('text', 'N/A')}")
                    # Ignore other message types for listeners
                    
                except asyncio.TimeoutError:
                    # Timeout is expected - this allows background tasks to run
                    logger.debug(f"🎧 Timeout waiting for message from {client_id} (expected)")
                    
                    # Check if WebSocket is still connected by checking state
                    try:
                        # Attempt to check WebSocket state - different implementations may vary
                        if hasattr(websocket, 'client_state'):
                            logger.debug(f"🎧 Checking client_state for {client_id}: {getattr(websocket.client_state, 'name', 'unknown')}")
                            if websocket.client_state.name != 'CONNECTED':
                                logger.info(f"🔌 Listener connection lost (client_state): {client_id}")
                                break
                        elif hasattr(websocket, 'application_state'):
                            logger.debug(f"🎧 Checking application_state for {client_id}")
                            if websocket.application_state != websocket.application_state.CONNECTED:
                                logger.info(f"🔌 Listener connection lost (application_state): {client_id}")
                                break
                        # If we can't check state, just continue - the receive will fail if disconnected
                        else:
                            logger.debug(f"🎧 No state checking available for {client_id}, continuing")
                    except Exception as e:
                        logger.debug(f"🔍 Could not check WebSocket state for {client_id}: {e}")
                    
                    # Continue loop to check for messages again
                    continue
                    
            except WebSocketDisconnect:
                logger.info(f"🔌 Listener disconnected: {client_id}")
                break
            except Exception as e:
                logger.error(f"❌ Listener receive error for {client_id}: {e}")
                # Continue to try receiving unless it's a critical error
                if "connection" in str(e).lower():
                    break
                    
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