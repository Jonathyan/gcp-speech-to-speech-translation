import logging
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
import pybreaker

# Importeer de mock services vanuit hetzelfde package
from .services import (
    mock_speech_to_text,
    mock_text_to_speech,
    mock_translation,
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

@pipeline_retry_decorator
async def process_pipeline(audio_chunk: bytes) -> bytes:
    """
    Verwerkt een audio-chunk door de volledige pijplijn.
    De decorator handelt de retries af.
    """
    attempt_num = process_pipeline.retry.statistics.get('attempt_number', 1)
    if attempt_num > 1:
        logging.info(f"Pipeline-poging {attempt_num}...")

    text_result = await mock_speech_to_text(audio_chunk)
    translation_result = await mock_translation(text_result)
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
                    if circuit_breaker.is_open:
                        logging.warning(f"[{client_id}] Circuit breaker is open. Draaien in 'degraded mode'.")
                        await websocket.send_bytes(settings.FALLBACK_AUDIO)
                        continue

                    # 2. Pipeline Execution met Timeout
                    async with asyncio.timeout(settings.PIPELINE_TIMEOUT_S):
                        # 3. Roep de pijplijn aan, die retries en circuit breaking bevat
                        output_audio = await circuit_breaker.call_async(process_pipeline, audio_chunk)
                        await websocket.send_bytes(output_audio)
                        logging.info(f"[{client_id}] Pijplijn succesvol. Vertaalde audio teruggestuurd.")

                except asyncio.TimeoutError:
                    logging.error(f"[{client_id}] Pijplijn-timeout na {settings.PIPELINE_TIMEOUT_S}s.")
                    circuit_breaker.failure()  # Timeout telt als een fout voor de breaker
                    await websocket.send_bytes(settings.FALLBACK_AUDIO)
                except RetryError as e:
                    # Wordt getriggerd als alle tenacity-retries falen.
                    # De fout is al gelogd door de circuit breaker.
                    logging.error(f"[{client_id}] Pijplijn definitief mislukt na {settings.API_RETRY_ATTEMPTS} pogingen. Laatste fout: {e.last_attempt.exception()}")
                    await websocket.send_bytes(settings.FALLBACK_AUDIO)
                except pybreaker.CircuitBreakerError:
                    # Wordt getriggerd als de breaker al open was bij de aanroep.
                    logging.warning(f"[{client_id}] Aanroep geblokkeerd door open circuit breaker.")
                    await websocket.send_bytes(settings.FALLBACK_AUDIO)
                except Exception as e:
                    # Vangt alle andere onverwachte fouten op
                    logging.critical(f"[{client_id}] Onverwachte fout in pijplijn-handler: {e}", exc_info=True)
                    await websocket.send_bytes(settings.FALLBACK_AUDIO)

            elif "text" in message and message.get("text") is not None:
                text_data = message["text"]
                logging.info(f"[{client_id}] Tekstdata ontvangen: {text_data}")
                json_data = json.loads(text_data)
                await websocket.send_json(json_data)
                logging.info(f"[{client_id}] JSON-data teruggekaatst naar client.")

    except WebSocketDisconnect:
        logging.info(f"Client {client_id} heeft de verbinding verbroken.")
    except Exception as e:
        logging.error(f"[{client_id}] Onverwachte fout in WebSocket-loop: {e}", exc_info=True)
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1011, reason="Interne serverfout")