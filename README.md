# GCP Live Speech-to-Speech Translation Service

This project is a live, real-time speech-to-speech translation service. It's designed to capture audio from a speaker's microphone, send it to Google Cloud for transcription and translation, and then broadcast the translated audio to multiple listeners via a web interface.

The development follows a strict Test-Driven Development (TDD) approach, with each feature built in small, testable iterations as outlined in the `plan/plan.md` document.

## Technology Stack

*   **Backend:** Python with FastAPI (for WebSockets), hosted on Google Cloud Run.
*   **Frontend:** Plain HTML, CSS, and JavaScript, hosted on Firebase Hosting.
*   **Testing:** `pytest` and `pytest-asyncio`.
*   **Dependency Management:** Poetry.

![Alt tekst](gcp-arch.png "Solution Architecture in GCP")

## Project Status

### Completed
**Iteration 1: Basis WebSocket Server**

*   A basic FastAPI server is running.
*   A `/ws` endpoint is available that accepts WebSocket connections.
*   A `pytest` test (`tests/test_websocket.py`) verifies that the WebSocket connection handshake is successful.

**Iteration 2: Echo Service & Refactoring**

*   The WebSocket server now implements a two-way communication "echo" service.
*   It correctly receives a JSON message and sends the exact same message back to the client, validated by a dedicated `pytest` test.
*   **Refactoring:** The implementation was improved with professional logging, robust error handling for invalid data, and a fix to ensure compatibility with `pytest`'s `TestClient`.

**Iteration 3: Mocked API Pipeline with Resilience Patterns**

*   ✅ The full backend logic (Speech-to-Text -> Translation -> Text-to-Speech) is simulated using mock functions.
*   ✅ WebSocket handler processes binary audio data through the mock pipeline and returns binary audio response.
*   ✅ End-to-end flow with realistic timing (~150ms) validated by comprehensive `pytest` test suite.
*   ✅ **Resilience patterns implemented:**
    *   **Retry Logic:** Exponential backoff with configurable attempts (default 3x)
    *   **Circuit Breaker:** Opens after 5 consecutive failures, prevents cascade failures
    *   **Timeout Protection:** 2s timeout per pipeline execution
    *   **Graceful Fallback:** Fallback audio for all failure scenarios
*   ✅ **Comprehensive test coverage:** 12 tests including happy path, error scenarios, performance, concurrency

**Iteration 4: Google Cloud Speech-to-Text Integration**

*   ✅ **Production-ready STT implementation** with Google Cloud Speech-to-Text API
*   ✅ **Streaming support** with optimized `latest_short` model for real-time performance
*   ✅ **Environment configuration** - Sample rate, language code, timeout via env vars
*   ✅ **Robust error handling** - Specific Google API exceptions and retry logic
*   ✅ **Health check endpoint** - `GET /health/speech` for service monitoring
*   ✅ **Service account authentication** - Secure credential management
*   ✅ **Backwards compatibility** - All existing resilience patterns maintained

**Iteration 5: Google Cloud Translation Integration**

*   ✅ **Production-ready Translation implementation** with Google Cloud Translation API v2
*   ✅ **Real-time translation** - Dutch to English with ~250ms average latency
*   ✅ **Environment configuration** - Source/target languages, timeout via env vars
*   ✅ **Async executor pattern** - Non-blocking API calls with proper timeout handling
*   ✅ **Health check endpoint** - `GET /health/translation` with live API test
*   ✅ **Comprehensive error handling** - Google API exceptions, timeout, and retry logic
*   ✅ **Performance optimization** - Sub-400ms response times for typical requests
*   ✅ **Integration testing** - Full test suite with performance benchmarks


### Next Steps
**Iteration 6: Google Cloud Text-to-Speech Integration**

*   Replace `mock_text_to_speech` with real Google Cloud Text-to-Speech API
*   Implement voice selection and audio format configuration
*   Complete end-to-end real-time translation pipeline

## Current Architecture

```
┌─────────────────┐                    ┌─────────────────────────────────┐
│   Client        │ ◄─── WebSocket ───► │   FastAPI Server               │
│   (Browser)     │    Binary Audio     │   - WebSocket Handler (/ws)    │
│                 │                     │   - Health Check (/health)     │
└─────────────────┘                     └─────────────────────────────────┘
                                                         │
                                                         ▼
                                        ┌─────────────────────────────────┐
                                        │   Audio Processing Pipeline     │
                                        │                                 │
                                        │  ┌─────────────────────────┐    │
                                        │  │ 1. Speech-to-Text       │    │
                                        │  │    ✅ Google Cloud API   │    │
                                        │  │    - Streaming support  │    │
                                        │  │    - Dutch language     │    │
                                        │  │    - Retry logic        │    │
                                        │  └─────────────────────────┘    │
                                        │              │                  │
                                        │              ▼                  │
                                        │  ┌─────────────────────────┐    │
                                        │  │ 2. Translation          │    │
                                        │  │    ✅ Google Cloud API   │    │
                                        │  │    - Dutch → English    │    │
                                        │  │    - ~250ms latency     │    │
                                        │  │    - Retry logic        │    │
                                        │  └─────────────────────────┘    │
                                        │              │                  │
                                        │              ▼                  │
                                        │  ┌─────────────────────────┐    │
                                        │  │ 3. Text-to-Speech       │    │
                                        │  │    🔄 Mock Service       │    │
                                        │  │    (English Audio)      │    │
                                        │  └─────────────────────────┘    │
                                        └─────────────────────────────────┘
                                                         │
                                                         ▼
                                        ┌─────────────────────────────────┐
                                        │   Resilience Layer              │
                                        │   ✅ Retry Logic (3x)            │
                                        │   ✅ Circuit Breaker (5 fails)   │
                                        │   ✅ Timeout Protection (2s)     │
                                        │   ✅ Graceful Fallback Audio     │
                                        └─────────────────────────────────┘
```

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

### Health Monitoring

The service provides health check endpoints for monitoring:

*   **Speech-to-Text Health:** `GET /health/speech`
*   **Translation Health:** `GET /health/translation`

Both endpoints test actual API connectivity and return detailed status information.

### Performance Testing

To run translation performance tests:

```bash
poetry run pytest tests/test_translation_performance.py -v -s
```

Expected performance:
*   Average translation latency: ~250ms
*   Maximum latency: <1s for typical requests
*   All requests complete within 3s timeout