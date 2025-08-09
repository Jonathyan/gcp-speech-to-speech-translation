import logging
import json
import asyncio
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
import pybreaker
from google.cloud import speech
from google.cloud import translate_v2 as translate

# Importeer de services vanuit hetzelfde package
from .services import (
    real_speech_to_text,
    real_translation,
    mock_text_to_speech,
)

# Importeer de configuratie en resilience componenten
from .config import settings
from .resilience import circuit_breaker

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
    title="Live Translation Service",
    description="A FastAPI service for real-time speech-to-speech translation using WebSockets.",
    version="0.3.0",
)

# Initialize Google Cloud clients
speech_client = None
translation_client = None

@app.on_event("startup")
async def startup_event():
    global speech_client, translation_client
    try:
        # Load credentials from environment variable
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        speech_client = speech.SpeechClient()
        logging.info("Google Cloud Speech client initialized successfully")
        
        translation_client = translate.Client()
        logging.info("Google Cloud Translation client initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize Google Cloud clients: {e}")
        speech_client = None
        translation_client = None

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

@pipeline_retry_decorator
async def process_pipeline(audio_chunk: bytes) -> bytes:
    """
    Verwerkt een audio-chunk door de volledige pijplijn.
    De decorator handelt de retries af.
    """
    attempt_num = process_pipeline.retry.statistics.get('attempt_number', 1)
    if attempt_num > 1:
        logging.info(f"Pipeline-poging {attempt_num}...")

    text_result = await real_speech_to_text(audio_chunk)
    translation_result = await real_translation(text_result)
    output_audio = await mock_text_to_speech(translation_result)
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
                            await websocket.send_bytes(output_audio)
                            logging.info(f"[{client_id}] Pijplijn succesvol. Vertaalde audio teruggestuurd.")
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