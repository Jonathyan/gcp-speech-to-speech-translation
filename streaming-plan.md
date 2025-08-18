# Google Cloud Streaming STT Implementation Plan

## Executive Summary

This document outlines a comprehensive plan to implement robust Google Cloud Speech-to-Text streaming functionality for the live speech translation service. The approach uses a hybrid architecture that maintains reliability while adding low-latency streaming capabilities.

## Current Status

### ✅ Working Components
- **Buffered STT**: WebM chunk buffering with 2-second windows
- **Google Cloud Integration**: All APIs (STT, Translation, TTS) connected
- **WebSocket Infrastructure**: Real-time audio streaming between browser and backend
- **Circuit Breaker**: Resilience patterns for API failures

### ❌ Issues to Resolve
- **Audio Format Compatibility**: WebM chunks from browser not consistently recognized
- **Latency**: 2-4 second delay due to buffering requirements
- **Streaming Complexity**: Threading issues between sync Google API and async WebSockets

## Project Goals

### Primary Objectives
1. **Reduce Latency**: From 2-4 seconds to <800ms end-to-end
2. **Improve Reliability**: Graceful fallback between streaming and buffered modes
3. **Maintain Quality**: Preserve current translation accuracy and audio quality
4. **Production Ready**: Handle edge cases, errors, and high concurrency

### Success Metrics
- **Latency**: <800ms average end-to-end (Dutch speech → English audio)
- **Reliability**: >99.5% successful translations (no silent failures)
- **Throughput**: Support 50+ concurrent streams
- **Recovery**: <2s fallback time from streaming to buffered mode

## Technical Architecture

### Phase 1: Enhanced Buffered Mode (Weeks 1-2)

#### Goals
- Fix current WebM audio format issues
- Improve error handling and recovery
- Establish reliable baseline for fallback

#### Technical Changes

```python
# Enhanced audio format handling
class EnhancedAudioProcessor:
    def __init__(self):
        self.format_detectors = [
            WebMDetector(),
            WAVDetector(), 
            OGGDetector()
        ]
        self.converters = {
            'webm': WebMToLinear16Converter(),
            'wav': WAVToLinear16Converter(),
            'unknown': RawAudioHandler()
        }
    
    async def process_chunk(self, chunk: bytes) -> bytes:
        format_type = self.detect_format(chunk)
        converter = self.converters[format_type]
        return await converter.convert(chunk)
```

```python
# Improved buffering with quality metrics
class SmartAudioBuffer:
    def __init__(self):
        self.quality_threshold = 0.8
        self.min_duration = 1.5  # Reduced from 2.0s
        self.adaptive_timeout = True
    
    def is_ready(self) -> bool:
        # Early release for high-quality audio
        if self.audio_quality > self.quality_threshold:
            return self.duration >= 1.0
        return self.duration >= self.min_duration
```

#### Deliverables
- [ ] Enhanced format detection and conversion
- [ ] Smart buffering with quality-based early release  
- [ ] Comprehensive error recovery
- [ ] Performance metrics and logging
- [ ] Unit tests (>95% coverage)

### Phase 2: Hybrid Streaming Architecture (Weeks 3-5)

#### Goals
- Add low-latency streaming mode alongside buffered mode
- Implement seamless fallback mechanisms
- Maintain backward compatibility

#### Technical Design

```python
class HybridSTTService:
    """Hybrid service supporting both streaming and buffered STT."""
    
    def __init__(self):
        self.streaming_enabled = True
        self.buffered_service = BufferedSpeechToText()
        self.streaming_service = AsyncStreamingSpeechToText()
        self.mode = "auto"  # auto, streaming, buffered
    
    async def process_audio(self, stream_id: str, chunk: bytes) -> Optional[str]:
        if self.mode == "streaming" or (self.mode == "auto" and self.streaming_enabled):
            try:
                result = await self.streaming_service.process_chunk(stream_id, chunk)
                if result is not None:
                    return result
            except StreamingError as e:
                logging.warning(f"Streaming failed, falling back: {e}")
                await self.fallback_to_buffered(stream_id)
        
        # Fallback to buffered mode
        return await self.buffered_service.process_chunk(chunk)
```

#### Streaming STT Implementation

```python
class AsyncStreamingSpeechToText:
    """Fully async streaming STT using proper threading patterns."""
    
    def __init__(self):
        self._streams: Dict[str, StreamingSession] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    async def create_session(self, stream_id: str) -> StreamingSession:
        """Create new streaming session for stream ID."""
        session = StreamingSession(
            stream_id=stream_id,
            client=self.speech_client,
            executor=self._executor
        )
        await session.start()
        self._streams[stream_id] = session
        return session

class StreamingSession:
    """Individual streaming session with proper async/sync coordination."""
    
    def __init__(self, stream_id: str, client, executor):
        self.stream_id = stream_id
        self.client = client
        self.executor = executor
        self._audio_queue = asyncio.Queue(maxsize=50)
        self._response_task = None
        self._is_active = False
    
    async def start(self):
        """Start streaming session."""
        self._is_active = True
        
        # Create async request generator
        request_gen = self._create_request_generator()
        
        # Run sync streaming_recognize in executor
        self._response_task = asyncio.create_task(
            self._run_streaming_recognition(request_gen)
        )
    
    async def _run_streaming_recognition(self, request_gen):
        """Run streaming recognition in thread executor."""
        loop = asyncio.get_event_loop()
        
        try:
            # Convert async generator to sync iterator
            sync_requests = await loop.run_in_executor(
                self.executor,
                self._async_to_sync_requests,
                request_gen
            )
            
            # Run streaming recognition
            response_stream = await loop.run_in_executor(
                self.executor,
                lambda: self.client.streaming_recognize(sync_requests)
            )
            
            # Process responses async
            await self._process_responses(response_stream)
            
        except Exception as e:
            logging.error(f"Streaming session {self.stream_id} error: {e}")
            raise StreamingError(f"Session failed: {e}")
```

#### Fallback Mechanism

```python
class StreamingFallbackManager:
    """Manages fallback between streaming and buffered modes."""
    
    def __init__(self):
        self.failure_threshold = 3
        self.recovery_interval = 30  # seconds
        self.stream_failures = {}
    
    async def handle_streaming_failure(self, stream_id: str, error: Exception):
        """Handle streaming failure and decide on fallback."""
        failures = self.stream_failures.get(stream_id, 0) + 1
        self.stream_failures[stream_id] = failures
        
        if failures >= self.failure_threshold:
            logging.warning(f"Stream {stream_id} exceeded failure threshold, "
                          f"disabling streaming for {self.recovery_interval}s")
            await self.disable_streaming_temporarily(stream_id)
        
        return "buffered"  # Fall back to buffered mode
    
    async def should_attempt_streaming(self, stream_id: str) -> bool:
        """Check if streaming should be attempted for stream."""
        if stream_id not in self.stream_failures:
            return True
        
        last_failure = self.stream_failures[stream_id]
        if time.time() - last_failure > self.recovery_interval:
            # Reset failures after recovery interval
            del self.stream_failures[stream_id]
            return True
        
        return False
```

#### Deliverables
- [ ] AsyncStreamingSpeechToText implementation
- [ ] StreamingSession management
- [ ] HybridSTTService with auto-fallback
- [ ] Comprehensive error handling and recovery
- [ ] Performance monitoring and metrics
- [ ] Integration tests for both modes
- [ ] Load testing (50+ concurrent streams)

### Phase 3: Production Optimization (Weeks 6-7)

#### Goals
- Optimize performance for production workloads
- Add comprehensive monitoring and alerting
- Implement advanced resilience patterns

#### Technical Enhancements

```python
class ProductionStreamingService:
    """Production-ready streaming service with advanced features."""
    
    def __init__(self):
        # Connection pooling for Google Cloud clients
        self.client_pool = SpeechClientPool(pool_size=10)
        
        # Advanced circuit breaker per stream type
        self.streaming_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=StreamingError
        )
        
        # Metrics collection
        self.metrics = StreamingMetrics()
        
        # Rate limiting
        self.rate_limiter = RateLimiter(
            requests_per_minute=1000,
            concurrent_streams=100
        )
    
    async def process_with_monitoring(self, stream_id: str, chunk: bytes):
        """Process audio with comprehensive monitoring."""
        with self.metrics.timer(f"processing.{stream_id}"):
            try:
                # Rate limiting
                await self.rate_limiter.acquire(stream_id)
                
                # Circuit breaker protection
                result = await self.streaming_breaker.call(
                    self._process_audio_internal, stream_id, chunk
                )
                
                self.metrics.increment("success", tags={"stream_id": stream_id})
                return result
                
            except Exception as e:
                self.metrics.increment("error", tags={
                    "stream_id": stream_id,
                    "error_type": type(e).__name__
                })
                raise
```

#### Monitoring and Alerting

```python
class StreamingMetrics:
    """Comprehensive metrics for streaming STT service."""
    
    def collect_metrics(self) -> Dict[str, Any]:
        return {
            # Performance metrics
            "latency_p50": self.latency_histogram.percentile(50),
            "latency_p95": self.latency_histogram.percentile(95),
            "latency_p99": self.latency_histogram.percentile(99),
            
            # Reliability metrics
            "success_rate": self.success_counter / self.total_requests,
            "fallback_rate": self.fallback_counter / self.total_requests,
            "error_rate": self.error_counter / self.total_requests,
            
            # Resource metrics
            "active_streams": len(self.active_sessions),
            "queue_depth": sum(s.queue_size for s in self.active_sessions.values()),
            "memory_usage": psutil.Process().memory_info().rss,
            
            # Google Cloud API metrics
            "api_quota_remaining": self.quota_tracker.remaining,
            "api_errors_by_type": dict(self.api_error_counter)
        }
```

#### Deliverables
- [ ] Connection pooling for Google Cloud clients
- [ ] Advanced circuit breaker patterns
- [ ] Rate limiting and quota management
- [ ] Comprehensive metrics and monitoring
- [ ] Performance optimization (memory, CPU)
- [ ] Production deployment configuration
- [ ] Monitoring dashboard and alerts

## Implementation Timeline

### Week 1-2: Enhanced Buffered Mode
- **Day 1-3**: Audio format detection and conversion improvements
- **Day 4-7**: Smart buffering with quality-based early release
- **Day 8-10**: Error handling and recovery mechanisms
- **Day 11-14**: Testing, metrics, and documentation

### Week 3-4: Core Streaming Implementation  
- **Day 15-18**: AsyncStreamingSpeechToText base implementation
- **Day 19-22**: StreamingSession management and lifecycle
- **Day 23-26**: Sync/async coordination and request generation
- **Day 27-28**: Initial integration testing

### Week 5: Hybrid Architecture
- **Day 29-31**: HybridSTTService implementation
- **Day 32-34**: Fallback mechanisms and error recovery
- **Day 35**: Integration testing and debugging

### Week 6: Production Features
- **Day 36-38**: Connection pooling and resource management
- **Day 39-41**: Advanced monitoring and metrics
- **Day 42**: Load testing and performance optimization

### Week 7: Final Integration
- **Day 43-45**: End-to-end testing and bug fixes
- **Day 46-47**: Documentation and deployment preparation
- **Day 48-49**: Production deployment and monitoring setup

## Risk Assessment

### High Risk
- **Google API Threading Complexity**: Sync API in async context
  - *Mitigation*: Extensive testing with ThreadPoolExecutor patterns
  - *Fallback*: Always maintain buffered mode as backup

- **WebM Format Compatibility**: Browser audio format variations
  - *Mitigation*: Multiple format detectors and converters
  - *Fallback*: Force WAV format in browser if needed

### Medium Risk  
- **Performance Under Load**: 50+ concurrent streaming sessions
  - *Mitigation*: Connection pooling and resource limits
  - *Monitoring*: Real-time performance dashboards

- **Google Cloud Quotas**: API rate limits and billing
  - *Mitigation*: Rate limiting and quota monitoring
  - *Monitoring*: Alert on quota approaching limits

### Low Risk
- **Backward Compatibility**: Existing WebSocket clients
  - *Mitigation*: Hybrid service maintains existing API
  - *Testing*: Comprehensive integration tests

## Success Criteria

### Technical Metrics
- [ ] **Latency**: <800ms average end-to-end translation
- [ ] **Reliability**: >99.5% successful translations  
- [ ] **Throughput**: Support 50+ concurrent streams
- [ ] **Recovery**: <2s fallback time to buffered mode
- [ ] **Test Coverage**: >95% unit test coverage
- [ ] **Zero Downtime**: Seamless deployment and rollback

### Quality Metrics
- [ ] **Translation Accuracy**: Maintain current quality levels
- [ ] **Audio Quality**: No degradation in TTS output
- [ ] **User Experience**: Smooth real-time interaction
- [ ] **Error Handling**: Graceful degradation, no silent failures

### Operational Metrics
- [ ] **Monitoring**: Full observability of streaming performance
- [ ] **Alerting**: Proactive notifications for issues
- [ ] **Documentation**: Complete API and operational docs
- [ ] **Runbooks**: Clear procedures for troubleshooting

## Appendix

### Technology Stack
- **Backend**: Python 3.13, FastAPI, asyncio
- **Google Cloud**: Speech-to-Text, Translation, Text-to-Speech APIs
- **WebSockets**: Real-time audio streaming
- **Threading**: ThreadPoolExecutor for sync/async coordination
- **Testing**: pytest, asyncio testing, load testing with locust
- **Monitoring**: Prometheus metrics, Grafana dashboards

### References
- [Google Cloud Speech-to-Text Streaming API](https://cloud.google.com/speech-to-text/docs/streaming-recognize)
- [Python asyncio Best Practices](https://docs.python.org/3/library/asyncio.html)
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)

---

**Document Version**: 1.0  
**Last Updated**: 2025-08-14  
**Next Review**: 2025-08-21