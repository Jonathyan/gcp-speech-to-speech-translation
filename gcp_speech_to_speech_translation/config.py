from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Beheert de applicatie-instellingen, laadbaar vanuit environment variables.
    """

    # Model-configuratie voor pydantic
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Retry-instellingen
    API_RETRY_ATTEMPTS: int = 3  # Totaal 3 pogingen (1 origineel + 2 retries)
    API_RETRY_WAIT_MULTIPLIER_S: int = 1  # Wacht 1s, 2s, 4s, etc. tussen retries

    # Timeout-instellingen
    PIPELINE_TIMEOUT_S: float = 5.0  # Increased for TTS processing time
    
    # Speech-to-Text configuratie
    STT_SAMPLE_RATE: int = 16000
    STT_LANGUAGE_CODE: str = "nl-NL"
    STT_TIMEOUT_S: float = 10.0

    # Translation configuratie
    TRANSLATION_SOURCE_LANGUAGE: str = "nl"
    TRANSLATION_TARGET_LANGUAGE: str = "en"
    TRANSLATION_TIMEOUT_S: float = 10.0

    # Text-to-Speech configuratie
    TTS_LANGUAGE_CODE: str = "en-US"
    TTS_VOICE_NAME: str = "en-US-Wavenet-D"  # High-quality Wavenet voice
    TTS_VOICE_GENDER: str = "NEUTRAL"  # MALE, FEMALE, NEUTRAL
    TTS_AUDIO_FORMAT: str = "MP3"  # MP3, LINEAR16, OGG_OPUS
    TTS_TIMEOUT_S: float = 10.0

    # Circuit Breaker-instellingen
    CIRCUIT_BREAKER_FAIL_MAX: int = 5  # Na 5 opeenvolgende fouten opent de breaker
    CIRCUIT_BREAKER_RESET_TIMEOUT_S: int = 30  # Probeer na 30s weer te sluiten

    # Fallback-instellingen
    FALLBACK_AUDIO: bytes = b"error_fallback_audio"


# Maak een globale instantie die overal in de app kan worden geïmporteerd
settings = AppSettings()