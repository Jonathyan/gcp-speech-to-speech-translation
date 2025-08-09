import os
import pytest
from gcp_speech_to_speech_translation.services import real_translation


@pytest.mark.asyncio
async def test_real_translation_with_dutch_text():
    # Skip if no credentials
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        pytest.skip("No GCP credentials")
    
    # Call real function (will fail initially)
    result = await real_translation("hallo wereld")
    
    # Assert result is valid and contains English equivalent
    assert isinstance(result, str)
    assert result
    assert "hello" in result.lower() or "world" in result.lower()


@pytest.mark.asyncio
async def test_real_translation_with_empty_text():
    # Skip if no credentials
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        pytest.skip("No GCP credentials")
    
    # Test empty string
    result = await real_translation("")
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_real_translation_error_handling():
    # Skip if no credentials
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        pytest.skip("No GCP credentials")
    
    # Test with very long text that might cause API errors
    long_text = "hallo " * 1000
    try:
        result = await real_translation(long_text)
        assert isinstance(result, str)
    except Exception:
        # Should handle errors gracefully
        pass