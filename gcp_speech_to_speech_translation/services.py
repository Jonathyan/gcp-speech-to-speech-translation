import asyncio
import logging
import random

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


async def real_speech_to_text(audio_chunk: bytes) -> str:
    """
    Production-ready Google Cloud Speech-to-Text API met streaming support.
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
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, max=2),
        reraise=True
    )
    async def _recognize_with_retry():
        try:
            client = speech.SpeechClient()
            
            # Optimized config voor streaming performance
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,
                language_code=language_code,
                enable_automatic_punctuation=True,
                model="latest_short",
            )
            
            audio = speech.RecognitionAudio(content=audio_chunk)
            
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


async def mock_text_to_speech(text: str) -> bytes:
    """
    Simuleert een Text-to-Speech API-aanroep.

    Wacht 50ms en geeft een vaste audio byte-string terug, met een kans op een fout.
    """
    logging.info(f"TTS: Tekst ontvangen: '{text}', start audiosynthese...")
    if random.random() < 0.08:  # 8% kans op een fout
        logging.error("TTS: Gesimuleerde API-fout!")
        raise Exception("TTS API Error")

    await asyncio.sleep(0.05)  # Simuleer 50ms netwerklatentie
    result = b"mock_english_audio_output"
    logging.info(f"TTS: Audiosynthese voltooid. Resultaat: {result}")
    return result