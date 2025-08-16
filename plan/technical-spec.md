# Technical Specification
## Real-Time Speech-to-Speech Translation System

---

## 1. System Overview

### Architecture Type
**Simplified WebSocket-based client-server architecture** (Phase 3 minimal design)
- Frontend: Static HTML/JavaScript served via Firebase Hosting
- Backend: FastAPI WebSocket server on Google Cloud Run
- APIs: Google Cloud Speech-to-Text, Translation, and Text-to-Speech

### Current Implementation Status
```
Version: 1.0.0-minimal
Deployment: Cloud Run (europe-west1)
Service URL: https://hybrid-stt-service-980225887796.europe-west1.run.app
Architecture: Simplified from 7+ layers to 3 core components
```

---

## 2. Technology Stack

### Frontend Technologies
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Core | Vanilla JavaScript | ES6+ | Application logic |
| Audio Capture | Web Audio API | Native | Professional audio recording |
| Encoding | Custom WAV Encoder | 1.0 | LINEAR16 PCM generation |
| WebSocket | Native WebSocket API | Native | Real-time communication |
| UI Framework | None (Vanilla) | - | Minimal dependencies |
| Build Tool | Custom build.js | 1.0 | Production bundling |

### Backend Technologies
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Framework | FastAPI | 0.104.0 | WebSocket server |
| Language | Python | 3.11 | Backend runtime |
| STT | Google Cloud Speech | v1 | Dutch speech recognition |
| Translation | Google Cloud Translate | v2 | Dutch to English |
| TTS | Google Cloud TTS | v1 | English speech synthesis |
| Async | asyncio | Native | Concurrent processing |
| Package Manager | Poetry | 1.8.5 | Dependency management |

### Infrastructure
| Component | Service | Configuration |
|-----------|---------|---------------|
| Hosting (Frontend) | Firebase Hosting | Auto-SSL, CDN |
| Compute (Backend) | Cloud Run | 2 CPU, 4GB RAM |
| Container | Docker | Multi-stage build |
| Registry | Artifact Registry | europe-west1 |
| Monitoring | Cloud Logging | Real-time logs |

---

## 3. System Architecture

### High-Level Architecture
```
┌─────────────┐      WebSocket       ┌──────────────┐      GCP APIs      ┌─────────────┐
│   Browser   │◄────────────────────►│   Cloud Run  │◄──────────────────►│  Google     │
│  Frontend   │      Audio/Data       │   Backend    │   STT/Trans/TTS   │  Cloud      │
└─────────────┘                       └──────────────┘                    └─────────────┘
     │                                       │
     ▼                                       ▼
[Web Audio API]                    [Connection Manager]
[WAV Encoder]                      [Pipeline Processing]
[UI Controls]                      [Error Recovery]
```

### Component Interaction Flow
```
1. Audio Capture (Frontend)
   └─► WAV Encoding (LINEAR16 PCM)
       └─► WebSocket Send (2-second chunks - PROBLEM!)
           └─► Backend Receipt
               └─► STT Processing (0.55s avg)
                   └─► Translation (0.05s avg)
                       └─► TTS Synthesis (0.17s avg)
                           └─► Broadcast to Listeners
                               └─► Audio Playback (Frontend)
```

### WebSocket Endpoints
| Endpoint | Purpose | Protocol | Data Format |
|----------|---------|----------|-------------|
| `/ws/speak/{stream_id}` | Speaker audio input | Binary | WAV LINEAR16 |
| `/ws/listen/{stream_id}` | Listener audio output | Binary | MP3 audio |
| `/ws/stream/{stream_id}` | Streaming STT (planned) | Binary | Raw audio chunks |

---

## 4. Detailed Component Specifications

### 4.1 Frontend Components

#### Audio Capture System
```javascript
// Current Implementation
class ProfessionalAudioRecorder {
    // Configuration
    sampleRate: 16000 Hz
    channels: 1 (mono)
    bitDepth: 16
    chunkSize: 4096 samples
    chunkIntervalMs: 2000 // CRITICAL ISSUE - should be 250ms
    
    // Audio Pipeline
    getUserMedia() → MediaStream
    → AudioContext (16kHz)
    → ScriptProcessorNode
    → Float32Array buffer
    → WAV Encoder
    → Binary WebSocket
}
```

#### WAV Encoder Specification
```javascript
class WAVEncoder {
    // WAV Header Structure
    RIFF Header: 'RIFF' + size + 'WAVE'
    Format Chunk: 'fmt ' + PCM(1) + mono(1) + 16kHz + 16-bit
    Data Chunk: 'data' + size + PCM samples
    
    // Encoding Process
    Float32 [-1.0, 1.0] → Int16 [-32768, 32767]
    Little-endian byte order
    No compression
}
```

#### WebSocket Connection Manager
```javascript
class ConnectionManager {
    // Retry Logic
    maxRetries: 3
    retryDelayBase: 1000ms (exponential backoff)
    connectionTimeout: 5000ms
    
    // Message Protocol
    Binary messages only
    No text frame support
    Automatic reconnection on disconnect
}
```

### 4.2 Backend Components

#### Connection Manager
```python
class ConnectionManager:
    # Thread-safe broadcasting
    _streams: Dict[str, List[WebSocket]]
    
    # Methods
    add_listener(stream_id, websocket)
    remove_listener(stream_id, websocket)
    broadcast_to_stream(stream_id, data)
    
    # Features
    - Multiple listeners per stream
    - Automatic cleanup on disconnect
    - Thread-safe operations
```

#### Audio Processing Pipeline
```python
async def minimal_audio_pipeline(audio_chunk: bytes):
    # Current Configuration
    MIN_CHUNK_SIZE = 8000 bytes  # ~0.25s at 16kHz
    
    # Processing Steps with Timing
    1. STT (0.55s avg):
       - model: "latest_short"
       - language: "nl-NL"
       - enhanced: True
       
    2. Translation (0.05s avg):
       - source: "nl"
       - target: "en"
       
    3. TTS (0.17s avg):
       - voice: "en-US-Neural2-D" (MALE)
       - format: MP3
       - rate: 1.1x
    
    # Total: ~0.77s per chunk
```

#### Streaming STT Service (Unused but Available!)
```python
class StreamingSpeechToText:
    # Existing Infrastructure
    - Google Cloud Streaming API ready
    - Interim results support
    - Continuous recognition
    - 321 lines of production code
    
    # Just needs wiring up to main.py!
```

---

## 5. API Specifications

### 5.1 REST Endpoints

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| GET | `/health` | Health check | `{"status": "ok", "version": "1.0.0-minimal"}` |
| GET | `/stats` | Performance metrics | Pipeline and connection statistics |
| GET | `/` | API documentation | FastAPI auto-generated docs |

### 5.2 WebSocket Protocol

#### Message Format
```
Speaker → Backend:
[Binary Frame]
├── WAV Header (44 bytes)
└── PCM Audio Data (65,536 bytes typically)

Backend → Listeners:
[Binary Frame]
└── MP3 Audio Data (variable size)
```

#### Connection Lifecycle
```
1. Connect: ws://[host]/ws/speak/[stream_id]
2. Send: Binary audio chunks every 2000ms (ISSUE!)
3. Receive: Status updates (if any)
4. Disconnect: Clean close or timeout
```

---

## 6. Data Flow Specifications

### 6.1 Audio Data Flow
```
Microphone Input (Analog)
    ↓ [ADC at 16kHz]
Browser Audio Buffer (Float32)
    ↓ [WAV Encoder]
WAV Binary (LINEAR16 PCM)
    ↓ [WebSocket]
Backend Buffer (bytes)
    ↓ [Google STT]
Dutch Text (string)
    ↓ [Google Translate]
English Text (string)
    ↓ [Google TTS]
MP3 Audio (bytes)
    ↓ [WebSocket Broadcast]
Browser Audio Element (MP3)
    ↓ [DAC]
Speaker Output (Analog)
```

### 6.2 Timing Analysis
```
Current Pipeline (per 2-second chunk):
├── Capture & Encode: ~50ms
├── Network (to backend): ~20ms
├── STT Processing: 550ms
├── Translation: 50ms
├── TTS Synthesis: 170ms
├── Network (to frontend): ~20ms
├── Audio Playback Start: ~10ms
└── Total: ~870ms (but 2s chunks = 2.5s perceived latency!)
```

---

## 7. Configuration & Settings

### 7.1 Frontend Configuration
```javascript
// config.js
CONFIG = {
    WEBSOCKET_URL: {
        development: 'ws://localhost:8000',
        production: 'wss://hybrid-stt-service-*.run.app'
    },
    AUDIO: {
        CHUNK_INTERVAL_MS: 1000,  // Ignored! Hardcoded to 2000
        MAX_CHUNK_SIZE: 150KB,
        USE_WEB_AUDIO_API: true
    }
}
```

### 7.2 Backend Configuration
```python
# Environment Variables
GOOGLE_APPLICATION_CREDENTIALS = "credentials/service-account.json"
PROJECT_ID = "your-project-id"
REGION = "europe-west1"

# Runtime Settings
MIN_CHUNK_SIZE = 8000  # bytes
MAX_RETRIES = 2
TIMEOUT = 10.0  # seconds
```

---

## 8. Performance Characteristics

### Current Performance Metrics
| Metric | Value | Target | Gap |
|--------|-------|--------|-----|
| Chunk Interval | 2000ms | 250ms | 8x improvement needed |
| Processing Time | 770ms | <200ms | 3.8x improvement needed |
| Word Capture | 43% | 95% | Major fix required |
| Empty Chunks | 57% | <5% | VAD needed |
| Concurrent Users | 10 | 50+ | Scaling required |

### Bottleneck Analysis
1. **Primary Bottleneck**: 2-second fixed chunking (wavEncoder.js:114)
2. **Secondary**: No streaming STT (using batch mode)
3. **Tertiary**: Sequential processing (no pipelining)
4. **Hidden Issue**: Sending silence (no VAD)

---

## 9. Security & Authentication

### Current Security Model
- **No authentication** (open access)
- **HTTPS/WSS** in production
- **Service account** for GCP APIs
- **No PII storage**
- **Stateless design**

### Security Considerations
```yaml
Risks:
- Open WebSocket endpoints (DoS potential)
- No rate limiting
- No user isolation

Mitigations:
- Cloud Run auto-scaling limits
- Firewall rules
- Monitoring alerts
```

---

## 10. Deployment Architecture

### Container Structure
```dockerfile
# Multi-stage Dockerfile
FROM node:18-slim AS frontend-builder
→ Build frontend assets
→ Minify and bundle

FROM python:3.11-slim
→ Install Poetry dependencies  
→ Copy backend code
→ Copy frontend dist
→ Run with uvicorn
```

### Cloud Run Configuration
```yaml
service: hybrid-stt-service
region: europe-west1
cpu: 2
memory: 4Gi
minInstances: 2
maxInstances: 20
concurrency: 50
```

### CI/CD Pipeline
```bash
# Current deployment process
1. gcloud builds submit
2. gcloud run deploy
3. Firebase hosting deploy
```

---

## 11. Monitoring & Observability

### Logging
- **Cloud Logging**: All stdout/stderr
- **Log Levels**: INFO for operations, ERROR for failures
- **Structured Logs**: JSON format with context

### Metrics
```python
# Currently tracked
pipeline_stats = {
    "total_requests": int,
    "successful_requests": int,
    "failed_requests": int,
    "avg_processing_time": float,
    "stt_avg_time": float,
    "translation_avg_time": float,
    "tts_avg_time": float
}
```

### Alerting
- Cloud Run 5xx errors
- Memory/CPU usage > 80%
- Cold start frequency

---

## 12. Known Issues & Technical Debt

### Critical Issues
1. **Hardcoded 2s chunks** (wavEncoder.js:114) - Causes 57% word loss
2. **Unused streaming code** - 321 lines of streaming_stt.py sitting idle
3. **Config not passed through** - Frontend ignores configuration values
4. **No VAD** - Sending silence wastes processing

### Technical Debt
- ScriptProcessorNode deprecated (should use AudioWorklet)
- No WebRTC for lower latency
- Missing integration tests
- No performance benchmarks
- Manual deployment process

---

## 13. Optimization Opportunities

### Immediate Fixes (< 1 day)
```javascript
// Change wavEncoder.js line 114
this.chunkIntervalMs = 250;  // From 2000
```

### Short-term (< 1 week)
- Wire up streaming_stt.py
- Implement basic VAD
- Add parallel processing
- Reduce chunk sizes

### Long-term (> 1 week)
- WebRTC for direct streaming
- Edge processing with WASM
- Custom models for Dutch
- Multi-language support

---

## 14. Testing Strategy

### Current Test Coverage
```bash
# Backend: 75 tests
pytest backend/tests/  # 98% pass rate

# Frontend: 33 tests  
npm test  # 88% pass rate

# Integration: Manual only
```

### Test Categories
- Unit tests: Core functions
- Integration tests: API calls
- Performance tests: Latency measurements
- Load tests: Concurrent users
- E2E tests: Full pipeline

---

## 15. API Rate Limits & Quotas

### Google Cloud Quotas
| Service | Quota | Current Usage | Limit |
|---------|-------|---------------|-------|
| Speech-to-Text | 300 min/month | ~50 min/day | Within limit |
| Translation | 500K chars/month | ~100K/day | Within limit |
| Text-to-Speech | 1M chars/month | ~200K/day | Within limit |

### Optimization Strategies
- Caching common translations
- Batching where possible
- Silence detection to reduce STT calls
- Rate limiting per user

---

*Document Version: 1.0*
*Last Updated: 2025-01-16*
*Architecture: Phase 3 Minimal Implementation*