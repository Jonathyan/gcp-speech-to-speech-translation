# Frontend - Live Speech Translation

🎤 **Production-ready web interface** for real-time speech-to-speech translation with comprehensive audio streaming capabilities.

## ✨ Features

- **Real-time Audio Streaming** - 250ms chunks via WebSocket
- **Production Audio Playback** - Web Audio API with queue management and memory optimization
- **Advanced Error Recovery** - Circuit breaker patterns with automatic recovery mode
- **User Experience Excellence** - Dutch error messages, progress indicators, quality monitoring
- **Audio System Management** - AudioContext suspension handling and user gesture prompts
- **Comprehensive Diagnostics** - System health reports and troubleshooting recommendations
- **Multi-browser Support** - Automatic format detection and fallback

## 🚀 Quick Start

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Development mode:**
```bash
npm run serve
```
Open http://localhost:3000

3. **Production build:**
```bash
npm run build
npm run serve:prod
```

## 📁 Project Structure

```
frontend/
├── public/           # Static files
│   ├── index.html    # Main interface
│   └── *.html        # Test pages
├── src/              # Source modules
│   ├── config.js     # Production audio configuration
│   ├── audio.js      # Audio recording & processing
│   ├── audioPlayer.js# Audio playback & error recovery
│   ├── connection.js # WebSocket streaming
│   ├── ui.js         # User interface & diagnostics
│   └── utils.js      # Browser compatibility & utilities
├── tests/            # Comprehensive test suite
├── dist/             # Production build output
└── build.js          # Build script
```

## 🎯 User Interface

### Main Controls
- **Start Uitzending** - Begin broadcasting with microphone access
- **Luister mee** - Join as listener with stream ID
- **Test Microfoon** - Quick microphone access test
- **Start Opname** - Record audio with real-time validation
- **Diagnostiek** - Run comprehensive system diagnostics

### Visual Feedback
- **Audio Loading Indicators** - Progress bars with detailed loading messages
- **Quality Monitoring** - Real-time audio quality assessment with color coding
- **Audio Level Visualization** - Live audio level meter with dynamic colors
- **Error Dialogs** - Comprehensive error information with diagnostic data
- **Recovery Messages** - Success indicators when system recovers from errors
- **Real-time Status** - Stream info, chunk processing, and performance metrics

## ⚙️ Configuration

### Audio Settings (Production)
```javascript
AUDIO: {
  CHUNK_INTERVAL_MS: 250,        // Real-time streaming
  MAX_CHUNK_SIZE: 100 * 1024,    // 100KB limit
  AUDIO_CONSTRAINTS: {
    audio: {
      sampleRate: 16000,         // Optimal for speech
      channelCount: 1,           // Mono audio
      echoCancellation: true,    // Noise reduction
      noiseSuppression: true,    // Audio enhancement
      autoGainControl: true      // Volume normalization
    }
  },
  SUPPORTED_MIME_TYPES: ['audio/webm', 'audio/mp4', 'audio/wav']
}
```

### Environment Settings
- **Development:** `ws://localhost:8000/ws`
- **Production:** `wss://your-domain.com/ws`

## 🧪 Testing

### Automated Tests (210 tests with production coverage)
```bash
# Run all tests
npm test

# Error Recovery & User Experience (17 tests)
npm test -- --testNamePattern="Error Recovery & User Experience"

# Specific test suites
npm test tests/audioPlayer.test.js  # Audio playback & error recovery
npm test tests/ui.test.js           # User interface & diagnostics
npm test tests/connection.test.js   # WebSocket streaming
npm test tests/utils.test.js        # Utility functions
npm test tests/audio.test.js        # Audio capture & processing
```

### Manual Testing Procedures
1. **Microphone Test** - Click "Test Microfoon"
2. **Recording Test** - Click "Start Opname" 
3. **Broadcast Test** - Click "Start Uitzending"
4. **Diagnostics Test** - Click "Diagnostiek"
5. **Error Recovery** - Deny microphone access

## 🛡️ Advanced Error Recovery & Circuit Breaker

### Production-Ready Error Recovery
- **Circuit Breaker Patterns** - Automatic recovery mode after 10+ consecutive failures
- **Exponential Backoff with Jitter** - Smart retry logic with adaptive delays
- **Memory Pressure Detection** - Emergency cleanup when approaching browser limits
- **AudioContext Suspension Recovery** - User gesture prompts for audio activation
- **Quality-Based Adaptive Behavior** - System adjusts based on real-time performance

### User Experience Excellence (Dutch)
- **Context-Aware Error Messages** - Specific suggestions based on error type:
  - **Network Errors** - "Controleer uw internetverbinding en herlaad de pagina"
  - **Audio Context Issues** - "Audio systeem geblokkeerd - klik ergens op de pagina"
  - **Memory Pressure** - "Herlaad de pagina om geheugen vrij te maken"
- **Progressive Error Dialogs** - Comprehensive diagnostic information with recovery options
- **Success Recovery Messages** - "✅ Audio systeem hersteld" notifications

## 📊 Diagnostics & Performance

### Comprehensive System Health Monitoring
- **Audio Player Health Reports** - Queue size, memory usage, success rates
- **Real-time Quality Assessment** - Latency, stability, and performance metrics
- **Browser Capability Detection** - Web Audio API, MediaRecorder, WebSocket support
- **Performance Troubleshooting** - Context-aware recommendations based on system state
- **Memory Usage Analysis** - Buffer pool monitoring and memory pressure detection

### Advanced Performance Metrics
```javascript
// AudioPlayer Performance Metrics
{
  overall: 'Good',                    // Quality assessment
  audioContext: { state: 'running' },
  playback: { queueSize: 3, isPlaying: true },
  performance: { 
    processedChunks: 150, 
    droppedChunks: 2,
    avgLatency: 75 
  },
  memory: { queueMemory: '2.1MB' },
  errors: { successRate: '98.67%' },
  troubleshooting: ['Systeem werkt normaal']
}
```

## 🌐 Browser Support

### Supported Browsers
- **Chrome 16+** - Full WebRTC and MediaRecorder support
- **Firefox 11+** - Complete WebSocket and audio features
- **Safari 7+** - Modern audio API support
- **Edge 12+** - Full compatibility

### Automatic Fallbacks
- **Audio Formats** - webm → mp4 → wav fallback chain
- **Feature Detection** - Graceful degradation for unsupported features
- **Compatibility Warnings** - User notifications for limited browsers

## 🚀 Deployment

### Production Build
```bash
npm run build
# Optimized files in dist/ directory
```

### Static Hosting
```bash
# Any static file server
npm run serve:prod

# Firebase Hosting
firebase deploy --only hosting

# Nginx/Apache
# Serve dist/ directory
```

## 🔍 Troubleshooting

### Common Issues
- **WebSocket Connection Failed** - Check backend server status
- **Microphone Access Denied** - Browser permissions required
- **Audio Format Unsupported** - Check browser compatibility
- **Rate Limiting** - Reduce chunk frequency

### Debug Information
Open browser console for detailed logging:
- Audio chunk processing
- WebSocket connection events
- Error recovery attempts
- Performance metrics

### Diagnostics Tool
Click "Diagnostiek" button for:
- Complete system capability report
- Audio system testing
- Performance analysis
- Troubleshooting recommendations

## 🏗️ Architecture

### Modular Design
- **config.js** - Production audio configuration & format detection
- **audio.js** - MediaRecorder integration with error recovery
- **audioPlayer.js** - Web Audio API with circuit breaker patterns and memory optimization
- **connection.js** - WebSocket streaming with AudioPlayer integration
- **ui.js** - User experience with comprehensive error handling and diagnostics
- **utils.js** - Browser compatibility & utility functions

### Key Technologies
- **Web Audio API** - Advanced audio playback with AudioContext management
- **MediaRecorder API** - Audio capture and processing
- **WebSocket** - Real-time binary data streaming
- **getUserMedia** - Microphone access with constraints
- **Performance API** - Memory monitoring and metrics collection
- **Circuit Breaker Pattern** - Resilient error recovery architecture

## 📈 Production Ready

✅ **Audio Streaming Pipeline** - Real-time 250ms chunks with WebSocket streaming  
✅ **Audio Playback System** - Web Audio API with queue management and memory optimization  
✅ **Circuit Breaker Resilience** - Automatic recovery mode with exponential backoff  
✅ **User Experience Excellence** - Dutch error messages with actionable suggestions  
✅ **Comprehensive Diagnostics** - System health reports and troubleshooting  
✅ **Performance Monitoring** - Real-time quality assessment and metrics  
✅ **Browser Compatibility** - Multi-browser support with graceful fallbacks  
✅ **Test Coverage** - 210 tests with production-ready error recovery coverage  
✅ **Memory Management** - Buffer pooling and emergency cleanup mechanisms  

Ready for production deployment with enterprise-grade reliability, comprehensive error recovery, and exceptional user experience.