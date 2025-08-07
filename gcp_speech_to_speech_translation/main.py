import logging
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

# Importeer de mock services vanuit hetzelfde package
from .services import (
    mock_speech_to_text,
    mock_text_to_speech,
    mock_translation,
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
    # De TestClient vult websocket.client niet altijd in.
    # We bieden een fallback om AttributeError in tests te voorkomen.
    if websocket.client:
        client_id = f"{websocket.client.host}:{websocket.client.port}"
    else:
        client_id = "testclient"
    logging.info(f"WebSocket-verbinding geaccepteerd van {client_id}")

    try:
        while True:
            # Gebruik de generieke receive() om zowel tekst als bytes te kunnen ontvangen
            message = await websocket.receive()

            # Verwerk binaire data (de hoofd-pijplijn)
            if "bytes" in message and message.get("bytes") is not None:
                audio_chunk = message["bytes"]
                logging.info(f"[{client_id}] Binaire audio-chunk ontvangen ({len(audio_chunk)} bytes).")

                try:
                    # --- Start Mock API Pijplijn ---
                    text_result = await mock_speech_to_text(audio_chunk)
                    translation_result = await mock_translation(text_result)
                    output_audio = await mock_text_to_speech(translation_result)
                    # --- Einde Pijplijn ---

                    await websocket.send_bytes(output_audio)
                    logging.info(f"[{client_id}] Vertaalde audio-chunk succesvol teruggestuurd.")

                except Exception as e:
                    # Vang fouten in de pijplijn netjes af zonder de verbinding te verbreken
                    logging.error(f"[{client_id}] Fout tijdens verwerking pijplijn: {e}")
                    # Stuur een fallback foutmelding terug naar de client
                    await websocket.send_bytes(b"error_in_pipeline")

            # Verwerk tekstdata (voor JSON echo en backward compatibility)
            elif "text" in message and message.get("text") is not None:
                text_data = message["text"]
                logging.info(f"[{client_id}] Tekstdata ontvangen: {text_data}")
                # De bestaande JSON echo-functionaliteit
                json_data = json.loads(text_data)
                await websocket.send_json(json_data)
                logging.info(f"[{client_id}] JSON-data teruggekaatst naar client.")

    except WebSocketDisconnect:
        logging.info(f"Client {client_id} heeft de verbinding verbroken.")
    except Exception as e:
        logging.error(f"[{client_id}] Onverwachte fout: {e}", exc_info=True)
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1011, reason="Interne serverfout")