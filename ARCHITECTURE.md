# Architecture Overview

Real-time Speech-to-Speech Translation Service - Dutch to English via Google Cloud APIs

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
│  │  • MediaRecorder    │         │  • Audio Playback   │                       │
│  │  • getUserMedia()   │         │  • MP3 Audio        │                       │
│  │  • WebSocket        │         │  • WebSocket        │                       │
│  │  • 250ms chunks     │         │  • Real-time play   │                       │
│  └─────────────────────┘         └─────────────────────┘                       │
│           │                               │                                     │
│           │ WebM/WAV Audio                │ MP3 Audio                          │
│           │ (16kHz mono)                  │ (Real-time)                        │
│           ▼                               ▲                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
           │                               │
           │ /ws/speak/{stream_id}         │ /ws/listen/{stream_id}
           │                               │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               APPLICATION LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                            FASTAPI SERVER                              │   │
│  │                               (main.py)                                │   │
│  │                                                                         │   │
│  │  ┌─────────────────────┐    ┌──────────────────┐    ┌──────────────┐   │   │
│  │  │   WebSocket         │    │  Connection       │    │  Health      │   │   │
│  │  │   Endpoints         │    │  Manager         │    │  Checks      │   │   │
│  │  │                     │    │                  │    │              │   │   │
│  │  │ • /ws/speak/{id}    │    │ • Thread-safe    │    │ • /health/*  │   │   │
│  │  │ • /ws/listen/{id}   │    │ • Broadcasting   │    │ • API Tests  │   │   │
│  │  │ • Rate Limiting     │    │ • 1-to-many      │    │ • Pipeline   │   │   │
│  │  │ • Error Handling    │    │ • Auto cleanup   │    │ • Individual │   │   │
│  │  └─────────────────────┘    └──────────────────┘    └──────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                         │
│                                      ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         PROCESSING PIPELINE                            │   │
│  │                            (services.py)                               │   │
│  │                                                                         │   │
│  │  Audio Buffer ──► STT Service ──► Translation ──► TTS Service ──► MP3  │   │
│  │       │              │              │              │             │     │   │
│  │   WebM/WAV      Dutch Text     English Text    Audio MP3     Broadcast│   │
│  │   Chunks         (nl-NL)         (en-US)       (Wavenet-D)           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               INFRASTRUCTURE LAYER                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         RESILIENCE PATTERNS                            │   │
│  │                          (resilience.py)                               │   │
│  │                                                                         │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │   │
│  │  │   Circuit    │    │    Retry     │    │   Timeout    │              │   │
│  │  │   Breaker    │    │   Logic      │    │   Handling   │              │   │
│  │  │              │    │              │    │              │              │   │
│  │  │ • 5 failures │    │ • 3 attempts │    │ • 15s limit  │              │   │
│  │  │ • 30s reset  │    │ • Exp. back. │    │ • Per stage  │              │   │
│  │  │ • Fallback   │    │ • Fast fail  │    │ • Graceful   │              │   │
│  │  └──────────────┘    └──────────────┘    └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                         │
│                                      ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       GOOGLE CLOUD SERVICES                            │   │
│  │                                                                         │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │   │
│  │  │ Speech-to-   │    │ Translation  │    │ Text-to-     │              │   │
│  │  │ Text API     │    │    API v2    │    │ Speech API   │              │   │
│  │  │              │    │              │    │              │              │   │
│  │  │ • LINEAR16   │    │ • Dutch→Eng  │    │ • Wavenet-D  │              │   │
│  │  │ • Auto punct │    │ • Auto detect│    │ • MP3 format │              │   │
│  │  │ • 16kHz mono │    │ • Batch proc │    │ • Neutral    │              │   │
│  │  └──────────────┘    └──────────────┘    └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Component Overview

### Frontend (JavaScript/Browser)
- **Audio Capture**: MediaRecorder with getUserMedia() for microphone access
- **WebSocket Client**: Bi-directional communication with rate limiting
- **Audio Playback**: Direct MP3 playback with fallback beep system
- **UI Management**: Dutch interface with connection status and controls

### Backend (FastAPI/Python)
- **WebSocket Server**: Handles speaker/listener connections with stream isolation  
- **Connection Manager**: Thread-safe broadcasting for 1-to-many communication
- **Processing Pipeline**: STT → Translation → TTS with buffering and optimization
- **Health Monitoring**: Comprehensive API testing and service validation

### Google Cloud Integration
- **Speech-to-Text**: Real-time audio transcription (Dutch → Text)
- **Translation API**: Text translation (Dutch → English)
- **Text-to-Speech**: Audio synthesis (English Text → MP3)

### Resilience & Reliability
- **Circuit Breaker**: Prevents cascade failures, opens after 5 consecutive errors
- **Retry Logic**: Exponential backoff with 3 attempts per operation
- **Timeout Handling**: 15-second pipeline timeout with graceful fallbacks
- **Fallback Audio**: Test beep markers when APIs fail

## Data Flow

1. **Audio Capture**: Browser captures 250ms audio chunks via MediaRecorder
2. **WebSocket Upload**: Audio sent to `/ws/speak/{stream_id}` endpoint
3. **Audio Processing**: ffmpeg conversion to LINEAR16 PCM format
4. **Speech Recognition**: Google Cloud STT converts Dutch audio to text
5. **Translation**: Google Translate converts Dutch text to English
6. **Speech Synthesis**: Google Cloud TTS generates English MP3 audio
7. **Broadcasting**: Translated audio sent to all `/ws/listen/{stream_id}` connections
8. **Playback**: Browsers directly play MP3 audio or fallback beeps

## Deployment Architecture

### Development Environment
- **Backend**: `uvicorn backend.main:app --reload` (localhost:8000)
- **Frontend**: Static files served via `npm run serve` (localhost:3000)
- **Testing**: Comprehensive test suites (75 backend + 33 frontend tests)

### Production Considerations
- **WebSocket URLs**: Configurable development vs production endpoints
- **Audio Settings**: Optimized 16kHz mono recording with noise suppression
- **Error Handling**: Graceful degradation with user-visible status updates
- **Performance**: <1s end-to-end latency for real-time translation

## Key Design Patterns

### Stream Isolation
Multiple independent translation streams via unique `stream_id` routing, allowing concurrent sessions without interference.

### Broadcasting Pattern
One speaker broadcasts to multiple listeners through the Connection Manager's thread-safe implementation.

### Buffered Processing
Audio chunks are accumulated before STT processing to improve recognition accuracy and reduce API costs.

### Resilience First
Every external API call is wrapped with circuit breakers, retries, and timeouts to ensure system stability.

This architecture prioritizes real-time performance, reliability, and scalability while maintaining simplicity in deployment and maintenance.

## Application Layer Deep Dive

The application layer serves as the orchestration hub, managing WebSocket connections, processing pipelines, and coordinating between multiple STT processing modes. This section explores the internal architecture of the core application modules.

### Application Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              APPLICATION LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                              main.py                                   │   │
│  │                         (FastAPI Application)                          │   │
│  │                                                                         │   │
│  │  ┌─────────────┐  ┌────────────────┐  ┌──────────────┐  ┌─────────────┐ │   │
│  │  │ Startup/    │  │   WebSocket    │  │    Health    │  │  Phase 2    │ │   │
│  │  │ Shutdown    │  │   Endpoints    │  │   Checks     │  │   Hybrid    │ │   │
│  │  │ Management  │  │                │  │              │  │    STT      │ │   │
│  │  │             │  │ • Speaker WS   │  │ • /health/*  │  │  Service    │ │   │
│  │  │ • GCP Init  │  │ • Listener WS  │  │ • API Tests  │  │             │ │   │
│  │  │ • Service   │  │ • Legacy WS    │  │ • Pipeline   │  │ • Hybrid    │ │   │
│  │  │   Setup     │  │ • Rate Limit   │  │ • Individual │  │ • Streaming │ │   │
│  │  │ • Cleanup   │  │ • Error Hand.  │  │ • Phase2 STT │  │ • Fallback  │ │   │
│  │  └─────────────┘  └────────────────┘  └──────────────┘  └─────────────┘ │   │
│  │                                  │                                       │   │
│  │                                  ▼                                       │   │
│  │  ┌───────────────────────────────────────────────────────────────────┐   │   │
│  │  │                    Connection Manager                            │   │   │
│  │  │                 (connection_manager.py)                          │   │   │
│  │  │                                                                   │   │   │
│  │  │  • Thread-safe stream management                                 │   │   │
│  │  │  • 1-to-many broadcasting with stream isolation                  │   │   │
│  │  │  • Automatic cleanup of failed connections                       │   │   │
│  │  │  • Stream-based listener groups                                  │   │   │
│  │  └───────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        Processing Pipeline                             │   │
│  │                           (services.py)                                │   │
│  │                                                                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │
│  │  │ Enhanced    │  │ Real STT    │  │ Translation │  │ Text-to-    │   │   │
│  │  │ STT Buffer  │  │ Service     │  │ Service     │  │ Speech      │   │   │
│  │  │             │  │             │  │             │  │ Service     │   │   │
│  │  │ • Audio     │  │ • LINEAR16  │  │ • Dutch→Eng │  │ • Wavenet-D │   │   │
│  │  │   Buffering │  │ • Auto punc │  │ • Auto det. │  │ • MP3 out   │   │   │
│  │  │ • WebM conv │  │ • 16kHz     │  │ • Batch     │  │ • Streaming │   │   │
│  │  │ • Chunk     │  │ • Retry     │  │   process   │  │ • Quality   │   │   │
│  │  │   analysis  │  │   logic     │  │ • Caching   │  │   voice     │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │   │
│  │                                                                         │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │                   Phase 2 Hybrid STT System                    │   │   │
│  │  │                  (hybrid_stt_service.py)                       │   │   │
│  │  │                                                                 │   │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │   │   │
│  │  │  │ Adaptive    │  │ Streaming   │  │ Connection  │            │   │   │
│  │  │  │ Stream      │  │ STT         │  │ Quality     │            │   │   │
│  │  │  │ Buffer      │  │ Manager     │  │ Monitor     │            │   │   │
│  │  │  │             │  │             │  │             │            │   │   │
│  │  │  │ • Mode det. │  │ • Sessions  │  │ • Latency   │            │   │   │
│  │  │  │ • Quality   │  │ • Real-time │  │ • Success   │            │   │   │
│  │  │  │   analysis  │  │ • Callbacks │  │   rate      │            │   │   │
│  │  │  │ • Adaptive  │  │ • Cleanup   │  │ • Quality   │            │   │   │
│  │  │  │   buffering │  │             │  │   scoring   │            │   │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘            │   │   │
│  │  │                                │                                │   │   │
│  │  │                                ▼                                │   │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐   │   │   │
│  │  │  │               Fallback Orchestrator                    │   │   │
│  │  │  │            (fallback_orchestrator.py)                  │   │   │
│  │  │  │                                                         │   │   │
│  │  │  │ • Mode decision logic (streaming vs buffered)          │   │   │
│  │  │  │ • Failure tracking and recovery attempts               │   │   │
│  │  │  │ • Quality-based fallback triggers                      │   │   │
│  │  │  │ • Global and per-stream statistics                     │   │   │
│  │  │  │ • Automatic mode switching based on performance        │   │   │
│  │  │  └─────────────────────────────────────────────────────────┘   │   │   │
│  │  └─────────────────────────────────────────────────────────────────┐   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      Reliability & Configuration                        │   │
│  │                                                                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │
│  │  │ Circuit     │  │ Resilience  │  │ Config      │  │ Retry       │   │   │
│  │  │ Breaker     │  │ Patterns    │  │ Management  │  │ Decorators  │   │   │
│  │  │             │  │             │  │             │  │             │   │   │
│  │  │ • 5 fail    │  │ • Tenacity  │  │ • Pydantic  │  │ • Exp. back │   │   │
│  │  │   threshold │  │ • Timeout   │  │ • Env vars  │  │ • 3 attempts│   │   │
│  │  │ • 30s reset │  │ • Graceful  │  │ • Type safe │  │ • Error     │   │   │
│  │  │ • Fallback  │  │   degraded  │  │ • Defaults  │  │   propag.   │   │   │
│  │  │   audio     │  │   modes     │  │ • Phase 2   │  │             │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Core Module Breakdown

#### main.py - Application Entry Point

**Responsibilities:**
- **FastAPI Application Setup**: Configures the ASGI server with title, description, and version
- **Service Initialization**: Manages startup/shutdown of Google Cloud clients and STT services  
- **WebSocket Route Management**: Defines endpoints for speaker/listener connections
- **Health Check System**: Comprehensive API testing endpoints for monitoring
- **Phase 2 Integration**: Initializes and manages the Hybrid STT Service

**Key Components:**
```
┌─────────────────────────────────────────────────────────────────┐
│                           main.py                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Global State Management                                        │
│  ├─ speech_client: Google Cloud STT client                     │
│  ├─ translation_client: Google Translate client                │
│  ├─ tts_client: Google Text-to-Speech client                   │
│  ├─ hybrid_stt_service: Phase 2 Hybrid STT coordinator        │
│  └─ connection_manager: WebSocket broadcast manager            │
│                                                                 │
│  WebSocket Endpoints                                            │
│  ├─ /ws/speak/{stream_id}: Audio input from speakers          │
│  ├─ /ws/listen/{stream_id}: Audio output to listeners         │
│  └─ /ws: Legacy endpoint for backward compatibility            │
│                                                                 │
│  Health Check Endpoints                                         │
│  ├─ /health/speech: STT service connectivity                   │
│  ├─ /health/translation: Translation API testing               │
│  ├─ /health/tts: Text-to-Speech service validation            │
│  ├─ /health/full: Complete pipeline integration test          │
│  ├─ /health/enhanced: Phase 1 enhanced STT status             │
│  ├─ /health/phase2: Phase 2 hybrid STT diagnostics            │
│  ├─ /health: Main health endpoint for Cloud Run               │
│  └─ /ready: Readiness probe for container orchestration       │
│                                                                 │
│  Processing Pipeline Integration                                │
│  ├─ process_pipeline(): Main audio processing orchestrator     │
│  ├─ Circuit breaker integration with fallback audio           │
│  ├─ Timeout handling (15s pipeline limit)                     │
│  └─ Error handling with graceful degradation                  │
└─────────────────────────────────────────────────────────────────┘
```

#### services.py - Processing Pipeline

**Responsibilities:**  
- **Audio Format Conversion**: ffmpeg integration for WebM/WAV to LINEAR16 PCM
- **Google Cloud API Integration**: STT, Translation, and TTS service calls
- **Buffered Processing**: Enhanced STT with chunk accumulation and analysis
- **Streaming STT Service**: Real-time speech recognition with callback handling
- **Resilience Patterns**: Retry logic, timeout handling, and error classification

**Key Components:**
```
┌─────────────────────────────────────────────────────────────────┐
│                        services.py                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Audio Processing                                               │
│  ├─ convert_audio_to_linear16(): ffmpeg format conversion       │
│  ├─ Format detection (WebM, WAV, MP4)                          │
│  ├─ Robust error handling and fallback                         │
│  └─ Debug logging for audio analysis                           │
│                                                                 │
│  STT Services                                                   │
│  ├─ real_speech_to_text(): Production Google Cloud STT         │
│  ├─ BufferedSpeechToText: Chunk accumulation service           │
│  ├─ buffered_speech_to_text(): Enhanced STT with buffering     │
│  └─ StreamingSTTService: Real-time transcription management    │
│                                                                 │
│  Translation & TTS                                              │
│  ├─ real_translation(): Google Translate API v2                │
│  ├─ real_text_to_speech(): Wavenet voice synthesis            │
│  ├─ Translation caching to avoid re-processing                 │
│  └─ High-quality MP3 audio generation                          │
│                                                                 │
│  Mock Services (for testing)                                   │
│  ├─ mock_speech_to_text(): Simulated STT with error injection  │
│  ├─ mock_translation(): Test translation with timing           │
│  └─ mock_text_to_speech(): Test beep audio markers             │
│                                                                 │
│  Resilience Integration                                         │
│  ├─ @retry decorators with exponential backoff                 │
│  ├─ Timeout handling per service (10s default)                 │
│  ├─ Error classification and propagation                       │
│  └─ Graceful fallback with detailed logging                    │
└─────────────────────────────────────────────────────────────────┘
```

#### Phase 2 Hybrid STT System

**hybrid_stt_service.py - Orchestration Hub**
- **Mode Coordination**: Seamless switching between streaming and buffered processing  
- **Quality Monitoring**: Connection quality assessment and performance tracking
- **Fallback Management**: Intelligent mode switching based on performance metrics
- **Stream Management**: Per-stream state tracking and lifecycle management

**fallback_orchestrator.py - Decision Engine**
- **Processing Mode Logic**: Quality-based decision making for STT mode selection
- **Failure Tracking**: Per-stream and global failure statistics
- **Recovery Management**: Automatic recovery attempts with backoff logic  
- **Performance Analytics**: Comprehensive metrics and failure analysis

### Data Flow Through Application Layer

1. **WebSocket Connection**: Client connects to `/ws/speak/{stream_id}` or `/ws/listen/{stream_id}`
2. **Audio Chunk Reception**: Raw WebM/WAV audio received via WebSocket message
3. **Mode Decision**: Fallback orchestrator determines streaming vs buffered processing  
4. **Quality Assessment**: Connection quality monitor evaluates network performance
5. **Processing Execution**: Audio processed through selected STT pipeline
6. **Translation Pipeline**: Dutch text converted to English via Translation API
7. **Speech Synthesis**: English text converted to MP3 audio via TTS API
8. **Broadcasting**: Translated audio broadcasted to all stream listeners
9. **Error Handling**: Circuit breaker and retry logic manage API failures
10. **Fallback Audio**: Test beep markers sent when pipeline fails

### Configuration and Resilience

#### Configuration Management (config.py)
- **Environment Variables**: Comprehensive configuration via environment
- **Phase 2 Settings**: Streaming thresholds, quality parameters, fallback config
- **Service Timeouts**: Per-service timeout configuration with defaults
- **Cloud Run Integration**: Port, worker, and monitoring configuration

#### Resilience Patterns (resilience.py)  
- **Circuit Breaker**: 5-failure threshold with 30-second reset timeout
- **State Change Logging**: Comprehensive circuit breaker state monitoring
- **Integration Points**: Used throughout processing pipeline for fault tolerance

This application layer design enables high-throughput, fault-tolerant speech translation with intelligent mode switching and comprehensive observability.

## Infrastructure Layer 

The infrastructure layer provides the foundation for deploying, scaling, and monitoring the speech translation service in Google Cloud. This layer handles containerization, service orchestration, API management, and observability.

### Infrastructure Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             INFRASTRUCTURE LAYER                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        Google Cloud Platform                           │   │
│  │                                                                         │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │                        Cloud Run Service                       │   │   │
│  │  │                     (Serverless Container)                     │   │   │
│  │  │                                                                 │   │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │   │   │
│  │  │  │   Auto      │  │   HTTP/2    │  │   WebSocket │            │   │   │
│  │  │  │   Scaling   │  │   Load      │  │   Support   │            │   │   │
│  │  │  │             │  │   Balancer  │  │             │            │   │   │
│  │  │  │ • 1-10 inst │  │ • SSL Term. │  │ • Real-time │            │   │   │
│  │  │  │ • CPU/Mem   │  │ • Global    │  │ • Bi-direct │            │   │   │
│  │  │  │   based     │  │   CDN       │  │ • Stream    │            │   │   │
│  │  │  │ • Request   │  │ • DDoS      │  │   isolate   │            │   │   │
│  │  │  │   volume    │  │   protect   │  │             │            │   │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘            │   │   │
│  │  │                                                                 │   │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐   │   │   │
│  │  │  │              Container Configuration                  │   │   │   │
│  │  │  │                                                         │   │   │
│  │  │  │ • 2 CPU cores, 2GB memory per instance                │   │   │   │
│  │  │  │ • 10 concurrent requests per container                │   │   │   │
│  │  │  │ • 1-hour request timeout for long translations       │   │   │   │
│  │  │  │ • Health checks: /health (liveness), /ready (startup)│   │   │   │
│  │  │  │ • Non-root container execution for security          │   │   │   │
│  │  │  └─────────────────────────────────────────────────────────┘   │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                         │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │                      Google Cloud APIs                        │   │   │
│  │  │                                                                 │   │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │   │   │
│  │  │  │ Cloud       │  │ Translation │  │ Text-to-    │            │   │   │
│  │  │  │ Speech-to-  │  │ API v2      │  │ Speech API  │            │   │   │
│  │  │  │ Text API    │  │             │  │             │            │   │   │
│  │  │  │             │  │ • Dutch→Eng │  │ • Wavenet-D │            │   │   │
│  │  │  │ • Streaming │  │ • Auto det. │  │ • MP3/WAV   │            │   │   │
│  │  │  │ • Buffered  │  │ • Batch     │  │ • Multiple  │            │   │   │
│  │  │  │ • LINEAR16  │  │   process   │  │   voices    │            │   │   │
│  │  │  │ • Auto punc │  │ • Caching   │  │ • Quality   │            │   │   │
│  │  │  │ • Multi-lang│  │ • Rate mgmt │  │   control   │            │   │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘            │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                         │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │                    Identity & Access Management                │   │   │
│  │  │                                                                 │   │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │   │   │
│  │  │  │ Service     │  │   IAM       │  │   API       │            │   │   │
│  │  │  │ Account     │  │   Policies  │  │   Keys      │            │   │   │
│  │  │  │             │  │             │  │             │            │   │   │
│  │  │  │ • speech-   │  │ • Least     │  │ • Rotation  │            │   │   │
│  │  │  │   translator│  │   privilege │  │ • Quotas    │            │   │   │
│  │  │  │ • Editor    │  │ • Resource  │  │ • Rate      │            │   │   │
│  │  │  │   roles     │  │   scoped    │  │   limits    │            │   │   │
│  │  │  │ • Secure    │  │ • Audit     │  │ • Monitor   │            │   │   │
│  │  │  │   creds     │  │   logs      │  │             │            │   │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘            │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                     Containerization & Deployment                      │   │
│  │                                                                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │
│  │  │  Docker     │  │   Container │  │   Build     │  │   Deploy    │   │   │
│  │  │  Image      │  │   Registry  │  │   Pipeline  │  │   Script    │   │   │
│  │  │             │  │             │  │             │  │             │   │   │
│  │  │ • Multi-    │  │ • GCR       │  │ • Cloud     │  │ • Automated │   │   │
│  │  │   stage     │  │   hosting   │  │   Build     │  │ • API       │   │   │
│  │  │ • Python    │  │ • Versioned │  │ • Poetry    │  │   enable    │   │   │
│  │  │   3.11 slim │  │   tags      │  │   deps      │  │ • IAM setup │   │   │
│  │  │ • Non-root  │  │ • Security  │  │ • Health    │  │ • Service   │   │   │
│  │  │   user      │  │   scanning  │  │   checks    │  │   config    │   │   │
│  │  │ • Poetry    │  │             │  │             │  │             │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      Monitoring & Observability                        │   │
│  │                                                                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │
│  │  │   Cloud     │  │   Cloud     │  │   Error     │  │   Service   │   │   │
│  │  │   Logging   │  │ Monitoring  │  │  Reporting  │  │  Health     │   │   │
│  │  │             │  │             │  │             │  │  Checks     │   │   │
│  │  │ • Structured│  │ • Metrics   │  │ • Exception │  │ • /health   │   │   │
│  │  │   logs      │  │ • Dashboards│  │   tracking  │  │ • /ready    │   │   │
│  │  │ • Log       │  │ • Alerting  │  │ • Stack     │  │ • /health/* │   │   │
│  │  │   aggreg.   │  │ • SLO/SLI   │  │   traces    │  │ • Phase 2   │   │   │
│  │  │ • Search    │  │ • Custom    │  │ • Auto      │  │   diagnostics│   │   │
│  │  │ • Export    │  │   metrics   │  │   grouping  │  │             │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Infrastructure Components

#### Cloud Run Service Configuration

**Serverless Container Platform**
- **Auto-scaling**: 1-10 instances based on traffic and resource utilization
- **Resource Allocation**: 2 CPU cores, 2GB memory per instance optimized for ML workloads
- **Concurrent Requests**: 10 requests per container to balance throughput and stability
- **Request Timeout**: 1-hour maximum for long-running translation sessions
- **Generation 2**: Latest Cloud Run runtime with improved performance and WebSocket support

**Network & Security**
- **Global Load Balancer**: Automatic SSL termination and DDoS protection
- **CDN Integration**: Static content delivery optimization
- **WebSocket Support**: Full-duplex real-time communication for audio streaming
- **Ingress Control**: Configurable public/private access with IAM integration

#### Container Architecture

**Multi-stage Docker Build**
```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Builder Stage (python:3.11-slim)                              │
│  ├─ System dependencies (gcc, g++, curl)                       │
│  ├─ Poetry installation and configuration                      │
│  ├─ Dependency resolution and installation                     │
│  └─ Build artifact caching                                     │
│                                                                 │
│  Production Stage (python:3.11-slim)                           │
│  ├─ Minimal runtime dependencies                               │
│  ├─ Non-root user (appuser) for security                      │
│  ├─ Virtual environment from builder stage                     │
│  ├─ Application code with proper ownership                     │
│  ├─ Health check configuration                                 │
│  └─ Uvicorn ASGI server startup                               │
└─────────────────────────────────────────────────────────────────┘
```

**Security Hardening**
- **Non-root Execution**: Container runs as dedicated `appuser` with minimal privileges
- **Minimal Attack Surface**: Slim base image with only required runtime components
- **Dependency Management**: Poetry lock files ensure reproducible builds
- **Health Monitoring**: Built-in health checks for container lifecycle management

#### Google Cloud API Integration

**Speech-to-Text API**
- **Streaming Recognition**: Real-time audio processing with WebSocket connections
- **Batch Processing**: Buffered audio chunks for improved accuracy
- **Multi-format Support**: WebM, WAV, LINEAR16 PCM with automatic conversion
- **Language Models**: Latest short-form and long-form speech recognition models

**Translation API v2**
- **Language Pairs**: Dutch to English with automatic source detection
- **Batch Processing**: Efficient translation of multiple text segments
- **Caching Layer**: Translation results cached to reduce API calls and costs
- **Quality Metrics**: Translation confidence scoring and validation

**Text-to-Speech API**
- **Wavenet Voices**: High-quality neural voice synthesis (en-US-Wavenet-D)
- **Multiple Formats**: MP3, WAV, LINEAR16 output with quality optimization
- **SSML Support**: Advanced speech markup for natural pronunciation
- **Voice Customization**: Gender, speed, and pitch adjustments

#### Identity & Access Management

**Service Account Configuration**
- **Least Privilege**: Minimal required permissions for each Google Cloud service
- **Resource Scoping**: Project-level access with service-specific roles
- **Credential Management**: Secure service account key rotation and storage
- **Audit Trail**: Comprehensive IAM activity logging

**API Security**
- **Quota Management**: Per-service rate limiting and usage monitoring  
- **Key Rotation**: Automated API key lifecycle management
- **Access Control**: IP-based restrictions and client authentication
- **Usage Analytics**: Real-time API consumption tracking and alerting

#### Deployment Pipeline

**Automated Deployment (deploy.sh)**
- **Prerequisites Validation**: gcloud CLI, Docker, and authentication checks
- **API Enablement**: Automatic activation of required Google Cloud services
- **Service Account Setup**: IAM role assignment and permission validation
- **Container Build**: Multi-stage Docker image creation and optimization
- **Registry Push**: Secure image upload to Google Container Registry
- **Service Deployment**: Cloud Run service configuration and deployment
- **Health Validation**: Post-deployment service health verification

**Configuration Management**
- **Environment Variables**: Comprehensive configuration via Cloud Run environment
- **Service Discovery**: Automatic endpoint registration and DNS setup
- **Version Control**: Tagged container images with rollback capability
- **Blue-Green Deployment**: Zero-downtime deployment with traffic splitting

#### Monitoring & Observability

**Cloud Logging Integration**
- **Structured Logging**: JSON-formatted logs with trace correlation
- **Log Aggregation**: Centralized collection from all container instances
- **Search & Filter**: Advanced log querying and real-time monitoring
- **Export & Archive**: Long-term log retention in Cloud Storage

**Cloud Monitoring**
- **Built-in Metrics**: CPU, memory, request latency, and error rates
- **Custom Metrics**: Application-specific performance indicators
- **SLO/SLI Definition**: Service level objectives for reliability tracking
- **Alert Policies**: Automated incident response and escalation

**Health Check System**
- **Multi-tier Health Checks**: Service, API, and pipeline validation
- **Dependency Monitoring**: Google Cloud service connectivity verification
- **Performance Metrics**: End-to-end latency and throughput measurement
- **Diagnostic Endpoints**: Detailed system status and debugging information

### Production Deployment Characteristics

**Scalability**
- **Horizontal Scaling**: 1-10 instances with automatic traffic distribution
- **Resource Efficiency**: Optimized container sizing for cost-performance balance
- **Global Availability**: Multi-region deployment capability with low-latency routing
- **WebSocket Persistence**: Session affinity for real-time connection maintenance

**Reliability**
- **Health Monitoring**: Liveness and readiness probes with automatic restart
- **Circuit Breaker Integration**: Application-level fault tolerance
- **Graceful Degradation**: Fallback audio and error recovery mechanisms
- **Disaster Recovery**: Multi-region deployment with automated failover

**Security**
- **Network Isolation**: VPC-based networking with private service communication
- **Encryption**: TLS termination and end-to-end data protection
- **Compliance**: SOC 2 and ISO 27001 certified infrastructure
- **Vulnerability Scanning**: Automated container image security analysis

This infrastructure layer provides a robust, scalable foundation for the speech translation service with enterprise-grade security, monitoring, and operational excellence.