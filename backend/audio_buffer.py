import logging
import time
from typing import List, Optional, Dict, Any


class WebMChunkBuffer:
    """
    Buffer for WebM audio chunks to accumulate complete audio segments 
    before sending to Google Cloud Speech-to-Text API.
    
    WebM is a streaming format where individual chunks may not contain
    complete audio data. This buffer accumulates chunks until we have
    enough data for successful speech recognition.
    """
    
    def __init__(self, 
                 min_duration_seconds: float = 2.0,
                 max_buffer_size: int = 500 * 1024,  # 500KB
                 timeout_seconds: float = 5.0):
        """
        Initialize WebM chunk buffer.
        
        Args:
            min_duration_seconds: Minimum time to wait before processing buffer
            max_buffer_size: Maximum buffer size in bytes before forced processing
            timeout_seconds: Maximum time to wait before forcing processing
        """
        self.min_duration_seconds = min_duration_seconds
        self.max_buffer_size = max_buffer_size
        self.timeout_seconds = timeout_seconds
        
        self.chunks: List[bytes] = []
        self.total_size: int = 0
        self.first_chunk_time: Optional[float] = None
        
        self._logger = logging.getLogger(__name__)

    def add_chunk(self, chunk: bytes) -> None:
        """
        Add an audio chunk to the buffer.
        
        Args:
            chunk: Raw audio chunk bytes from MediaRecorder
        """
        if not chunk:
            return
            
        self.chunks.append(chunk)
        self.total_size += len(chunk)
        
        # Set timestamp for first chunk
        if self.first_chunk_time is None:
            self.first_chunk_time = time.time()
            
        is_webm_header = self._is_webm_header(chunk)
        self._logger.debug(f"Added chunk: {len(chunk)} bytes, WebM header: {is_webm_header}, total: {self.total_size}")

    def is_ready(self) -> bool:
        """
        Check if buffer is ready to be processed.
        
        Returns:
            True if buffer meets any of the ready conditions
        """
        if not self.chunks:
            return False
            
        current_time = time.time()
        
        # Check if we've waited long enough
        if self.first_chunk_time is not None:
            buffer_duration = current_time - self.first_chunk_time
            
            # Ready if minimum duration passed
            if buffer_duration >= self.min_duration_seconds:
                self._logger.debug(f"Buffer ready: duration {buffer_duration:.1f}s >= {self.min_duration_seconds}s")
                return True
                
            # Ready if timeout exceeded
            if buffer_duration >= self.timeout_seconds:
                self._logger.debug(f"Buffer ready: timeout {buffer_duration:.1f}s >= {self.timeout_seconds}s")
                return True
        
        # Ready if buffer size limit exceeded
        if self.total_size >= self.max_buffer_size:
            self._logger.debug(f"Buffer ready: size {self.total_size} >= {self.max_buffer_size}")
            return True
            
        return False

    def get_combined_audio(self) -> bytes:
        """
        Get all buffered chunks combined into a single audio blob.
        
        Returns:
            Combined audio data as bytes
        """
        if not self.chunks:
            return b''
            
        combined = b''.join(self.chunks)
        self._logger.info(f"Combined {len(self.chunks)} chunks into {len(combined)} bytes")
        return combined

    def clear(self) -> None:
        """Clear the buffer after processing."""
        chunk_count = len(self.chunks)
        total_size = self.total_size
        
        self.chunks.clear()
        self.total_size = 0
        self.first_chunk_time = None
        
        self._logger.debug(f"Buffer cleared: {chunk_count} chunks, {total_size} bytes")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get buffer statistics for debugging.
        
        Returns:
            Dictionary with buffer statistics
        """
        buffer_duration = 0.0
        if self.first_chunk_time is not None:
            buffer_duration = time.time() - self.first_chunk_time
            
        has_webm_header = any(self._is_webm_header(chunk) for chunk in self.chunks)
        
        return {
            'chunk_count': len(self.chunks),
            'total_size': self.total_size,
            'buffer_duration': buffer_duration,
            'has_webm_header': has_webm_header,
            'is_ready': self.is_ready()
        }

    def _is_webm_header(self, chunk: bytes) -> bool:
        """
        Check if chunk contains WebM header.
        
        Args:
            chunk: Audio chunk bytes
            
        Returns:
            True if chunk starts with WebM header magic bytes
        """
        return chunk.startswith(b'\x1a\x45\xdf\xa3')