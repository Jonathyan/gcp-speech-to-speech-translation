# Live Speech-to-Speech Translation Service
## High-Level Project Plan & Technical Specification

---

## 1. Executive Summary

### Project Overview
Real-time speech-to-speech translation service designed for live events (conferences, church services, meetings). The system captures audio from professional mixing consoles via audio interfaces, translates speech in real-time using Google Cloud APIs, and broadcasts translated audio to multiple listeners through a web interface.

### Key Features
- **Professional Audio Input**: Direct integration with mixing consoles via audio interfaces
- **Real-time Translation**: Sub-200ms latency from speech to translated output
- **Multi-listener Broadcasting**: One speaker, multiple listeners per session
- **Web-based Interface**: No app installation required
- **Production-ready Architecture**: Scalable GCP deployment

### Success Criteria
- **Latency**: <200ms end-to-end translation latency
- **Audio Quality**: Professional-grade audio processing
- **Scalability**: Support 100+ concurrent listeners per session
- **Reliability**: 99.9% uptime during live events

---

## 2. Architecture Overview

### System Architecture
```
Audio Console → Audio Interface → Browser (Web Audio API) → WAV Chunks
    ↓
Cloud Run Service (FastAPI + WebSockets) → Translation Pipeline
    ↓
Google Cloud APIs: Speech-to-Text → Translation → Text-to-Speech
    ↓
Broadcast to Listeners → Web Audio API Playback
```

### Technology Stack
- **Frontend**: HTML5, CSS3, JavaScript (Web Audio API)
- **Backend**: Python 3.9+, FastAPI, WebSockets
- **Cloud Platform**: Google Cloud Platform
- **Deployment**: Cloud Run + Firebase Hosting
- **Audio Format**: WAV (LINEAR16, 16kHz, Mono)
- **Testing**: pytest, jest
- **Dependency Management**: Poetry

---

## 3. Technical Specifications

### 3.1 Audio Processing Requirements

#### Input Specifications
```yaml
Audio Interface Input:
  - Sample Rate: 48kHz (native) → 16kHz (processed)
  - Bit Depth: 24-bit → 16-bit
  - Channels: Mono (left channel from stereo if needed)
  - Input Type: Line level (mixing console output)
  - Connector: 1/4" TRS or XLR → USB interface

Web Audio API Settings:
  - echoCancellation: false
  - noiseSuppression: false  
  - autoGainControl: false
  - latencyHint: 'interactive'
```

#### Processing Pipeline
```yaml
Audio Processing Flow:
  1. Capture: Web Audio API (AudioContext)
  2. Chunk: 250ms segments (4000 samples @ 16kHz)
  3. Encode: Custom WAV encoder with proper headers
  4. Stream: WebSocket transmission to Cloud Run
  5. Decode: Direct processing (no conversion needed)
```

### 3.2 Backend API Specifications

#### WebSocket Endpoints
```yaml
Speaker Endpoint: /ws/speak/{session_id}
  - Receives: Binary WAV chunks
  - Processes: STT → Translation → TTS pipeline
  - Sends: Translated WAV chunks to listeners

Listener Endpoint: /ws/listen/{session_id}
  - Receives: Translated WAV chunks
  - Buffers: Audio queue management
  - Plays: Seamless audio stream

Admin Endpoint: /ws/admin/{session_id}
  - Monitors: Real-time session metrics
  - Controls: Session management
```

#### Google Cloud API Integration
```yaml
Speech-to-Text API:
  encoding: LINEAR16
  sample_rate_hertz: 16000
  language_code: nl-NL
  enable_automatic_punctuation: true
  model: latest_long

Translation API:
  source_language: nl
  target_language: en
  format: text

Text-to-Speech API:
  language_code: en-US
  voice_name: en-US-Wavenet-D
  audio_encoding: LINEAR16
  sample_rate_hertz: 16000
```

### 3.3 Data Models

#### Session Management
```python
class Session:
    session_id: str
    speaker_connection: WebSocket
    listener_connections: List[WebSocket]
    created_at: datetime
    status: SessionStatus
    audio_metrics: AudioMetrics

class AudioMetrics:
    input_level: float
    processing_latency: float
    translation_accuracy: float
    listener_count: int
```

#### WebSocket Message Types
```python
class AudioChunk:
    type: Literal["audio_chunk"]
    session_id: str
    chunk_data: bytes
    timestamp: float
    sequence_number: int

class SessionStatus:
    type: Literal["session_status"]
    session_id: str
    speaker_connected: bool
    listener_count: int
    audio_level: float
```

---

## 4. Development Phases

### Phase 1: Core Infrastructure (Iterations 1-7)
**Timeline: 2-3 weeks**

#### Iteration 1: Basic WebSocket Server
- **Goal**: Establish FastAPI WebSocket foundation
- **Test**: WebSocket connection handshake success
- **Implementation**: Basic `/ws` endpoint with connection acceptance

#### Iteration 2: Echo Service with Error Handling  
- **Goal**: Validate bidirectional communication
- **Test**: JSON message echo functionality
- **Implementation**: Message receive/send loop with error handling

#### Iteration 3: Mock Translation Pipeline
- **Goal**: Simulate complete processing flow
- **Test**: Binary audio input → processed binary audio output
- **Implementation**: Three async mock functions (STT, Translation, TTS)

#### Iteration 4: Google Speech-to-Text Integration
- **Goal**: Replace STT mock with real API
- **Test**: WAV audio → Dutch text transcription
- **Implementation**: Real Google Cloud STT API integration

#### Iteration 5: Google Translation Integration
- **Goal**: Add translation capability
- **Test**: Dutch text → English text translation
- **Implementation**: Google Cloud Translation API integration

#### Iteration 6: Google Text-to-Speech Integration
- **Goal**: Complete translation pipeline
- **Test**: English text → English audio generation
- **Implementation**: Google Cloud TTS API integration

#### Iteration 7: Multi-listener Broadcasting
- **Goal**: Support multiple concurrent listeners
- **Test**: One speaker → multiple listeners receive audio
- **Implementation**: Connection manager with session-based broadcasting

### Phase 2: Professional Audio Frontend (Iterations 8-11)
**Timeline: 2-3 weeks**

#### Iteration 8: Audio Interface Detection & Setup
- **Goal**: Detect and configure professional audio interfaces
- **Test**: Audio interface enumeration and selection
- **Implementation**: Device detection, constraint validation

#### Iteration 9: Web Audio API Recording
- **Goal**: Professional-grade audio capture
- **Test**: Audio interface → WAV chunks with proper settings
- **Implementation**: Web Audio API with pro audio constraints

#### Iteration 10: Custom WAV Encoding
- **Goal**: Reliable WAV format generation
- **Test**: Raw audio samples → valid LINEAR16 WAV format
- **Implementation**: Custom WAV encoder with proper headers

#### Iteration 11: Real-time Audio Monitoring
- **Goal**: Live audio level and quality monitoring
- **Test**: Real-time level detection and silence handling
- **Implementation**: Audio analysis, level meters, quality alerts

### Phase 3: Advanced Playback & UI (Iterations 12-15)
**Timeline: 1-2 weeks**

#### Iteration 12: Seamless Audio Playback
- **Goal**: Continuous, buffer-managed audio output
- **Test**: Incoming audio chunks → seamless audio stream
- **Implementation**: Audio queue management, smooth playback

#### Iteration 13: Production UI Components
- **Goal**: Professional interface for live events
- **Test**: UI component functionality and responsiveness
- **Implementation**: Speaker dashboard, listener interface, admin panel

#### Iteration 14: Session Management
- **Goal**: Create, join, and manage translation sessions
- **Test**: Session lifecycle management
- **Implementation**: Session creation, joining, monitoring

#### Iteration 15: Error Handling & Recovery
- **Goal**: Robust error handling for live events
- **Test**: Network failures, API errors, audio device issues
- **Implementation**: Automatic reconnection, fallback strategies

### Phase 4: Production Deployment (Iterations 16-18)
**Timeline: 1 week**

#### Iteration 16: Cloud Run Deployment
- **Goal**: Scalable backend deployment
- **Test**: Production deployment with environment variables
- **Implementation**: Dockerfile, Cloud Run configuration

#### Iteration 17: Firebase Hosting Setup
- **Goal**: Frontend deployment and CDN
- **Test**: Frontend deployment with backend connectivity
- **Implementation**: Firebase configuration, domain setup

#### Iteration 18: Monitoring & Analytics
- **Goal**: Production monitoring and observability
- **Test**: Metrics collection and alerting
- **Implementation**: Cloud Monitoring, logging, performance tracking

---

## 5. File Structure

```
gcp-speech-translation/
├── backend/
│   ├── src/
│   │   ├── main.py                 # FastAPI application
│   │   ├── websocket_handler.py    # WebSocket logic
│   │   ├── audio_processor.py      # Audio processing pipeline
│   │   ├── google_apis.py          # Google Cloud API clients
│   │   ├── session_manager.py      # Session and connection management
│   │   └── models.py               # Data models
│   ├── tests/
│   │   ├── test_websocket.py       # WebSocket tests
│   │   ├── test_audio_processing.py # Audio pipeline tests
│   │   ├── test_google_apis.py     # API integration tests
│   │   └── fixtures/               # Test audio files
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── index.html              # Main interface
│   │   ├── speaker.html            # Speaker dashboard
│   │   ├── listener.html           # Listener interface
│   │   ├── admin.html              # Admin panel
│   │   ├── js/
│   │   │   ├── audio-recorder.js   # Web Audio API recording
│   │   │   ├── audio-player.js     # Audio playback management
│   │   │   ├── wav-encoder.js      # Custom WAV encoding
│   │   │   ├── websocket-client.js # WebSocket communication
│   │   │   └── session-manager.js  # Session management
│   │   └── css/
│   │       ├── main.css            # Main styles
│   │       └── components.css      # Component styles
│   ├── tests/
│   │   ├── audio-recorder.test.js  # Audio recording tests
│   │   ├── wav-encoder.test.js     # WAV encoding tests
│   │   └── websocket-client.test.js # WebSocket tests
│   ├── firebase.json
│   └── package.json
├── docs/
│   ├── api-documentation.md
│   ├── deployment-guide.md
│   └── user-manual.md
├── deployment/
│   ├── cloudbuild.yaml
│   ├── terraform/                  # Infrastructure as code
│   └── scripts/                    # Deployment scripts
└── README.md
```

---

## 6. Performance Requirements

### Latency Targets
```yaml
End-to-end Latency Budget (Total: <200ms):
  - Audio capture & encoding: <20ms
  - WebSocket transmission: <10ms
  - Speech-to-Text processing: <80ms
  - Translation processing: <30ms
  - Text-to-Speech processing: <50ms
  - Audio playback buffering: <10ms
```

### Scalability Requirements
```yaml
Concurrent Capacity:
  - Sessions per Cloud Run instance: 50
  - Listeners per session: 200
  - Audio chunk throughput: 1000 chunks/second
  - Bandwidth per listener: 32KB/second (WAV)
```

### Audio Quality Requirements
```yaml
Audio Specifications:
  - Dynamic range: >90dB
  - Frequency response: 20Hz-20kHz (input), 100Hz-8kHz (processed)
  - Latency jitter: <5ms
  - Packet loss tolerance: <1%
```

---

## 7. Security & Compliance

### Data Protection
```yaml
Audio Data Handling:
  - No permanent storage of audio content
  - In-memory processing only
  - Automatic cleanup after session end
  - GDPR-compliant data handling

API Security:
  - Google Cloud service account authentication
  - Environment variable configuration
  - Rate limiting on WebSocket connections
  - Input validation and sanitization
```

### Network Security
```yaml
Transport Security:
  - WSS (WebSocket Secure) for all connections
  - HTTPS for all HTTP endpoints
  - CORS configuration for frontend
  - Firebase Hosting security headers
```

---

## 8. Testing Strategy

### Unit Testing
```yaml
Backend Tests:
  - WebSocket connection handling
  - Audio processing pipeline
  - Google API integration
  - Session management logic

Frontend Tests:
  - Web Audio API functionality
  - WAV encoding accuracy
  - WebSocket communication
  - UI component behavior
```

### Integration Testing
```yaml
End-to-end Tests:
  - Complete audio translation pipeline
  - Multi-listener broadcasting
  - Error handling and recovery
  - Performance under load
```

### Load Testing
```yaml
Performance Tests:
  - Concurrent session capacity
  - Audio processing throughput
  - WebSocket connection limits
  - Memory usage patterns
```

---

## 9. Deployment Configuration

### Environment Variables
```yaml
Backend Environment:
  GOOGLE_APPLICATION_CREDENTIALS: /path/to/service-account.json
  PROJECT_ID: your-gcp-project-id
  SPEECH_TO_TEXT_MODEL: latest_long
  TRANSLATION_TARGET_LANGUAGE: en
  TTS_VOICE_NAME: en-US-Wavenet-D
  
Cloud Run Configuration:
  CPU: 2 vCPU
  Memory: 4Gi
  Max instances: 10
  Concurrency: 100
  Timeout: 300s
```

### Firebase Configuration
```yaml
Hosting Configuration:
  Public directory: frontend/src
  Rewrites: SPA routing
  Headers: Security headers
  Caching: Static asset optimization
```

---

## 10. Monitoring & Observability

### Key Metrics
```yaml
Performance Metrics:
  - End-to-end translation latency
  - Audio processing throughput
  - WebSocket connection count
  - API response times

Business Metrics:
  - Active sessions count
  - Total listeners served
  - Session duration average
  - Error rate by component

Resource Metrics:
  - Cloud Run CPU/memory usage
  - Network bandwidth consumption
  - Google API usage and costs
  - Firebase hosting traffic
```

### Alerting
```yaml
Critical Alerts:
  - Translation latency >200ms
  - Error rate >1%
  - Cloud Run instance failures
  - Google API quota exceeded

Warning Alerts:
  - High CPU/memory usage
  - WebSocket disconnection rate
  - Audio quality degradation
  - Unusual traffic patterns
```

---

This specification provides a comprehensive blueprint for implementing the live speech-to-speech translation service with professional audio support. Each iteration builds incrementally toward a production-ready system optimized for live events.