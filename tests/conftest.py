import pytest
from unittest.mock import patch
from gcp_speech_to_speech_translation.config import settings

@pytest.fixture
def fast_retry_settings():
    """Temporarily reduce retry settings for faster test execution."""
    with patch.object(settings, 'API_RETRY_ATTEMPTS', 2), \
         patch.object(settings, 'API_RETRY_WAIT_MULTIPLIER_S', 0.01), \
         patch.object(settings, 'PIPELINE_TIMEOUT_S', 5.0):
        yield