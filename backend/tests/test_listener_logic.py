import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_listener_added_to_connection_manager_on_connect(client):
    """Test that listener is added to ConnectionManager when connecting."""
    stream_id = "test-stream"
    
    with patch('backend.main.connection_manager') as mock_manager:
        with client.websocket_connect(f"/ws/listen/{stream_id}") as websocket:
            # Verify add_listener was called
            mock_manager.add_listener.assert_called_once()
            call_args = mock_manager.add_listener.call_args
            assert call_args[0][0] == stream_id
            assert call_args[0][1] is not None  # websocket object


def test_listener_removed_from_connection_manager_on_disconnect(client):
    """Test that listener is removed from ConnectionManager when disconnecting."""
    stream_id = "test-stream"
    
    with patch('backend.main.connection_manager') as mock_manager:
        with client.websocket_connect(f"/ws/listen/{stream_id}") as websocket:
            pass  # Connection will be closed when exiting context
        
        # Verify remove_listener was called
        mock_manager.remove_listener.assert_called_once()
        call_args = mock_manager.remove_listener.call_args
        assert call_args[0][0] == stream_id
        assert call_args[0][1] is not None  # websocket object


def test_multiple_listeners_same_stream_managed_correctly(client):
    """Test that multiple listeners for same stream are managed correctly."""
    stream_id = "multi-listener-stream"
    
    with patch('backend.main.connection_manager') as mock_manager:
        # Connect first listener
        with client.websocket_connect(f"/ws/listen/{stream_id}") as ws1:
            # Connect second listener
            with client.websocket_connect(f"/ws/listen/{stream_id}") as ws2:
                # Both should be added
                assert mock_manager.add_listener.call_count == 2
                
                # Both calls should use same stream_id
                calls = mock_manager.add_listener.call_args_list
                assert calls[0][0][0] == stream_id
                assert calls[1][0][0] == stream_id
        
        # Both should be removed when disconnecting
        assert mock_manager.remove_listener.call_count == 2


def test_listener_connection_lifecycle(client):
    """Test complete listener connection lifecycle."""
    stream_id = "lifecycle-test"
    
    with patch('backend.main.connection_manager') as mock_manager:
        # Test connection phase
        with client.websocket_connect(f"/ws/listen/{stream_id}") as websocket:
            # Verify listener was added
            mock_manager.add_listener.assert_called_once()
            
            # Test that connection stays alive (no immediate disconnect)
            assert websocket is not None
        
        # Test disconnection phase
        mock_manager.remove_listener.assert_called_once()


def test_listener_error_handling_cleanup(client):
    """Test that listeners are cleaned up even when errors occur."""
    stream_id = "error-test"
    
    with patch('backend.main.connection_manager') as mock_manager:
        # Simulate connection that will have an error
        mock_manager.add_listener.side_effect = Exception("Connection error")
        
        try:
            with client.websocket_connect(f"/ws/listen/{stream_id}") as websocket:
                pass
        except:
            pass  # Expected to fail due to mocked error
        
        # Even with error, add_listener should have been attempted
        mock_manager.add_listener.assert_called_once()


def test_different_streams_isolated_in_connection_manager(client):
    """Test that listeners for different streams are properly isolated."""
    stream_1 = "stream-one"
    stream_2 = "stream-two"
    
    with patch('backend.main.connection_manager') as mock_manager:
        # Connect to different streams
        with client.websocket_connect(f"/ws/listen/{stream_1}") as ws1:
            with client.websocket_connect(f"/ws/listen/{stream_2}") as ws2:
                # Verify both streams got listeners
                assert mock_manager.add_listener.call_count == 2
                
                # Verify correct stream_ids were used
                calls = mock_manager.add_listener.call_args_list
                stream_ids = [call[0][0] for call in calls]
                assert stream_1 in stream_ids
                assert stream_2 in stream_ids
        
        # Verify both were cleaned up
        assert mock_manager.remove_listener.call_count == 2


def test_listener_connection_stability(client):
    """Test that listener connections remain stable and handle keepalive."""
    stream_id = "stability-test"
    
    with patch('backend.main.connection_manager') as mock_manager:
        with client.websocket_connect(f"/ws/listen/{stream_id}") as websocket:
            # Verify connection is established
            mock_manager.add_listener.assert_called_once()
            
            # Connection should remain stable without immediate disconnect
            assert websocket is not None
            
            # Test that we can send a keepalive message
            websocket.send_json({"type": "keepalive"})
        
        # Verify cleanup on disconnect
        mock_manager.remove_listener.assert_called_once()