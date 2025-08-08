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