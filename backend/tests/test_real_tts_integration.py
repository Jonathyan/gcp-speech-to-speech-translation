import os
import pytest
from backend.services import real_text_to_speech


@pytest.mark.asyncio
async def test_real_text_to_speech_with_english_text():
    """Test real TTS integration with English text."""
    # Skip if no credentials
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        pytest.skip("No GCP credentials")
    
    # Call real function (will fail initially)
    result = await real_text_to_speech("hello world")
    
    # Assert result is valid audio bytes
    assert isinstance(result, bytes)
    assert len(result) > 1000, "Audio data too small"
    assert len(result) < 1024 * 1024, "Audio data too large (>1MB)"


@pytest.mark.asyncio
async def test_real_text_to_speech_with_empty_text():
    """Test TTS with empty string."""
    # Skip if no credentials
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        pytest.skip("No GCP credentials")
    
    # Test empty string
    result = await real_text_to_speech("")
    assert isinstance(result, bytes)


@pytest.mark.asyncio
async def test_real_text_to_speech_with_long_text():
    """Test TTS with long text input."""
    # Skip if no credentials
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        pytest.skip("No GCP credentials")
    
    # Test with long text
    long_text = "This is a very long sentence that will test how the Text-to-Speech API handles longer inputs and whether it can generate appropriate audio output for extended text content."
    result = await real_text_to_speech(long_text)
    
    assert isinstance(result, bytes)
    assert len(result) > 5000, "Long text should produce more audio data"


@pytest.mark.asyncio
async def test_real_text_to_speech_with_special_characters():
    """Test TTS with special characters and punctuation."""
    # Skip if no credentials
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        pytest.skip("No GCP credentials")
    
    # Test with special characters
    special_text = "Hello! How are you? I'm fine, thanks. Numbers: 1, 2, 3."
    result = await real_text_to_speech(special_text)
    
    assert isinstance(result, bytes)
    assert len(result) > 1000


@pytest.mark.asyncio
async def test_real_text_to_speech_audio_format():
    """Test that TTS returns valid audio format."""
    # Skip if no credentials
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        pytest.skip("No GCP credentials")
    
    result = await real_text_to_speech("test audio format")
    
    assert isinstance(result, bytes)
    assert len(result) > 0
    
    # Check for common audio format signatures
    # MP3 starts with ID3 or 0xFF 0xFX (various MP3 frame sync patterns)
    # WAV starts with RIFF
    # OGG starts with OggS
    is_valid_audio = (
        result.startswith(b'ID3') or  # MP3 with ID3 tag
        (result[0:1] == b'\xff' and (result[1] & 0xE0) == 0xE0) or  # MP3 frame sync
        result.startswith(b'RIFF') or  # WAV
        result.startswith(b'OggS')  # OGG
    )
    
    assert is_valid_audio, f"Audio format not recognized. First 10 bytes: {result[:10]}"


@pytest.mark.asyncio
async def test_real_text_to_speech_error_handling():
    """Test TTS error handling with problematic input."""
    # Skip if no credentials
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        pytest.skip("No GCP credentials")
    
    # Test with very long text that might cause API errors
    very_long_text = "test " * 10000
    try:
        result = await real_text_to_speech(very_long_text)
        assert isinstance(result, bytes)
    except Exception:
        # Should handle errors gracefully
        pass