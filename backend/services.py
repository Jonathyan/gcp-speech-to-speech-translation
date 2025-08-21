import asyncio
import logging
import subprocess
import os
from typing import Optional

# Configureer basis logging om de flow te kunnen volgen
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# Mock services removed - using only real Google Cloud APIs


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


# Mock translation service removed - using only real Google Cloud Translation API


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


# Mock TTS service removed - using only real Google Cloud TTS API


# Buffered and legacy services removed - production uses streaming STT only


# Buffered STT removed - using streaming STT only for production


# Legacy streaming service classes removed - production uses direct streaming_stt.py implementation