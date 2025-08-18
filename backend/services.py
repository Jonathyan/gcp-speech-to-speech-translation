import asyncio
import logging
import random
import io
import subprocess
import tempfile
import os
from typing import Optional
from .audio_buffer import WebMChunkBuffer
from .streaming_stt import stream_manager
# Enhanced STT service will be imported when needed to avoid circular imports

# Configureer basis logging om de flow te kunnen volgen
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def mock_speech_to_text(audio_chunk: bytes) -> str:
    """
    Simuleert een Speech-to-Text API-aanroep.

    Wacht 50ms en geeft een vaste tekst terug, met een kans op een fout.
    """
    logging.info("STT: Audio chunk ontvangen, start verwerking...")
    
    # Debug browser audio format
    convert_audio_to_linear16(audio_chunk)
    
    if random.random() < 0.10:  # 10% kans op een fout
        logging.error("STT: Gesimuleerde API-fout!")
        raise Exception("STT API Error")

    await asyncio.sleep(0.05)  # Simuleer 50ms netwerklatentie
    result = "mocked dutch text"
    logging.info(f"STT: Verwerking voltooid. Resultaat: '{result}'")
    return result


async def pass_through_speech_to_text(audio_chunk: bytes) -> str:
    """
    Pass-through STT functie voor isolatie testing.
    Simuleert succesvolle STT zonder echte API call.
    """
    logging.info("STT: Pass-through mode - hardcoded result")
    await asyncio.sleep(0.05)  # Behoud timing consistency
    result = "hallo wereld"
    logging.info(f"STT: Pass-through voltooid. Resultaat: '{result}'")
    return result


def convert_audio_to_linear16(audio_chunk: bytes) -> bytes:
    """
    Convert browser audio to LINEAR16 PCM format using ffmpeg subprocess.
    """
    try:
        logging.info(f"Audio conversion: {len(audio_chunk)} bytes received")
        
        # Inspect audio format
        header = audio_chunk[:16] if len(audio_chunk) >= 16 else audio_chunk
        header_hex = header.hex()
        logging.info(f"Audio header: {header_hex}")
        
        # Detect format
        format_detected = "unknown"
        if audio_chunk.startswith(b'\x1a\x45\xdf\xa3'):
            format_detected = "webm"
        elif audio_chunk.startswith(b'RIFF'):
            format_detected = "wav"
        elif len(audio_chunk) > 4 and audio_chunk[4:8] == b'ftyp':
            format_detected = "mp4"
        
        logging.info(f"Detected format: {format_detected}")
        
        # Skip conversion for very small chunks - likely incomplete
        if len(audio_chunk) < 1024:
            logging.warning(f"Skipping conversion for small chunk: {len(audio_chunk)} bytes")
            return audio_chunk
        
        import subprocess
        
        # Use more robust ffmpeg command for all formats
        if format_detected == "webm":
            # For WebM format, don't specify input format - let ffmpeg detect
            cmd = [
                'ffmpeg',
                '-hide_banner',      # Reduce output noise
                '-i', 'pipe:0',      # Input from stdin
                '-vn',               # No video (audio only)
                '-acodec', 'pcm_s16le',  # Output codec: PCM signed 16-bit little-endian
                '-ar', '16000',      # Sample rate 16kHz
                '-ac', '1',          # Mono (1 channel)
                '-f', 's16le',       # Output format container
                '-loglevel', 'warning',  # Show warnings and errors
                'pipe:1'             # Output to stdout
            ]
        elif format_detected == "wav":
            # For WAV format
            cmd = [
                'ffmpeg',
                '-hide_banner',
                '-f', 'wav',
                '-i', 'pipe:0',
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1', 
                '-f', 's16le',
                '-loglevel', 'warning',
                'pipe:1'
            ]
        else:
            # For unknown formats, let ffmpeg auto-detect
            cmd = [
                'ffmpeg',
                '-hide_banner',
                '-i', 'pipe:0',
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-f', 's16le',
                '-loglevel', 'warning',
                'pipe:1'
            ]
        
        # Run ffmpeg conversion
        result = subprocess.run(
            cmd,
            input=audio_chunk,
            capture_output=True,
            timeout=10  # Increased timeout for WebM processing
        )
        
        if result.returncode == 0 and result.stdout:
            logging.info(f"Audio converted successfully: {len(audio_chunk)} → {len(result.stdout)} bytes (LINEAR16)")
            return result.stdout
        else:
            # Log detailed error information
            stderr_text = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "No error output"
            stdout_text = result.stdout.decode('utf-8', errors='ignore') if result.stdout else "No stdout"
            logging.error(f"ffmpeg conversion failed:")
            logging.error(f"  Command: {' '.join(cmd)}")
            logging.error(f"  Return code: {result.returncode}")
            logging.error(f"  Stderr: {stderr_text[:500]}")  # First 500 chars of error
            logging.error(f"  Stdout: {stdout_text[:200]}")  # First 200 chars of stdout
            logging.error(f"  Input size: {len(audio_chunk)} bytes")
            
            # For debugging, let's try a simple ffmpeg test to see what's wrong
            if result.returncode == 183:
                logging.warning("Return code 183: Invalid input format - will use raw audio for Google Cloud auto-detection")
            elif result.returncode == 1:
                logging.warning("ffmpeg general error - will use raw audio for Google Cloud auto-detection")
            else:
                logging.warning(f"ffmpeg failed with return code {result.returncode} - using raw audio")
                
            # Return original audio - Google Cloud will handle format detection
            return audio_chunk
            
    except subprocess.TimeoutExpired:
        logging.error("Audio conversion timeout (10s exceeded)")
        return audio_chunk
    except FileNotFoundError:
        logging.warning("ffmpeg not found - install with: brew install ffmpeg")
        return audio_chunk
    except Exception as e:
        logging.error(f"Audio conversion error: {e}")
        return audio_chunk

async def real_speech_to_text(audio_chunk: bytes) -> str:
    """
    Production-ready Google Cloud Speech-to-Text API with Phase 2 WAV support.
    """
    import os
    from google.cloud import speech
    from google.api_core import exceptions as gcp_exceptions
    from tenacity import retry, stop_after_attempt, wait_exponential
    
    # Configuratie via environment variables
    sample_rate = int(os.getenv('STT_SAMPLE_RATE', '16000'))
    language_code = os.getenv('STT_LANGUAGE_CODE', 'nl-NL')
    timeout_seconds = float(os.getenv('STT_TIMEOUT_S', '10.0'))
    
    logging.info(f"STT: Real API call - {len(audio_chunk)} bytes, {language_code}")
    
    # PHASE 2 SIMPLIFIED: Just use the audio as-is and assume it's LINEAR16 PCM
    # This eliminates all format detection complexity
    logging.info(f"Phase 2: Processing audio as LINEAR16 PCM - {len(audio_chunk)} bytes")
    
    # DEBUGGING: Check audio data characteristics
    if len(audio_chunk) >= 16:
        header_hex = audio_chunk[:16].hex()
        logging.info(f"Audio header debug: {header_hex}")
        
        # Check if this looks like WAV data
        if audio_chunk.startswith(b'RIFF'):
            logging.info("Detected RIFF WAV header")
        else:
            # Check for patterns in raw audio data
            import struct
            try:
                # Sample first few 16-bit values
                samples = struct.unpack('<8h', audio_chunk[:16])
                logging.info(f"First 8 PCM samples: {samples}")
                
                # Check if all samples are zero (silence)
                if all(s == 0 for s in samples[:8]):
                    logging.warning("Audio appears to be silence - all zero samples")
                else:
                    logging.info("Audio contains non-zero samples - should be processable")
            except:
                logging.warning("Could not parse audio as 16-bit PCM")
    
    # Check minimum audio duration for meaningful STT processing
    # 32,768 bytes at 16kHz 16-bit = ~1 second of audio
    min_audio_bytes = 32000  # ~1 second minimum
    if len(audio_chunk) < min_audio_bytes:
        logging.warning(f"Audio chunk too short for STT: {len(audio_chunk)} bytes < {min_audio_bytes} bytes minimum")
        raise Exception(f"Audio chunk too short: {len(audio_chunk)} bytes")
    
    converted_audio = audio_chunk
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, max=2),
        reraise=True
    )
    async def _recognize_with_retry():
        try:
            client = speech.SpeechClient()
            
            # SIMPLIFIED: Always try LINEAR16 first for Phase 2 audio
            # This should work with both WAV files and raw PCM data from Web Audio API
            encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
            config_sample_rate = 16000
            logging.info("Phase 2: Using LINEAR16 encoding for all audio (simplified approach)")
            
            # Build config conditionally based on whether we specify sample rate
            config_params = {
                "encoding": encoding,
                "language_code": language_code,
                "enable_automatic_punctuation": True,
                "model": "latest_short",
                "audio_channel_count": 1,  # Explicitly set mono
            }
            
            # CRITICAL FIX: Always add sample_rate_hertz - required even for ENCODING_UNSPECIFIED
            if config_sample_rate is not None:
                config_params["sample_rate_hertz"] = config_sample_rate
            else:
                # Fallback: Use 16kHz for unknown formats (Google Cloud STT requirement)
                config_params["sample_rate_hertz"] = 16000
                logging.warning("No sample rate specified, defaulting to 16kHz for STT compatibility")
                
            config = speech.RecognitionConfig(**config_params)
            
            audio = speech.RecognitionAudio(content=converted_audio)
            
            # Synchronous recognize met timeout
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: client.recognize(
                    config=config, 
                    audio=audio,
                    timeout=timeout_seconds
                )
            )
            
            if response.results and response.results[0].alternatives:
                transcript = response.results[0].alternatives[0].transcript.strip()
                confidence = response.results[0].alternatives[0].confidence
                logging.info(f"STT: Success - '{transcript}' (confidence: {confidence:.2f})")
                return transcript
            else:
                raise Exception("No transcription results")
                
        except gcp_exceptions.GoogleAPIError as e:
            logging.error(f"STT: Google API error - {e}")
            raise Exception(f"Google Cloud STT API Error: {e}")
        except Exception as e:
            logging.error(f"STT: Unexpected error - {e}")
            raise Exception(f"STT Error: {e}")
    
    try:
        return await _recognize_with_retry()
    except Exception as e:
        logging.error(f"STT: Final failure after retries - {e}")
        # Raise the error instead of returning fallback
        raise


async def real_translation(text: str) -> str:
    """
    Production-ready Google Cloud Translation API v2 met resilience patterns.
    """
    import os
    from google.cloud import translate_v2 as translate
    from google.api_core import exceptions as gcp_exceptions
    from tenacity import retry, stop_after_attempt, wait_exponential
    
    # Configuratie via environment variables
    source_language = os.getenv('TRANSLATION_SOURCE_LANGUAGE', 'nl')
    target_language = os.getenv('TRANSLATION_TARGET_LANGUAGE', 'en')
    timeout_seconds = float(os.getenv('TRANSLATION_TIMEOUT_S', '10.0'))
    
    logging.info(f"Translation: Real API call - '{text}' ({source_language} → {target_language})")
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, max=2),
        reraise=True
    )
    async def _translate_with_retry():
        try:
            client = translate.Client()
            
            # Async executor pattern voor API call
            loop = asyncio.get_event_loop()
            
            def _sync_translate():
                return client.translate(
                    text,
                    source_language=source_language,
                    target_language=target_language
                )
            
            # Run in executor met timeout
            result = await asyncio.wait_for(
                loop.run_in_executor(None, _sync_translate),
                timeout=timeout_seconds
            )
            
            translated_text = result['translatedText'].strip()
            detected_language = result.get('detectedSourceLanguage', source_language)
            
            logging.info(f"Translation: Success - '{translated_text}' (detected: {detected_language})")
            return translated_text
                
        except gcp_exceptions.GoogleAPIError as e:
            logging.error(f"Translation: Google API error - {e}")
            raise Exception(f"Google Cloud Translation API Error: {e}")
        except asyncio.TimeoutError:
            logging.error(f"Translation: Timeout after {timeout_seconds}s")
            raise Exception(f"Translation timeout after {timeout_seconds}s")
        except Exception as e:
            logging.error(f"Translation: Unexpected error - {e}")
            raise Exception(f"Translation Error: {e}")
    
    try:
        return await _translate_with_retry()
    except Exception as e:
        logging.error(f"Translation: Final failure after retries - {e}")
        raise


async def mock_translation(text: str) -> str:
    """
    Simuleert een Translation API-aanroep.

    Wacht 50ms en geeft een vaste vertaling terug, met een kans op een fout.
    """
    logging.info(f"Translate: Tekst ontvangen: '{text}', start vertaling...")
    if random.random() < 0.05:  # 5% kans op een fout
        logging.error("Translate: Gesimuleerde API-fout!")
        raise Exception("Translation API Error")

    await asyncio.sleep(0.05)  # Simuleer 50ms netwerklatentie
    result = "mocked english translation"
    logging.info(f"Translate: Vertaling voltooid. Resultaat: '{result}'")
    return result


async def real_text_to_speech(text: str) -> bytes:
    """
    Production-ready Google Cloud Text-to-Speech API met resilience patterns.
    """
    import os
    from google.cloud import texttospeech
    from google.api_core import exceptions as gcp_exceptions
    from tenacity import retry, stop_after_attempt, wait_exponential
    
    # Configuratie via environment variables
    language_code = os.getenv('TTS_LANGUAGE_CODE', 'en-US')
    voice_name = os.getenv('TTS_VOICE_NAME', 'en-US-Wavenet-D')
    voice_gender = os.getenv('TTS_VOICE_GENDER', 'NEUTRAL')
    audio_format = os.getenv('TTS_AUDIO_FORMAT', 'MP3')
    timeout_seconds = float(os.getenv('TTS_TIMEOUT_S', '10.0'))
    
    logging.info(f"TTS: Real API call - '{text}' ({language_code}, {voice_name}, {audio_format})")
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, max=2),
        reraise=True
    )
    async def _synthesize_with_retry():
        try:
            client = texttospeech.TextToSpeechClient()
            
            # Configure synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Configure voice parameters
            gender_mapping = {
                'MALE': texttospeech.SsmlVoiceGender.MALE,
                'FEMALE': texttospeech.SsmlVoiceGender.FEMALE,
                'NEUTRAL': texttospeech.SsmlVoiceGender.NEUTRAL
            }
            
            voice_params = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name,
                ssml_gender=gender_mapping.get(voice_gender, texttospeech.SsmlVoiceGender.NEUTRAL)
            )
            
            # Configure audio format
            format_mapping = {
                'MP3': texttospeech.AudioEncoding.MP3,
                'LINEAR16': texttospeech.AudioEncoding.LINEAR16,
                'OGG_OPUS': texttospeech.AudioEncoding.OGG_OPUS
            }
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=format_mapping.get(audio_format, texttospeech.AudioEncoding.MP3)
            )
            
            # Async executor pattern voor API call
            loop = asyncio.get_event_loop()
            
            def _sync_synthesize():
                return client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice_params,
                    audio_config=audio_config
                )
            
            # Run in executor met timeout
            response = await asyncio.wait_for(
                loop.run_in_executor(None, _sync_synthesize),
                timeout=timeout_seconds
            )
            
            audio_content = response.audio_content
            audio_size_kb = len(audio_content) / 1024
            
            logging.info(f"TTS: Success - {len(audio_content)} bytes ({audio_size_kb:.1f}KB) audio generated")
            return audio_content
                
        except gcp_exceptions.GoogleAPIError as e:
            logging.error(f"TTS: Google API error - {e}")
            raise Exception(f"Google Cloud TTS API Error: {e}")
        except asyncio.TimeoutError:
            logging.error(f"TTS: Timeout after {timeout_seconds}s")
            raise Exception(f"TTS timeout after {timeout_seconds}s")
        except Exception as e:
            logging.error(f"TTS: Unexpected error - {e}")
            raise Exception(f"TTS Error: {e}")
    
    try:
        return await _synthesize_with_retry()
    except Exception as e:
        logging.error(f"TTS: Final failure after retries - {e}")
        raise


async def mock_text_to_speech(text: str) -> bytes:
    """
    Simuleert een Text-to-Speech API-aanroep.
    
    Geeft een tekst-marker terug die de frontend zal herkennen als test audio.
    De frontend zal dan een hoorbare beep genereren.
    """
    logging.info(f"TTS: Tekst ontvangen: '{text}', start audiosynthese...")
    if random.random() < 0.08:  # 8% kans op een fout
        logging.error("TTS: Gesimuleerde API-fout!")
        raise Exception("TTS API Error")

    await asyncio.sleep(0.05)  # Simuleer 50ms netwerklatentie
    
    # Return a special marker that the frontend will recognize and convert to an audible beep
    # This ensures the user will hear something audible for testing
    result = b"TEST_AUDIO_BEEP_MARKER:" + text.encode('utf-8')
    
    logging.info(f"TTS: Mock audiosynthese voltooid. Test audio marker gegenereerd ({len(result)} bytes)")
    return result


class BufferedSpeechToText:
    """
    Buffered Speech-to-Text service that accumulates WebM chunks 
    before sending to Google Cloud for better recognition accuracy.
    """
    
    def __init__(self, 
                 buffer_duration: float = 2.0,
                 max_buffer_size: int = 500 * 1024,
                 timeout_seconds: float = 5.0,
                 stt_service = None):
        """
        Initialize buffered STT service.
        
        Args:
            buffer_duration: Minimum time to wait before processing buffer
            max_buffer_size: Maximum buffer size before forced processing  
            timeout_seconds: Maximum wait time before forcing processing
            stt_service: Optional mock STT service for testing
        """
        self.buffer = WebMChunkBuffer(
            min_duration_seconds=buffer_duration,
            max_buffer_size=max_buffer_size,
            timeout_seconds=timeout_seconds
        )
        self.stt_service = stt_service  # For testing
        
        self._logger = logging.getLogger(__name__)

    async def process_chunk(self, audio_chunk: bytes) -> Optional[str]:
        """
        Process an audio chunk, buffering until ready for STT.
        
        Args:
            audio_chunk: Raw audio chunk from MediaRecorder
            
        Returns:
            Transcription text if buffer is ready, None if still buffering
        """
        if not audio_chunk:
            return None
            
        # Add chunk to buffer
        self.buffer.add_chunk(audio_chunk)
        
        # Log buffer status
        stats = self.buffer.get_stats()
        self._logger.debug(f"Buffer stats: {stats}")
        
        # Check if buffer is ready for processing
        if self.buffer.is_ready():
            return await self._process_buffered_audio()
        
        return None  # Still buffering

    async def _process_buffered_audio(self) -> str:
        """
        Process the buffered audio through STT pipeline.
        
        Returns:
            Transcription text
        """
        combined_audio = self.buffer.get_combined_audio()
        stats = self.buffer.get_stats()
        
        self._logger.info(f"Processing buffered audio: {len(combined_audio)} bytes, "
                         f"{stats['chunk_count']} chunks, {stats['buffer_duration']:.1f}s duration")
        
        # Clear buffer before processing
        self.buffer.clear()
        
        try:
            # Use mock service if provided (for testing)
            if self.stt_service:
                return self.stt_service.recognize_audio(combined_audio)
            
            # Otherwise use real STT service
            return await real_speech_to_text(combined_audio)
            
        except Exception as e:
            self._logger.error(f"Buffered STT processing failed: {e}")
            raise


# Global buffered STT instance for the WebSocket handlers
_buffered_stt_service = BufferedSpeechToText(
    buffer_duration=2.0,  # Wait 2 seconds for complete audio
    max_buffer_size=300 * 1024,  # 300KB max buffer
    timeout_seconds=4.0   # Force processing after 4 seconds
)


async def buffered_speech_to_text(audio_chunk: bytes) -> Optional[str]:
    """
    Process audio chunk through enhanced buffered STT service.
    
    This is the main interface that WebSocket handlers should use
    for Phase 1 enhanced audio processing.
    
    Args:
        audio_chunk: Raw audio chunk from browser
        
    Returns:
        Transcription text if ready, None if still buffering
    """
    # Import here to avoid circular import
    from .enhanced_stt_service import enhanced_stt_service
    return await enhanced_stt_service.process_chunk(audio_chunk)


class StreamingSTTService:
    """
    Service wrapper for streaming Speech-to-Text functionality.
    
    Integrates Google Cloud streaming STT with the translation pipeline
    for real-time speech-to-speech translation.
    """
    
    def __init__(self):
        """Initialize streaming STT service."""
        self._logger = logging.getLogger(__name__)
        # Translation cache to avoid re-translating partial results
        self._translation_cache = {}

    async def create_stream(self, stream_id: str, broadcast_callback) -> bool:
        """
        Create new streaming STT session for WebSocket stream.
        
        Args:
            stream_id: Unique stream identifier 
            broadcast_callback: Async function to broadcast translated audio
            
        Returns:
            True if stream created successfully
        """
        async def on_transcript(transcript: str, is_final: bool, confidence: float):
            """Handle transcript results from streaming STT."""
            try:
                self._logger.info(f"[{stream_id}] STT: '{transcript}' (final: {is_final}, conf: {confidence:.2f})")
                
                # Only process final transcripts for translation
                if is_final and transcript.strip():
                    # Check cache to avoid re-translating
                    cache_key = transcript.strip().lower()
                    if cache_key in self._translation_cache:
                        translated_text = self._translation_cache[cache_key]
                        self._logger.debug(f"[{stream_id}] Using cached translation: '{translated_text}'")
                    else:
                        # Translate the text
                        translated_text = await real_translation(transcript)
                        self._translation_cache[cache_key] = translated_text
                    
                    # Generate speech audio
                    audio_content = await real_text_to_speech(translated_text)
                    
                    # Broadcast to listeners
                    await broadcast_callback(stream_id, audio_content)
                    
                    self._logger.info(f"[{stream_id}] Pipeline completed: '{transcript}' → '{translated_text}'")
                
            except Exception as e:
                self._logger.error(f"[{stream_id}] Error processing transcript: {e}")

        async def on_error(error: Exception):
            """Handle streaming STT errors."""
            self._logger.error(f"[{stream_id}] Streaming STT error: {error}")
        
        # Create streaming session
        success = await stream_manager.create_stream(stream_id, on_transcript, on_error)
        
        if success:
            self._logger.info(f"[{stream_id}] Streaming STT session created")
        else:
            self._logger.error(f"[{stream_id}] Failed to create streaming STT session")
        
        return success

    async def send_audio(self, stream_id: str, audio_chunk: bytes):
        """
        Send audio chunk to streaming STT session.
        
        Args:
            stream_id: Target stream identifier
            audio_chunk: Raw audio data from WebSocket
        """
        await stream_manager.send_audio(stream_id, audio_chunk)
        self._logger.debug(f"[{stream_id}] Sent {len(audio_chunk)} bytes to streaming STT")

    async def close_stream(self, stream_id: str):
        """
        Close streaming STT session.
        
        Args:
            stream_id: Stream identifier to close
        """
        await stream_manager.close_stream(stream_id)
        
        # Clear translation cache for this stream
        cache_keys_to_remove = [key for key in self._translation_cache.keys() 
                               if key.startswith(stream_id)]
        for key in cache_keys_to_remove:
            del self._translation_cache[key]
        
        self._logger.info(f"[{stream_id}] Streaming STT session closed")

    def get_stats(self):
        """Get streaming STT service statistics."""
        manager_stats = stream_manager.get_stats()
        return {
            **manager_stats,
            'translation_cache_size': len(self._translation_cache)
        }


# Global streaming STT service instance
streaming_stt_service = StreamingSTTService()