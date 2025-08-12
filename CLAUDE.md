# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a real-time speech-to-speech translation service that converts Dutch speech to English via Google Cloud APIs. The system has two main components:
- **Backend**: FastAPI WebSocket server with Google Cloud integration (STT → Translation → TTS)
- **Frontend**: Browser-based JavaScript client for audio capture and playback

## Development Commands

### Backend (Python/Poetry)
```bash
# Install dependencies
poetry install

# Run development server
poetry run uvicorn backend.main:app --reload

# Run all tests (75 tests)
poetry run pytest

# Run specific test suites
poetry run pytest backend/tests/test_connection_manager.py -v
poetry run pytest backend/tests/test_translation_performance.py -v -s
poetry run pytest backend/tests/test_real_tts_integration.py -v -s
```

### Frontend (JavaScript/Node.js)
```bash
cd frontend

# Install dependencies
npm install

# Run tests (33 tests - 88% success rate)
npm test

# Run specific test files
npm test tests/audio.test.js
npm test tests/connection.test.js

# Development server
npm run serve  # Serves on http://localhost:3000

# Production build
npm run build     # Creates dist/ directory
npm run serve:prod  # Serves production build
```

### Environment Setup
- Set `GOOGLE_APPLICATION_CREDENTIALS="credentials/service-account.json"` 
- Google Cloud services must be enabled: Speech-to-Text, Translation, Text-to-Speech

## Architecture Overview

### Backend Structure
- **main.py**: FastAPI app with WebSocket endpoints (`/ws/speak/{id}`, `/ws/listen/{id}`)
- **connection_manager.py**: Thread-safe broadcasting system for 1-to-many connections
- **services.py**: Google Cloud API pipeline (STT → Translation → TTS)
- **resilience.py**: Circuit breaker patterns with retry logic (3x retries, 5s timeouts)

### Frontend Structure
- **src/config.js**: Production audio settings (16kHz mono, 250ms chunks)
- **src/connection.js**: WebSocket management with retry logic and rate limiting
- **src/audio.js**: MediaRecorder integration with getUserMedia
- **src/ui.js**: Dutch UI with loading states and error handling

### Key Design Patterns
- **Broadcasting**: Speaker sends to `/ws/speak/{stream_id}`, multiple listeners connect to `/ws/listen/{stream_id}`
- **Stream Isolation**: Multiple independent translation streams via stream_id routing
- **Resilience**: Circuit breaker + tenacity retry + graceful fallbacks
- **Real-time Processing**: 250ms audio chunks with <1s end-to-end latency

## Testing Strategy

The project uses Test-Driven Development with comprehensive test coverage:
- **Backend**: 75 tests covering connection management, API integration, and error handling
- **Frontend**: 33 tests with Jest/jsdom for audio streaming, WebSocket connections, and UI interactions
- **Integration Tests**: Real Google Cloud API tests for performance validation

When making changes, run the appropriate test suite first to understand current behavior, then implement changes while maintaining test coverage.