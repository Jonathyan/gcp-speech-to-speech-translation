import asyncio
import logging
import threading
import time
from typing import Dict, List, Set, Optional
from fastapi import WebSocket
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for multiple streams.
    Thread-safe connection management for broadcasting audio to multiple listeners.
    """

    def __init__(self):
        """Initialize ConnectionManager with thread-safe storage and keepalive mechanism."""
        self._streams: Dict[str, Set[WebSocket]] = {}
        self._connection_metadata: Dict[WebSocket, Dict] = {}  # Store ping/pong metadata
        self._lock = threading.Lock()
        self._keepalive_task: Optional[asyncio.Task] = None
        self._keepalive_running = False
        
        # Keepalive configuration
        self.PING_INTERVAL = 30  # seconds
        self.PONG_TIMEOUT = 10   # seconds
        
        logger.info("ConnectionManager initialized with keepalive mechanism")

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
                # Initialize connection metadata for keepalive
                self._connection_metadata[websocket] = {
                    'last_ping': 0,
                    'last_pong': time.time(),
                    'stream_id': stream_id,
                    'connected_at': time.time()
                }
                logger.info(f"Added listener to stream '{stream_id}'. Total listeners: {len(self._streams[stream_id])}")
                
                # Start keepalive task if not running
                if not self._keepalive_running:
                    asyncio.create_task(self._start_keepalive_monitor())
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
                    # Clean up connection metadata
                    if websocket in self._connection_metadata:
                        del self._connection_metadata[websocket]
                    logger.info(f"Removed listener from stream '{stream_id}'. Remaining listeners: {len(self._streams[stream_id])}")
                    
                    # Clean up empty streams
                    if len(self._streams[stream_id]) == 0:
                        del self._streams[stream_id]
                        logger.info(f"Cleaned up empty stream '{stream_id}'")
                        
                    # Stop keepalive if no connections remain
                    if not self._has_active_connections():
                        self._keepalive_running = False
                        logger.info("No active connections, keepalive monitor will stop")
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

    def get_active_streams_count(self) -> int:
        """
        Get the number of active streams.
        
        Returns:
            Number of streams with active listeners
        """
        with self._lock:
            return len(self._streams)

    def _has_active_connections(self) -> bool:
        """Check if there are any active connections."""
        with self._lock:
            return len(self._connection_metadata) > 0

    async def _start_keepalive_monitor(self):
        """Start the keepalive monitoring background task."""
        if self._keepalive_running:
            return
            
        self._keepalive_running = True
        logger.info("Starting WebSocket keepalive monitor")
        
        while self._keepalive_running:
            try:
                await self._perform_keepalive_check()
                await asyncio.sleep(self.PING_INTERVAL)
            except Exception as e:
                logger.error(f"Keepalive monitor error: {e}")
                await asyncio.sleep(5)  # Short delay before retry

    async def _perform_keepalive_check(self):
        """Perform keepalive check on all connections."""
        current_time = time.time()
        dead_connections = []
        
        # Get copy of connections to avoid locking during async operations
        with self._lock:
            connections_to_check = list(self._connection_metadata.items())
        
        for websocket, metadata in connections_to_check:
            try:
                # Check if connection needs ping
                time_since_ping = current_time - metadata['last_ping']
                time_since_pong = current_time - metadata['last_pong']
                
                # If we haven't received pong within timeout, mark as dead
                if metadata['last_ping'] > 0 and time_since_pong > self.PONG_TIMEOUT:
                    logger.warning(f"Connection timeout: no pong for {time_since_pong:.1f}s > {self.PONG_TIMEOUT}s")
                    dead_connections.append((websocket, metadata['stream_id'], 'pong_timeout'))
                    continue
                
                # Send ping if interval elapsed
                if time_since_ping >= self.PING_INTERVAL:
                    await self._send_ping(websocket, metadata)
                    
            except Exception as e:
                logger.error(f"Error checking connection: {e}")
                dead_connections.append((websocket, metadata.get('stream_id'), 'check_error'))
        
        # Clean up dead connections
        for websocket, stream_id, reason in dead_connections:
            logger.info(f"Removing dead connection from stream '{stream_id}': {reason}")
            if stream_id:
                self.remove_listener(stream_id, websocket)

    async def _send_ping(self, websocket: WebSocket, metadata: Dict):
        """Send ping to a WebSocket connection."""
        try:
            # Check connection state before ping
            if (hasattr(websocket, 'client_state') and 
                websocket.client_state == WebSocketState.DISCONNECTED):
                raise ConnectionClosed(None, None)
                
            # FastAPI WebSocket doesn't have ping() method, use send_text with keepalive message
            await websocket.send_text('{"type":"keepalive","action":"ping"}')
            metadata['last_ping'] = time.time()
            logger.debug(f"Sent ping to connection in stream '{metadata['stream_id']}'")
            
        except (ConnectionClosed, WebSocketException) as e:
            logger.info(f"Connection closed during ping: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to send ping: {e}")
            raise

    async def handle_pong(self, websocket: WebSocket):
        """Handle pong response from WebSocket."""
        with self._lock:
            if websocket in self._connection_metadata:
                self._connection_metadata[websocket]['last_pong'] = time.time()
                stream_id = self._connection_metadata[websocket]['stream_id']
                logger.debug(f"Received pong from connection in stream '{stream_id}'")

    def get_keepalive_stats(self) -> Dict:
        """Get keepalive statistics for monitoring."""
        with self._lock:
            current_time = time.time()
            stats = {
                'keepalive_running': self._keepalive_running,
                'total_connections': len(self._connection_metadata),
                'ping_interval': self.PING_INTERVAL,
                'pong_timeout': self.PONG_TIMEOUT,
                'connections': []
            }
            
            for websocket, metadata in self._connection_metadata.items():
                conn_stats = {
                    'stream_id': metadata['stream_id'],
                    'connected_duration': current_time - metadata['connected_at'],
                    'time_since_ping': current_time - metadata['last_ping'],
                    'time_since_pong': current_time - metadata['last_pong'],
                    'healthy': (current_time - metadata['last_pong']) < self.PONG_TIMEOUT
                }
                stats['connections'].append(conn_stats)
            
            return stats