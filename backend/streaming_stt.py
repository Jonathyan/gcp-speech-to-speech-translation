import asyncio
import logging
import queue
import threading
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
        
        # Start processing in background thread (Google Cloud Speech is sync)
        self._streaming_thread = threading.Thread(target=self._stream_worker)
        self._streaming_thread.start()
        
        self._logger.info("Simple streaming STT started")

    def send_audio_chunk(self, audio_chunk: bytes):
        """Send audio chunk - non-blocking."""
        if not self.is_streaming:
            return
        try:
            self._audio_queue.put(audio_chunk, block=False)
            self._logger.debug(f"📥 Audio chunk queued: {len(audio_chunk)} bytes")
        except queue.Full:
            self._logger.warning("Audio queue full, dropping chunk")

    async def stop_streaming(self):
        """Stop streaming."""
        if not self.is_streaming:
            return
            
        self.is_streaming = False
        self._audio_queue.put(None)  # Signal stop
        
        if self._streaming_thread:
            self._streaming_thread.join(timeout=2.0)
        
        self._logger.info("Simple streaming STT stopped")

    def _stream_worker(self):
        """Background thread worker - handles Google Cloud Speech streaming."""
        try:
            # Create streaming config - use LINEAR16 for raw audio data
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code='nl-NL',
                enable_automatic_punctuation=True,
                model="latest_short",
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
                        chunk = self._audio_queue.get(timeout=1.0)
                        if chunk is None:  # Stop signal
                            break
                        yield speech.StreamingRecognizeRequest(audio_content=chunk)
                    except queue.Empty:
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