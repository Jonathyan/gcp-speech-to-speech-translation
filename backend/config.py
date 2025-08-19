import os
from typing import Optional
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
    PIPELINE_TIMEOUT_S: float = 15.0  # Increased for real Translation + TTS processing
    
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

    # Circuit Breaker-instellingen - Production optimized
    CIRCUIT_BREAKER_FAIL_MAX: int = 5  # More reasonable threshold
    CIRCUIT_BREAKER_RESET_TIMEOUT_S: int = 30  # Longer recovery time

    # Fallback-instellingen - test marker for frontend beep generation
    FALLBACK_AUDIO: bytes = b'TEST_AUDIO_BEEP_MARKER:PIPELINE_ERROR_FALLBACK'

    # Phase 2 Hybrid STT Configuration
    ENABLE_STREAMING: bool = os.getenv("ENABLE_STREAMING", "true").lower() == "true"
    QUALITY_THRESHOLD: float = float(os.getenv("QUALITY_THRESHOLD", "0.7"))
    STREAMING_TIMEOUT: float = float(os.getenv("STREAMING_TIMEOUT", "5.0"))
    
    # Streaming Parameters
    STREAMING_THRESHOLD_BYTES: int = int(os.getenv("STREAMING_THRESHOLD_BYTES", "5000"))
    BUFFERED_TIMEOUT_SECONDS: float = float(os.getenv("BUFFERED_TIMEOUT_SECONDS", "2.0"))
    FREQUENCY_THRESHOLD_PER_SECOND: float = float(os.getenv("FREQUENCY_THRESHOLD_PER_SECOND", "8.0"))
    
    # Fallback Configuration
    FAILURE_THRESHOLD: int = int(os.getenv("FAILURE_THRESHOLD", "3"))
    RECOVERY_INTERVAL_SECONDS: float = float(os.getenv("RECOVERY_INTERVAL_SECONDS", "60.0"))
    MAX_RECOVERY_ATTEMPTS: int = int(os.getenv("MAX_RECOVERY_ATTEMPTS", "5"))
    
    # Connection Quality
    MEASUREMENT_WINDOW_SECONDS: float = float(os.getenv("MEASUREMENT_WINDOW_SECONDS", "10.0"))
    MAX_CONCURRENT_SESSIONS: int = int(os.getenv("MAX_CONCURRENT_SESSIONS", "20"))
    
    # Cloud Run Configuration
    PORT: int = int(os.getenv("PORT", "8080"))
    WORKERS: int = 1  # Cloud Run works best with single worker
    
    # Monitoring  
    ENABLE_MONITORING: bool = os.getenv("ENABLE_MONITORING", "true").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "9090"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_CLOUD_LOGGING: bool = os.getenv("ENABLE_CLOUD_LOGGING", "true").lower() == "true"


# Maak een globale instantie die overal in de app kan worden geïmporteerd
settings = AppSettings()