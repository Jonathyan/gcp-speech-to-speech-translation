import pytest
from fastapi.testclient import TestClient
from backend.main import app


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


def test_websocket_echo(client: TestClient):
    """
    Tests that the WebSocket endpoint echoes back the JSON message it receives.
    This validates two-way communication and data integrity.
    """
    with client.websocket_connect("/ws") as websocket:
        data_to_send = {"type": "greeting", "payload": "hallo"}
        websocket.send_json(data_to_send)
        received_data = websocket.receive_json()
        assert received_data == data_to_send