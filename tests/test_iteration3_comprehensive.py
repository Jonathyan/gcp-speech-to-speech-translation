import pytest
import asyncio
from unittest.mock import patch

from fastapi.testclient import TestClient

# Importeer de app en de componenten die we willen testen en mocken
from gcp_speech_to_speech_translation.main import app, circuit_breaker
from gcp_speech_to_speech_translation.config import settings

# Gebruik pytest-asyncio voor alle asynchrone tests in deze module
pytestmark = pytest.mark.asyncio


# --- Fixtures ---

@pytest.fixture(scope="function", autouse=True)
def reset_circuit_breaker_state():
    """
    Zorgt ervoor dat de circuit breaker voor elke test wordt gereset.
    Dit is cruciaal voor test-isolatie, zodat falende tests elkaar niet beïnvloeden.
    """
    circuit_breaker.reset()
    yield
    circuit_breaker.reset()


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
        # Patch random.random om altijd een waarde te retourneren die geen fout veroorzaakt.
        with patch('gcp_speech_to_speech_translation.services.random.random', return_value=1.0):
            with test_client.websocket_connect("/ws") as websocket:
                start_time = asyncio.get_event_loop().time()

                websocket.send_bytes(b'\x01\x02\x03')
                response_audio = websocket.receive_bytes()

                end_time = asyncio.get_event_loop().time()
                duration = end_time - start_time

                assert response_audio == b'mock_english_audio_output'
                # 3 * 50ms = 150ms. Sta een kleine buffer toe voor overhead.
                assert 0.14 < duration < 0.25, f"Duur was {duration:.2f}s, niet ~0.15s"


class TestErrorAndResilienceScenarios:
    """
    Test hoe het systeem zich gedraagt onder diverse foutcondities,
    en valideert de retry-, fallback- en circuit breaker-logica.
    """

    @pytest.fixture
    def fast_retry_settings(self, monkeypatch):
        """Een fixture om de retry-wachttijd tijdens tests te versnellen."""
        monkeypatch.setattr(settings, 'API_RETRY_WAIT_MULTIPLIER_S', 0.01)

    async def test_stt_failure_with_successful_retry(self, test_client, fast_retry_settings):
        """
        Simuleert een initiële STT API-fout, gevolgd door een succesvolle retry.
        """
        # De eerste `random` call faalt (STT), de tweede slaagt. De rest slaagt ook.
        error_then_success = [0.05, 0.9, 0.9, 0.9]
        with patch('gcp_speech_to_speech_translation.services.random.random', side_effect=error_then_success):
            with test_client.websocket_connect("/ws") as websocket:
                websocket.send_bytes(b'test_retry')
                response_audio = websocket.receive_bytes()

                assert response_audio == b'mock_english_audio_output'

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
        assert circuit_breaker.is_closed

        with patch('gcp_speech_to_speech_translation.services.random.random', return_value=0.01):  # Altijd falen
            with test_client.websocket_connect("/ws") as websocket:
                # Trigger genoeg fouten om de breaker te openen
                for i in range(settings.CIRCUIT_BREAKER_FAIL_MAX):
                    websocket.send_bytes(f'fail_{i}'.encode())
                    response = websocket.receive_bytes()
                    assert response == settings.FALLBACK_AUDIO

                assert circuit_breaker.is_open, "Circuit breaker had open moeten zijn"

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