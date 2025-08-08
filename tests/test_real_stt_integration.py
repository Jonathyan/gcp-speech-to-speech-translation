import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch

from gcp_speech_to_speech_translation.main import app


def test_real_stt_integration_with_audio_file():
    """
    Test echte STT integratie met audio bestand.
    Deze test MOET falen totdat echte STT implementatie bestaat.
    """
    # Path naar het test audio bestand
    audio_file_path = Path(__file__).parent / "fixtures" / "hallo_wereld.wav"
    
    # Skip test als audio bestand niet bestaat
    if not audio_file_path.exists():
        pytest.skip(f"Audio bestand niet gevonden: {audio_file_path}. Zie tests/fixtures/README.md")
    
    # Laad het echte audio bestand
    with open(audio_file_path, "rb") as f:
        real_audio_data = f.read()
    
    # Mock Translation en TTS, maar gebruik echte STT (die nog niet bestaat)
    with patch('gcp_speech_to_speech_translation.main.mock_speech_to_text') as mock_stt, \
         patch('gcp_speech_to_speech_translation.services.random.random', return_value=1.0):
        
        # Import de nog-niet-bestaande real STT function
        try:
            from gcp_speech_to_speech_translation.services import real_speech_to_text
            mock_stt.side_effect = real_speech_to_text
        except ImportError:
            pytest.fail("real_speech_to_text function niet gevonden - implementatie ontbreekt")
        
        with TestClient(app).websocket_connect("/ws") as websocket:
            # Verstuur het echte audio bestand
            websocket.send_bytes(real_audio_data)
            
            # Verwacht JSON response met transcriptie
            response = websocket.receive_json()
            
            # Valideer transcriptie response
            assert "transcription" in response, "Response moet transcription field bevatten"
            assert response["transcription"].lower() in ["hallo wereld", "hello world"], \
                f"Onverwachte transcriptie: {response['transcription']}"