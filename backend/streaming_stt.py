import asyncio
import logging
import threading
import queue
from typing import Dict, Optional, Callable, Any
from google.cloud import speech
from google.api_core import exceptions as gcp_exceptions


class StreamingSpeechToText:
    """
    Google Cloud streaming Speech-to-Text service for real-time audio processing.
    
    This service handles continuous audio streams from WebSocket connections,
    sending chunks to Google Cloud STT streaming API and returning transcripts
    in real-time as they become available.
    """
    
    def __init__(self, client: Optional[speech.SpeechClient] = None):
        """
        Initialize streaming STT service.
        
        Args:
            client: Optional Google Cloud Speech client for testing
        """
        self.client = client or speech.SpeechClient()
        self.language_code = 'nl-NL'
        self.sample_rate = 16000
        
        # Streaming state
        self.is_streaming = False
        self._audio_queue = queue.Queue()
        self._request_stream = None
        self._response_stream = None
        self._streaming_task = None
        
        # Callbacks
        self._transcript_callback = None
        self._error_callback = None
        
        self._logger = logging.getLogger(__name__)

    async def start_streaming(self, 
                             transcript_callback: Callable,
                             error_callback: Optional[Callable] = None):
        """
        Start streaming recognition session.
        
        Args:
            transcript_callback: Async function called with (transcript, is_final)
            error_callback: Optional async function called with exceptions
        """
        if self.is_streaming:
            self._logger.warning("Streaming already active, stopping previous session")
            await self.stop_streaming()
        
        self._transcript_callback = transcript_callback
        self._error_callback = error_callback
        
        try:
            # Configure streaming recognition
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                sample_rate_hertz=16000,  # CRITICAL FIX: Required even for ENCODING_UNSPECIFIED
                language_code=self.language_code,
                enable_automatic_punctuation=True,
                model="latest_short",
                audio_channel_count=1,
            )
            
            streaming_config = speech.StreamingRecognitionConfig(
                config=config,
                interim_results=True,  # Get partial results
                single_utterance=False,  # Continuous streaming
            )
            
            # Create request generator  
            self._request_stream = self._create_request_stream(streaming_config)
            
            # Start streaming recognition
            self._response_stream = self.client.streaming_recognize(self._request_stream)
            
            # Start background task to handle responses
            self._streaming_task = asyncio.create_task(self._process_responses())
            
            self.is_streaming = True
            self._logger.info("Streaming STT session started")
            
        except Exception as e:
            self._logger.error(f"Failed to start streaming STT: {e}")
            if self._error_callback:
                await self._error_callback(e)
            raise

    async def send_audio_chunk(self, audio_chunk: bytes):
        """
        Send audio chunk to streaming recognition.
        
        Args:
            audio_chunk: Raw audio data from browser
        """
        if not self.is_streaming:
            self._logger.warning("Cannot send audio - streaming not active")
            return
        
        try:
            # Add to queue for request generator
            self._audio_queue.put(audio_chunk, block=False)
            self._logger.debug(f"Queued audio chunk: {len(audio_chunk)} bytes")
            
        except queue.Full:
            self._logger.error("Audio queue full, dropping chunk")

    async def stop_streaming(self):
        """Stop streaming recognition session."""
        if not self.is_streaming:
            return
        
        self.is_streaming = False
        
        try:
            # Signal end of stream
            self._audio_queue.put(None, block=False)
            
            # Wait for streaming task to complete
            if self._streaming_task:
                await asyncio.wait_for(self._streaming_task, timeout=5.0)
                
        except asyncio.TimeoutError:
            self._logger.warning("Streaming task did not complete within timeout")
        except Exception as e:
            self._logger.error(f"Error stopping streaming: {e}")
        finally:
            self._cleanup_streaming_resources()
            self._logger.info("Streaming STT session stopped")

    def _create_request_stream(self, streaming_config):
        """
        Create request generator for streaming recognition.
        
        Args:
            streaming_config: Google Cloud streaming configuration
            
        Yields:
            StreamingRecognizeRequest objects
        """
        # First request contains the configuration
        yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
        
        # Subsequent requests contain audio data
        while self.is_streaming:
            try:
                # Get audio chunk from queue (blocking with timeout)
                audio_chunk = self._audio_queue.get(timeout=1.0)
                
                if audio_chunk is None:
                    # End of stream signal
                    break
                    
                yield speech.StreamingRecognizeRequest(audio_content=audio_chunk)
                
            except queue.Empty:
                # Timeout - continue if still streaming
                continue
            except Exception as e:
                self._logger.error(f"Error in request stream: {e}")
                break

    async def _process_responses(self):
        """Process streaming recognition responses in background task."""
        try:
            # Convert sync iterator to async
            loop = asyncio.get_event_loop()
            
            for response in self._response_stream:
                if not self.is_streaming:
                    break
                
                # Process each result in the response
                for result in response.results:
                    if result.alternatives:
                        transcript = result.alternatives[0].transcript
                        is_final = result.is_final
                        confidence = getattr(result.alternatives[0], 'confidence', 0.0)
                        
                        self._logger.debug(f"STT result: '{transcript}' (final: {is_final}, confidence: {confidence:.2f})")
                        
                        # Call transcript callback
                        if self._transcript_callback:
                            await self._transcript_callback(transcript, is_final, confidence)
                
        except gcp_exceptions.GoogleAPIError as e:
            self._logger.error(f"Google Cloud STT API error: {e}")
            if self._error_callback:
                await self._error_callback(e)
        except Exception as e:
            self._logger.error(f"Unexpected error in response processing: {e}")
            if self._error_callback:
                await self._error_callback(e)

    def _cleanup_streaming_resources(self):
        """Clean up streaming resources."""
        self._request_stream = None
        self._response_stream = None
        self._streaming_task = None
        self._transcript_callback = None
        self._error_callback = None
        
        # Clear audio queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break


class StreamManager:
    """
    Manager for multiple concurrent streaming STT sessions.
    
    Handles creating, managing, and cleaning up streaming sessions
    for different WebSocket connections/stream IDs.
    """
    
    def __init__(self):
        """Initialize stream manager."""
        self.streams: Dict[str, StreamingSpeechToText] = {}
        self.total_created = 0
        self._logger = logging.getLogger(__name__)

    async def create_stream(self, 
                           stream_id: str,
                           transcript_callback: Callable,
                           error_callback: Optional[Callable] = None) -> bool:
        """
        Create new streaming session for stream ID.
        
        Args:
            stream_id: Unique identifier for the stream
            transcript_callback: Async function for transcript results
            error_callback: Optional async function for errors
            
        Returns:
            True if stream created successfully
        """
        if stream_id in self.streams:
            self._logger.warning(f"Stream {stream_id} already exists, replacing")
            await self.close_stream(stream_id)
        
        try:
            streaming_stt = StreamingSpeechToText()
            await streaming_stt.start_streaming(transcript_callback, error_callback)
            
            self.streams[stream_id] = streaming_stt
            self.total_created += 1
            
            self._logger.info(f"Created streaming session for {stream_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to create stream {stream_id}: {e}")
            return False

    async def send_audio(self, stream_id: str, audio_chunk: bytes):
        """
        Send audio chunk to specific stream.
        
        Args:
            stream_id: Target stream identifier
            audio_chunk: Audio data to send
        """
        if stream_id not in self.streams:
            self._logger.debug(f"Stream {stream_id} not found, ignoring audio")
            return
        
        try:
            await self.streams[stream_id].send_audio_chunk(audio_chunk)
        except Exception as e:
            self._logger.error(f"Error sending audio to stream {stream_id}: {e}")

    async def close_stream(self, stream_id: str):
        """
        Close streaming session for stream ID.
        
        Args:
            stream_id: Stream identifier to close
        """
        if stream_id not in self.streams:
            self._logger.debug(f"Stream {stream_id} not found for closing")
            return
        
        try:
            await self.streams[stream_id].stop_streaming()
            del self.streams[stream_id]
            self._logger.info(f"Closed streaming session for {stream_id}")
            
        except Exception as e:
            self._logger.error(f"Error closing stream {stream_id}: {e}")

    async def close_all_streams(self):
        """Close all active streaming sessions."""
        stream_ids = list(self.streams.keys())
        for stream_id in stream_ids:
            await self.close_stream(stream_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stream manager.
        
        Returns:
            Dictionary with stream statistics
        """
        return {
            'active_streams': len(self.streams),
            'total_streams_created': self.total_created,
            'stream_ids': list(self.streams.keys())
        }


# Global stream manager instance
stream_manager = StreamManager()