# Live Speech Translation System - Developer Handover

## Project Overview

This is a **real-time Dutch-to-English speech translation system** using Google Cloud Platform services. The system captures Dutch audio via WebSocket, processes it through Google Cloud STT → Translation → TTS APIs, and delivers English audio back to listeners in real-time.

### **Live System URLs**
- **Frontend**: https://lfhs-translate.web.app
- **Backend**: https://hybrid-stt-service-ysw2dobxea-ew.a.run.app
- **Architecture**: Speaker/Listener broadcasting model with stream isolation

## Architecture Overview

```
[Dutch Speaker] → [WebSocket] → [Cloud Run] → [Google APIs] → [WebSocket] → [English Listeners]
                    Frontend        Backend      STT→Trans→TTS      Frontend
```

### **Technology Stack**
- **Frontend**: Vanilla JavaScript, Firebase Hosting
- **Backend**: Python FastAPI, Google Cloud Run
- **APIs**: Google Cloud Speech-to-Text, Translation, Text-to-Speech
- **Communication**: WebSockets with binary audio streaming
- **Testing**: Jest (Frontend), pytest (Backend)

## Project Structure

```
├── backend/                          # Python FastAPI backend
│   ├── main.py                      # FastAPI app with WebSocket endpoints
│   ├── connection_manager.py        # Thread-safe broadcasting system
│   ├── services.py                  # Google Cloud API integration
│   ├── hybrid_stt_service.py       # Phase 2 Hybrid STT Service
│   ├── config.py                   # Environment configuration
│   ├── resilience.py               # Circuit breaker & retry logic
│   └── tests/                      # Backend test suite (75 tests)
│
├── frontend/                        # JavaScript frontend
│   ├── src/
│   │   ├── config.js               # Environment & WebSocket config
│   │   ├── connection.js           # WebSocket management
│   │   ├── audio.js                # Audio recording/playback
│   │   ├── ui.js                  # UI management & event handling
│   │   └── app.js                 # Application initialization
│   ├── tests/                     # Frontend test suite (33 tests)
│   ├── dist/                      # Production build output
│   └── firebase.json              # Firebase hosting configuration
│
├── CLAUDE.md                       # Project documentation for AI assistants
├── gcp-plan.md                    # Firebase deployment plan
├── DEPLOYMENT.md                  # Cloud Run deployment guide
└── requirements.txt               # Python dependencies
```

## Development History & Phases

### **Phase 1: Basic Pipeline (Iterations 1-6)**
- WebSocket server with echo service
- Mock API pipeline development
- Google Cloud API integration (STT, Translation, TTS)
- Error handling and resilience patterns
- **Status**: ✅ Complete, 75 backend tests passing

### **Phase 2: Hybrid Streaming (Iterations 7-10)**
- Broadcasting to multiple listeners (1-to-many)
- Connection quality monitoring
- Hybrid streaming/buffered mode switching
- Performance optimization and fallback mechanisms
- **Status**: ✅ Complete, production-ready

### **Phase 3: Production Deployment (Iteration 11)**
- Firebase frontend deployment
- Cloud Run backend deployment
- End-to-end integration testing
- **Status**: ✅ Live and operational

## Key Components

### **Backend Services**

#### **main.py** - FastAPI Application
```python
# Key endpoints:
GET  /health                    # Health check
GET  /health/phase2            # Phase 2 system health
POST /ws/speak/{stream_id}     # Speaker WebSocket
POST /ws/listen/{stream_id}    # Listener WebSocket
```

#### **connection_manager.py** - Broadcasting System
```python
class ConnectionManager:
    # Thread-safe 1-to-many WebSocket broadcasting
    # Stream isolation by stream_id
    # Automatic cleanup of disconnected clients
```

#### **services.py** - Google Cloud Integration
```python
# Real Google Cloud API implementations:
- real_speech_to_text()      # Dutch audio → text
- real_translation()         # Dutch text → English text  
- real_text_to_speech()      # English text → audio
```

#### **hybrid_stt_service.py** - Phase 2 System
```python
class HybridSTTService:
    # Intelligent switching between streaming/buffered modes
    # Quality monitoring and fallback orchestration
    # Performance metrics and adaptive behavior
```

### **Frontend Components**

#### **config.js** - Environment Management
```javascript
WEBSOCKET_URL: {
    development: 'ws://localhost:8000',
    production: 'wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app'
}
```

#### **connection.js** - WebSocket Management
```javascript
// Speaker/Listener endpoint routing:
// /ws/speak/{stream_id}  - Send Dutch audio
// /ws/listen/{stream_id} - Receive English audio
```

#### **audio.js** - Audio Processing
```javascript
// MediaRecorder for audio capture (250ms chunks)
// Audio playback with MP3 format support
// Browser compatibility handling
```

## Deployment Architecture

### **Production Infrastructure**
- **Frontend**: Firebase Hosting (https://lfhs-translate.web.app)
- **Backend**: Google Cloud Run (auto-scaling, serverless)
- **Authentication**: Service account `speech-translator@lfhs-translate.iam.gserviceaccount.com`
- **APIs**: Cloud Speech, Translation, Text-to-Speech

### **Environment Configuration**

#### **Google Cloud Project**: `lfhs-translate`
Required APIs enabled:
- Cloud Speech-to-Text API
- Cloud Translation API  
- Cloud Text-to-Speech API
- Cloud Run API
- Firebase Hosting API

#### **Service Account Permissions**:
```bash
# Runtime permissions:
roles/speech.editor
roles/translate.editor  
roles/texttospeech.editor
roles/logging.logWriter
roles/monitoring.metricWriter

# Deployment permissions:
roles/iam.serviceAccountUser
roles/run.developer
roles/storage.admin
```

## Development Setup

### **Prerequisites**
```bash
# Required tools:
- Python 3.9+
- Node.js 16+
- Google Cloud SDK
- Firebase CLI
- Docker (for deployment)
```

### **Backend Development**
```bash
cd backend/

# Install dependencies
poetry install

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="credentials/service-account.json"

# Run development server
poetry run uvicorn backend.main:app --reload

# Run all tests (75 tests)
poetry run pytest

# Run specific test suites
poetry run pytest backend/tests/test_connection_manager.py -v
poetry run pytest backend/tests/test_translation_performance.py -v -s
```

### **Frontend Development**
```bash
cd frontend/

# Install dependencies  
npm install

# Run tests (33 tests)
npm test

# Development server
npm run serve  # http://localhost:3000

# Production build
npm run build
npm run serve:prod
```

## Testing Strategy

### **Backend Tests (75 tests, TDD approach)**
- **Unit Tests**: Individual component testing
- **Integration Tests**: Google Cloud API integration
- **Performance Tests**: Translation speed and reliability
- **Connection Tests**: WebSocket broadcasting and error handling

### **Frontend Tests (33 tests, Jest + jsdom)**
- **Audio Tests**: MediaRecorder and playback functionality  
- **Connection Tests**: WebSocket client behavior
- **UI Tests**: Button states and user interactions
- **Integration Tests**: Cloud Run connectivity

### **End-to-End Testing**
```bash
# Test the complete system:
1. Open https://lfhs-translate.web.app (2 tabs)
2. Tab 1: Enter stream ID → "Start Uitzending" → Speak Dutch
3. Tab 2: Same stream ID → "Luister mee" → Hear English
```

## Key Configuration Files

### **Backend Configuration**
- **`pyproject.toml`**: Python dependencies and build config
- **`backend/config.py`**: Environment variables and settings
- **`Dockerfile`**: Multi-stage build for Cloud Run
- **`deploy.sh`**: Cloud Run deployment script

### **Frontend Configuration**  
- **`package.json`**: Node.js dependencies and scripts
- **`firebase.json`**: Hosting config with security headers
- **`build.js`**: Production build process
- **`.firebaserc`**: Firebase project configuration

## Operational Monitoring

### **Health Checks**
- **Backend**: `/health`, `/health/phase2`, `/ready`
- **Frontend**: Production build validation
- **System**: End-to-end translation flow testing

### **Performance Metrics**
- **Latency**: End-to-end translation time (<3 seconds)
- **Success Rate**: API call success rates
- **Connection Quality**: WebSocket stability monitoring
- **Error Tracking**: Circuit breaker and retry statistics

### **Logging & Debugging**
```bash
# View Cloud Run logs:
gcloud logs tail --follow --project=lfhs-translate

# Firebase hosting logs:
firebase serve --debug

# Local backend debugging:
poetry run uvicorn backend.main:app --reload --log-level debug
```

## Common Issues & Solutions

### **WebSocket Connection Issues**
```javascript
// Check browser console for:
- Mixed content warnings (http/https)
- CORS preflight failures  
- WebSocket connection timeouts
```

### **Audio Playback Problems**
```javascript
// Common causes:
- Browser autoplay restrictions
- Microphone permission denied
- Unsupported audio formats
```

### **Google Cloud API Errors**
```python
# Check service account permissions:
- GOOGLE_APPLICATION_CREDENTIALS path
- API quotas and billing
- Service account role assignments
```

### **Deployment Issues**
```bash
# Backend deployment:
- Docker platform architecture (linux/amd64)
- Environment variable configuration
- Service account authentication

# Frontend deployment:  
- Firebase project initialization
- Build output validation
- Production WebSocket URLs
```

## Development Workflow

### **Making Changes**

1. **Backend Changes**:
   ```bash
   # Write tests first (TDD)
   poetry run pytest backend/tests/test_new_feature.py -v
   
   # Implement feature
   # Run all tests
   poetry run pytest
   
   # Deploy to Cloud Run
   ./deploy.sh
   ```

2. **Frontend Changes**:
   ```bash
   # Write tests first
   npm test tests/new-feature.test.js
   
   # Implement feature
   # Run all tests
   npm test
   
   # Build and deploy
   npm run build
   firebase deploy
   ```

3. **Full System Testing**:
   ```bash
   # Test locally first:
   # Backend: poetry run uvicorn backend.main:app --reload
   # Frontend: npm run serve
   
   # Then test production endpoints
   ```

## Scaling & Future Enhancements

### **Potential Improvements**
- **Multi-language Support**: Add more language pairs
- **Audio Quality**: Implement noise reduction and audio preprocessing
- **Performance**: Add Redis caching for frequent translations
- **Analytics**: User session tracking and usage metrics
- **Mobile**: Progressive Web App (PWA) features
- **Security**: Add authentication and rate limiting

### **Scaling Considerations**
- **Backend**: Cloud Run auto-scales based on requests
- **Database**: Consider Cloud Firestore for session persistence  
- **CDN**: Firebase hosting includes global CDN
- **APIs**: Monitor Google Cloud quotas and costs

## Emergency Contacts & Resources

### **Documentation**
- **Project Instructions**: `CLAUDE.md` (for AI assistants)
- **Deployment Guide**: `DEPLOYMENT.md`
- **Firebase Setup**: `gcp-plan.md`

### **External Resources**
- **Google Cloud Console**: https://console.cloud.google.com/run/detail/europe-west1/hybrid-stt-service
- **Firebase Console**: https://console.firebase.google.com/project/lfhs-translate
- **Live Frontend**: https://lfhs-translate.web.app
- **Live Backend**: https://hybrid-stt-service-ysw2dobxea-ew.a.run.app/health

### **Repository Status**
- **Branch**: `local-prototype` (contains latest production code)
- **Main Branch**: `master` (use for pull requests)
- **Tests**: 75 backend + 33 frontend tests passing
- **Coverage**: >95% backend, ~88% frontend

---

## Final Notes

This system represents a complete, production-ready real-time speech translation solution. The architecture is designed for reliability, scalability, and maintainability. The TDD approach ensures robust testing coverage, and the deployment infrastructure provides automatic scaling and high availability.

**Key Success Metrics**:
- ✅ Real-time translation latency <3 seconds
- ✅ Multi-listener broadcasting working
- ✅ 108/108 total tests passing
- ✅ Production deployment operational
- ✅ End-to-end system validation complete

The system is ready for production use and can handle multiple concurrent translation sessions with automatic scaling through Google Cloud Run.

**Last Updated**: August 14, 2025  
**System Status**: Production Ready ✅