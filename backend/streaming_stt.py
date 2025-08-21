import asyncio
import logging
import queue
import threading
import time
from typing import Callable, Optional
from google.cloud import speech
from google.api_core import exceptions as gcp_exceptions


class SimpleStreamingSpeechToText:
    """
    Simplified streaming STT - direct Google Cloud Speech API calls only.
    No wrappers, no abstractions, no complex error handling.
    """
    
    def __init__(self):
        self.client = speech.SpeechClient()
        self._logger = logging.getLogger(__name__)
        
        # Debug logging
        self._logger.info(f"🔍 INIT DEBUG: Created client type = {type(self.client)}")
        self._logger.info(f"🔍 INIT DEBUG: Client module = {self.client.__class__.__module__}")
        self._logger.info(f"🔍 INIT DEBUG: Client class = {self.client.__class__.__name__}")
        
        self.is_streaming = False
        self._audio_queue = queue.Queue()
        self._streaming_thread = None
        self._transcript_callback = None
        self._error_callback = None
        self._main_loop = None  # Store main event loop reference
        
        # 5-minute stream restart tracking
        self._stream_start_time = None
        self._max_stream_duration = 280  # 4:40 mark (20s safety buffer before 5min limit)
        self._restart_in_progress = False

    async def start_streaming(self, 
                             transcript_callback: Callable,
                             error_callback: Optional[Callable] = None):
        """Start streaming recognition - simplified."""
        if self.is_streaming:
            await self.stop_streaming()
        
        self._transcript_callback = transcript_callback
        self._error_callback = error_callback
        self._main_loop = asyncio.get_running_loop()  # Store current event loop
        self.is_streaming = True
        self._stream_start_time = time.time()  # Track stream start time
        self._restart_in_progress = False
        
        # Start processing in background thread (Google Cloud Speech is sync)
        self._streaming_thread = threading.Thread(target=self._stream_worker)
        self._streaming_thread.start()
        
        self._logger.info(f"Simple streaming STT started (max duration: {self._max_stream_duration}s)")

    def send_audio_chunk(self, audio_chunk: bytes):
        """Send audio chunk - non-blocking."""
        if not self.is_streaming:
            self._logger.warning("🚫 Received audio chunk but streaming is not active")
            return
            
        # Check if stream restart is needed (but not if already in progress)
        if not self._restart_in_progress and self._should_restart_stream():
            self._logger.info("🔄 Stream duration limit approaching, scheduling restart...")
            # Schedule restart asynchronously to avoid blocking audio processing
            if self._main_loop:
                asyncio.run_coroutine_threadsafe(self._restart_stream(), self._main_loop)
            
        try:
            self._audio_queue.put(audio_chunk, block=False)
            # Enhanced logging for debugging
            queue_size = self._audio_queue.qsize()
            self._logger.info(f"📥 Audio chunk queued: {len(audio_chunk)} bytes (queue size: {queue_size})")
            
            # Log chunk timing to help debug Google Cloud Speech timeouts
            import time
            current_time = time.time()
            if hasattr(self, '_last_chunk_time'):
                chunk_gap = (current_time - self._last_chunk_time) * 1000  # ms
                if chunk_gap > 500:  # Log gaps longer than 500ms
                    self._logger.warning(f"⏰ Large gap between chunks: {chunk_gap:.1f}ms")
            self._last_chunk_time = current_time
            
        except queue.Full:
            self._logger.error("❌ Audio queue full, dropping chunk - this will cause Speech API timeout!")
            # Try to clear some older chunks if queue is full
            try:
                for _ in range(3):  # Remove up to 3 old chunks
                    if not self._audio_queue.empty():
                        self._audio_queue.get(block=False)
                # Try to add the new chunk after clearing space
                self._audio_queue.put(audio_chunk, block=False)
                self._logger.info("✅ Recovered from queue full by clearing old chunks")
            except:
                self._logger.error("❌ Failed to recover from full queue")

    async def stop_streaming(self):
        """Stop streaming."""
        if not self.is_streaming:
            return
            
        self.is_streaming = False
        self._audio_queue.put(None)  # Signal stop
        
        if self._streaming_thread:
            self._streaming_thread.join(timeout=2.0)
        
        self._stream_start_time = None
        self._restart_in_progress = False
        self._logger.info("Simple streaming STT stopped")

    def _should_restart_stream(self) -> bool:
        """Check if stream should be restarted due to duration limit."""
        if not self._stream_start_time:
            return False
            
        current_duration = time.time() - self._stream_start_time
        should_restart = current_duration >= self._max_stream_duration
        
        if should_restart:
            self._logger.info(f"⏰ Stream duration: {current_duration:.1f}s >= {self._max_stream_duration}s - restart needed")
        
        return should_restart

    async def _restart_stream(self):
        """Gracefully restart the streaming connection before hitting 5-minute limit."""
        if self._restart_in_progress:
            self._logger.debug("Restart already in progress, skipping")
            return
            
        self._restart_in_progress = True
        
        try:
            self._logger.info("🔄 Starting graceful stream restart...")
            
            # Store current callbacks for new stream
            transcript_callback = self._transcript_callback
            error_callback = self._error_callback
            
            # Stop current stream gracefully
            await self.stop_streaming()
            
            # Small delay to ensure clean shutdown
            await asyncio.sleep(0.1)
            
            # Start new stream with same callbacks
            if transcript_callback:
                await self.start_streaming(transcript_callback, error_callback)
                self._logger.info("✅ Stream restart completed successfully")
            else:
                self._logger.warning("No transcript callback available for restart")
                
        except Exception as e:
            self._logger.error(f"❌ Stream restart failed: {e}")
            # Try to notify error callback
            if self._error_callback and self._main_loop:
                try:
                    asyncio.run_coroutine_threadsafe(self._error_callback(e), self._main_loop)
                except Exception as callback_error:
                    self._logger.error(f"❌ Error callback during restart failed: {callback_error}")
        finally:
            self._restart_in_progress = False

    def _stream_worker(self):
        """Background thread worker - handles Google Cloud Speech streaming."""
        try:
            # Create streaming config - optimized for continuous speech
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code='nl-NL',
                enable_automatic_punctuation=True,
                model="latest_long",  # Better for continuous speech
                use_enhanced=True,    # Better accuracy (slight cost increase)
                audio_channel_count=1,
            )
            
            streaming_config = speech.StreamingRecognitionConfig(
                config=config,
                interim_results=True,
                single_utterance=False,
                # Note: VoiceActivityTimeout might not be available in v1 API
                # Removed timeout config to fix the attribute error
            )

            # Create audio request generator - only audio data, no config
            def audio_request_generator():
                # Only audio requests, no config
                while self.is_streaming:
                    try:
                        # Reduced timeout to 0.2s to prevent long gaps that cause STT timeouts
                        chunk = self._audio_queue.get(timeout=0.2)
                        if chunk is None:  # Stop signal
                            break
                        yield speech.StreamingRecognizeRequest(audio_content=chunk)
                    except queue.Empty:
                        # Send a small silence chunk to keep the stream alive
                        # 16kHz, 16-bit mono, 0.1 second of silence = 3200 bytes
                        silence_chunk = b'\x00' * 3200
                        yield speech.StreamingRecognizeRequest(audio_content=silence_chunk)
                        continue

            # Call Google Cloud Speech API - SpeechHelpers expects config and requests separately
            responses = self.client.streaming_recognize(
                config=streaming_config,
                requests=audio_request_generator()
            )
            
            # Process responses
            for response in responses:
                if not self.is_streaming:
                    break
                    
                for result in response.results:
                    if result.alternatives:
                        transcript = result.alternatives[0].transcript
                        is_final = result.is_final
                        confidence = getattr(result.alternatives[0], 'confidence', 1.0)
                        
                        # Only process FINAL transcripts to avoid delays from partial results
                        if self._transcript_callback and is_final and self._main_loop:
                            try:
                                # Use the stored main event loop for async callback execution
                                asyncio.run_coroutine_threadsafe(
                                    self._transcript_callback(transcript, is_final, confidence),
                                    self._main_loop
                                )
                                self._logger.info(f"📝 Final transcript scheduled: '{transcript}'")
                            except Exception as e:
                                self._logger.error(f"❌ Callback scheduling failed: {e}")
                        elif self._transcript_callback and not is_final:
                            # Log partial transcripts but don't process them (causes delays)
                            self._logger.debug(f"⏸️  Partial transcript ignored: '{transcript}'")
                            
        except Exception as e:
            self._logger.error(f"Streaming STT error: {e}")
            if self._error_callback and self._main_loop:
                try:
                    asyncio.run_coroutine_threadsafe(self._error_callback(e), self._main_loop)
                except Exception as callback_error:
                    self._logger.error(f"❌ Error callback scheduling failed: {callback_error}")


# Global instance - keep it simple
streaming_stt = SimpleStreamingSpeechToText()