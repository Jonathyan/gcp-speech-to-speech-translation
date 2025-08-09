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

**Iteration 6: Google Cloud Text-to-Speech Integration**

*   ✅ **Production-ready TTS implementation** with Google Cloud Text-to-Speech API
*   ✅ **Premium voice quality** - Wavenet voices with MP3 output format
*   ✅ **Environment configuration** - Voice selection, language, format via env vars
*   ✅ **Complete pipeline** - Real STT → Real Translation → Real TTS
*   ✅ **Health monitoring** - Individual service health checks + full pipeline test
*   ✅ **Performance verified** - End-to-end latency 677-817ms, concurrent handling
*   ✅ **Production ready** - Comprehensive error handling and resilience patterns

### Next step
**Iteration 7: Frontend Integration
*   ✅ **Frontend development** - Basic HTML/JS client for live audio streaming




### Recap: GCP Speech-to-Speech Translation Service - Status na 6 Iteraties
🏗️ Wat we hebben gebouwd
Core Architecture
FastAPI WebSocket Server - Real-time bidirectionele communicatie

Complete Audio Pipeline - STT → Translation → TTS met Google Cloud APIs

Production-Ready Resilience - Retry logic, circuit breaker, timeouts, fallback

Comprehensive Health Monitoring - 4 endpoints voor service status

Pipeline Components (Alle LIVE)
1. Speech-to-Text (Google Cloud)
✅ Real Google Cloud Speech API integration

✅ Dutch language support (nl-NL)

✅ Optimized latest_short model voor real-time

✅ Automatic punctuation enabled

✅ Confidence scoring

✅ Retry logic met exponential backoff

2. Translation (Google Cloud)
✅ Real Google Cloud Translation API v2

✅ Dutch → English translation

✅ ~250ms average latency

✅ Language detection

✅ Async executor pattern

✅ Performance benchmarked

3. Text-to-Speech (Google Cloud)
✅ Real Google Cloud TTS API

✅ Premium Wavenet voices (en-US-Wavenet-D)

✅ MP3 output format voor web compatibility

✅ Configurable voice parameters

✅ Audio size optimization

🔧 Wat werkt en hoe
WebSocket Endpoint (/ws)
Client sends: Binary audio chunk (Dutch speech)
Server processes: STT → Translation → TTS
Server returns: Binary MP3 audio (English speech)

Copy
Health Monitoring
/health/speech - STT client connectivity

/health/translation - Live translation test

/health/tts - Audio generation test met voice config

/health/full - Complete pipeline end-to-end test

Resilience Patterns
Retry Logic: 2-3 attempts per service met exponential backoff

Circuit Breaker: Opens na 5 failures, prevents cascade

Timeouts: 5s pipeline, 10s per service

Fallback Audio: Graceful degradation bij failures

Performance Metrics
End-to-end latency: 677-817ms

Translation: ~250ms average

TTS: ~400-600ms typical

Concurrent handling: 5+ simultaneous requests

Success rate: 100% onder normale condities

🧪 Test Coverage
Test Suites
Unit Tests: Alle services geïsoleerd getest

Integration Tests: Real API connectivity

Performance Tests: Latency benchmarks

WebSocket Tests: End-to-end flow

Health Tests: Alle monitoring endpoints

Concurrent Tests: Multi-client handling

Test Results
✅ 20+ tests passing

✅ Real API integration verified

✅ Performance requirements met

✅ Error scenarios handled

✅ Concurrent load tested

🚀 Production Readiness
Environment Configuration
Service account authentication

Configurable via environment variables

Language/voice/format selection

Timeout en retry parameters

Error Handling
Google API exceptions caught

Network timeouts handled

Invalid audio gracefully handled

Comprehensive logging

Monitoring
Health check endpoints

Performance metrics logging

Error rate tracking

Service dependency status

📊 Current Status: PRODUCTION READY
Je hebt een volledig werkende, production-ready real-time speech-to-speech translation service met:

Complete Google Cloud integration

Sub-second end-to-end latency

Robust error handling

Comprehensive monitoring

Proven concurrent performance

Full test coverage

Ready voor Iteration 7! 🎯



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
                                        │  │    ✅ Google Cloud API   │    │
                                        │  │    - Wavenet voices     │    │
                                        │  │    - MP3 format         │    │
                                        │  │    - Retry logic        │    │
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

The service provides comprehensive health check endpoints for monitoring:

*   **Speech-to-Text Health:** `GET /health/speech` - Client connectivity status
*   **Translation Health:** `GET /health/translation` - Live API test with sample translation
*   **Text-to-Speech Health:** `GET /health/tts` - Audio generation test with voice config details
*   **Complete Pipeline Health:** `GET /health/full` - End-to-end pipeline test (Translation + TTS)

All endpoints test actual API connectivity and return detailed status information including error details when services are unavailable.

### Performance Testing

To run performance tests:

```bash
# Translation performance
poetry run pytest tests/test_translation_performance.py -v -s

# TTS integration tests
poetry run pytest tests/test_real_tts_integration.py -v -s
```

Expected performance:
*   **Translation latency:** ~250ms average
*   **TTS latency:** ~400-600ms for typical text
*   **End-to-end pipeline:** 677-817ms total
*   **Concurrent handling:** 5+ simultaneous requests
*   **All requests complete within 5s timeout**