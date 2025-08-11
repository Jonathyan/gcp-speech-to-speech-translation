import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_speech_endpoint():
    """Test the speech health check endpoint."""
    response = client.get("/health/speech")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "speech_client" in data

def test_health_translation_endpoint():
    """Test the translation health check endpoint."""
    response = client.get("/health/translation")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "translation_client" in data
    assert "test_result" in data

def test_health_tts_endpoint():
    """Test the TTS health check endpoint."""
    response = client.get("/health/tts")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "tts_client" in data
    assert "test_result" in data
    
    # If TTS is working, check additional fields
    if data["status"] == "ok":
        assert "audio_output_size" in data
        assert "voice_config" in data
        assert data["audio_output_size"] > 0
        assert "language" in data["voice_config"]
        assert "voice_name" in data["voice_config"]
        assert "format" in data["voice_config"]

def test_health_full_endpoint():
    """Test the complete pipeline health check endpoint."""
    response = client.get("/health/full")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "pipeline" in data
    assert "services" in data
    
    # Check all services are listed
    services = data["services"]
    assert "speech" in services
    assert "translation" in services
    assert "tts" in services
    
    # If pipeline is complete, check test results
    if data["status"] == "ok" and data["pipeline"] == "complete":
        assert "test_results" in data
        assert "translation" in data["test_results"]
        assert "audio_size" in data["test_results"]
        assert data["test_results"]["audio_size"] > 0

def test_all_health_endpoints_accessible():
    """Test that all health endpoints are accessible."""
    endpoints = ["/health/speech", "/health/translation", "/health/tts", "/health/full"]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 200, f"Endpoint {endpoint} failed"
        data = response.json()
        assert "status" in data, f"Endpoint {endpoint} missing status field"