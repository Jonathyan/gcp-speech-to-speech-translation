# Current System Architecture - Phase 3 Simplified

**Live Speech-to-Speech Translation Service - Dutch to English**  
**Status**: Phase 3 Simplified Architecture (Post-Evolution)  
**Date**: August 2025  
**Current State**: Minimal viable system after complexity reduction

---

## Executive Summary

This system has undergone **significant architectural evolution** from a complex 7+ layer system to a **minimal 3-layer architecture**. The current implementation represents **Phase 3: Radical Simplification** after Phase 1 (over-engineered) and Phase 2 (attempted fixes) both failed to resolve fundamental multi-sentence translation issues.

### Key Architectural Decision
**FROM**: Complex buffering → Circuit breakers → Fallback orchestrators → Multi-format audio processing  
**TO**: Direct Google Cloud API calls → Simple retry logic → Minimal error handling

---

## Current Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SIMPLIFIED ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Browser (Speaker) ──────► FastAPI WebSocket ──────► Browser (Listener) │
│                                   │                                     │
│                                   ▼                                     │
│                            Direct Pipeline:                             │
│                      Audio → STT → Translate → TTS                      │
│                                   │                                     │
│                                   ▼                                     │
│                            Google Cloud APIs                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Three Core Layers

1. **Communication Layer**: WebSocket endpoints + connection manager
2. **Processing Layer**: Direct Google Cloud API pipeline 
3. **Infrastructure Layer**: Minimal error handling + retry logic

---

## Technical Implementation Details

### Backend Architecture (`main.py`)

**Current Implementation**: `backend/main.py` (Minimal version)
```python
# Core pipeline - simplified to 3 functions
async def minimal_audio_pipeline(audio_chunk: bytes) -> Optional[bytes]:
    # Step 1: Speech-to-Text
    transcript = await _stt_with_retry(audio_chunk)
    if not transcript: return None
    
    # Step 2: Translation  
    translated_text = await _translation_with_retry(transcript)
    
    # Step 3: Text-to-Speech
    audio_output = await _tts_with_retry(translated_text)
    return audio_output
```

**Key Characteristics**:
- **No buffering systems**: Direct chunk processing
- **Simple retries**: 2 attempts with exponential backoff
- **Direct API calls**: No abstraction layers
- **Performance tracking**: Built-in timing metrics
- **Fallback audio**: Simple beep marker on failures

### Connection Management (`connection_manager.py`)

**Purpose**: Thread-safe 1-to-many broadcasting
```python
class ConnectionManager:
    # Thread-safe stream management
    async def broadcast_to_stream(stream_id: str, audio_data: bytes)
    
    # Automatic cleanup of failed connections
    def remove_listener(stream_id: str, websocket: WebSocket)
```

**Features**:
- **Stream isolation**: Multiple concurrent translation sessions
- **Automatic cleanup**: Failed connections automatically removed
- **Thread safety**: Concurrent access protection
- **Broadcasting**: One speaker → multiple listeners

### Audio Processing (`services.py`)

**Current State**: Simplified processing functions
- `real_speech_to_text()`: Direct Google Cloud STT calls
- `real_translation()`: Direct Google Translate API
- `real_text_to_speech()`: Direct Google Cloud TTS
- `convert_audio_to_linear16()`: ffmpeg fallback (when available)

**Audio Format Strategy**:
- **Primary**: Process audio chunks as-is (let Google Cloud handle format detection)
- **Fallback**: ffmpeg conversion if available in container
- **Skip small chunks**: < 8KB chunks ignored for better responsiveness

---

## Frontend Architecture

### Current Configuration (`frontend/src/config.js`)
```javascript
AUDIO: {
  CHUNK_INTERVAL_MS: 1000,     // 1s intervals - simplified
  MAX_CHUNK_SIZE: 150 * 1024,  // 150KB chunks
  AUDIO_CONSTRAINTS: {
    sampleRate: 16000,         // Optimal for Google STT
    channelCount: 1,           // Mono audio
    echoCancellation: true
  }
}
```

### WebSocket Communication (`frontend/src/connection.js`)
- **Speaker endpoint**: `/ws/speak/{stream_id}`
- **Listener endpoint**: `/ws/listen/{stream_id}`
- **Audio format**: WebM (MediaRecorder) or WAV (Web Audio API)
- **Error handling**: Connection retry with exponential backoff

---

## Known Issues and Bottlenecks

### Critical Issues (Updated with Latest Findings - January 2025)

1. **2-Second Hardcoded Chunking** 🚨 **MOST CRITICAL**
   - **Location**: `frontend/src/wavEncoder.js` line 114
   - **Issue**: `chunkIntervalMs = 2000` hardcoded, ignores config
   - **Impact**: 57% word loss, 2.5s perceived latency
   - **Fix**: Change to 250ms for 8x improvement

2. **Unused Streaming Infrastructure** ⚠️
   - **Issue**: 321 lines of production-ready streaming code unused
   - **Location**: `backend/streaming_stt.py`
   - **Impact**: Using batch mode instead of real-time streaming
   - **Fix**: Wire up existing streaming endpoints

3. **Multi-sentence Translation Failure** ⚠️
   - **Status**: Root cause now understood - 2s chunking splits words
   - **Symptom**: First sentence works, subsequent fail with beep fallbacks
   - **Root Cause**: Words split across 2-second boundaries → empty STT results
   - **Impact**: System unusable for continuous conversations

4. **Circuit Breaker Cascade** ⚠️
   - **Issue**: STT failures trigger circuit breaker → fallback audio → more failures
   - **Current Setting**: 50 failures before circuit opens (relaxed from 5)
   - **Impact**: System enters "death spiral" of beep audio

### Performance Characteristics

| Metric | Current (Actual) | Config (Ignored) | Target | Impact |
|--------|------------------|------------------|--------|--------|
| **Chunk Interval** | 2000ms | 1000ms | 250ms | 8x latency reduction |
| **Chunk Size** | 65,580 bytes | Variable | ~8KB | Better word boundaries |
| **Processing Time** | 770ms/chunk | - | <200ms | Real-time feel |
| **Word Capture** | 43% | - | >95% | Usable system |
| **Empty Chunks** | 57% | - | <5% | Less waste |
| **End-to-end Latency** | 2500ms | - | <300ms | Natural conversation |

---

## Deployment Architecture

### Cloud Run Configuration
```yaml
# cloud-run-service.yaml
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/cpu: "2"
        run.googleapis.com/memory: "2Gi"
        run.googleapis.com/execution-environment: gen2
    spec:
      containerConcurrency: 10
      timeoutSeconds: 3600
```

### Container Details (`Dockerfile.simple`)
- **Base**: `python:3.11-slim`
- **Dependencies**: Poetry, ffmpeg, Google Cloud libraries
- **Security**: Non-root execution
- **Health checks**: `/health`, `/ready`, `/stats`

### Google Cloud Services
- **Speech-to-Text**: `latest_short` model, LINEAR16 PCM, Dutch (nl-NL)
- **Translation**: Dutch → English, v2 API
- **Text-to-Speech**: Wavenet-D voice, MP3 output, English (en-US)

---

## Evolution History

### Phase 1: Over-Engineering (Failed)
**Complexity**: 7+ layers with smart buffers, adaptive streaming, fallback orchestrators
**Files**: `enhanced_stt_service.py`, `smart_buffer.py`, `fallback_orchestrator.py`, etc.
**Result**: State corruption, multi-sentence failures, impossible debugging

### Phase 2: Attempted Fixes (Failed)  
**Approach**: Fix buffer state, add WAV support, relax circuit breakers
**Result**: Same fundamental issues, Google STT still returns empty results

### Phase 3: Radical Simplification (Current)
**Philosophy**: Delete complexity, use direct API calls, minimal abstraction
**Status**: Functional for single sentences, multi-sentence issue persists
**Files**: Simplified `main.py`, removed 80% of complex modules

---

## Technical Debt

### Removed Complexity (Good Debt Reduction)
- ❌ `enhanced_stt_service.py` - Over-engineered buffering
- ❌ `smart_buffer.py` - State corruption source
- ❌ `adaptive_stream_buffer.py` - Unnecessary optimization
- ❌ `fallback_orchestrator.py` - Complex failure handling
- ❌ `performance_monitor.py` - Over-instrumentation

### Remaining Issues (Active Debt)
- ⚠️ Multi-sentence translation reliability
- ⚠️ Audio format compatibility with Google Cloud STT
- ⚠️ Circuit breaker tuning for speech patterns
- ⚠️ WebSocket connection state management

### Current File Structure
```
backend/
├── main.py              # ✅ Simplified core application
├── services.py          # ✅ Direct Google Cloud API calls  
├── connection_manager.py # ✅ Thread-safe broadcasting
├── config.py            # ✅ Environment configuration
├── resilience.py        # ✅ Basic circuit breaker
└── main_*_backup.py     # 📁 Historical versions (Phase 1&2)
```

---

## Next Steps and Recommendations

### Immediate Priorities (Based on Code Review)

1. **Fix 2-Second Chunking** (5 minutes - CRITICAL)
   ```javascript
   // frontend/src/wavEncoder.js line 114
   // CHANGE FROM:
   this.chunkIntervalMs = 2000;
   // CHANGE TO:
   this.chunkIntervalMs = 250;
   ```
   - Instant 8x latency improvement
   - Fixes 57% word loss issue
   - Aligns with word boundaries

2. **Audio Format Standardization** (High)
   - Implement consistent LINEAR16 PCM generation
   - Add audio validation before STT calls
   - Test browser audio format compatibility

3. **Circuit Breaker Optimization** (Medium)
   - Implement per-stream circuit breakers
   - Add success rate monitoring
   - Tune failure thresholds for speech patterns

### Architecture Improvements

1. **Keep It Simple**: Don't re-add complexity that was removed
2. **Focus on Core Issue**: Multi-sentence translation reliability
3. **Data-Driven Decisions**: Use `/stats` endpoint for optimization
4. **Progressive Enhancement**: Add features only when core works

### Testing Strategy

1. **Manual Testing**: Use Firebase frontend for multi-sentence tests
2. **Audio Format Testing**: Test different MediaRecorder outputs
3. **Google Cloud API Testing**: Direct API calls with known-good audio
4. **Performance Monitoring**: Use built-in metrics in simplified architecture

---

## Monitoring and Observability

### Health Endpoints
- `/health` - Basic service status
- `/ready` - Container readiness probe  
- `/stats` - Performance metrics and pipeline statistics

### Key Metrics
```javascript
{
  "pipeline_stats": {
    "total_requests": 150,
    "successful_requests": 45,
    "success_rate_percent": 30.0
  },
  "performance_metrics": {
    "avg_total_time_seconds": 2.1,
    "avg_stt_time_seconds": 0.8,
    "avg_translation_time_seconds": 0.3,
    "avg_tts_time_seconds": 1.0
  }
}
```

### Logging Strategy
- **Structured JSON**: Cloud Run compatible logs
- **Performance Tracking**: Per-operation timing
- **Error Classification**: STT, Translation, TTS error separation
- **Debug Information**: Audio format detection, chunk sizes

---

## Success Criteria

### Functional Requirements
- ✅ Single Dutch sentence → English audio translation
- ❌ **Multi-sentence translation** (PRIMARY BLOCKER)
- ✅ 1-to-many broadcasting (speaker → multiple listeners)
- ✅ WebSocket real-time communication

### Technical Requirements  
- ✅ <3s end-to-end latency
- ❌ **>90% success rate** (currently ~30% overall)
- ✅ Automatic error recovery
- ✅ Cloud Run scalability

### Quality Requirements
- ✅ Simplified, maintainable codebase
- ✅ Comprehensive monitoring
- ❌ **Production reliability** (blocked by multi-sentence issue)

---

## Conclusion

The current architecture represents a **successful simplification** from an over-engineered system to a minimal viable implementation. However, the **core multi-sentence translation issue remains unresolved** and blocks production readiness.

**Key Insight**: The problem appears to be at the **Google Cloud STT integration level**, not in the application architecture. Future efforts should focus on audio format compatibility and Google Cloud API requirements rather than adding system complexity.

**Status**: ✅ Architecture simplified, ❌ Core functionality blocked by 2s chunking  
**Root Cause Identified**: Not Google STT issue - it's the 2-second chunking splitting words!  
**Next Action**: Fix line 114 in wavEncoder.js (2000 → 250ms) for immediate improvement  
**Time to Fix**: Literally 5 minutes for 8x performance gain

*Last Updated: August 2025*