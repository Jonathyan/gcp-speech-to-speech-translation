Geweldige timing! Je hebt een solide backend met complete broadcasting en een functionele frontend basis. Laten we Iteratie 9 opsplitsen in zeer kleine, LLM-vriendelijke micro-iteraties die veilig en incrementeel zijn.

## 🎯 Iteratie 9: Audio Capture & Streaming - Micro-Iteratie Plan

### Overzicht Transformatie
**VAN:** Frontend met alleen WebSocket connectie (geen audio)  
**NAAR:** Frontend met microfoon access + real-time audio streaming

---

## 📋 Micro-Iteratie 9A: Browser Audio Capabilities & Testing

### Step 9A.1: Browser Audio Support Detection (Test-First)
**Instructie voor LLM:**
```
Update `frontend/src/utils.js` met audio capability detection:

1. Voeg functie toe: `isMediaRecorderSupported()`
2. Voeg functie toe: `isGetUserMediaSupported()`
3. Voeg functie toe: `checkAudioSupport()` die beide controleert
4. Update `showCompatibilityWarning()` om ook audio warnings te tonen

Update `frontend/tests/utils.test.js` met tests voor:
- Test dat audio support detection werkt
- Test dat warnings getoond worden voor unsupported browsers
- Mock navigator.mediaDevices voor testing

Maak ook `frontend/public/test-audio-support.html` voor manual testing.
```

**Success Criteria:**
- ✅ Audio support detection functions bestaan
- ✅ Tests pass voor browser compatibility
- ✅ Manual test page toont audio capabilities
- ✅ Graceful degradation voor unsupported browsers

---

### Step 9A.2: Microfoon Permission Request (Test-First)
**Instructie voor LLM:**
```
Maak `frontend/src/audio.js` met:

1. `async requestMicrophoneAccess()` function:
   - Gebruik getUserMedia({ audio: true })
   - Return Promise met success/failure
   - Handle permission denied gracefully
   - Proper error logging

2. `stopAudioStream(stream)` utility function

Maak `frontend/tests/audio.test.js` met tests:
- Test successful microphone access (mock getUserMedia)
- Test permission denied scenario
- Test browser not supported scenario
- Test cleanup function

Manual test: Update `frontend/public/index.html` met "Test Microfoon" button.
```

**Success Criteria:**
- ✅ Microfoon permission request werkt
- ✅ Error handling voor denied permissions
- ✅ Tests pass met mocked getUserMedia
- ✅ Manual test button in interface

---

## 📋 Micro-Iteratie 9B: Audio Recording Infrastructure

### Step 9B.1: MediaRecorder Setup (Test-First)
**Instructie voor LLM:**
```
Update `frontend/src/audio.js` met MediaRecorder logic:

1. `class AudioRecorder` met:
   - constructor(stream, options)
   - start() method
   - stop() method
   - onDataAvailable callback setup
   - Error handling

2. Recording configuratie:
   - mimeType: 'audio/webm' of 'audio/mp4' (browser compatibility)
   - timeslice: 250ms (voor 250ms chunks)

Update tests in `frontend/tests/audio.test.js`:
- Test AudioRecorder class instantiation
- Test start/stop recording
- Test data callback firing
- Test different audio formats
- Mock MediaRecorder API

Voeg "Start Opname" button toe aan test page.
```

**Success Criteria:**
- ✅ AudioRecorder class werkend
- ✅ MediaRecorder correctly configured
- ✅ 250ms chunk timing verified
- ✅ Tests pass met mocked MediaRecorder
- ✅ Manual recording test mogelijk

---

### Step 9B.2: Audio Format Conversion & Validation
**Instructie voor LLM:**
```
Update `frontend/src/audio.js` met audio processing:

1. `convertAudioChunk(blob)` function:
   - Convert Blob naar ArrayBuffer
   - Validate audio data niet empty
   - Handle conversion errors

2. `validateAudioChunk(arrayBuffer)` function:
   - Check minimum size (> 100 bytes)
   - Check maximum size (< 100KB per chunk)
   - Validate format headers waar mogelijk

Update tests:
- Test audio conversion Blob → ArrayBuffer
- Test validation logic
- Test edge cases (empty, too large)
- Mock Blob en FileReader APIs

Add chunk size logging naar test interface.
```

**Success Criteria:**
- ✅ Audio format conversion werkt
- ✅ Validation prevents bad chunks
- ✅ Tests pass voor alle edge cases
- ✅ Size monitoring in test interface

---

## 📋 Micro-Iteratie 9C: WebSocket Audio Streaming Integration

### Step 9C.1: Audio Streaming via WebSocket (Test-First)
**Instructie voor LLM:**
```
Update `frontend/src/connection.js` met audio streaming:

1. `sendAudioChunk(websocket, audioData)` function:
   - Send binary data via websocket.send()
   - Handle send errors gracefully
   - Add retry logic voor network hiccups
   - Rate limiting voor network protection

2. Update `connectWebSocket()` om audio mode te ondersteunen:
   - Parameter: mode = 'broadcast' | 'listener'
   - Use correct endpoint (/ws/speak/{stream_id} vs /ws/listen/{stream_id})
   - Generate of accept stream_id

Update tests in `frontend/tests/connection.test.js`:
- Test audio chunk sending
- Test WebSocket binary message handling
- Test rate limiting
- Test error scenarios (connection lost tijdens streaming)
- Mock WebSocket voor binary data testing

Test endpoint selection: /ws/speak/test-stream vs /ws/listen/test-stream
```

**Success Criteria:**
- ✅ Binary audio streaming via WebSocket werkt
- ✅ Correct endpoint selection (speak vs listen)
- ✅ Error handling tijdens streaming
- ✅ Tests pass voor streaming scenarios
- ✅ Rate limiting prevents flooding

---

### Step 9C.2: Complete Audio Pipeline Integration
**Instructie voor LLM:**
```
Update `frontend/src/ui.js` om audio recording te integreren:

1. Update `startBroadcast()` function:
   - Request microphone access
   - Start audio recording
   - Setup WebSocket met /ws/speak/{stream_id}
   - Stream audio chunks real-time
   - Update UI status accordingly

2. Add `stopBroadcast()` function:
   - Stop audio recording
   - Cleanup MediaRecorder
   - Close WebSocket connection
   - Update UI state

3. Update button states:
   - "Start Uitzending" → "Stop Uitzending" tijdens recording
   - Status updates: "Microfoon toegang...", "Opname actief", etc.

Update tests in `frontend/tests/ui.test.js`:
- Test complete broadcast flow
- Test microphone access integration
- Test audio streaming pipeline
- Test stop recording cleanup
- Test UI state transitions

Add stream_id generation (simple: timestamp + random)
```

**Success Criteria:**
- ✅ Complete audio capture pipeline werkend
- ✅ UI reflects audio recording state
- ✅ Start/stop lifecycle management
- ✅ Tests pass voor complete flow
- ✅ Stream ID generation implemented

---

## 📋 Micro-Iteratie 9D: Production Readiness & Error Handling

### Step 9D.1: Production Audio Configuration
**Instructie voor LLM:**
```
Update `frontend/src/config.js` met audio settings:

1. Audio configuration object:
   - CHUNK_INTERVAL_MS: 250
   - MAX_CHUNK_SIZE: 100 * 1024 (100KB)
   - AUDIO_CONSTRAINTS: { audio: { sampleRate: 16000, channelCount: 1 } }
   - SUPPORTED_MIME_TYPES: ['audio/webm', 'audio/mp4', 'audio/wav']

2. `getBestAudioFormat()` function:
   - Test MediaRecorder.isTypeSupported()
   - Return best available format
   - Fallback strategy

Update `frontend/src/audio.js` om config te gebruiken:
- Use configured constraints
- Use configured chunk timing
- Use best available audio format

Tests voor configuration:
- Test audio format selection
- Test constraint application
- Test fallback scenarios
```

**Success Criteria:**
- ✅ Production audio configuration
- ✅ Browser-specific format optimization
- ✅ Configurable parameters
- ✅ Format fallback strategy working

---

### Step 9D.2: Error Recovery & User Experience
**Instructie voor LLM:**
```
Implement comprehensive error handling:

1. Update `frontend/src/audio.js` met error recovery:
   - Automatic retry voor MediaRecorder errors
   - Graceful degradation voor unsupported formats
   - User-friendly error messages
   - Recovery suggestions

2. Update `frontend/src/ui.js` met UX improvements:
   - Loading states tijdens microphone access
   - Visual indicator voor recording (pulsing dot)
   - Audio level indicator (optional, basic)
   - Clear error messages en recovery actions

3. Add `frontend/src/diagnostics.js`:
   - Browser capability reporting
   - Audio system diagnostics
   - Debug information gathering
   - Performance metrics

Update tests voor error scenarios:
- Test all error recovery paths
- Test user feedback mechanisms
- Test diagnostic reporting

Add comprehensive manual testing procedures.
```

**Success Criteria:**
- ✅ Robust error handling en recovery
- ✅ Excellent user experience
- ✅ Visual feedback during recording
- ✅ Diagnostic capabilities
- ✅ Production-ready reliability

---

## 🚀 LLM Workflow Strategie

### Voor elke micro-iteratie:

1. **Test-First Development:**
```bash
# Terminal 1: Start backend
cd /path/to/project
poetry run uvicorn backend.main:app --reload

# Terminal 2: Frontend development
cd frontend
npm test -- --watch

# Terminal 3: Manual testing
cd frontend  
npm run serve
# Browser: http://localhost:3000
```

2. **Implementation Cycle:**
```bash
# 1. LLM schrijft failing tests
npm test

# 2. LLM implementeert feature
# Edit src/ files

# 3. Tests passing
npm test

# 4. Manual verification
# Test in browser met backend running
```

3. **Integration Testing:**
```bash
# Test tegen real backend
curl http://localhost:8000/health/full

# Test audio streaming
# Browser: open index.html, click "Start Uitzending"
# Verify WebSocket connection in Network tab
```

### Veiligheidsnet per stap:
- **Progressive enhancement:** Audio features alleen als browser ondersteunt
- **Graceful degradation:** App werkt nog steeds zonder audio
- **Error boundaries:** Geen crashes bij audio failures
- **Manual testing:** Elke stap testbaar in browser

## 🎯 Success Criteria voor Complete Iteratie 9

### Architectuur Achievement:
```
✅ OLD: Frontend alleen WebSocket text/JSON
✅ NEW: Frontend met microphone capture + audio streaming
✅ INTEGRATION: Real-time audio naar backend pipeline
```

### Functional Achievement:
- ✅ Microfoon toegang request en handling
- ✅ Real-time audio recording in 250ms chunks
- ✅ Binary audio streaming via WebSocket
- ✅ Integration met backend /ws/speak/{stream_id}
- ✅ Complete speaker workflow: click button → stream audio

### Quality Achievement:
- ✅ Comprehensive test coverage (Jest tests)
- ✅ Browser compatibility detection en warnings
- ✅ Error handling en graceful degradation
- ✅ User-friendly interface en feedback
- ✅ Production-ready audio configuration

### Technical Achievement:
- ✅ MediaRecorder API integration
- ✅ getUserMedia permission handling
- ✅ WebSocket binary data streaming
- ✅ Audio format optimization per browser
- ✅ Stream ID generation en management

## 📱 Browser Testing Checklist
- **Chrome/Chromium:** Primary development target
- **Firefox:** Secondary target
- **Safari:** macOS compatibility
- **Mobile browsers:** Basic functionality check

## 🔧 Development Tips voor LLM

### Quick Audio Testing:
```bash
# 1. Start backend
poetry run uvicorn backend.main:app --reload

# 2. Start frontend
cd frontend && npm run serve

# 3. Browser: http://localhost:3000
# Click "Start Uitzending"
# Check Console for audio chunk logs
# Check Network tab for WebSocket binary messages
```

### Debug Audio Issues:
```javascript
// Browser console debugging
navigator.mediaDevices.getUserMedia({audio: true})
  .then(stream => console.log('Microphone OK', stream))
  .catch(err => console.error('Microphone failed', err));

// Check MediaRecorder support
console.log('WebM:', MediaRecorder.isTypeSupported('audio/webm'));
console.log('MP4:', MediaRecorder.isTypeSupported('audio/mp4'));
```

**Ready to start? Begin met Micro-Iteratie 9A.1! 🎤**

Deze gefaseerde aanpak zorgt ervoor dat elke stap klein, testbaar en reversible is, perfect voor agentic LLM development! 🚀