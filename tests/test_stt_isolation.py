import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch

from gcp_speech_to_speech_translation.main import app


def test_stt_pass_through_with_mock_pipeline():
    """
    Test STT pass-through met gemockte Translation en TTS.
    Valideert dat mock isolation infrastructure werkt.
    """
    # Path naar het test audio bestand
    audio_file_path = Path(__file__).parent / "fixtures" / "hallo_wereld.wav"
    
    # Skip test als audio bestand niet bestaat
    if not audio_file_path.exists():
        pytest.skip(f"Audio bestand niet gevonden: {audio_file_path}. Zie tests/fixtures/README.md")
    
    # Laad het echte audio bestand
    with open(audio_file_path, "rb") as f:
        real_audio_data = f.read()
    
    # Mock alleen Translation en TTS, STT wordt pass-through
    with patch('gcp_speech_to_speech_translation.main.mock_speech_to_text') as mock_stt, \
         patch('gcp_speech_to_speech_translation.services.random.random', return_value=1.0):
        
        # Import pass-through function en patch STT
        from gcp_speech_to_speech_translation.services import pass_through_speech_to_text
        mock_stt.side_effect = pass_through_speech_to_text
        
        with TestClient(app).websocket_connect("/ws") as websocket:
            # Verstuur het echte audio bestand
            websocket.send_bytes(real_audio_data)
            
            # Verwacht final audio output via mock pipeline
            response = websocket.receive_bytes()
            
            # Valideer dat volledige pipeline werkt
            assert isinstance(response, bytes), "Response moet binaire data zijn"
            assert len(response) > 0, "Response mag niet leeg zijn"
            assert response == b'mock_english_audio_output', "Verwacht mock TTS output"
            
            # Valideer dat STT pass-through werd aangeroepen
            mock_stt.assert_called_once()


def test_mock_isolation_infrastructure():
    """
    Test dat Translation en TTS mocks nog steeds correct werken
    wanneer STT in pass-through mode is.
    """
    from gcp_speech_to_speech_translation.services import (
        pass_through_speech_to_text,
        mock_translation,
        mock_text_to_speech
    )
    
    # Patch random voor consistente resultaten
    with patch('gcp_speech_to_speech_translation.services.random.random', return_value=1.0):
        # Test STT pass-through
        import asyncio
        
        async def test_pipeline():
            # STT pass-through
            stt_result = await pass_through_speech_to_text(b'dummy_audio')
            assert stt_result == "hallo wereld"
            
            # Translation mock
            translation_result = await mock_translation(stt_result)
            assert translation_result == "mocked english translation"
            
            # TTS mock
            tts_result = await mock_text_to_speech(translation_result)
            assert tts_result == b'mock_english_audio_output'
        
        # Run async test
        asyncio.run(test_pipeline())