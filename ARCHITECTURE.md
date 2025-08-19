# Clean Streaming Architecture - Production Ready

**Real-time Dutch-to-English Speech Translation**  
**Status:** Production operational with clean streaming implementation  
**Performance:** <1s end-to-end latency, >90% success rate  
**Architecture:** Simplified 3-layer system (Communication → Processing → Infrastructure)

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   CLIENT LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────┐         ┌─────────────────────┐                       │
│  │      SPEAKER        │         │      LISTENER       │                       │
│  │   (Browser App)     │         │   (Browser App)     │                       │
│  │                     │         │                     │                       │
│  │  • Web Audio API    │         │  • Audio Playback   │                       │
│  │  • LINEAR16 PCM     │         │  • MP3 Audio        │                       │
│  │  • WebSocket        │         │  • WebSocket        │                       │
│  │  • 100ms chunks     │         │  • Real-time play   │                       │
│  └─────────────────────┘         └─────────────────────┘                       │
│           │                               │                                     │
│           │ Raw LINEAR16 Audio            │ MP3 Audio                          │
│           │ (16kHz mono, 16-bit)          │ (Real-time)                        │
│           ▼                               ▲                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
           │                               │
           │ /ws/stream/{stream_id}        │ /ws/listen/{stream_id}
           │                               │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               APPLICATION LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         SIMPLE FASTAPI SERVER                          │   │
│  │                               (main.py)                                │   │
│  │                                                                         │   │
│  │  ┌─────────────────────┐    ┌──────────────────┐    ┌──────────────┐   │   │
│  │  │   WebSocket         │    │  Connection       │    │  Health      │   │   │
│  │  │   Endpoints         │    │  Manager         │    │  Checks      │   │   │
│  │  │                     │    │                  │    │              │   │   │
│  │  │ • /ws/stream/{id}   │    │ • Thread-safe    │    │ • /health    │   │   │
│  │  │ • /ws/listen/{id}   │    │ • Broadcasting   │    │ • Real-time  │   │   │
│  │  │ • Streaming STT     │    │ • 1-to-many      │    │ • Minimal    │   │   │
│  │  │ • Error Handling    │    │ • Auto cleanup   │    │ • Status     │   │   │
│  │  └─────────────────────┘    └──────────────────┘    └──────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                         │
│                                      ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      STREAMING PIPELINE                               │   │
│  │                     (streaming_stt.py)                                │   │
│  │                                                                         │   │
│  │ Raw LINEAR16 ──► Streaming STT ──► Translation ──► TTS Service ──► MP3 │   │
│  │       │                │              │              │             │   │   │
│  │   100ms chunks    Dutch Text     English Text    Audio MP3     Broadcast │   │
│  │   (16-bit PCM)     (nl-NL)         (en-US)       (Neural2-F)           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               INFRASTRUCTURE LAYER                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│                         Google Cloud Services                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                    │
│  │ Speech-to-   │    │ Translation  │    │ Text-to-     │                    │
│  │ Text API     │    │    API v2    │    │ Speech API   │                    │
│  │              │    │              │    │              │                    │
│  │ • LINEAR16   │    │ • Dutch→Eng  │    │ • Neural2-F  │                    │
│  │ • Streaming  │    │ • Real-time  │    │ • MP3 format │                    │
│  │ • 16kHz mono │    │ • Direct API │    │ • English    │                    │
│  └──────────────┘    └──────────────┘    └──────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Component Overview

### Frontend (JavaScript/Browser)
- **Audio Capture**: Web Audio API with LINEAR16 PCM generation
- **WebSocket Client**: Streaming binary audio data (100ms chunks)
- **Audio Playback**: Direct MP3 playback with Web Audio API
- **UI Management**: Dutch interface with real-time status updates

### Backend (FastAPI/Python)
- **WebSocket Server**: Single streaming endpoint `/ws/stream/{stream_id}`  
- **Connection Manager**: Thread-safe broadcasting for 1-to-many communication
- **Streaming STT**: Real-time Google Cloud Speech recognition
- **Translation Pipeline**: Direct API calls without complex buffering

### Google Cloud Integration
- **Speech-to-Text**: Streaming recognition with LINEAR16 audio
- **Translation API**: Dutch to English text translation
- **Text-to-Speech**: Neural2-F voice synthesis to MP3

### Reliability (Minimal)
- **Async Callbacks**: Proper event loop scheduling from worker threads
- **Basic Error Handling**: Simple retry logic and graceful failures
- **Health Checks**: Basic service connectivity monitoring

## Data Flow

1. **Audio Capture**: Browser generates raw LINEAR16 PCM audio (100ms chunks)
2. **WebSocket Upload**: Audio streamed to `/ws/stream/{stream_id}` endpoint
3. **Streaming STT**: Google Cloud Speech processes audio in real-time
4. **Translation**: Google Translate converts Dutch text to English
5. **Speech Synthesis**: Google Cloud TTS generates English MP3 audio
6. **Broadcasting**: Translated audio sent to all `/ws/listen/{stream_id}` connections
7. **Playback**: Browsers play MP3 audio directly

## Deployment Architecture

### Development Environment
- **Backend**: `poetry run uvicorn backend.main:app --reload` (localhost:8000)
- **Frontend**: Static files served via `npm run serve` (localhost:3000)
- **Testing**: Comprehensive test suites (75 backend + 33 frontend tests)

### Production Environment
- **Backend**: Google Cloud Run with Docker containers
- **Frontend**: Firebase Hosting with static deployment
- **Performance**: <1s end-to-end latency for real-time translation
- **Status**: Currently operational at `streaming-stt-service-00024-lfj`

## Key Design Patterns

### Stream Isolation
Multiple independent translation streams via unique `stream_id` routing, allowing concurrent sessions without interference.

### Broadcasting Pattern
One speaker broadcasts to multiple listeners through the Connection Manager's thread-safe implementation.

### Streaming Processing
Real-time audio processing with Google Cloud Speech streaming API - no buffering or batching delays.

### Simplicity First
Minimal complexity with direct API calls, clean error handling, and straightforward async patterns.

This architecture prioritizes **simplicity and reliability** over complex resilience patterns, achieving production stability through clean code rather than defensive programming.

---

## Current File Structure

### Backend (`backend/`)
```
backend/
├── main.py              # FastAPI server with streaming endpoints
├── streaming_stt.py     # Google Cloud Speech streaming integration  
├── connection_manager.py # Thread-safe broadcasting
├── services.py          # Translation and TTS services
├── config.py           # Configuration management
└── resilience.py       # Basic error handling
```

### Frontend (`frontend/src/`)
```
frontend/src/
├── config.js           # Audio settings (100ms chunks, LINEAR16)
├── wavEncoder.js       # Raw LINEAR16 PCM audio generation
├── connection.js       # WebSocket streaming with `/ws/stream/{id}`
├── audio.js           # Web Audio API integration
└── ui.js              # Dutch interface with status updates
```

## Removed Complexity

**Files Successfully Removed:**
- ❌ `debug_speechhelpers.py` - Debug utilities (no longer needed)
- ❌ `main_complex_backup.py` - Complex legacy implementation
- ❌ `batch_stt.py` - Batch processing fallback (unused)
- ❌ Complex hybrid STT systems and fallback orchestrators
- ❌ Over-engineered buffering and adaptive streaming

**Result:** Clean, maintainable codebase focused on core functionality.

## Production Status

**✅ OPERATIONAL:** Dutch-to-English streaming translation system is production-ready and deployed.

**Current Deployment:**
- **Backend**: Google Cloud Run `streaming-stt-service-00024-lfj`
- **Frontend**: Firebase Hosting `https://lfhs-translate.web.app`
- **Status**: Fully functional real-time translation

---

*Last Updated: August 2025 - Reflects current production streaming implementation*