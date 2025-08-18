import logging
import threading
from typing import Dict, List, Set
from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for multiple streams.
    Thread-safe connection management for broadcasting audio to multiple listeners.
    """

    def __init__(self):
        """Initialize ConnectionManager with thread-safe storage."""
        self._streams: Dict[str, Set[WebSocket]] = {}
        self._lock = threading.Lock()
        logger.info("ConnectionManager initialized")

    def add_listener(self, stream_id: str, websocket: WebSocket) -> None:
        """
        Add a WebSocket listener to a stream.
        
        Args:
            stream_id: Unique identifier for the stream
            websocket: WebSocket connection to add
        """
        with self._lock:
            if stream_id not in self._streams:
                self._streams[stream_id] = set()
            
            if websocket not in self._streams[stream_id]:
                self._streams[stream_id].add(websocket)
                logger.info(f"Added listener to stream '{stream_id}'. Total listeners: {len(self._streams[stream_id])}")
            else:
                logger.warning(f"Listener already exists in stream '{stream_id}'")

    def remove_listener(self, stream_id: str, websocket: WebSocket) -> None:
        """
        Remove a WebSocket listener from a stream.
        
        Args:
            stream_id: Stream identifier
            websocket: WebSocket connection to remove
        """
        with self._lock:
            if stream_id in self._streams:
                if websocket in self._streams[stream_id]:
                    self._streams[stream_id].remove(websocket)
                    logger.info(f"Removed listener from stream '{stream_id}'. Remaining listeners: {len(self._streams[stream_id])}")
                    
                    # Clean up empty streams
                    if len(self._streams[stream_id]) == 0:
                        del self._streams[stream_id]
                        logger.info(f"Cleaned up empty stream '{stream_id}'")
                else:
                    logger.warning(f"Listener not found in stream '{stream_id}'")
            else:
                logger.warning(f"Stream '{stream_id}' does not exist")

    def get_listeners(self, stream_id: str) -> List[WebSocket]:
        """
        Get all listeners for a stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            List of WebSocket connections for the stream
        """
        with self._lock:
            if stream_id in self._streams:
                return list(self._streams[stream_id])
            return []

    async def broadcast_to_stream(self, stream_id: str, audio_data: bytes) -> None:
        """
        Broadcast audio data to all listeners in a stream.
        
        Args:
            stream_id: Stream identifier
            audio_data: Binary audio data to broadcast
        """
        # Clean up dead connections first
        await self.cleanup_dead_connections(stream_id)
        
        listeners = self.get_listeners(stream_id)
        
        if not listeners:
            logger.info(f"No listeners for stream '{stream_id}', skipping broadcast")
            return
        
        logger.info(f"Broadcasting {len(audio_data)} bytes to {len(listeners)} listeners in stream '{stream_id}'")
        
        # Broadcast to all listeners, handle individual failures
        failed_listeners = []
        for websocket in listeners:
            try:
                await websocket.send_bytes(audio_data)
            except Exception as e:
                logger.error(f"Failed to send audio to listener in stream '{stream_id}': {e}")
                failed_listeners.append(websocket)
        
        # Remove failed listeners
        for failed_websocket in failed_listeners:
            self.remove_listener(stream_id, failed_websocket)
    
    async def cleanup_dead_connections(self, stream_id: str) -> int:
        """
        Remove dead WebSocket connections from a stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Number of dead connections removed
        """
        listeners = self.get_listeners(stream_id)
        dead_count = 0
        
        for websocket in listeners:
            # Check if WebSocket is closed or in invalid state
            if (not hasattr(websocket, 'client_state') or 
                websocket.client_state == WebSocketState.DISCONNECTED or
                (hasattr(websocket, 'application_state') and 
                 websocket.application_state == WebSocketState.DISCONNECTED)):
                self.remove_listener(stream_id, websocket)
                dead_count += 1
                logger.info(f"Removed dead connection from stream '{stream_id}'")
        
        if dead_count > 0:
            logger.info(f"Cleaned up {dead_count} dead connections from stream '{stream_id}'")
        
        return dead_count