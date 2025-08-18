import asyncio
import logging
from typing import Callable, Optional
from google.cloud import speech


class BatchSpeechToText:
    """
    Batch STT - accumulate audio chunks and process them in batches.
    Temporary solution to bypass streaming API issues.
    """
    
    def __init__(self):
        self.client = speech.SpeechClient()
        self.is_active = False
        self._audio_buffer = bytearray()
        self._transcript_callback = None
        self._batch_size = 32768  # 32KB batch size
        self._batch_count = 0
        self._logger = logging.getLogger(__name__)

    async def start_processing(self, transcript_callback: Callable):
        """Start batch processing."""
        self._transcript_callback = transcript_callback
        self.is_active = True
        self._logger.info("Batch STT processing started")

    def send_audio_chunk(self, audio_chunk: bytes):
        """Accumulate audio chunks."""
        if not self.is_active:
            return
            
        self._audio_buffer.extend(audio_chunk)
        
        # Process batch when buffer is large enough
        if len(self._audio_buffer) >= self._batch_size:
            asyncio.create_task(self._process_batch())

    async def _process_batch(self):
        """Process accumulated audio as batch."""
        if len(self._audio_buffer) == 0:
            return
            
        try:
            # Get current buffer and reset
            audio_data = bytes(self._audio_buffer)
            self._audio_buffer.clear()
            self._batch_count += 1
            
            # Configure recognition
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                sample_rate_hertz=16000,
                language_code='nl-NL',
                enable_automatic_punctuation=True,
                model="latest_short",
                audio_channel_count=1,
            )
            
            audio = speech.RecognitionAudio(content=audio_data)
            
            # Call batch STT API directly
            response = self.client.recognize(config=config, audio=audio)
            
            # Process results
            for result in response.results:
                if result.alternatives:
                    transcript = result.alternatives[0].transcript.strip()
                    confidence = result.alternatives[0].confidence
                    
                    if transcript:
                        self._logger.info(f"🎤 Batch #{self._batch_count}: '{transcript}' (confidence: {confidence:.2f})")
                        
                        # Call transcript callback
                        if self._transcript_callback:
                            await self._transcript_callback(transcript, True, confidence)
                            
        except Exception as e:
            self._logger.error(f"Batch STT error: {e}")

    async def stop_processing(self):
        """Stop processing and process final batch."""
        self.is_active = False
        
        # Process any remaining audio
        if len(self._audio_buffer) > 1024:  # Only if significant audio remains
            await self._process_batch()
            
        self._logger.info("Batch STT processing stopped")


# Global instance
batch_stt = BatchSpeechToText()