import pytest
from fastapi.testclient import TestClient
from gcp_speech_to_speech_translation.main import app


@pytest.fixture
def client():
    """
    Provides a TestClient instance for the FastAPI app.
    This is a standard pytest fixture setup.
    """
    return TestClient(app)


def test_websocket_connection_accepts(client: TestClient):
    """
    Tests that the /ws endpoint successfully accepts a WebSocket connection.
    """
    # The `websocket_connect` context manager handles the handshake.
    # If the server does not return a 101 "Switching Protocols" status,
    # it will raise an exception, and the test will fail.
    with client.websocket_connect("/ws") as websocket:
        assert websocket is not None