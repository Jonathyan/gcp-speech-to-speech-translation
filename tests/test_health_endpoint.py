import pytest
from fastapi.testclient import TestClient
from gcp_speech_to_speech_translation.main import app


def test_health_speech_endpoint():
    """
    Test dat de health check endpoint voor Speech-to-Text werkt.
    """
    with TestClient(app) as client:
        response = client.get("/health/speech")
        
        # Verwacht 200 status code
        assert response.status_code == 200
        
        # Verwacht JSON response
        data = response.json()
        assert isinstance(data, dict)
        
        # Verwacht status field
        assert "status" in data
        assert data["status"] in ["ok", "error"]
        
        # Verwacht speech_client field
        assert "speech_client" in data
        assert data["speech_client"] in ["connected", "disconnected"]