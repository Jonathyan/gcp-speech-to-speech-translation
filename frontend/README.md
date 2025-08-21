# Frontend - Live Speech Translation Interface

> 🎤 **Production-ready web interface** for real-time Dutch-to-English speech translation with enterprise-grade audio streaming and error recovery.

[![Frontend Live](https://img.shields.io/badge/Live%20Demo-🌐%20ONLINE-green)](https://lfhs-translate.web.app)
[![Tests](https://img.shields.io/badge/Tests-210+%20Passing-green)](#-testing)
[![Browser Support](https://img.shields.io/badge/Browsers-Chrome%20|%20Firefox%20|%20Safari%20|%20Edge-blue)](#-browser-support)

**🔗 Part of**: [Dutch-to-English Speech Translation System](../README.md) | **📖 System Docs**: [Main README](../README.md) | **🔧 Development**: [CLAUDE.md](../CLAUDE.md)

## 🌟 **Live Demo & Quick Links**

- **🌐 Live Interface**: https://lfhs-translate.web.app
- **🎤 Speaker Mode**: Start broadcasting Dutch speech for real-time translation
- **👂 Listener Mode**: Join to receive translated English audio
- **📊 System Status**: [Backend Health](https://streaming-stt-service-ysw2dobxea-ew.a.run.app/health)

## ✨ **Key Features**

### **🎵 Real-time Audio Pipeline**
- **100ms streaming chunks** for minimal latency WebSocket transmission
- **Linear16 PCM encoding** optimized for Google Cloud Speech API
- **Advanced error recovery** with circuit breaker patterns and exponential backoff
- **Memory management** with buffer pooling and emergency cleanup mechanisms

### **🛡️ Production Reliability**  
- **Circuit breaker patterns** - Auto-recovery after 10+ consecutive failures
- **Exponential backoff with jitter** - Smart retry logic with adaptive delays
- **AudioContext suspension recovery** - User gesture prompts for audio activation
- **Quality-based adaptive behavior** - System adjusts based on real-time performance

### **🎯 User Experience Excellence**
- **Dutch interface** with context-aware error messages and recovery suggestions
- **Comprehensive diagnostics** - System health reports and troubleshooting recommendations
- **Visual feedback system** - Real-time audio levels, quality indicators, progress bars
- **Multi-browser support** - Automatic format detection with graceful fallbacks

## 🚀 **Quick Start**

### **For Development**

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Development server
npm run serve
# Opens http://localhost:3000

# Production build
npm run build
npm run serve:prod
```

### **For System Integration**

See [Main README - Development Setup](../README.md#-development-setup) for complete system setup including backend integration.

```bash
# From project root - full system development
./setup-devops-venv.sh                    # Setup DevOps tools
poetry run uvicorn backend.main:app --reload  # Backend (Terminal 1)
cd frontend && npm run serve               # Frontend (Terminal 2)
```

## 📁 **Frontend Architecture**

### **File Structure**

```
frontend/
├── 📱 User Interface
│   ├── public/
│   │   ├── index.html                    # Main application interface
│   │   ├── test-microphone.html          # Microphone testing page
│   │   ├── test-recording.html           # Audio recording validation
│   │   └── test-connection.html          # WebSocket connection testing
│   └── dist/                             # Production build output
│
├── 🎵 Core Audio System
│   ├── src/
│   │   ├── config.js                     # Production audio configuration
│   │   ├── wavEncoder.js                 # Linear16 PCM generation
│   │   ├── audio.js                      # MediaRecorder & streaming
│   │   ├── audioPlayer.js                # Web Audio API & error recovery
│   │   ├── connection.js                 # WebSocket streaming management
│   │   ├── ui.js                         # Dutch interface & diagnostics
│   │   └── utils.js                      # Browser compatibility & utilities
│
├── 🧪 Testing Infrastructure
│   ├── tests/
│   │   ├── audio.test.js                 # Audio capture & processing (45 tests)
│   │   ├── audioPlayer.test.js           # Playback & error recovery (52 tests)  
│   │   ├── connection.test.js            # WebSocket streaming (38 tests)
│   │   ├── ui.test.js                    # Interface & diagnostics (42 tests)
│   │   └── utils.test.js                 # Utilities & compatibility (33+ tests)
│   └── jest.config.js                    # Test configuration
│
├── 🚢 Deployment & Build
│   ├── build.js                          # Production build script
│   ├── deploy-frontend.sh                # Firebase deployment
│   ├── firebase.json                     # Firebase hosting config
│   └── package.json                      # Dependencies & scripts
│
└── 📖 Documentation
    ├── README.md                         # This file
    ├── FIREBASE_MANUAL_SETUP.md          # Firebase configuration guide
    └── manual-test-script.md             # Manual testing procedures
```

### **Core Components**

#### **🎵 Audio Processing Chain**
```javascript
Microphone → MediaRecorder → wavEncoder → WebSocket → Backend
    ↓              ↓             ↓           ↓
getUserMedia   100ms chunks   Linear16    Streaming STT
  (16kHz)      (real-time)     (PCM)      (Google Cloud)
```

#### **🔊 Audio Playback System**
```javascript
WebSocket ← Backend ← TTS ← Translation ← STT
    ↓          ↓        ↓        ↓         ↓
AudioPlayer  MP3    English   Dutch→EN   Dutch
(Web Audio)  chunks  audio     text      speech
```

## ⚙️ **Configuration**

### **Production Audio Settings**

```javascript
// src/config.js - Optimized for real-time performance
export const CONFIG = {
  AUDIO: {
    CHUNK_INTERVAL_MS: 100,               // Real-time streaming
    MAX_CHUNK_SIZE: 100 * 1024,           // 100KB limit  
    AUDIO_CONSTRAINTS: {
      audio: {
        sampleRate: 16000,                // Optimal for Google Speech
        channelCount: 1,                  // Mono audio
        echoCancellation: true,           // Noise reduction
        noiseSuppression: true,           // Audio enhancement
        autoGainControl: true             // Volume normalization
      }
    },
    SUPPORTED_MIME_TYPES: [
      'audio/webm;codecs=opus',           // Chrome, Firefox
      'audio/mp4',                        // Safari, Edge  
      'audio/wav'                         // Fallback
    ]
  },
  
  WEBSOCKET: {
    DEVELOPMENT: "ws://localhost:8000/ws",
    PRODUCTION: "wss://streaming-stt-service-ysw2dobxea-ew.a.run.app/ws"
  },
  
  ERROR_RECOVERY: {
    MAX_RETRIES: 10,                      // Circuit breaker threshold
    INITIAL_DELAY: 1000,                  // Base retry delay
    MAX_DELAY: 10000,                     // Maximum retry delay
    JITTER_FACTOR: 0.1                    // Randomization factor
  }
};
```

### **Environment Integration**

```bash
# Development - integrates with local backend
npm run serve
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000 (run separately)

# Production - connects to deployed backend
npm run build && npm run serve:prod
# Frontend: http://localhost:8080  
# Backend:  https://streaming-stt-service-ysw2dobxea-ew.a.run.app
```

## 🧪 **Testing**

### **Test Suite Overview** (210+ Tests)

| Test Category | Tests | Focus Area | Coverage |
|---------------|-------|------------|----------|
| **Audio System** | 45 tests | MediaRecorder, encoding, streaming | ✅ 95%+ |
| **Audio Player** | 52 tests | Playback, error recovery, memory | ✅ 98%+ |
| **WebSocket** | 38 tests | Connection management, retry logic | ✅ 90%+ |
| **User Interface** | 42 tests | Dutch UI, diagnostics, error handling | ✅ 85%+ |
| **Utilities** | 33+ tests | Browser compatibility, utilities | ✅ 95%+ |

### **Running Tests**

```bash
# All tests with coverage
npm test

# Specific test suites
npm test tests/audio.test.js              # Audio capture & processing
npm test tests/audioPlayer.test.js        # Audio playback & recovery
npm test tests/connection.test.js         # WebSocket streaming
npm test tests/ui.test.js                 # User interface & diagnostics
npm test tests/utils.test.js              # Browser compatibility

# Watch mode for development
npm test -- --watch

# Coverage report
npm test -- --coverage
open coverage/lcov-report/index.html
```

### **Test Categories**

#### **🎵 Audio System Tests**
```bash
# Test audio capture, encoding, and streaming
npm test tests/audio.test.js

# Key test areas:
# - MediaRecorder initialization and configuration
# - Linear16 PCM encoding via wavEncoder
# - Real-time 100ms chunk generation
# - Error handling for unsupported browsers
# - Memory management and cleanup
```

#### **🔊 Audio Player Tests**
```bash
# Test audio playback and error recovery
npm test tests/audioPlayer.test.js

# Key test areas:
# - Web Audio API integration and AudioContext management
# - Queue management with memory optimization
# - Circuit breaker patterns and exponential backoff
# - AudioContext suspension recovery
# - Performance metrics and health reporting
```

#### **🔗 WebSocket Tests**
```bash
# Test connection management and streaming
npm test tests/connection.test.js

# Key test areas:
# - WebSocket connection establishment and management
# - Binary data streaming (Linear16 PCM)
# - Connection retry logic with exponential backoff
# - Error recovery and automatic reconnection
# - Rate limiting and connection state management
```

## 🎯 **User Interface Guide**

### **Main Interface Controls**

#### **🎤 Speaker Mode**
```javascript
// Start broadcasting Dutch speech
document.getElementById('startBroadcast').click()
// → Requests microphone access
// → Connects to WebSocket
// → Begins real-time audio streaming
// → Shows audio level visualization
```

#### **👂 Listener Mode**  
```javascript
// Join as listener with stream ID
document.getElementById('startListening').click()
// → Connects to WebSocket for receiving
// → Initializes audio playback system
// → Shows connection status and audio queue
```

#### **🔧 Diagnostic Tools**
```javascript
// Run comprehensive system diagnostics  
document.getElementById('runDiagnostics').click()
// → Tests browser capabilities
// → Validates audio system health
// → Generates troubleshooting recommendations
// → Displays performance metrics
```

### **Visual Feedback System**

#### **🎵 Audio Level Visualization**
- **Green**: Good audio levels (optimal for speech recognition)
- **Yellow**: Acceptable levels (minor adjustments recommended)  
- **Red**: Poor levels (microphone adjustment needed)

#### **📊 Connection Status Indicators**
- **🟢 Connected**: WebSocket active, ready for streaming
- **🟡 Connecting**: Attempting connection with retry logic
- **🔴 Disconnected**: Connection failed, automatic retry in progress

#### **⚡ Performance Metrics**
- **Latency**: Real-time end-to-end processing time
- **Success Rate**: Percentage of successful audio chunk processing
- **Queue Status**: Audio playback buffer health and memory usage

## 🛡️ **Error Recovery & Circuit Breaker**

### **Advanced Error Recovery System**

```javascript
// Circuit breaker implementation with exponential backoff
class CircuitBreaker {
  constructor() {
    this.failures = 0;
    this.state = 'CLOSED';        // CLOSED → OPEN → HALF_OPEN
    this.threshold = 10;          // Failures before opening
    this.timeout = 30000;         // Recovery attempt interval
  }
  
  async execute(operation) {
    if (this.state === 'OPEN') {
      if (Date.now() - this.lastFailure > this.timeout) {
        this.state = 'HALF_OPEN';
      } else {
        throw new Error('Circuit breaker is OPEN');
      }
    }
    
    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }
}
```

### **Dutch Error Messages**

The system provides context-aware error messages in Dutch:

- **🔴 Network Errors**: "Controleer uw internetverbinding en herlaad de pagina"
- **🎤 Audio Context Issues**: "Audio systeem geblokkeerd - klik ergens op de pagina"  
- **💾 Memory Pressure**: "Herlaad de pagina om geheugen vrij te maken"
- **🔗 WebSocket Failures**: "Verbinding verbroken - automatisch opnieuw proberen..."
- **✅ Recovery Success**: "Audio systeem hersteld - verbinding actief"

## 🌐 **Browser Support**

### **Supported Browsers**

| Browser | Version | WebRTC | MediaRecorder | WebSocket | AudioContext |
|---------|---------|--------|---------------|-----------|--------------|
| **Chrome** | 16+ | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **Firefox** | 11+ | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **Safari** | 7+ | ✅ Limited | ✅ Limited | ✅ Full | ✅ Full |
| **Edge** | 12+ | ✅ Full | ✅ Full | ✅ Full | ✅ Full |

### **Automatic Fallbacks**

```javascript
// Audio format detection and fallback chain
const getSupportedMimeType = () => {
  const types = [
    'audio/webm;codecs=opus',    // Preferred: Chrome, Firefox
    'audio/mp4',                 // Fallback: Safari, Edge
    'audio/wav'                  // Last resort: Universal support
  ];
  
  return types.find(type => MediaRecorder.isTypeSupported(type)) || 'audio/wav';
};

// Feature detection with graceful degradation
if (!navigator.mediaDevices?.getUserMedia) {
  showCompatibilityWarning('Microphone access not supported');
}

if (!window.AudioContext && !window.webkitAudioContext) {
  showCompatibilityWarning('Web Audio API not supported');
}
```

## 🚢 **Deployment**

### **Production Build & Deployment**

```bash
# Build for production
npm run build
# → Creates optimized files in dist/
# → Minifies JavaScript and CSS
# → Optimizes assets for performance

# Deploy to Firebase Hosting
./deploy-frontend.sh
# → Builds production version
# → Deploys to Firebase Hosting
# → Updates live site at https://lfhs-translate.web.app

# Manual Firebase deployment
firebase deploy --only hosting
```

### **Integration with Backend Deployment**

See [Main README - Deployment](../README.md#-deployment--devops) for full system deployment:

```bash
# From project root - deploy complete system
./deploy-backend.sh                       # Backend with blue-green deployment
cd frontend && ./deploy-frontend.sh       # Frontend to Firebase

# Validate deployment
./validate-system.sh                      # Full system validation
./validate-system.sh frontend             # Frontend-specific checks
```

### **Environment Configuration**

```javascript
// Frontend automatically detects environment
const getWebSocketURL = () => {
  if (window.location.hostname === 'localhost') {
    return 'ws://localhost:8000/ws';       // Development
  }
  return 'wss://streaming-stt-service-ysw2dobxea-ew.a.run.app/ws';  // Production
};
```

## 🔍 **Troubleshooting**

### **Common Frontend Issues**

#### **🎤 Microphone Access Problems**
```bash
# Issue: "Microphone access denied"
# Solution: Check browser permissions and HTTPS requirement
# - Microphone requires HTTPS (except localhost)
# - Check browser permission settings: chrome://settings/content/microphone
# - Try refreshing page and re-granting permission
```

#### **🔊 Audio Playback Issues**
```bash
# Issue: "Audio not playing" or "AudioContext suspended"
# Solution: User interaction required for audio
# - Modern browsers require user gesture to start audio
# - Click anywhere on the page to activate AudioContext
# - Check browser console for specific AudioContext errors
```

#### **🔗 WebSocket Connection Failures**
```bash
# Issue: "WebSocket connection failed"
# Solution: Verify backend health and network connectivity
./validate-system.sh websocket            # Test WebSocket connectivity
curl -f https://streaming-stt-service-ysw2dobxea-ew.a.run.app/health  # Backend health
```

### **Debug Information**

Open browser console (F12) for detailed debugging:

```javascript
// Enable verbose logging
localStorage.setItem('audioDebug', 'true');
localStorage.setItem('connectionDebug', 'true');

// View audio system health
console.log('Audio System Health:', window.audioPlayer?.getHealthReport());

// View connection status
console.log('Connection Status:', window.connection?.getStatus());

// View performance metrics
console.log('Performance Metrics:', window.performanceMonitor?.getMetrics());
```

### **Performance Optimization**

```bash
# Check memory usage and performance
# Open Chrome DevTools → Performance tab → Record
# Look for:
# - Memory leaks in audio buffers
# - High CPU usage during audio processing
# - WebSocket message frequency and size

# Frontend performance validation
npm test tests/audioPlayer.test.js -- --verbose  # Memory and performance tests
npm test tests/utils.test.js -- --verbose        # Browser compatibility tests
```

## 🔗 **Integration with System**

### **Development Workflow Integration**

```bash
# Complete development setup (run from project root)
./setup-devops-venv.sh                    # DevOps environment
poetry install                            # Backend dependencies
cd frontend && npm install                # Frontend dependencies

# Daily development
poetry run uvicorn backend.main:app --reload  # Terminal 1: Backend
cd frontend && npm run serve               # Terminal 2: Frontend

# Testing during development
poetry run pytest                         # Backend tests
cd frontend && npm test                   # Frontend tests
./validate-system.sh                     # Integration tests
```

### **System Monitoring Integration**

The frontend integrates with system-wide monitoring:

```bash
# Frontend-specific health checks
./validate-system.sh frontend             # Frontend accessibility
./validate-system.sh integration         # Frontend-backend integration

# Performance monitoring
./validate-system.sh performance         # End-to-end performance including frontend
```

---

## 📄 **Additional Resources**

- **📖 System Documentation**: [Main README](../README.md)
- **🔧 Development Guide**: [CLAUDE.md](../CLAUDE.md)  
- **🏗️ Architecture Details**: [ARCHITECTURE.md](../ARCHITECTURE.md)
- **🧪 Testing Guide**: [END_TO_END_TESTING_GUIDE.md](../END_TO_END_TESTING_GUIDE.md)
- **🚢 DevOps Implementation**: [plan/devops-i2.md](../plan/devops-i2.md)

---

**🎯 Production-ready frontend with enterprise-grade audio streaming, comprehensive error recovery, and seamless system integration.**