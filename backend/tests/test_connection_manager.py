import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from backend.connection_manager import ConnectionManager


@pytest.fixture
def connection_manager():
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    websocket = Mock()
    websocket.send_bytes = AsyncMock()
    return websocket


def test_connection_manager_init(connection_manager):
    """Test ConnectionManager initialization."""
    assert hasattr(connection_manager, '_streams')
    assert hasattr(connection_manager, '_lock')
    assert len(connection_manager._streams) == 0


def test_add_listener(connection_manager, mock_websocket):
    """Test adding a listener to a stream."""
    stream_id = "test-stream"
    connection_manager.add_listener(stream_id, mock_websocket)
    
    listeners = connection_manager.get_listeners(stream_id)
    assert len(listeners) == 1
    assert mock_websocket in listeners


def test_add_multiple_listeners(connection_manager):
    """Test adding multiple listeners to same stream."""
    stream_id = "test-stream"
    ws1 = Mock()
    ws2 = Mock()
    
    connection_manager.add_listener(stream_id, ws1)
    connection_manager.add_listener(stream_id, ws2)
    
    listeners = connection_manager.get_listeners(stream_id)
    assert len(listeners) == 2
    assert ws1 in listeners
    assert ws2 in listeners


def test_add_duplicate_listener(connection_manager, mock_websocket):
    """Test adding same websocket twice to same stream."""
    stream_id = "test-stream"
    connection_manager.add_listener(stream_id, mock_websocket)
    connection_manager.add_listener(stream_id, mock_websocket)
    
    listeners = connection_manager.get_listeners(stream_id)
    assert len(listeners) == 1  # Should not duplicate


def test_remove_listener(connection_manager, mock_websocket):
    """Test removing a listener from a stream."""
    stream_id = "test-stream"
    connection_manager.add_listener(stream_id, mock_websocket)
    connection_manager.remove_listener(stream_id, mock_websocket)
    
    listeners = connection_manager.get_listeners(stream_id)
    assert len(listeners) == 0


def test_remove_nonexistent_listener(connection_manager, mock_websocket):
    """Test removing listener that doesn't exist."""
    stream_id = "test-stream"
    # Should not raise exception
    connection_manager.remove_listener(stream_id, mock_websocket)
    
    listeners = connection_manager.get_listeners(stream_id)
    assert len(listeners) == 0


def test_get_listeners_empty_stream(connection_manager):
    """Test getting listeners for non-existent stream."""
    listeners = connection_manager.get_listeners("nonexistent-stream")
    assert len(listeners) == 0


@pytest.mark.asyncio
async def test_broadcast_to_stream(connection_manager):
    """Test broadcasting audio to all listeners in a stream."""
    stream_id = "test-stream"
    ws1 = Mock()
    ws1.send_bytes = AsyncMock()
    ws2 = Mock()
    ws2.send_bytes = AsyncMock()
    
    connection_manager.add_listener(stream_id, ws1)
    connection_manager.add_listener(stream_id, ws2)
    
    audio_data = b"test_audio_data"
    await connection_manager.broadcast_to_stream(stream_id, audio_data)
    
    ws1.send_bytes.assert_called_once_with(audio_data)
    ws2.send_bytes.assert_called_once_with(audio_data)


@pytest.mark.asyncio
async def test_broadcast_to_empty_stream(connection_manager):
    """Test broadcasting to stream with no listeners."""
    # Should not raise exception
    await connection_manager.broadcast_to_stream("empty-stream", b"test_data")


@pytest.mark.asyncio
async def test_broadcast_handles_websocket_errors(connection_manager):
    """Test broadcast continues even if one websocket fails."""
    stream_id = "test-stream"
    ws1 = Mock()
    ws1.send_bytes = AsyncMock(side_effect=Exception("Connection failed"))
    ws2 = Mock()
    ws2.send_bytes = AsyncMock()
    
    connection_manager.add_listener(stream_id, ws1)
    connection_manager.add_listener(stream_id, ws2)
    
    audio_data = b"test_audio_data"
    await connection_manager.broadcast_to_stream(stream_id, audio_data)
    
    # ws2 should still receive data despite ws1 failing
    ws2.send_bytes.assert_called_once_with(audio_data)


def test_stream_isolation(connection_manager):
    """Test that different streams are isolated."""
    ws1 = Mock()
    ws2 = Mock()
    
    connection_manager.add_listener("stream-1", ws1)
    connection_manager.add_listener("stream-2", ws2)
    
    listeners_1 = connection_manager.get_listeners("stream-1")
    listeners_2 = connection_manager.get_listeners("stream-2")
    
    assert len(listeners_1) == 1
    assert len(listeners_2) == 1
    assert ws1 in listeners_1
    assert ws2 in listeners_2
    assert ws1 not in listeners_2
    assert ws2 not in listeners_1