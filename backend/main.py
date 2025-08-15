import logging
import json
import asyncio
import os
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
import pybreaker
from tenacity import RetryError
from google.cloud import speech
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech

# Import ConnectionManager
from .connection_manager import ConnectionManager

# Importeer de services vanuit hetzelfde package - gebruik echte Google Cloud APIs
from .services import (
    real_speech_to_text,
    real_translation, 
    real_text_to_speech,
    buffered_speech_to_text,
    streaming_stt_service,
)

# Import Phase 2 Hybrid STT Service
from .hybrid_stt_service import HybridSTTService, HybridSTTServiceBuilder
from .fallback_orchestrator import ProcessingMode

# Importeer de configuratie en resilience componenten
from .config import settings
from .resilience import circuit_breaker

# Import enhanced STT service directly to avoid circular imports
from .enhanced_stt_service import enhanced_stt_service

# Definieer de retry-decorator op basis van de configuratie
pipeline_retry_decorator = retry(
    stop=stop_after_attempt(settings.API_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=settings.API_RETRY_WAIT_MULTIPLIER_S),
    reraise=True,  # Essentieel om de fout door te geven aan de circuit breaker
)

# Configureer logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="Phase 2 Hybrid STT Service",
    description="A FastAPI service with hybrid streaming/buffered speech-to-text translation using WebSockets.",
    version="2.0.0",
)

# Initialize Google Cloud clients
speech_client = None
translation_client = None
tts_client = None

# Initialize Phase 2 Hybrid STT Service
hybrid_stt_service = None

# Initialize ConnectionManager
connection_manager = ConnectionManager()

# Message counters for debugging multi-sentence issues
message_counters = {}

@app.on_event("startup")
async def startup_event():
    global speech_client, translation_client, tts_client, hybrid_stt_service
    try:
        # Load credentials from environment variable
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        speech_client = speech.SpeechClient()
        logging.info("Google Cloud Speech client initialized successfully")
        
        translation_client = translate.Client()
        logging.info("Google Cloud Translation client initialized successfully")
        
        tts_client = texttospeech.TextToSpeechClient()
        logging.info("Google Cloud Text-to-Speech client initialized successfully")
        
        # Initialize enhanced STT service
        await enhanced_stt_service.start()
        logging.info("Enhanced STT service initialized successfully")
        
        # Initialize Phase 2 Hybrid STT Service
        hybrid_stt_service = HybridSTTServiceBuilder() \
            .with_streaming_config(
                threshold_bytes=settings.STREAMING_THRESHOLD_BYTES,
                timeout_seconds=settings.STREAMING_TIMEOUT
            ) \
            .with_fallback_config(
                failure_threshold=settings.FAILURE_THRESHOLD,
                recovery_interval=settings.RECOVERY_INTERVAL_SECONDS
            ) \
            .with_quality_threshold(settings.QUALITY_THRESHOLD) \
            .build()
        
        if not settings.ENABLE_STREAMING:
            await hybrid_stt_service.set_global_mode(ProcessingMode.BUFFERED)
            
        logging.info("Phase 2 Hybrid STT Service initialized successfully")
        
    except Exception as e:
        logging.error(f"Failed to initialize services: {e}")
        speech_client = None
        translation_client = None
        tts_client = None
        hybrid_stt_service = None

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    try:
        await enhanced_stt_service.stop()
        logging.info("Enhanced STT service stopped")
    except Exception as e:
        logging.error(f"Error stopping enhanced STT service: {e}")
    
    # Shutdown Phase 2 Hybrid STT Service
    if hybrid_stt_service:
        try:
            await hybrid_stt_service.shutdown()
            logging.info("Phase 2 Hybrid STT Service stopped")
        except Exception as e:
            logging.error(f"Error stopping Phase 2 Hybrid STT Service: {e}")

@app.get("/health/speech")
async def health_speech():
    """Health check endpoint for Google Cloud Speech-to-Text service."""
    if speech_client is not None:
        return {"status": "ok", "speech_client": "connected"}
    else:
        return {"status": "error", "speech_client": "disconnected"}

@app.get("/health/translation")
async def health_translation():
    """Health check endpoint for Google Cloud Translation service."""
    if translation_client is None:
        return {"status": "error", "translation_client": "disconnected", "test_result": "failed"}
    
    try:
        # Test translation API with minimal request
        test_result = translation_client.translate("test", target_language="en")
        return {
            "status": "ok", 
            "translation_client": "connected",
            "test_result": "success",
            "test_translation": test_result.get('translatedText', 'N/A')
        }
    except Exception as e:
        logging.error(f"Translation health check failed: {e}")
        return {
            "status": "error", 
            "translation_client": "connected",
            "test_result": "failed",
            "error": str(e)
        }

@app.get("/health/tts")
async def health_tts():
    """Health check endpoint for Google Cloud Text-to-Speech service."""
    if tts_client is None:
        return {"status": "error", "tts_client": "disconnected", "test_result": "failed"}
    
    try:
        # Test TTS API with minimal request
        synthesis_input = texttospeech.SynthesisInput(text="test")
        voice = texttospeech.VoiceSelectionParams(
            language_code=settings.TTS_LANGUAGE_CODE,
            name=settings.TTS_VOICE_NAME
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return {
            "status": "ok",
            "tts_client": "connected",
            "test_result": "success",
            "audio_output_size": len(response.audio_content),
            "voice_config": {
                "language": settings.TTS_LANGUAGE_CODE,
                "voice_name": settings.TTS_VOICE_NAME,
                "format": "MP3"
            }
        }
    except Exception as e:
        logging.error(f"TTS health check failed: {e}")
        return {
            "status": "error",
            "tts_client": "connected",
            "test_result": "failed",
            "error": str(e)
        }

@app.get("/health/full")
async def health_full():
    """Complete pipeline health check for all services."""
    try:
        # Check all clients
        if not all([speech_client, translation_client, tts_client]):
            return {
                "status": "error",
                "pipeline": "incomplete",
                "services": {
                    "speech": "connected" if speech_client else "disconnected",
                    "translation": "connected" if translation_client else "disconnected",
                    "tts": "connected" if tts_client else "disconnected"
                }
            }
        
        # Test complete pipeline with minimal data
        test_text = "test"
        
        # Test translation
        translation_result = translation_client.translate(test_text, target_language="en")
        translated_text = translation_result.get('translatedText', test_text)
        
        # Test TTS
        synthesis_input = texttospeech.SynthesisInput(text=translated_text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=settings.TTS_LANGUAGE_CODE,
            name=settings.TTS_VOICE_NAME
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        tts_response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return {
            "status": "ok",
            "pipeline": "complete",
            "services": {
                "speech": "connected",
                "translation": "connected", 
                "tts": "connected"
            },
            "test_results": {
                "translation": translated_text,
                "audio_size": len(tts_response.audio_content)
            }
        }
        
    except Exception as e:
        logging.error(f"Full pipeline health check failed: {e}")
        return {
            "status": "error",
            "pipeline": "failed",
            "error": str(e),
            "services": {
                "speech": "connected" if speech_client else "disconnected",
                "translation": "connected" if translation_client else "disconnected",
                "tts": "connected" if tts_client else "disconnected"
            }
        }

@app.get("/health/streaming")
async def health_streaming():
    """Health check endpoint for streaming STT service."""
    try:
        stats = streaming_stt_service.get_stats()
        return {
            "status": "ok",
            "streaming_stt": "active",
            "stats": stats
        }
    except Exception as e:
        logging.error(f"Streaming STT health check failed: {e}")
        return {
            "status": "error",
            "streaming_stt": "failed",
            "error": str(e)
        }

@app.get("/health/enhanced")
async def health_enhanced():
    """Health check endpoint for enhanced STT service."""
    try:
        health_info = await enhanced_stt_service.get_health_check()
        return {
            "status": "ok",
            "enhanced_stt": health_info,
            "service_stats": enhanced_stt_service.get_service_stats()
        }
    except Exception as e:
        logging.error(f"Enhanced STT health check failed: {e}")
        return {
            "status": "error",
            "enhanced_stt": "failed",
            "error": str(e)
        }

@app.get("/health/phase2")
async def health_phase2():
    """Health check endpoint for Phase 2 Hybrid STT service."""
    if not hybrid_stt_service:
        return {
            "status": "error",
            "phase2_hybrid": "not_initialized"
        }
    
    try:
        service_stats = hybrid_stt_service.get_service_stats()
        return {
            "status": "ok",
            "phase2_hybrid": "active",
            "service_stats": service_stats,
            "streaming_enabled": settings.ENABLE_STREAMING
        }
    except Exception as e:
        logging.error(f"Phase 2 health check failed: {e}")
        return {
            "status": "error",
            "phase2_hybrid": "failed",
            "error": str(e)
        }

@app.get("/health")
async def health():
    """Main health check endpoint for Cloud Run."""
    return {
        "status": "ok",
        "version": "2.0.0",
        "service": "Phase 2 Hybrid STT Service",
        "timestamp": asyncio.get_event_loop().time()
    }

@app.get("/ready")
async def ready():
    """Readiness check endpoint for Cloud Run."""
    checks = []
    
    # Check Google Cloud clients
    checks.append({"service": "speech", "status": "ok" if speech_client else "error"})
    checks.append({"service": "translation", "status": "ok" if translation_client else "error"})
    checks.append({"service": "tts", "status": "ok" if tts_client else "error"})
    checks.append({"service": "hybrid_stt", "status": "ok" if hybrid_stt_service else "error"})
    
    all_ready = all(check["status"] == "ok" for check in checks)
    
    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks
    }

@pipeline_retry_decorator
async def process_pipeline(audio_chunk: bytes) -> Optional[bytes]:
    """
    Verwerkt een audio-chunk door de volledige pijplijn.
    De decorator handelt de retries af.
    
    Returns:
        Audio output if processing completed, None if still buffering
    """
    attempt_num = process_pipeline.retry.statistics.get('attempt_number', 1)
    if attempt_num > 1:
        logging.info(f"Pipeline-poging {attempt_num}...")

    # Use buffered STT - may return None if still accumulating chunks
    text_result = await buffered_speech_to_text(audio_chunk)
    
    if text_result is None:
        # Still buffering - no output yet
        return None
        
    # Process through translation and TTS
    translation_result = await real_translation(text_result)
    output_audio = await real_text_to_speech(translation_result)
    return output_audio


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Verwerkt de WebSocket-verbinding voor de vertaalservice.

    Dit endpoint kan twee soorten data verwerken:
    1.  Binaire audio-chunks: Deze worden verwerkt via een gesimuleerde
        STT -> Translate -> TTS pijplijn.
    2.  JSON-berichten: Deze worden teruggekaatst naar de client voor
        testen en backward compatibility.
    """
    await websocket.accept()
    if websocket.client:
        client_id = f"{websocket.client.host}:{websocket.client.port}"
    else:
        client_id = "testclient"
    logging.info(f"WebSocket-verbinding geaccepteerd van {client_id}")

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message and message.get("bytes") is not None:
                audio_chunk = message["bytes"]
                logging.info(f"[{client_id}] Binaire audio-chunk ontvangen ({len(audio_chunk)} bytes).")

                try:
                    # 1. Circuit Breaker Check
                    if circuit_breaker.current_state == "open":
                        logging.warning(f"[{client_id}] Circuit breaker is open. Draaien in 'degraded mode'.")
                        await websocket.send_bytes(settings.FALLBACK_AUDIO)
                        continue

                    # 2. Pipeline Execution met Timeout
                    try:
                        async with asyncio.timeout(settings.PIPELINE_TIMEOUT_S):
                            output_audio = await process_pipeline(audio_chunk)
                            
                            # Check if pipeline returned audio (not still buffering)
                            if output_audio is not None:
                                await websocket.send_bytes(output_audio)
                                logging.info(f"[{client_id}] Pijplijn succesvol. Vertaalde audio teruggestuurd.")
                            else:
                                logging.debug(f"[{client_id}] Pijplijn nog aan het bufferen")
                    except asyncio.TimeoutError:
                        logging.error(f"[{client_id}] Pijplijn-timeout na {settings.PIPELINE_TIMEOUT_S}s.")
                        # Manually trigger circuit breaker failure
                        try:
                            circuit_breaker.call(lambda: None)
                        except:
                            pass
                        await websocket.send_bytes(settings.FALLBACK_AUDIO)

                except (RetryError, pybreaker.CircuitBreakerError, Exception) as e:
                    # Alle fouten leiden tot fallback audio
                    # Manually trigger circuit breaker failure for non-CircuitBreakerError exceptions
                    if not isinstance(e, pybreaker.CircuitBreakerError):
                        try:
                            circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Pipeline failed")))
                        except:
                            pass
                    
                    if isinstance(e, RetryError):
                        logging.error(f"[{client_id}] Pijplijn definitief mislukt na {settings.API_RETRY_ATTEMPTS} pogingen.")
                    elif isinstance(e, pybreaker.CircuitBreakerError):
                        logging.warning(f"[{client_id}] Aanroep geblokkeerd door open circuit breaker.")
                    else:
                        logging.critical(f"[{client_id}] Onverwachte fout in pijplijn-handler: {e}", exc_info=True)
                    await websocket.send_bytes(settings.FALLBACK_AUDIO)

            elif "text" in message and message.get("text") is not None:
                text_data = message["text"]
                logging.info(f"[{client_id}] Tekstdata ontvangen: {text_data}")
                # Vang specifiek JSON-decodeerfouten af zonder de verbinding te verbreken.
                try:
                    json_data = json.loads(text_data)
                    await websocket.send_json(json_data)
                    logging.info(f"[{client_id}] JSON-data teruggekaatst naar client.")
                except json.JSONDecodeError:
                    logging.warning(f"[{client_id}] Ongeldige JSON ontvangen: {text_data}")
                    # Stuur geen antwoord, maar houd de verbinding open.

    except WebSocketDisconnect:
        logging.info(f"Client {client_id} heeft de verbinding verbroken.")
    except Exception as e:
        logging.error(f"[{client_id}] Onverwachte fout in WebSocket-loop: {e}", exc_info=True)
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1011, reason="Interne serverfout")


@app.websocket("/ws/speak/{stream_id}")
async def websocket_speaker_endpoint(websocket: WebSocket, stream_id: str):
    """
    WebSocket endpoint for speakers to send audio for translation.
    """
    await websocket.accept()
    if websocket.client:
        client_id = f"{websocket.client.host}:{websocket.client.port}"
    else:
        client_id = "testclient"
    
    # Initialize message counter for this connection
    message_counters[client_id] = 0
    
    logging.info(f"Speaker connected to stream '{stream_id}' from {client_id}")
    logging.info(f"Circuit breaker initial state: {circuit_breaker.current_state}, fail_counter: {circuit_breaker.fail_counter}")
    
    try:
        while True:
            message = await websocket.receive()
            
            # Check for disconnect message
            if message["type"] == "websocket.disconnect":
                logging.info(f"[{client_id}] Received disconnect message for stream '{stream_id}'")
                break
            
            if "bytes" in message and message.get("bytes") is not None:
                audio_chunk = message["bytes"]
                message_counters[client_id] += 1
                msg_count = message_counters[client_id]
                
                logging.info(f"[{client_id}] Message #{msg_count}: Speaker audio received ({len(audio_chunk)} bytes) for stream '{stream_id}'")
                logging.info(f"[{client_id}] Message #{msg_count}: Circuit breaker state: {circuit_breaker.current_state}, fail_counter: {circuit_breaker.fail_counter}")
                logging.info(f"[{client_id}] Message #{msg_count}: WebSocket state: {websocket.client_state}")
                
                try:
                    # 1. Circuit Breaker Check
                    if circuit_breaker.current_state == "open":
                        logging.warning(f"[{client_id}] Message #{msg_count}: Circuit breaker OPEN - blocking API call. fail_counter: {circuit_breaker.fail_counter}, reset_timeout: {circuit_breaker.reset_timeout}s")
                        logging.warning(f"[{client_id}] Message #{msg_count}: Broadcasting fallback to stream '{stream_id}'")
                        await connection_manager.broadcast_to_stream(stream_id, settings.FALLBACK_AUDIO)
                        continue
                    
                    logging.info(f"[{client_id}] Message #{msg_count}: Circuit breaker CLOSED - proceeding with pipeline")
                    
                    # 2. Pipeline Execution with Timeout
                    try:
                        async with asyncio.timeout(settings.PIPELINE_TIMEOUT_S):
                            output_audio = await process_pipeline(audio_chunk)
                            
                            # Check if pipeline returned audio (not still buffering)
                            if output_audio is not None:
                                logging.info(f"[{client_id}] Message #{msg_count}: Pipeline SUCCESS for stream '{stream_id}'. Broadcasting {len(output_audio)} bytes to listeners.")
                                logging.info(f"[{client_id}] Message #{msg_count}: Circuit breaker state after success: {circuit_breaker.current_state}, fail_counter: {circuit_breaker.fail_counter}")
                                await connection_manager.broadcast_to_stream(stream_id, output_audio)
                            else:
                                logging.info(f"[{client_id}] Message #{msg_count}: Pipeline still buffering audio for stream '{stream_id}'")
                    except asyncio.TimeoutError:
                        logging.error(f"[{client_id}] Message #{msg_count}: Pipeline TIMEOUT ({settings.PIPELINE_TIMEOUT_S}s) for stream '{stream_id}'. Broadcasting fallback.")
                        logging.error(f"[{client_id}] Message #{msg_count}: Circuit breaker before timeout failure: {circuit_breaker.current_state}, fail_counter: {circuit_breaker.fail_counter}")
                        # Manually trigger circuit breaker failure
                        try:
                            circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Pipeline timeout")))
                        except Exception as cb_error:
                            logging.error(f"[{client_id}] Message #{msg_count}: Circuit breaker after timeout: {circuit_breaker.current_state}, fail_counter: {circuit_breaker.fail_counter}")
                        await connection_manager.broadcast_to_stream(stream_id, settings.FALLBACK_AUDIO)
                
                except (RetryError, pybreaker.CircuitBreakerError, Exception) as e:
                    # All errors lead to fallback broadcast
                    if not isinstance(e, pybreaker.CircuitBreakerError):
                        try:
                            circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Pipeline failed")))
                        except:
                            pass
                    
                    if isinstance(e, RetryError):
                        logging.error(f"[{client_id}] Message #{msg_count}: Pipeline FAILED after retries for stream '{stream_id}'. Broadcasting fallback.")
                        logging.error(f"[{client_id}] Message #{msg_count}: Circuit breaker after retry failure: {circuit_breaker.current_state}, fail_counter: {circuit_breaker.fail_counter}")
                    elif isinstance(e, pybreaker.CircuitBreakerError):
                        logging.warning(f"[{client_id}] Message #{msg_count}: Circuit breaker BLOCKED call for stream '{stream_id}'. Broadcasting fallback.")
                        logging.warning(f"[{client_id}] Message #{msg_count}: Circuit breaker state: {circuit_breaker.current_state}, fail_counter: {circuit_breaker.fail_counter}")
                    else:
                        logging.critical(f"[{client_id}] Message #{msg_count}: Unexpected pipeline error for stream '{stream_id}': {e}", exc_info=True)
                        logging.critical(f"[{client_id}] Message #{msg_count}: Circuit breaker after unexpected error: {circuit_breaker.current_state}, fail_counter: {circuit_breaker.fail_counter}")
                    
                    await connection_manager.broadcast_to_stream(stream_id, settings.FALLBACK_AUDIO)
            
    except WebSocketDisconnect:
        logging.info(f"Speaker {client_id} disconnected from stream '{stream_id}' after {message_counters.get(client_id, 0)} messages")
        # Cleanup message counter
        if client_id in message_counters:
            del message_counters[client_id]
    except Exception as e:
        logging.error(f"[{client_id}] Error in speaker endpoint after {message_counters.get(client_id, 0)} messages: {e}", exc_info=True)
        # Cleanup message counter
        if client_id in message_counters:
            del message_counters[client_id]
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1011, reason="Speaker endpoint error")


@app.websocket("/ws/listen/{stream_id}")
async def websocket_listener_endpoint(websocket: WebSocket, stream_id: str):
    """
    WebSocket endpoint for listeners to receive translated audio.
    """
    await websocket.accept()
    if websocket.client:
        client_id = f"{websocket.client.host}:{websocket.client.port}"
    else:
        client_id = "testclient"
    
    logging.info(f"Listener connected to stream '{stream_id}' from {client_id}")
    
    # Add listener to connection manager
    connection_manager.add_listener(stream_id, websocket)
    
    try:
        while True:
            # Keep connection alive, wait for disconnect
            message = await websocket.receive()
            
            # Check for disconnect message
            if message["type"] == "websocket.disconnect":
                logging.info(f"[{client_id}] Received disconnect message for stream '{stream_id}'")
                break
            
    except WebSocketDisconnect:
        logging.info(f"Listener {client_id} disconnected from stream '{stream_id}'")
        connection_manager.remove_listener(stream_id, websocket)
    except Exception as e:
        logging.error(f"[{client_id}] Error in listener endpoint: {e}", exc_info=True)
        connection_manager.remove_listener(stream_id, websocket)
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1011, reason="Listener endpoint error")