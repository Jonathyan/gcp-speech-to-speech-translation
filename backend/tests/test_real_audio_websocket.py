import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.main import app


def test_real_audio_file_websocket_integration():
    """
    Test dat een echt audio bestand via WebSocket kan worden verstuurd
    zonder dat de server crasht.
    """
    # Path naar het test audio bestand
    audio_file_path = Path(__file__).parent / "fixtures" / "hallo_wereld.wav"
    
    # Skip test als audio bestand niet bestaat (niet in git)
    if not audio_file_path.exists():
        pytest.skip(f"Audio bestand niet gevonden: {audio_file_path}. Zie tests/fixtures/README.md")
    
    # Laad het echte audio bestand
    with open(audio_file_path, "rb") as f:
        real_audio_data = f.read()
    
    # Patch random om consistente resultaten te krijgen
    with patch('backend.services.random.random', return_value=1.0):
        with TestClient(app).websocket_connect("/ws") as websocket:
            # Verstuur het echte audio bestand als binaire data
            websocket.send_bytes(real_audio_data)
            
            # Verwacht een response (kan mock output of fallback zijn)
            response = websocket.receive_bytes()
            
            # Assert dat we een response krijgen (server crasht niet)
            assert isinstance(response, bytes), "Response moet binaire data zijn"
            assert len(response) > 0, "Response mag niet leeg zijn"
            
            # Verwacht mock output of fallback audio
            assert response in [b'mock_english_audio_output', b'error_fallback_audio'], \
                f"Onverwachte response: {response}"