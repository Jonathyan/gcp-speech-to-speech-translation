# Dutch-to-English Streaming Translation Service

Real-time speech-to-speech translation system using Google Cloud APIs with clean streaming architecture.

![Alt tekst](frontend-mock.png "Mockup of UI")

## 🎯 Production Status: **✅ OPERATIONAL**

### System Overview
- **Real-time Translation**: Dutch speech → English audio in <1s
- **Streaming Architecture**: Clean 3-layer system (Communication → Processing → Infrastructure)
- **Broadcasting**: 1-to-many speaker-to-listeners with stream isolation
- **Performance**: >90% success rate, stable under concurrent load
- **Deployment**: Google Cloud Run + Firebase Hosting (currently active)

### Core Features ✅
- **Backend**: FastAPI WebSocket server with Google Cloud Speech streaming
- **Frontend**: Production-ready JavaScript client with Web Audio API
- **Audio Processing**: Raw LINEAR16 PCM for optimal Google Cloud compatibility
- **Error Recovery**: Circuit breaker patterns with automatic retry
- **Health Monitoring**: Comprehensive diagnostics and system status
- **User Experience**: Dutch interface with real-time quality assessment

## 🏗️ Clean Streaming Architecture

![Alt tekst](gcp-arch.png "Solution Architecture in GCP")

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       PRODUCTION STREAMING SYSTEM                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Browser (Speaker) ──────► FastAPI WebSocket ──────► Browser (Listener) │
│       │                           │                          │         │
│  Raw LINEAR16              Streaming STT                   MP3 Audio     │
│  100ms chunks                     │                          │         │
│                                   ▼                                     │
│              ┌─────────────────────────────────────────────┐            │
│              │         REAL-TIME PIPELINE                  │            │
│              │                                             │            │
│              │  Audio ──► Google STT ──► Translate ──► TTS │            │
│              │   100ms      (Dutch)       (Dutch→EN)   MP3 │            │
│              │                                             │            │
│              │  • Streaming API    • Real-time      • Neural│           │
│              │  • LINEAR16 PCM     • Google v2      • Voice │           │  
│              │  • <1s latency      • Direct calls   • Broadcast│        │
│              └─────────────────────────────────────────────┘            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Design Principles
- **Simplicity**: Direct Google Cloud API calls without complex abstraction
- **Real-time**: 100ms audio chunks with streaming STT for <1s latency
- **Broadcasting**: Thread-safe 1-to-many communication via ConnectionManager
- **Reliability**: Basic error handling with automatic retry and recovery

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Poetry
- Google Cloud credentials
- Node.js (for frontend development)

### Backend Setup
```bash
# Install dependencies
poetry install

# Set up Google Cloud credentials
export GOOGLE_APPLICATION_CREDENTIALS="credentials/service-account.json"

# Run development server
poetry run uvicorn backend.main:app --reload
```

### Frontend Setup
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Development mode
npm run serve

# Production build
npm run build
npm run serve:prod
```

## 📡 API Endpoints

### WebSocket Endpoints
- **`/ws/stream/{stream_id}`** - Speaker sends audio for real-time translation
- **`/ws/listen/{stream_id}`** - Listeners receive translated audio
- **Stream Isolation** - Multiple concurrent streams via unique stream_id

### Health Monitoring
- **`GET /health`** - Basic service connectivity status
- **`GET /ready`** - Container readiness probe
- **`GET /stats`** - Performance metrics and pipeline statistics

## 🎮 Usage

### Speaker Mode
1. Open frontend in browser
2. Click "Start Uitzending"
3. Allow microphone access
4. Speak in Dutch - audio gets translated to English and broadcast to listeners

### Listener Mode
1. Open frontend in browser (can be multiple browsers/devices)
2. Click "Luister mee"
3. Receive translated English audio from any active speaker

### Stream Isolation
Multiple independent streams can run simultaneously using different `stream_id` values.

## 📊 Production Performance

- **End-to-end latency**: <1000ms (real-time optimized)
- **Translation success rate**: >90% (production validated)
- **Concurrent streams**: 10+ simultaneous sessions
- **Audio processing**: 100ms chunks for minimal delay
- **System stability**: Stable under concurrent load

## 🧪 Testing

### Backend Tests
```bash
# Run all tests (75 comprehensive tests)
poetry run pytest

# Specific test suites
poetry run pytest backend/tests/test_connection_manager.py -v
poetry run pytest backend/tests/test_translation_performance.py -v -s
poetry run pytest backend/tests/test_real_tts_integration.py -v -s
```

### Frontend Tests
```bash
cd frontend

# Run all tests (210 tests - production ready)
npm test

# Specific test categories
npm test tests/audio.test.js        # Audio capture & processing
npm test tests/connection.test.js   # WebSocket streaming
npm test tests/audioPlayer.test.js  # Audio playback & error recovery
npm test tests/ui.test.js           # User interface & diagnostics
npm test tests/utils.test.js        # Utility functions
```

### Manual Testing
```bash
# Development testing
npm run serve          # Frontend at http://localhost:3000
open public/index.html # Main interface testing
```

## 🔧 Configuration

### Environment Variables
```bash
# Required
GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"

# Optional (with defaults)
TTS_VOICE_NAME="en-US-Wavenet-D"
TTS_LANGUAGE_CODE="en-US"
TRANSLATION_TARGET_LANGUAGE="en"
```

### Frontend Configuration
Edit `frontend/src/config.js` for:
- **Audio Settings**: 16kHz mono, 100ms chunks, production optimized
- **WebSocket URLs**: Development vs production streaming endpoints
- **Audio Processing**: Raw LINEAR16 PCM generation via Web Audio API
- **Browser Support**: Automatic format detection with graceful fallbacks

## 📁 Current Project Structure

```
├── backend/                            # Clean backend implementation
│   ├── tests/                         # Comprehensive tests (75 tests)
│   ├── main.py                        # FastAPI WebSocket server
│   ├── streaming_stt.py               # Google Cloud Speech streaming
│   ├── connection_manager.py          # Thread-safe broadcasting
│   ├── services.py                    # Translation and TTS pipeline
│   ├── config.py                      # Environment configuration
│   └── resilience.py                  # Basic error handling
├── frontend/                          # Production-ready frontend
│   ├── public/                        # Static HTML interface
│   ├── src/                           # JavaScript modules
│   │   ├── config.js                  # Audio settings (100ms chunks)
│   │   ├── wavEncoder.js              # Raw LINEAR16 PCM generation
│   │   ├── connection.js              # WebSocket streaming
│   │   ├── audio.js                   # MediaRecorder integration
│   │   └── ui.js                      # Dutch interface with diagnostics
│   ├── tests/                         # Jest tests (210 tests)
│   └── dist/                          # Production build output
└── ARCHITECTURE.md                    # Current system documentation
```

## ✅ **Production System Features**

### 🎵 **Real-time Audio Pipeline**
- ✅ Raw LINEAR16 PCM generation via Web Audio API 
- ✅ 100ms audio chunks for minimal latency streaming
- ✅ Google Cloud Speech streaming API integration
- ✅ Direct translation pipeline without complex buffering
- ✅ MP3 audio broadcasting to multiple listeners

### 🛡️ **Production Reliability**
- ✅ Circuit breaker patterns with automatic error recovery
- ✅ Thread-safe connection management and broadcasting
- ✅ Comprehensive health monitoring and diagnostics
- ✅ Basic retry logic with graceful failure handling
- ✅ Memory optimization and performance monitoring

### 🎯 **User Experience**
- ✅ Dutch interface with real-time quality assessment
- ✅ Comprehensive diagnostics and troubleshooting tools
- ✅ Multi-browser support with automatic format fallbacks
- ✅ Production-ready error messages and recovery workflows
- ✅ Visual feedback and audio level monitoring

### 🚀 **Current Deployment Status**
- ✅ Google Cloud Run backend deployment (operational)
- ✅ Firebase Hosting frontend deployment (operational)
- ✅ Production monitoring with health endpoints
- ✅ Real-time performance: <1s latency, >90% success rate

## 🔒 Security & Privacy

- Service account authentication for Google Cloud APIs
- No audio data stored permanently
- Environment-based configuration management
- CORS and WebSocket security headers

## 📈 Production Monitoring

Current operational monitoring includes:
- **Health endpoints**: `/health`, `/ready`, `/stats` for service status
- **Real-time performance**: <1s latency tracking and success rate monitoring  
- **Error tracking**: Structured logging with Google Cloud Run integration
- **User diagnostics**: Comprehensive frontend diagnostic tools
- **System metrics**: Connection state and performance monitoring

## 🤝 Development & Testing

The system follows Test-Driven Development with:
- **285 total tests**: 75 backend + 210 frontend comprehensive test coverage
- **Production validation**: Real-time performance and reliability testing
- **Clean architecture**: Simplified 3-layer system design
- **Continuous monitoring**: Health endpoints with operational metrics

## 🎯 Production Status Summary

**✅ OPERATIONAL**: Dutch-to-English real-time translation system
- **Backend**: `streaming-stt-service-00024-lfj` (Google Cloud Run)
- **Frontend**: `https://lfhs-translate.web.app` (Firebase Hosting)  
- **Performance**: <1s end-to-end latency, >90% success rate
- **Architecture**: Clean streaming implementation with direct Google Cloud API integration

## 📄 License

This project is for educational and demonstration purposes.