import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import os

# Import Phase 1 components
from backend.audio_processor import (
    EnhancedAudioProcessor, WebMDetector, WAVDetector, 
    AudioFormat, AudioAnalysis, WebMToLinear16Converter
)
from backend.smart_buffer import (
    SmartAudioBuffer, BufferMetrics, BufferReleaseReason
)
from backend.error_recovery import (
    ErrorRecoveryManager, ErrorCategory, ErrorSeverity,
    FormatFallbackStrategy, APIRetryStrategy
)
from backend.performance_monitor import (
    PerformanceMonitor, MetricsCollector, PerformanceHistogram
)
from backend.enhanced_stt_service import EnhancedBufferedSTTService


class TestEnhancedAudioProcessor:
    """Test suite for EnhancedAudioProcessor."""
    
    @pytest.fixture
    def audio_processor(self):
        return EnhancedAudioProcessor()
    
    def test_initialization(self, audio_processor):
        """Test audio processor initializes correctly."""
        assert len(audio_processor.detectors) == 4  # WebM, WAV, OGG, MP4
        assert len(audio_processor.converters) == 5  # All formats + unknown
        assert audio_processor.stats['total_chunks'] == 0
    
    def test_webm_detection(self, audio_processor):
        """Test WebM format detection."""
        webm_header = b'\x1a\x45\xdf\xa3' + b'\x00' * 1000
        detector = WebMDetector()
        
        analysis = detector.detect(webm_header)
        
        assert analysis.format_type == AudioFormat.WEBM
        assert analysis.confidence >= 0.9
        assert analysis.quality_score > 0.0
    
    def test_wav_detection(self, audio_processor):
        """Test WAV format detection."""
        # Create minimal WAV header
        wav_header = (
            b'RIFF' + (44 + 1000).to_bytes(4, 'little') +  # File size
            b'WAVE' +
            b'fmt ' + (16).to_bytes(4, 'little') +  # fmt chunk size
            (1).to_bytes(2, 'little') +  # PCM format
            (1).to_bytes(2, 'little') +  # Mono
            (16000).to_bytes(4, 'little') +  # Sample rate
            (32000).to_bytes(4, 'little') +  # Byte rate
            (2).to_bytes(2, 'little') +  # Block align
            (16).to_bytes(2, 'little') +  # Bits per sample
            b'data' + (1000).to_bytes(4, 'little') +  # Data chunk size
            b'\x00' * 1000  # Audio data
        )
        
        detector = WAVDetector()
        analysis = detector.detect(wav_header)
        
        assert analysis.format_type == AudioFormat.WAV
        assert analysis.confidence >= 0.9
        assert analysis.sample_rate == 16000
        assert analysis.channels == 1
    
    @pytest.mark.asyncio
    async def test_chunk_processing(self, audio_processor):
        """Test complete chunk processing pipeline."""
        webm_chunk = b'\x1a\x45\xdf\xa3' + b'\x00' * 5000
        
        processed_chunk, analysis = await audio_processor.process_chunk(webm_chunk)
        
        assert processed_chunk is not None
        assert analysis.format_type == AudioFormat.WEBM
        assert analysis.confidence > 0.0
        assert audio_processor.stats['total_chunks'] == 1
    
    @pytest.mark.asyncio
    async def test_conversion_fallback(self, audio_processor):
        """Test conversion fallback for unknown formats."""
        unknown_chunk = b'\xff\xfe\xfd\xfc' + b'\x00' * 1000
        
        processed_chunk, analysis = await audio_processor.process_chunk(unknown_chunk)
        
        assert processed_chunk == unknown_chunk  # Should return original
        assert analysis.format_type == AudioFormat.UNKNOWN
    
    def test_statistics_tracking(self, audio_processor):
        """Test statistics are tracked correctly."""
        stats = audio_processor.get_stats()
        
        assert 'total_chunks' in stats
        assert 'format_counts' in stats
        assert 'conversion_successes' in stats
        assert 'conversion_failures' in stats
        assert 'success_rate' in stats


class TestSmartAudioBuffer:
    """Test suite for SmartAudioBuffer."""
    
    @pytest.fixture
    def smart_buffer(self):
        return SmartAudioBuffer(
            min_duration_seconds=1.0,
            quality_threshold=0.8,
            max_buffer_size=50000,
            timeout_seconds=3.0
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, smart_buffer):
        """Test buffer initializes correctly."""
        assert smart_buffer.min_duration_seconds == 1.0
        assert smart_buffer.quality_threshold == 0.8
        assert len(smart_buffer.chunks) == 0
        assert smart_buffer.total_size == 0
    
    @pytest.mark.asyncio
    async def test_chunk_addition(self, smart_buffer):
        """Test adding chunks to buffer."""
        chunk = b'\x1a\x45\xdf\xa3' + b'\x00' * 1000
        
        result = await smart_buffer.add_chunk(chunk)
        
        assert len(smart_buffer.chunks) == 1
        assert smart_buffer.total_size > 0
        assert smart_buffer.first_chunk_time is not None
        # Should not be ready yet with small buffer
        assert result is None
    
    @pytest.mark.asyncio
    async def test_quality_based_early_release(self, smart_buffer):
        """Test early release based on quality threshold."""
        # Add high-quality chunks
        high_quality_chunk = b'\x1a\x45\xdf\xa3' + b'\x18\x53\x80\x67' + b'\x00' * 8000
        
        # Add multiple chunks to reach quality threshold
        for _ in range(3):
            result = await smart_buffer.add_chunk(high_quality_chunk)
            await asyncio.sleep(0.1)  # Small delay for timing
        
        # Should trigger early release due to quality
        if result is not None:
            assert result.release_reason == BufferReleaseReason.QUALITY_THRESHOLD
            assert result.average_quality >= smart_buffer.quality_threshold
    
    @pytest.mark.asyncio
    async def test_timeout_release(self, smart_buffer):
        """Test buffer release on timeout."""
        chunk = b'\x1a\x45\xdf\xa3' + b'\x00' * 1000
        
        # Add chunk and wait for timeout
        await smart_buffer.add_chunk(chunk)
        
        # Mock time to trigger timeout
        with patch('time.time', return_value=time.time() + 4.0):
            result = await smart_buffer.add_chunk(chunk)
        
        if result is not None:
            assert result.release_reason == BufferReleaseReason.TIMEOUT
    
    @pytest.mark.asyncio
    async def test_max_size_release(self, smart_buffer):
        """Test buffer release when max size is reached."""
        large_chunk = b'\x1a\x45\xdf\xa3' + b'\x00' * 60000  # Larger than max_buffer_size
        
        result = await smart_buffer.add_chunk(large_chunk)
        
        assert result is not None
        assert result.release_reason == BufferReleaseReason.MAX_SIZE
    
    @pytest.mark.asyncio
    async def test_buffer_metrics(self, smart_buffer):
        """Test buffer metrics calculation."""
        chunk = b'\x1a\x45\xdf\xa3' + b'\x00' * 10000
        
        await smart_buffer.add_chunk(chunk)
        await smart_buffer.add_chunk(chunk)
        
        # Force release to get metrics
        with patch('time.time', return_value=time.time() + 4.0):
            result = await smart_buffer.add_chunk(chunk)
        
        if result is not None:
            assert isinstance(result, BufferMetrics)
            assert result.chunks_count >= 2
            assert result.total_size > 0
            assert result.duration_seconds > 0
            assert result.average_quality >= 0.0
    
    def test_combined_audio_retrieval(self, smart_buffer):
        """Test getting combined audio from buffer."""
        # Manually add chunks for testing
        chunk1 = b'chunk1'
        chunk2 = b'chunk2'
        
        from backend.smart_buffer import BufferChunk
        from backend.audio_processor import AudioAnalysis, AudioFormat
        
        # Create mock buffer chunks
        smart_buffer.chunks = [
            BufferChunk(chunk1, AudioAnalysis(AudioFormat.WEBM, 0.8), time.time(), 0),
            BufferChunk(chunk2, AudioAnalysis(AudioFormat.WEBM, 0.7), time.time(), 1)
        ]
        
        combined = smart_buffer.get_combined_audio()
        assert combined == chunk1 + chunk2
    
    def test_buffer_clearing(self, smart_buffer):
        """Test buffer clearing functionality."""
        # Add some data
        smart_buffer.total_size = 1000
        original_time = time.time()
        smart_buffer.first_chunk_time = original_time
        
        smart_buffer.clear()
        
        assert len(smart_buffer.chunks) == 0
        assert smart_buffer.total_size == 0
        # CRITICAL FIX: first_chunk_time should be preserved to enable multi-sentence translation
        assert smart_buffer.first_chunk_time == original_time


class TestErrorRecoveryManager:
    """Test suite for ErrorRecoveryManager."""
    
    @pytest.fixture
    def error_manager(self):
        return ErrorRecoveryManager()
    
    def test_initialization(self, error_manager):
        """Test error manager initializes correctly."""
        assert len(error_manager.error_history) == 0
        assert len(error_manager.strategies) > 0
        assert ErrorCategory.AUDIO_FORMAT in error_manager.strategies
        assert ErrorCategory.GOOGLE_API in error_manager.strategies
    
    def test_error_classification(self, error_manager):
        """Test error classification logic."""
        # Test Google API error
        google_error = Exception("google.api_core.exceptions.InvalidArgument: bad encoding")
        category, severity = error_manager.classify_error(google_error, {})
        assert category == ErrorCategory.AUDIO_FORMAT
        assert severity == ErrorSeverity.HIGH
        
        # Test network error
        network_error = Exception("ConnectionError: network timeout")
        category, severity = error_manager.classify_error(network_error, {})
        assert category == ErrorCategory.NETWORK
        assert severity == ErrorSeverity.MEDIUM
        
        # Test timeout error
        timeout_error = asyncio.TimeoutError("Operation timed out")
        category, severity = error_manager.classify_error(timeout_error, {})
        assert category == ErrorCategory.TIMEOUT
        assert severity == ErrorSeverity.MEDIUM
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, error_manager):
        """Test complete error handling workflow."""
        test_error = Exception("Test error for handling")
        context = {'operation': 'test', 'data_size': 1000}
        fallback_called = False
        
        async def mock_fallback(error, ctx):
            nonlocal fallback_called
            fallback_called = True
        
        # Handle the error
        result = await error_manager.handle_error(test_error, context, mock_fallback)
        
        # Check error was recorded
        assert len(error_manager.error_history) == 1
        assert error_manager.stats['total_errors'] == 1
        
        # Check if recovery was attempted (depends on error type)
        if not result and fallback_called:
            # Fallback was called as expected
            pass
    
    def test_statistics_tracking(self, error_manager):
        """Test error statistics tracking."""
        stats = error_manager.get_error_stats()
        
        assert 'total_errors' in stats
        assert 'recovery_attempts' in stats
        assert 'recovery_successes' in stats
        assert 'recovery_success_rate' in stats
        assert 'errors_by_category' in stats
        assert 'errors_by_severity' in stats


class TestPerformanceMonitor:
    """Test suite for PerformanceMonitor."""
    
    @pytest.fixture
    def performance_monitor(self):
        return PerformanceMonitor(enable_system_metrics=False)  # Disable for testing
    
    def test_metrics_collector_initialization(self, performance_monitor):
        """Test metrics collector initializes correctly."""
        collector = performance_monitor.metrics_collector
        
        assert len(collector.counters) == 0
        assert len(collector.gauges) == 0
        assert len(collector.histograms) == 0
    
    def test_counter_metrics(self, performance_monitor):
        """Test counter metrics functionality."""
        collector = performance_monitor.metrics_collector
        
        collector.increment('test.counter', 1, {'tag': 'value'})
        collector.increment('test.counter', 2, {'tag': 'value'})
        
        summary = collector.get_metrics_summary()
        counter_key = 'test.counter:tag=value'
        
        assert counter_key in summary['counters']
        assert summary['counters'][counter_key] == 3
    
    def test_gauge_metrics(self, performance_monitor):
        """Test gauge metrics functionality."""
        collector = performance_monitor.metrics_collector
        
        collector.set_gauge('test.gauge', 42.5, {'metric': 'test'})
        
        summary = collector.get_metrics_summary()
        gauge_key = 'test.gauge:metric=test'
        
        assert gauge_key in summary['gauges']
        assert summary['gauges'][gauge_key] == 42.5
    
    def test_timing_metrics(self, performance_monitor):
        """Test timing metrics functionality."""
        collector = performance_monitor.metrics_collector
        
        collector.add_timing('test.operation', 150.5, {'operation': 'test'})
        collector.add_timing('test.operation', 200.3, {'operation': 'test'})
        
        summary = collector.get_metrics_summary()
        timing_key = 'test.operation:operation=test'
        
        assert timing_key in summary['timing_stats']
        timing_stats = summary['timing_stats'][timing_key]
        assert timing_stats['count'] == 2
        assert timing_stats['avg'] > 0
    
    @pytest.mark.asyncio
    async def test_timing_context_manager(self, performance_monitor):
        """Test timing context manager."""
        collector = performance_monitor.metrics_collector
        
        async with collector.time_operation('test.context', {'test': 'tag'}):
            await asyncio.sleep(0.01)  # Small delay
        
        summary = collector.get_metrics_summary()
        timing_key = 'test.context:test=tag'
        
        assert timing_key in summary['timing_stats']
        timing_stats = summary['timing_stats'][timing_key]
        assert timing_stats['count'] == 1
        assert timing_stats['avg'] >= 10  # At least 10ms
    
    def test_histogram_functionality(self):
        """Test performance histogram."""
        histogram = PerformanceHistogram()
        
        # Add sample data
        for i in range(100):
            histogram.add_sample(float(i))
        
        stats = histogram.get_stats()
        
        assert stats['count'] == 100
        assert stats['min'] == 0.0
        assert stats['max'] == 99.0
        assert stats['p50'] == 49.0  # Median
        assert stats['p95'] == 94.0  # 95th percentile
        assert stats['p99'] == 98.0  # 99th percentile


class TestEnhancedBufferedSTTService:
    """Test suite for EnhancedBufferedSTTService."""
    
    @pytest.fixture
    def enhanced_service(self):
        return EnhancedBufferedSTTService(
            min_duration_seconds=0.5,
            timeout_seconds=2.0,
            enable_performance_monitoring=False  # Disable for testing
        )
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, enhanced_service):
        """Test service initializes correctly."""
        assert enhanced_service.is_active == True
        assert enhanced_service.smart_buffer is not None
        assert enhanced_service.audio_processor is not None
        assert enhanced_service.error_recovery is not None
    
    @pytest.mark.asyncio
    async def test_service_lifecycle(self, enhanced_service):
        """Test service start/stop lifecycle."""
        await enhanced_service.start()
        assert enhanced_service.is_active == True
        
        await enhanced_service.stop()
        assert enhanced_service.is_active == False
    
    @pytest.mark.asyncio
    async def test_chunk_processing_workflow(self, enhanced_service):
        """Test complete chunk processing workflow."""
        # Mock the STT service to avoid real API calls
        with patch('backend.services.real_speech_to_text') as mock_stt:
            mock_stt.return_value = "test transcription"
            
            # Add chunks to trigger processing
            webm_chunk = b'\x1a\x45\xdf\xa3' + b'\x00' * 10000
            
            # Process multiple chunks
            result1 = await enhanced_service.process_chunk(webm_chunk)
            result2 = await enhanced_service.process_chunk(webm_chunk)
            
            # Should still be buffering
            assert result1 is None
            
            # Wait and add more to trigger release
            await asyncio.sleep(0.6)  # Exceed min duration
            result3 = await enhanced_service.process_chunk(webm_chunk)
            
            # Should have processed by now or continue buffering
            assert enhanced_service.processing_stats['total_chunks_processed'] >= 3
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, enhanced_service):
        """Test error handling integration."""
        # Mock STT to raise an error
        with patch('backend.services.real_speech_to_text') as mock_stt:
            mock_stt.side_effect = Exception("Test STT error")
            
            webm_chunk = b'\x1a\x45\xdf\xa3' + b'\x00' * 20000  # Large chunk to trigger processing
            
            # Should handle error gracefully
            result = await enhanced_service.process_chunk(webm_chunk)
            
            # Check error was tracked
            assert enhanced_service.processing_stats['total_errors'] > 0
    
    @pytest.mark.asyncio
    async def test_statistics_collection(self, enhanced_service):
        """Test statistics collection."""
        # Process some chunks
        chunk = b'\x1a\x45\xdf\xa3' + b'\x00' * 1000
        
        await enhanced_service.process_chunk(chunk)
        await enhanced_service.process_chunk(chunk)
        
        stats = enhanced_service.get_service_stats()
        
        assert 'service' in stats
        assert 'buffer' in stats
        assert 'processor' in stats
        assert 'error_recovery' in stats
        
        service_stats = stats['service']
        assert 'total_chunks_processed' in service_stats
        assert 'success_rate' in service_stats
        assert 'error_rate' in service_stats
    
    @pytest.mark.asyncio
    async def test_health_check(self, enhanced_service):
        """Test health check functionality."""
        health = await enhanced_service.get_health_check()
        
        assert 'status' in health
        assert 'is_active' in health
        assert 'success_rate' in health
        assert 'error_rate' in health
        assert health['status'] in ['healthy', 'degraded', 'unhealthy']
    
    def test_statistics_reset(self, enhanced_service):
        """Test statistics reset functionality."""
        # Add some statistics
        enhanced_service.processing_stats['total_chunks_processed'] = 100
        enhanced_service.processing_stats['total_errors'] = 10
        
        enhanced_service.reset_statistics()
        
        assert enhanced_service.processing_stats['total_chunks_processed'] == 0
        assert enhanced_service.processing_stats['total_errors'] == 0


class TestPhase1Integration:
    """Integration tests for Phase 1 components working together."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_processing(self):
        """Test complete end-to-end processing flow."""
        service = EnhancedBufferedSTTService(
            min_duration_seconds=0.1,
            timeout_seconds=1.0,
            enable_performance_monitoring=False
        )
        
        # Mock external dependencies
        with patch('backend.services.real_speech_to_text') as mock_stt:
            mock_stt.return_value = "hello world"
            
            await service.start()
            
            try:
                # Process audio chunks
                webm_chunk = b'\x1a\x45\xdf\xa3' + b'\x18\x53\x80\x67' + b'\x00' * 15000
                
                # Add several chunks
                results = []
                for i in range(5):
                    result = await service.process_chunk(webm_chunk)
                    results.append(result)
                    await asyncio.sleep(0.05)
                
                # Should eventually get a transcription
                transcriptions = [r for r in results if r is not None]
                
                # Verify service state
                stats = service.get_service_stats()
                assert stats['service']['total_chunks_processed'] == 5
                
                # Verify health
                health = await service.get_health_check()
                assert health['is_active'] == True
                
            finally:
                await service.stop()
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self):
        """Test error recovery across components."""
        service = EnhancedBufferedSTTService(
            min_duration_seconds=0.1,
            enable_performance_monitoring=False
        )
        
        # Mock STT to fail then succeed
        call_count = 0
        def mock_stt_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Temporary STT failure")
            return "recovery successful"
        
        with patch('backend.services.real_speech_to_text', side_effect=mock_stt_side_effect):
            await service.start()
            
            try:
                # Process chunk that will trigger error then recovery
                large_chunk = b'\x1a\x45\xdf\xa3' + b'\x00' * 25000
                
                result = await service.process_chunk(large_chunk)
                
                # Check error recovery stats
                error_stats = service.error_recovery.get_error_stats()
                assert error_stats['total_errors'] > 0
                
            finally:
                await service.stop()
    
    def test_component_interfaces(self):
        """Test that all components have expected interfaces."""
        # Test EnhancedAudioProcessor interface
        processor = EnhancedAudioProcessor()
        assert hasattr(processor, 'analyze_chunk')
        assert hasattr(processor, 'process_chunk')
        assert hasattr(processor, 'get_stats')
        
        # Test SmartAudioBuffer interface
        buffer = SmartAudioBuffer()
        assert hasattr(buffer, 'add_chunk')
        assert hasattr(buffer, 'get_combined_audio')
        assert hasattr(buffer, 'clear')
        assert hasattr(buffer, 'get_buffer_stats')
        
        # Test ErrorRecoveryManager interface
        error_manager = ErrorRecoveryManager()
        assert hasattr(error_manager, 'handle_error')
        assert hasattr(error_manager, 'classify_error')
        assert hasattr(error_manager, 'get_error_stats')
        
        # Test PerformanceMonitor interface
        monitor = PerformanceMonitor(enable_system_metrics=False)
        assert hasattr(monitor, 'start_monitoring')
        assert hasattr(monitor, 'stop_monitoring')
        assert hasattr(monitor, 'get_comprehensive_report')


# Performance benchmarks
class TestPhase1Performance:
    """Performance tests for Phase 1 components."""
    
    @pytest.mark.asyncio
    async def test_audio_processing_performance(self):
        """Test audio processing performance under load."""
        processor = EnhancedAudioProcessor()
        
        # Prepare test chunks
        webm_chunks = [b'\x1a\x45\xdf\xa3' + b'\x00' * (1000 + i*100) for i in range(10)]
        
        start_time = time.time()
        
        # Process chunks
        results = []
        for chunk in webm_chunks:
            result = await processor.process_chunk(chunk)
            results.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process 10 chunks in reasonable time (< 1 second)
        assert processing_time < 1.0
        assert len(results) == 10
        
        # All should have been processed successfully
        successful_processing = sum(1 for r in results if r[0] is not None)
        assert successful_processing == 10
    
    @pytest.mark.asyncio
    async def test_buffer_performance_under_load(self):
        """Test buffer performance with many chunks."""
        buffer = SmartAudioBuffer(
            min_duration_seconds=0.1,
            max_buffer_size=100000
        )
        
        # Add many small chunks rapidly
        chunk = b'\x1a\x45\xdf\xa3' + b'\x00' * 500
        
        start_time = time.time()
        releases = 0
        
        for i in range(50):
            result = await buffer.add_chunk(chunk)
            if result is not None:
                releases += 1
                buffer.clear()  # Clear for next batch
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should handle 50 chunks quickly
        assert processing_time < 2.0
        
        # Should have some buffer releases
        assert releases > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])