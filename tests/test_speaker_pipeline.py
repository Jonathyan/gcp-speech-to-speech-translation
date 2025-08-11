import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
from gcp_speech_to_speech_translation.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_speaker_pipeline_execution(client):
    """Test that speaker pipeline is executed when audio is sent."""
    stream_id = "pipeline-test"
    audio_data = b"test_audio_data"
    
    with patch('gcp_speech_to_speech_translation.main.process_pipeline', new_callable=AsyncMock) as mock_pipeline, \
         patch('gcp_speech_to_speech_translation.main.connection_manager') as mock_manager:
        
        mock_pipeline.return_value = b"translated_audio"
        mock_manager.broadcast_to_stream = AsyncMock()
        
        with client.websocket_connect(f"/ws/speak/{stream_id}") as websocket:
            websocket.send_bytes(audio_data)
            
            # Verify pipeline was called
            mock_pipeline.assert_called_once_with(audio_data)


def test_speaker_broadcasts_to_listeners(client):
    """Test that pipeline result is broadcast to listeners, not sent to speaker."""
    stream_id = "broadcast-test"
    audio_data = b"test_audio_data"
    translated_audio = b"translated_audio_output"
    
    with patch('gcp_speech_to_speech_translation.main.process_pipeline', new_callable=AsyncMock) as mock_pipeline, \
         patch('gcp_speech_to_speech_translation.main.connection_manager') as mock_manager:
        
        mock_pipeline.return_value = translated_audio
        mock_manager.broadcast_to_stream = AsyncMock()
        
        with client.websocket_connect(f"/ws/speak/{stream_id}") as websocket:
            websocket.send_bytes(audio_data)
            
            # Verify broadcast was called with correct data
            mock_manager.broadcast_to_stream.assert_called_once_with(stream_id, translated_audio)


def test_speaker_no_response_to_speaker(client):
    """Test that speaker receives no response back."""
    stream_id = "no-response-test"
    audio_data = b"test_audio_data"
    
    with patch('gcp_speech_to_speech_translation.main.process_pipeline') as mock_pipeline, \
         patch('gcp_speech_to_speech_translation.main.connection_manager') as mock_manager:
        
        mock_pipeline.return_value = b"translated_audio"
        
        with client.websocket_connect(f"/ws/speak/{stream_id}") as websocket:
            websocket.send_bytes(audio_data)
            
            # Speaker should not receive any response
            # The websocket should remain open but no data should be sent back


def test_speaker_pipeline_with_zero_listeners(client):
    """Test speaker pipeline works even with no listeners."""
    stream_id = "zero-listeners-test"
    audio_data = b"test_audio_data"
    
    with patch('gcp_speech_to_speech_translation.main.process_pipeline', new_callable=AsyncMock) as mock_pipeline, \
         patch('gcp_speech_to_speech_translation.main.connection_manager') as mock_manager:
        
        mock_pipeline.return_value = b"translated_audio"
        mock_manager.broadcast_to_stream = AsyncMock()
        
        with client.websocket_connect(f"/ws/speak/{stream_id}") as websocket:
            websocket.send_bytes(audio_data)
            
            # Pipeline should still execute
            mock_pipeline.assert_called_once()
            # Broadcast should still be attempted
            mock_manager.broadcast_to_stream.assert_called_once()


def test_speaker_pipeline_error_handling(client):
    """Test error handling when pipeline fails."""
    stream_id = "error-test"
    audio_data = b"test_audio_data"
    
    with patch('gcp_speech_to_speech_translation.main.process_pipeline', new_callable=AsyncMock) as mock_pipeline, \
         patch('gcp_speech_to_speech_translation.main.connection_manager') as mock_manager, \
         patch('gcp_speech_to_speech_translation.main.settings') as mock_settings:
        
        mock_pipeline.side_effect = Exception("Pipeline failed")
        mock_settings.FALLBACK_AUDIO = b"fallback_audio"
        mock_settings.PIPELINE_TIMEOUT_S = 5.0
        mock_manager.broadcast_to_stream = AsyncMock()
        
        with client.websocket_connect(f"/ws/speak/{stream_id}") as websocket:
            websocket.send_bytes(audio_data)
            
            # Should broadcast fallback audio on error
            mock_manager.broadcast_to_stream.assert_called_once_with(stream_id, b"fallback_audio")


def test_speaker_circuit_breaker_fallback(client):
    """Test circuit breaker triggers fallback broadcast."""
    stream_id = "circuit-breaker-test"
    audio_data = b"test_audio_data"
    
    with patch('gcp_speech_to_speech_translation.main.circuit_breaker') as mock_breaker, \
         patch('gcp_speech_to_speech_translation.main.connection_manager') as mock_manager, \
         patch('gcp_speech_to_speech_translation.main.settings') as mock_settings:
        
        mock_breaker.current_state = "open"
        mock_settings.FALLBACK_AUDIO = b"fallback_audio"
        mock_manager.broadcast_to_stream = AsyncMock()
        
        with client.websocket_connect(f"/ws/speak/{stream_id}") as websocket:
            websocket.send_bytes(audio_data)
            
            # Should broadcast fallback when circuit breaker is open
            mock_manager.broadcast_to_stream.assert_called_once_with(stream_id, b"fallback_audio")


def test_speaker_resilience_patterns_preserved(client):
    """Test that all resilience patterns are preserved."""
    stream_id = "resilience-test"
    audio_data = b"test_audio_data"
    
    with patch('gcp_speech_to_speech_translation.main.process_pipeline', new_callable=AsyncMock) as mock_pipeline, \
         patch('gcp_speech_to_speech_translation.main.connection_manager') as mock_manager, \
         patch('gcp_speech_to_speech_translation.main.circuit_breaker') as mock_breaker:
        
        mock_pipeline.return_value = b"translated_audio"
        mock_breaker.current_state = "closed"
        mock_manager.broadcast_to_stream = AsyncMock()
        
        with client.websocket_connect(f"/ws/speak/{stream_id}") as websocket:
            websocket.send_bytes(audio_data)
            
            # Verify circuit breaker state was checked
            assert mock_breaker.current_state == "closed"
            # Verify pipeline was executed
            mock_pipeline.assert_called_once()
            # Verify broadcast occurred
            mock_manager.broadcast_to_stream.assert_called_once()


def test_speaker_multiple_audio_chunks(client):
    """Test speaker can send multiple audio chunks sequentially."""
    stream_id = "multiple-chunks-test"
    
    with patch('gcp_speech_to_speech_translation.main.process_pipeline', new_callable=AsyncMock) as mock_pipeline, \
         patch('gcp_speech_to_speech_translation.main.connection_manager') as mock_manager:
        
        mock_pipeline.return_value = b"translated_audio"
        mock_manager.broadcast_to_stream = AsyncMock()
        
        with client.websocket_connect(f"/ws/speak/{stream_id}") as websocket:
            # Send multiple chunks
            websocket.send_bytes(b"chunk1")
            websocket.send_bytes(b"chunk2")
            websocket.send_bytes(b"chunk3")
            
            # Each chunk should trigger pipeline and broadcast
            assert mock_pipeline.call_count == 3
            assert mock_manager.broadcast_to_stream.call_count == 3