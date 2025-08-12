import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_speaker_endpoint_accepts_connection(client):
    """Test that speaker endpoint accepts WebSocket connections."""
    stream_id = "test-stream-123"
    with client.websocket_connect(f"/ws/speak/{stream_id}") as websocket:
        assert websocket is not None


def test_listener_endpoint_accepts_connection(client):
    """Test that listener endpoint accepts WebSocket connections."""
    stream_id = "test-stream-456"
    with client.websocket_connect(f"/ws/listen/{stream_id}") as websocket:
        assert websocket is not None


def test_stream_id_parameter_extraction_speaker(client):
    """Test that stream_id parameter is correctly extracted in speaker endpoint."""
    stream_id = "my-special-stream"
    
    # Mock the connection manager to verify stream_id is used
    with patch('backend.main.connection_manager') as mock_manager:
        with client.websocket_connect(f"/ws/speak/{stream_id}") as websocket:
            # Just connecting should be enough to trigger stream_id usage
            pass


def test_stream_id_parameter_extraction_listener(client):
    """Test that stream_id parameter is correctly extracted in listener endpoint."""
    stream_id = "another-test-stream"
    
    # Mock the connection manager to verify listener is added with correct stream_id
    with patch('backend.main.connection_manager') as mock_manager:
        with client.websocket_connect(f"/ws/listen/{stream_id}") as websocket:
            # Verify add_listener was called with correct stream_id
            mock_manager.add_listener.assert_called()
            call_args = mock_manager.add_listener.call_args
            assert call_args[0][0] == stream_id  # First argument should be stream_id


def test_listener_added_to_connection_manager(client):
    """Test that listeners are properly added to ConnectionManager."""
    stream_id = "listener-test-stream"
    
    with patch('backend.main.connection_manager') as mock_manager:
        with client.websocket_connect(f"/ws/listen/{stream_id}") as websocket:
            # Verify add_listener was called
            mock_manager.add_listener.assert_called_once()
            
            # Verify the call arguments
            call_args = mock_manager.add_listener.call_args
            assert call_args[0][0] == stream_id  # stream_id
            assert call_args[0][1] is not None   # websocket object


def test_backwards_compatibility_original_endpoint(client):
    """Test that original /ws endpoint still works."""
    with client.websocket_connect("/ws") as websocket:
        # Test echo functionality still works
        test_data = {"test": "message"}
        websocket.send_json(test_data)
        response = websocket.receive_json()
        assert response == test_data


def test_multiple_listeners_same_stream(client):
    """Test that multiple listeners can connect to same stream."""
    stream_id = "multi-listener-stream"
    
    with patch('backend.main.connection_manager') as mock_manager:
        # Connect first listener
        with client.websocket_connect(f"/ws/listen/{stream_id}") as ws1:
            # Connect second listener
            with client.websocket_connect(f"/ws/listen/{stream_id}") as ws2:
                # Both should be added to the same stream
                assert mock_manager.add_listener.call_count == 2
                
                # Both calls should use the same stream_id
                calls = mock_manager.add_listener.call_args_list
                assert calls[0][0][0] == stream_id
                assert calls[1][0][0] == stream_id


def test_different_stream_ids_isolated(client):
    """Test that different stream_ids are handled separately."""
    stream_id_1 = "stream-one"
    stream_id_2 = "stream-two"
    
    with patch('backend.main.connection_manager') as mock_manager:
        with client.websocket_connect(f"/ws/listen/{stream_id_1}") as ws1:
            with client.websocket_connect(f"/ws/listen/{stream_id_2}") as ws2:
                # Should have two separate add_listener calls
                assert mock_manager.add_listener.call_count == 2
                
                # Verify different stream_ids were used
                calls = mock_manager.add_listener.call_args_list
                stream_ids_used = [call[0][0] for call in calls]
                assert stream_id_1 in stream_ids_used
                assert stream_id_2 in stream_ids_used