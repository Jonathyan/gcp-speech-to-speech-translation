import pytest
import time
from fastapi.testclient import TestClient

# Importeer de 'app' instantie uit de nieuwe locatie binnen het package
# om de ModuleNotFoundError op te lossen.
from gcp_speech_to_speech_translation.main import app


@pytest.mark.asyncio
async def test_full_mocked_pipeline_with_binary_data():
    """
    Test de volledige gesimuleerde pijplijn voor het verwerken van binaire audiogegevens.
    Deze test volgt het TDD-principe voor Iteratie 3. Hij zal falen
    totdat de backend de gesimuleerde STT -> Translate -> TTS-flow implementeert.

    1. Maakt verbinding met de WebSocket op /ws.
    2. Verstuurt een binair audio-chunk.
    3. Verwacht een *ander* binair audio-chunk terug (de "vertaalde" audio).
    4. Verifieert dat de verwerkingstijd ongeveer 150ms bedraagt, wat de
       som is van de drie gesimuleerde vertragingen van 50ms in de mock-functies.
    """
    # Patch random to ensure success
    from unittest.mock import patch
    with patch('gcp_speech_to_speech_translation.services.random.random', return_value=1.0):
        # De websocket context manager van de TestClient is synchroon.
        with TestClient(app).websocket_connect("/ws") as websocket:
            # Een voorbeeld van een binair audio-chunk, zoals beschreven in het plan.
            input_audio_chunk = b'\x01\x02\x03'

            start_time = time.perf_counter()

            # Verstuurt de binaire data naar de server.
            websocket.send_bytes(input_audio_chunk)

            # Wacht op en ontvangt het binaire antwoord van de server.
            # De test zal hier vastlopen en een time-out geven als de server niet antwoordt.
            # De `timeout` parameter wordt niet ondersteund door de TestClient.
            response_audio_chunk = websocket.receive_bytes()

            end_time = time.perf_counter()

            # --- Verificaties ---
            assert isinstance(response_audio_chunk, bytes), "Het antwoord moet van het type bytes zijn"
            # Verifieer dat we de specifieke output van de mock TTS-service ontvangen.
            # Dit is een robuustere test dan simpelweg controleren of de output anders is.
            assert response_audio_chunk == b'mock_english_audio_output', "De ontvangen audio is niet de verwachte mock-output"

            duration = end_time - start_time
            expected_duration_s = 0.150  # 3 * 50ms
            assert duration == pytest.approx(expected_duration_s, abs=0.5), f"De duur was {duration:.4f}s, niet ~{expected_duration_s}s"