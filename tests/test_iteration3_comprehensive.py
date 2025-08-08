import pytest
import asyncio
import pybreaker
import sys

# --- Diagnostische print-statements ---
print("\n--- PYTEST DIAGNOSTICS ---")
print(f"Python executable: {sys.executable}")
print(f"Pybreaker module loaded from: {pybreaker.__file__}")
print(f"Pybreaker version hint (dir): {dir(pybreaker.CircuitBreaker)}")
print("--------------------------\n")

from unittest.mock import patch

from fastapi.testclient import TestClient

# Importeer de app en de componenten die we willen testen en mocken
from gcp_speech_to_speech_translation.main import app, circuit_breaker
from gcp_speech_to_speech_translation.config import settings

# Gebruik pytest-asyncio voor alle asynchrone tests in deze module
pytestmark = pytest.mark.asyncio
@pytest.fixture(scope="function", autouse=True)
def reset_circuit_breaker_state():
    """
    Zorgt ervoor dat de circuit breaker voor elke test wordt gereset.
    Dit is cruciaal voor test-isolatie, zodat falende tests elkaar niet beïnvloeden.
    """
    circuit_breaker.close()
    yield
    circuit_breaker.close()

@pytest.fixture(scope="module")
def test_client():
    """Levert een TestClient-instantie voor de gehele testmodule."""
    with TestClient(app) as client:
        yield client


# --- Test Suite ---

class TestHappyPath:
    """Test de ideale workflow waarin alles slaagt."""

    async def test_successful_pipeline(self, test_client):
        """
        Test de volledige pijplijn met een geldige audio-chunk, en verwacht
        een succesvolle vertaling en correcte timing.
        """
        # Patch random.random en gebruik mock STT voor deze test
        with patch('gcp_speech_to_speech_translation.services.random.random', return_value=1.0), \
             patch('gcp_speech_to_speech_translation.main.real_speech_to_text') as mock_stt:
            
            from gcp_speech_to_speech_translation.services import mock_speech_to_text
            mock_stt.side_effect = mock_speech_to_text
            with test_client.websocket_connect("/ws") as websocket:
                start_time = asyncio.get_event_loop().time()

                websocket.send_bytes(b'\x01\x02\x03')
                response_audio = websocket.receive_bytes()

                end_time = asyncio.get_event_loop().time()
                duration = end_time - start_time

                assert response_audio == b'mock_english_audio_output'
                # 3 * 50ms = 150ms. Sta een kleine buffer toe voor overhead.
                assert 0.10 < duration < 0.30, f"Duur was {duration:.2f}s, niet ~0.15s"


class TestErrorAndResilienceScenarios:
    """
    Test hoe het systeem zich gedraagt onder diverse foutcondities,
    en valideert de retry-, fallback- en circuit breaker-logica.
    """

    async def test_stt_failure_with_successful_retry(self, test_client, fast_retry_settings):
        """
        Simuleert een initiële STT API-fout, gevolgd door een succesvolle retry.
        """
        # De eerste `random` call in de pijplijn (mock_speech_to_text) faalt.
        # Bij de retry-poging slagen alle drie de calls.
        # We need 6 calls: 1st attempt (fail, success, success) + 2nd attempt (success, success, success)
        error_then_success = [0.05, 0.9, 0.9, 0.9, 0.9, 0.9]
        with patch('gcp_speech_to_speech_translation.services.random.random', side_effect=error_then_success):
            with test_client.websocket_connect("/ws") as websocket:
                websocket.send_bytes(b'test_retry')
                response_audio = websocket.receive_bytes()

                assert response_audio == b'mock_english_audio_output'

    async def test_translation_failure_triggers_fallback(self, test_client, fast_retry_settings):
        """
        Simuleert een specifieke, aanhoudende fout in de vertaalstap.
        """
        # De STT-stap slaagt, maar de Translation-stap faalt consequent.
        stt_success_translation_fail = [0.9, 0.05, 0.05, 0.05]
        with patch('gcp_speech_to_speech_translation.services.random.random', side_effect=stt_success_translation_fail):
            with test_client.websocket_connect("/ws") as websocket:
                websocket.send_bytes(b'test_translation_fail')
                response_audio = websocket.receive_bytes()

                # Verwacht de fallback omdat de pijplijn nooit slaagt.
                assert response_audio == settings.FALLBACK_AUDIO

    async def test_persistent_failure_triggers_fallback(self, test_client, fast_retry_settings):
        """
        Simuleert een aanhoudende API-fout die alle retries uitput,
        en verwacht een fallback-respons.
        """
        # Alle `random` calls veroorzaken een fout.
        with patch('gcp_speech_to_speech_translation.services.random.random', return_value=0.01):
            with test_client.websocket_connect("/ws") as websocket:
                websocket.send_bytes(b'test_fallback')
                response_audio = websocket.receive_bytes()

                assert response_audio == settings.FALLBACK_AUDIO

    async def test_circuit_breaker_opens_and_fails_fast(self, test_client, fast_retry_settings):
        """
        Valideert dat de circuit breaker opent na N opeenvolgende fouten
        en daarna onmiddellijk een fallback-respons geeft ('fail-fast').
        """
        assert circuit_breaker.current_state == "closed"

        with patch('gcp_speech_to_speech_translation.services.random.random', return_value=0.01):  # Altijd falen
            with test_client.websocket_connect("/ws") as websocket:
                # Trigger genoeg fouten om de breaker te openen
                for i in range(settings.CIRCUIT_BREAKER_FAIL_MAX):
                    websocket.send_bytes(f'fail_{i}'.encode())
                    response = websocket.receive_bytes()
                    assert response == settings.FALLBACK_AUDIO

                assert circuit_breaker.current_state == "open", "Circuit breaker had open moeten zijn"

                # Nu de breaker open is, moet de respons onmiddellijk zijn.
                start_time = asyncio.get_event_loop().time()
                websocket.send_bytes(b'fail_fast_now')
                response = websocket.receive_bytes()
                end_time = asyncio.get_event_loop().time()

                assert response == settings.FALLBACK_AUDIO
                # Moet zeer snel zijn omdat de pijplijn niet wordt uitgevoerd.
                assert (end_time - start_time) < 0.01


class TestPerformanceAndEdgeCases:
    """Test de prestaties en de afhandeling van ongebruikelijke invoer."""

    async def test_empty_audio_chunk_is_handled(self, test_client):
        """Test dat het sturen van een lege bytestring correct wordt afgehandeld."""
        with patch('gcp_speech_to_speech_translation.services.random.random', return_value=1.0):
            with test_client.websocket_connect("/ws") as websocket:
                websocket.send_bytes(b'')
                response = websocket.receive_bytes()
                assert response == b'mock_english_audio_output'

    async def test_large_audio_chunk_is_handled(self, test_client):
        """Test dat een grote (1MB) audio-chunk de server niet laat crashen."""
        large_chunk = b'\x00' * (1024 * 1024)  # 1MB
        with patch('gcp_speech_to_speech_translation.services.random.random', return_value=1.0):
            with test_client.websocket_connect("/ws") as websocket:
                websocket.send_bytes(large_chunk)
                response = websocket.receive_bytes()
                assert response == b'mock_english_audio_output'


class TestConcurrencyAndMalformedData:
    """Test de serverstabiliteit onder druk en met ongeldige data."""

    async def test_concurrent_requests_are_handled(self, test_client):
        """
        Valideert dat de server meerdere gelijktijdige verzoeken correct kan verwerken.
        """
        num_concurrent_requests = 10

        async def send_and_receive(index):
            with test_client.websocket_connect("/ws") as websocket:
                websocket.send_bytes(f"concurrent_{index}".encode())
                response = websocket.receive_bytes()
                assert response == b'mock_english_audio_output'

        # Patch random om altijd te slagen voor deze test
        with patch('gcp_speech_to_speech_translation.services.random.random', return_value=1.0):
            tasks = [send_and_receive(i) for i in range(num_concurrent_requests)]
            await asyncio.gather(*tasks)

    async def test_malformed_text_data_does_not_crash_server(self, test_client):
        """
        Valideert dat het sturen van een niet-JSON-tekstbericht de verbinding
        of de server niet laat crashen.
        """
        with test_client.websocket_connect("/ws") as websocket:
            # Stuur een tekstbericht dat geen geldig JSON is.
            websocket.send_text("this is not json")
            # De server zou de fout moeten loggen en de verbinding open moeten houden.
            # We controleren dit door een geldig bericht te sturen en een antwoord te verwachten.
            websocket.send_json({"echo": "still alive"})
            response = websocket.receive_json()
            assert response == {"echo": "still alive"}