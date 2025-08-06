# GCP Live Speech-to-Speech Translation Service

This project is a live, real-time speech-to-speech translation service. It's designed to capture audio from a speaker's microphone, send it to Google Cloud for transcription and translation, and then broadcast the translated audio to multiple listeners via a web interface.

The development follows a strict Test-Driven Development (TDD) approach, with each feature built in small, testable iterations as outlined in the `plan/plan.md` document.

## Technology Stack

*   **Backend:** Python with FastAPI (for WebSockets), hosted on Google Cloud Run.
*   **Frontend:** Plain HTML, CSS, and JavaScript, hosted on Firebase Hosting.
*   **Testing:** `pytest` and `pytest-asyncio`.
*   **Dependency Management:** Poetry.

## Current Status

**Iteration 1: Basis WebSocket Server - COMPLETED**

*   A basic FastAPI server is running.
*   A `/ws` endpoint is available and accepts WebSocket connections.
*   A `pytest` test (`tests/test_websocket.py`) verifies that the WebSocket connection handshake is successful.

## Development

This project uses Poetry for dependency management.

### Prerequisites

*   Python 3.9+
*   Poetry

### Setup

1.  **Install Poetry:**
    If you don't have Poetry, you can install it following the official instructions. For macOS, `brew install poetry` is a common method.

2.  **Install Dependencies:**
    Navigate to the project root and run:
    ```bash
    poetry install
    ```

### Running the Server

To run the development server with auto-reload:

```bash
poetry run uvicorn gcp_speech_to_speech_translation.main:app --reload
```

### Running Tests

To run the test suite:

```bash
poetry run pytest
```