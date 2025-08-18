import pytest
import pytest_asyncio
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import Dict, Any, Optional, AsyncGenerator

# Test imports - these will fail initially (TDD approach)
try:
    from backend.streaming_stt_manager import (
        AsyncStreamingSpeechToText, 
        StreamingSession,
        StreamingError,
        StreamingSessionState
    )
    from backend.adaptive_stream_buffer import (
        AdaptiveStreamBuffer,
        StreamingMode,
        BufferStrategy
    )
    from backend.connection_quality_monitor import (
        ConnectionQualityMonitor,
        ConnectionMetrics,
        QualityScore
    )
    from backend.fallback_orchestrator import (
        FallbackOrchestrator,
        ProcessingMode,
        FallbackReason
    )
    from backend.hybrid_stt_service import HybridSTTService
except ImportError:
    # These classes don't exist yet - we'll implement them
    pass


class TestStreamingSession:
    """Test suite for individual streaming sessions."""
    
    @pytest.fixture
    def mock_client(self):
        """Mock Google Cloud Speech client."""
        client = Mock()
        client.streaming_recognize = Mock()
        return client
    
    @pytest.fixture
    def executor(self):
        """Thread executor for sync/async coordination."""
        return ThreadPoolExecutor(max_workers=2)
    
    @pytest.mark.asyncio
    async def test_session_initialization(self, mock_client, executor):
        """Test streaming session initializes correctly."""
        session = StreamingSession(
            stream_id="test-stream",
            client=mock_client,
            executor=executor
        )
        
        assert session.stream_id == "test-stream"
        assert session.client == mock_client
        assert session.executor == executor
        assert session.state == StreamingSessionState.IDLE
        assert not session.is_active
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self, mock_client, executor):
        """Test complete session start/stop lifecycle."""
        session = StreamingSession(
            stream_id="lifecycle-test",
            client=mock_client,
            executor=executor
        )
        
        # Start session
        await session.start()
        assert session.state == StreamingSessionState.ACTIVE
        assert session.is_active
        
        # Stop session
        await session.stop()
        assert session.state == StreamingSessionState.STOPPED
        assert not session.is_active
    
    @pytest.mark.asyncio
    async def test_audio_chunk_processing(self, mock_client, executor):
        """Test audio chunk queuing and processing."""
        session = StreamingSession(
            stream_id="chunk-test",
            client=mock_client,
            executor=executor
        )
        
        await session.start()
        
        # Send audio chunks
        test_chunks = [b'chunk1', b'chunk2', b'chunk3']
        for chunk in test_chunks:
            await session.send_audio(chunk)
        
        # Verify chunks are queued
        assert session.get_queue_size() == 3
        
        await session.stop()
    
    @pytest.mark.asyncio
    async def test_session_error_handling(self, mock_client, executor):
        """Test session handles errors gracefully."""
        # Configure mock to raise error
        mock_client.streaming_recognize.side_effect = Exception("API Error")
        
        session = StreamingSession(
            stream_id="error-test",
            client=mock_client,
            executor=executor
        )
        
        with pytest.raises(StreamingError):
            await session.start()
            await asyncio.sleep(0.1)  # Let error propagate
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, mock_client, executor):
        """Test multiple concurrent streaming sessions."""
        sessions = []
        
        # Create multiple sessions
        for i in range(5):
            session = StreamingSession(
                stream_id=f"concurrent-{i}",
                client=mock_client,
                executor=executor
            )
            sessions.append(session)
        
        # Start all sessions concurrently
        start_tasks = [session.start() for session in sessions]
        await asyncio.gather(*start_tasks)
        
        # Verify all are active
        for session in sessions:
            assert session.is_active
        
        # Stop all sessions
        stop_tasks = [session.stop() for session in sessions]
        await asyncio.gather(*stop_tasks)


class TestAsyncStreamingSpeechToText:
    """Test suite for async streaming STT manager."""
    
    @pytest.fixture
    def streaming_stt(self):
        """Create streaming STT instance."""
        return AsyncStreamingSpeechToText()
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, streaming_stt):
        """Test streaming manager initializes correctly."""
        assert len(streaming_stt.sessions) == 0
        assert streaming_stt.executor is not None
        assert streaming_stt.max_concurrent_sessions == 10
    
    @pytest.mark.asyncio
    async def test_create_session(self, streaming_stt):
        """Test creating new streaming session."""
        session = await streaming_stt.create_session("test-stream")
        
        assert session.stream_id == "test-stream"
        assert "test-stream" in streaming_stt.sessions
        assert streaming_stt.get_active_sessions_count() == 1
    
    @pytest.mark.asyncio
    async def test_session_limit(self, streaming_stt):
        """Test concurrent session limits."""
        # Set low limit for testing
        streaming_stt.max_concurrent_sessions = 3
        
        # Create sessions up to limit
        sessions = []
        for i in range(3):
            session = await streaming_stt.create_session(f"limited-{i}")
            sessions.append(session)
        
        # Try to create one more - should raise error
        with pytest.raises(StreamingError, match="Maximum concurrent sessions"):
            await streaming_stt.create_session("overflow")
    
    @pytest.mark.asyncio
    async def test_session_cleanup(self, streaming_stt):
        """Test automatic session cleanup."""
        session = await streaming_stt.create_session("cleanup-test")
        session_id = session.stream_id
        
        # Simulate session completion
        await session.stop()
        
        # Manager should clean up stopped sessions
        await streaming_stt.cleanup_stopped_sessions()
        
        assert session_id not in streaming_stt.sessions
    
    @pytest.mark.asyncio
    async def test_broadcast_to_session(self, streaming_stt):
        """Test broadcasting audio to specific session."""
        session = await streaming_stt.create_session("broadcast-test")
        
        # Mock callback to capture transcriptions
        transcriptions = []
        async def mock_callback(stream_id, transcript, is_final):
            transcriptions.append((stream_id, transcript, is_final))
        
        session.set_callback(mock_callback)
        
        # Send audio and verify callback
        await streaming_stt.send_audio("broadcast-test", b"test-audio")
        
        # Note: In real implementation, this would trigger transcription
        # For now, just verify session received audio
        assert session.get_queue_size() > 0


class TestAdaptiveStreamBuffer:
    """Test suite for adaptive stream buffer."""
    
    @pytest.fixture
    def adaptive_buffer(self):
        """Create adaptive buffer instance."""
        return AdaptiveStreamBuffer(
            streaming_threshold_bytes=5000,
            buffered_timeout_seconds=2.0
        )
    
    def test_buffer_initialization(self, adaptive_buffer):
        """Test buffer initializes with correct parameters."""
        assert adaptive_buffer.streaming_threshold == 5000
        assert adaptive_buffer.buffered_timeout == 2.0
        assert adaptive_buffer.current_mode == StreamingMode.BUFFERED
    
    @pytest.mark.asyncio
    async def test_mode_switching_by_size(self, adaptive_buffer):
        """Test buffer switches to streaming based on data size."""
        # Add small chunks - should stay buffered
        small_chunk = b'x' * 1000
        mode = await adaptive_buffer.add_chunk(small_chunk)
        assert mode == StreamingMode.BUFFERED
        
        # Add large chunk - should switch to streaming
        large_chunk = b'x' * 6000
        mode = await adaptive_buffer.add_chunk(large_chunk)
        assert mode == StreamingMode.STREAMING
        assert adaptive_buffer.current_mode == StreamingMode.STREAMING
    
    @pytest.mark.asyncio
    async def test_mode_switching_by_frequency(self, adaptive_buffer):
        """Test buffer switches to streaming based on chunk frequency."""
        # Send chunks rapidly
        for i in range(10):
            chunk = b'x' * 500
            mode = await adaptive_buffer.add_chunk(chunk)
            await asyncio.sleep(0.05)  # 50ms intervals = high frequency
        
        # Should switch to streaming due to high frequency
        assert adaptive_buffer.current_mode == StreamingMode.STREAMING
    
    @pytest.mark.asyncio
    async def test_buffered_timeout(self, adaptive_buffer):
        """Test buffer releases on timeout in buffered mode."""
        # Add chunk and wait for timeout
        chunk = b'x' * 1000
        await adaptive_buffer.add_chunk(chunk)
        
        # Wait for timeout
        await asyncio.sleep(2.5)
        
        # Should trigger buffered release
        released_data = adaptive_buffer.get_buffered_audio()
        assert len(released_data) > 0
    
    def test_strategy_selection(self, adaptive_buffer):
        """Test buffer strategy selection logic."""
        # Test conditions for different strategies
        strategies = adaptive_buffer.evaluate_strategies({
            'chunk_frequency': 15,  # High frequency
            'average_chunk_size': 8000,  # Large chunks
            'connection_quality': 0.9  # Good connection
        })
        
        assert BufferStrategy.STREAMING in strategies
        
        # Test conditions favoring buffered mode
        strategies = adaptive_buffer.evaluate_strategies({
            'chunk_frequency': 2,   # Low frequency
            'average_chunk_size': 1000,  # Small chunks
            'connection_quality': 0.3   # Poor connection
        })
        
        assert BufferStrategy.BUFFERED in strategies


class TestConnectionQualityMonitor:
    """Test suite for connection quality monitoring."""
    
    @pytest.fixture
    def quality_monitor(self):
        """Create connection quality monitor."""
        return ConnectionQualityMonitor(
            measurement_window_seconds=5.0,
            quality_threshold=0.7
        )
    
    def test_monitor_initialization(self, quality_monitor):
        """Test monitor initializes correctly."""
        assert quality_monitor.measurement_window == 5.0
        assert quality_monitor.quality_threshold == 0.7
        assert len(quality_monitor.metrics_history) == 0
    
    @pytest.mark.asyncio
    async def test_latency_measurement(self, quality_monitor):
        """Test RTT latency measurement."""
        # Simulate successful request
        start_time = time.time()
        await asyncio.sleep(0.1)  # Simulate 100ms latency
        
        quality_monitor.record_request_timing(
            start_time=start_time,
            end_time=time.time(),
            success=True
        )
        
        metrics = quality_monitor.get_current_metrics()
        assert metrics.average_latency_ms >= 100
        assert metrics.success_rate == 1.0
    
    @pytest.mark.asyncio
    async def test_failure_tracking(self, quality_monitor):
        """Test failure rate tracking."""
        # Record mix of successes and failures
        for i in range(10):
            quality_monitor.record_request_timing(
                start_time=time.time(),
                end_time=time.time() + 0.1,
                success=i % 3 != 0  # 2/3 success rate
            )
        
        metrics = quality_monitor.get_current_metrics()
        assert 0.6 <= metrics.success_rate <= 0.7
        assert metrics.failure_rate >= 0.3
    
    def test_quality_score_calculation(self, quality_monitor):
        """Test overall quality score calculation."""
        # Add good metrics
        for _ in range(5):
            quality_monitor.record_request_timing(
                start_time=time.time(),
                end_time=time.time() + 0.05,  # 50ms latency
                success=True
            )
        
        score = quality_monitor.calculate_quality_score()
        assert score.overall_score > 0.8
        assert score.latency_score > 0.8
        assert score.reliability_score == 1.0
    
    def test_quality_degradation_detection(self, quality_monitor):
        """Test detection of quality degradation."""
        # Start with good quality
        for _ in range(5):
            quality_monitor.record_request_timing(
                start_time=time.time(),
                end_time=time.time() + 0.05,
                success=True
            )
        
        initial_score = quality_monitor.calculate_quality_score()
        
        # Add poor quality metrics
        for _ in range(10):
            quality_monitor.record_request_timing(
                start_time=time.time(),
                end_time=time.time() + 0.5,  # 500ms latency
                success=False
            )
        
        degraded_score = quality_monitor.calculate_quality_score()
        
        assert degraded_score.overall_score < initial_score.overall_score
        assert quality_monitor.is_quality_degraded()


class TestFallbackOrchestrator:
    """Test suite for fallback orchestrator."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create fallback orchestrator."""
        return FallbackOrchestrator()
    
    @pytest.mark.asyncio
    async def test_mode_decision_good_quality(self, orchestrator):
        """Test mode decision with good connection quality."""
        # Mock good quality metrics
        good_metrics = ConnectionMetrics(
            average_latency_ms=50,
            success_rate=0.95,
            failure_rate=0.05,
            requests_per_second=10
        )
        
        mode = await orchestrator.decide_processing_mode(
            stream_id="quality-test",
            connection_metrics=good_metrics,
            audio_characteristics={'frequency': 10, 'size': 8000}
        )
        
        assert mode == ProcessingMode.STREAMING
    
    @pytest.mark.asyncio
    async def test_mode_decision_poor_quality(self, orchestrator):
        """Test mode decision with poor connection quality."""
        # Mock poor quality metrics
        poor_metrics = ConnectionMetrics(
            average_latency_ms=800,
            success_rate=0.3,
            failure_rate=0.7,
            requests_per_second=2
        )
        
        mode = await orchestrator.decide_processing_mode(
            stream_id="poor-test",
            connection_metrics=poor_metrics,
            audio_characteristics={'frequency': 2, 'size': 1000}
        )
        
        assert mode == ProcessingMode.BUFFERED
    
    @pytest.mark.asyncio
    async def test_fallback_trigger(self, orchestrator):
        """Test automatic fallback triggering."""
        # Start in streaming mode
        orchestrator.current_mode = ProcessingMode.STREAMING
        
        # Simulate streaming failure
        fallback_triggered = await orchestrator.handle_processing_error(
            stream_id="fallback-test",
            error=Exception("Streaming failed"),
            current_mode=ProcessingMode.STREAMING
        )
        
        assert fallback_triggered
        assert orchestrator.get_mode_for_stream("fallback-test") == ProcessingMode.BUFFERED
    
    @pytest.mark.asyncio
    async def test_recovery_attempt(self, orchestrator):
        """Test recovery attempt after fallback."""
        # Force into buffered mode due to failures
        stream_id = "recovery-test"
        await orchestrator.record_failure(stream_id, FallbackReason.STREAMING_ERROR)
        await orchestrator.record_failure(stream_id, FallbackReason.STREAMING_ERROR)
        await orchestrator.record_failure(stream_id, FallbackReason.STREAMING_ERROR)
        
        assert orchestrator.get_mode_for_stream(stream_id) == ProcessingMode.BUFFERED
        
        # Simulate time passing for recovery
        orchestrator._set_failure_time(stream_id, time.time() - 61)  # 61 seconds ago
        
        # Should attempt recovery
        should_retry = await orchestrator.should_attempt_recovery(stream_id)
        assert should_retry


class TestHybridSTTService:
    """Test suite for the main hybrid STT service."""
    
    @pytest_asyncio.fixture
    async def hybrid_service(self):
        """Create hybrid STT service."""
        service = HybridSTTService()
        try:
            yield service
        finally:
            # Clean up after test
            try:
                await service.shutdown()
            except Exception:
                pass  # Ignore cleanup errors in tests
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, hybrid_service):
        """Test service initializes with all components."""
        assert hybrid_service.streaming_manager is not None
        assert hybrid_service.adaptive_buffer is not None
        assert hybrid_service.quality_monitor is not None
        assert hybrid_service.fallback_orchestrator is not None
        assert hybrid_service.enhanced_stt_service is not None  # Phase 1
    
    @pytest.mark.asyncio
    async def test_automatic_mode_selection(self, hybrid_service):
        """Test automatic mode selection based on conditions."""
        # Mock good conditions for streaming and successful streaming response
        with patch.object(hybrid_service.quality_monitor, 'get_current_metrics') as mock_metrics:
            with patch.object(hybrid_service, '_process_streaming') as mock_streaming:
                mock_metrics.return_value = ConnectionMetrics(
                    average_latency_ms=30,
                    success_rate=0.98,
                    failure_rate=0.02,
                    requests_per_second=15
                )
                
                # Mock streaming to return a transcription
                mock_streaming.return_value = "Streaming transcription"
                
                # Process audio chunk
                result = await hybrid_service.process_audio_chunk(
                    stream_id="auto-test",
                    audio_chunk=b'x' * 8000  # Large chunk
                )
                
                # Should select streaming mode
                assert hybrid_service.get_current_mode("auto-test") == ProcessingMode.STREAMING
    
    @pytest.mark.asyncio
    async def test_seamless_fallback(self, hybrid_service):
        """Test seamless fallback between modes."""
        stream_id = "seamless-test"
        
        # Start in streaming mode
        await hybrid_service.process_audio_chunk(stream_id, b'x' * 8000)
        
        # Simulate streaming failure by making the streaming session raise an error
        with patch.object(hybrid_service, '_process_streaming') as mock_streaming:
            mock_streaming.side_effect = Exception("Streaming failed")
            
            # Force buffer release to ensure we get a result
            with patch.object(hybrid_service.adaptive_buffer, 'should_release_buffer') as mock_release:
                mock_release.return_value = True
                
                # Should fallback to buffered mode gracefully
                result = await hybrid_service.process_audio_chunk(stream_id, b'x' * 2000)
                
                # Verify fallback occurred
                assert hybrid_service.get_current_mode(stream_id) == ProcessingMode.BUFFERED
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, hybrid_service):
        """Test service performance under concurrent load."""
        # Create multiple concurrent streams
        tasks = []
        
        for i in range(20):  # 20 concurrent streams
            task = hybrid_service.process_audio_chunk(
                stream_id=f"load-test-{i}",
                audio_chunk=b'x' * (1000 + i * 100)
            )
            tasks.append(task)
        
        # Process all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify no exceptions and reasonable performance
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0
    
    @pytest.mark.asyncio
    async def test_integration_with_phase1(self, hybrid_service):
        """Test integration with existing Phase 1 enhanced STT."""
        # When in buffered mode, should use Phase 1 enhanced service
        stream_id = "integration-test"
        
        # Force buffered mode
        hybrid_service.fallback_orchestrator.set_mode_for_stream(
            stream_id, ProcessingMode.BUFFERED
        )
        
        # Force buffer release by mocking should_release_buffer
        with patch.object(hybrid_service.adaptive_buffer, 'should_release_buffer') as mock_release:
            with patch.object(hybrid_service.enhanced_stt_service, 'process_chunk') as mock_phase1:
                mock_release.return_value = True
                mock_phase1.return_value = "Test transcription"
                
                result = await hybrid_service.process_audio_chunk(
                    stream_id=stream_id,
                    audio_chunk=b'test audio'
                )
                
                # Should have used Phase 1 service
                mock_phase1.assert_called_once()


# Performance and Integration Tests
class TestPhase2Integration:
    """Integration tests for Phase 2 hybrid streaming."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_streaming_flow(self):
        """Test complete streaming flow from audio input to transcription."""
        hybrid_service = HybridSTTService()
        
        # Mock Google Cloud streaming response
        with patch('backend.streaming_stt_manager.AsyncStreamingSpeechToText') as mock_streaming:
            mock_session = AsyncMock()
            mock_streaming.return_value.create_session.return_value = mock_session
            
            # Simulate streaming transcription
            mock_session.send_audio = AsyncMock()
            
            # Process audio chunks in streaming mode
            chunks = [b'chunk1', b'chunk2', b'chunk3']
            
            for chunk in chunks:
                await hybrid_service.process_audio_chunk("e2e-test", chunk)
            
            # Verify streaming session was used
            assert mock_session.send_audio.call_count == len(chunks)
    
    @pytest.mark.asyncio
    async def test_fallback_recovery_cycle(self):
        """Test complete fallback and recovery cycle."""
        hybrid_service = HybridSTTService()
        stream_id = "recovery-cycle"
        
        # Start in streaming mode (good conditions)
        with patch.object(hybrid_service.quality_monitor, 'calculate_quality_score') as mock_quality:
            mock_quality.return_value = QualityScore(
                overall_score=0.9,
                latency_score=0.9,
                reliability_score=0.9
            )
            
            await hybrid_service.process_audio_chunk(stream_id, b'x' * 8000)
            assert hybrid_service.get_current_mode(stream_id) == ProcessingMode.STREAMING
        
        # Simulate degraded conditions -> fallback
        with patch.object(hybrid_service.quality_monitor, 'calculate_quality_score') as mock_quality:
            mock_quality.return_value = QualityScore(
                overall_score=0.2,
                latency_score=0.1,
                reliability_score=0.3
            )
            
            await hybrid_service.process_audio_chunk(stream_id, b'x' * 2000)
            assert hybrid_service.get_current_mode(stream_id) == ProcessingMode.BUFFERED
        
        # Simulate recovery -> back to streaming
        with patch.object(hybrid_service.quality_monitor, 'calculate_quality_score') as mock_quality:
            mock_quality.return_value = QualityScore(
                overall_score=0.9,
                latency_score=0.9,
                reliability_score=0.9
            )
            
            # Wait for recovery interval
            hybrid_service.fallback_orchestrator.last_failure_time[stream_id] = time.time() - 61
            
            await hybrid_service.process_audio_chunk(stream_id, b'x' * 8000)
            assert hybrid_service.get_current_mode(stream_id) == ProcessingMode.STREAMING


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])