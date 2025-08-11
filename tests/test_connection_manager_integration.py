import pytest
import asyncio
import threading
import time
from unittest.mock import Mock, AsyncMock
from gcp_speech_to_speech_translation.connection_manager import ConnectionManager


@pytest.fixture
def connection_manager():
    return ConnectionManager()


@pytest.mark.asyncio
async def test_multiple_listeners_single_stream(connection_manager):
    """Test that multiple WebSocket mocks can be added to one stream."""
    stream_id = "multi-listener-stream"
    
    # Create multiple mock WebSockets
    ws1 = Mock()
    ws1.send_bytes = AsyncMock()
    ws2 = Mock()
    ws2.send_bytes = AsyncMock()
    ws3 = Mock()
    ws3.send_bytes = AsyncMock()
    
    # Add all listeners to same stream
    connection_manager.add_listener(stream_id, ws1)
    connection_manager.add_listener(stream_id, ws2)
    connection_manager.add_listener(stream_id, ws3)
    
    # Verify all listeners are in the stream
    listeners = connection_manager.get_listeners(stream_id)
    assert len(listeners) == 3
    assert ws1 in listeners
    assert ws2 in listeners
    assert ws3 in listeners


@pytest.mark.asyncio
async def test_broadcast_to_multiple_listeners(connection_manager):
    """Test that broadcasting works to all listeners in a stream."""
    stream_id = "broadcast-test"
    
    # Setup multiple listeners
    listeners = []
    for i in range(5):
        ws = Mock()
        ws.send_bytes = AsyncMock()
        listeners.append(ws)
        connection_manager.add_listener(stream_id, ws)
    
    # Broadcast audio data
    audio_data = b"test_broadcast_audio_data"
    await connection_manager.broadcast_to_stream(stream_id, audio_data)
    
    # Verify all listeners received the data
    for ws in listeners:
        ws.send_bytes.assert_called_once_with(audio_data)


@pytest.mark.asyncio
async def test_stream_isolation_complete(connection_manager):
    """Test that different stream_ids are completely isolated."""
    # Setup multiple streams with different listeners
    stream_configs = [
        ("stream-alpha", 3),
        ("stream-beta", 2),
        ("stream-gamma", 4)
    ]
    
    stream_listeners = {}
    
    # Create listeners for each stream
    for stream_id, listener_count in stream_configs:
        listeners = []
        for i in range(listener_count):
            ws = Mock()
            ws.send_bytes = AsyncMock()
            listeners.append(ws)
            connection_manager.add_listener(stream_id, ws)
        stream_listeners[stream_id] = listeners
    
    # Test broadcasting to one stream doesn't affect others
    test_stream = "stream-beta"
    audio_data = b"isolated_broadcast_test"
    
    await connection_manager.broadcast_to_stream(test_stream, audio_data)
    
    # Verify only target stream listeners received data
    for stream_id, listeners in stream_listeners.items():
        for ws in listeners:
            if stream_id == test_stream:
                ws.send_bytes.assert_called_once_with(audio_data)
            else:
                ws.send_bytes.assert_not_called()


@pytest.mark.asyncio
async def test_connection_cleanup_on_disconnection(connection_manager):
    """Test that connection cleanup works when listeners disconnect."""
    stream_id = "cleanup-test"
    
    # Add multiple listeners
    ws1 = Mock()
    ws1.send_bytes = AsyncMock()
    ws2 = Mock()
    ws2.send_bytes = AsyncMock(side_effect=Exception("Connection lost"))
    ws3 = Mock()
    ws3.send_bytes = AsyncMock()
    
    connection_manager.add_listener(stream_id, ws1)
    connection_manager.add_listener(stream_id, ws2)
    connection_manager.add_listener(stream_id, ws3)
    
    # Initial state: 3 listeners
    assert len(connection_manager.get_listeners(stream_id)) == 3
    
    # Broadcast should trigger cleanup of failed connection
    audio_data = b"cleanup_test_data"
    await connection_manager.broadcast_to_stream(stream_id, audio_data)
    
    # After cleanup: should have 2 listeners (ws2 removed due to failure)
    remaining_listeners = connection_manager.get_listeners(stream_id)
    assert len(remaining_listeners) == 2
    assert ws1 in remaining_listeners
    assert ws3 in remaining_listeners
    assert ws2 not in remaining_listeners


def test_concurrent_access_thread_safety(connection_manager):
    """Test concurrent access with multiple threads adding/removing connections."""
    stream_id = "concurrent-test"
    num_threads = 10
    connections_per_thread = 5
    
    # Create mock WebSockets for each thread
    all_websockets = []
    for i in range(num_threads * connections_per_thread):
        ws = Mock()
        ws.send_bytes = AsyncMock()
        all_websockets.append(ws)
    
    def add_connections(thread_id):
        """Add connections from a specific thread."""
        start_idx = thread_id * connections_per_thread
        end_idx = start_idx + connections_per_thread
        
        for i in range(start_idx, end_idx):
            connection_manager.add_listener(stream_id, all_websockets[i])
            time.sleep(0.001)  # Small delay to increase chance of race conditions
    
    def remove_connections(thread_id):
        """Remove connections from a specific thread."""
        start_idx = thread_id * connections_per_thread
        end_idx = start_idx + connections_per_thread
        
        for i in range(start_idx, end_idx):
            connection_manager.remove_listener(stream_id, all_websockets[i])
            time.sleep(0.001)
    
    # Start multiple threads adding connections
    add_threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=add_connections, args=(i,))
        add_threads.append(thread)
        thread.start()
    
    # Wait for all add threads to complete
    for thread in add_threads:
        thread.join()
    
    # Verify all connections were added
    listeners = connection_manager.get_listeners(stream_id)
    assert len(listeners) == num_threads * connections_per_thread
    
    # Start multiple threads removing connections
    remove_threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=remove_connections, args=(i,))
        remove_threads.append(thread)
        thread.start()
    
    # Wait for all remove threads to complete
    for thread in remove_threads:
        thread.join()
    
    # Verify all connections were removed
    listeners = connection_manager.get_listeners(stream_id)
    assert len(listeners) == 0


@pytest.mark.asyncio
async def test_concurrent_broadcast_during_modifications(connection_manager):
    """Test broadcasting while connections are being added/removed concurrently."""
    stream_id = "concurrent-broadcast-test"
    
    # Add initial listeners
    initial_listeners = []
    for i in range(5):
        ws = Mock()
        ws.send_bytes = AsyncMock()
        initial_listeners.append(ws)
        connection_manager.add_listener(stream_id, ws)
    
    # Function to continuously add/remove listeners
    def modify_connections():
        for i in range(10):
            ws = Mock()
            ws.send_bytes = AsyncMock()
            connection_manager.add_listener(stream_id, ws)
            time.sleep(0.01)
            connection_manager.remove_listener(stream_id, ws)
    
    # Start modification thread
    modify_thread = threading.Thread(target=modify_connections)
    modify_thread.start()
    
    # Perform multiple broadcasts while modifications are happening
    for i in range(20):
        audio_data = f"broadcast_{i}".encode()
        await connection_manager.broadcast_to_stream(stream_id, audio_data)
        await asyncio.sleep(0.005)
    
    # Wait for modification thread to complete
    modify_thread.join()
    
    # Verify system is still stable and initial listeners received some broadcasts
    final_listeners = connection_manager.get_listeners(stream_id)
    assert len(final_listeners) >= 5  # At least initial listeners should remain
    
    # Verify initial listeners received at least some broadcasts
    for ws in initial_listeners:
        assert ws.send_bytes.call_count > 0