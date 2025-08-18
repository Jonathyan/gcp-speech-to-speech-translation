import logging
import asyncio
from typing import Optional, Dict, Any, Callable
from .smart_buffer import SmartAudioBuffer, BufferMetrics, BufferReleaseReason
from .audio_processor import EnhancedAudioProcessor
from .error_recovery import ErrorRecoveryManager, error_recovery_decorator
from .performance_monitor import performance_monitor
# Import services functions directly to avoid circular imports


class EnhancedBufferedSTTService:
    """Enhanced buffered STT service with Phase 1 improvements."""
    
    def __init__(self,
                 min_duration_seconds: float = 1.5,
                 quality_threshold: float = 0.8,
                 max_buffer_size: int = 300 * 1024,
                 timeout_seconds: float = 4.0,
                 enable_performance_monitoring: bool = False):
        """
        Initialize enhanced buffered STT service.
        
        Args:
            min_duration_seconds: Minimum buffer duration before release
            quality_threshold: Quality score threshold for early release
            max_buffer_size: Maximum buffer size before forced release
            timeout_seconds: Maximum wait time before timeout release
            enable_performance_monitoring: Enable performance monitoring
        """
        # Core components
        self.smart_buffer = SmartAudioBuffer(
            min_duration_seconds=min_duration_seconds,
            quality_threshold=quality_threshold,
            max_buffer_size=max_buffer_size,
            timeout_seconds=timeout_seconds
        )
        
        self.audio_processor = EnhancedAudioProcessor()
        self.error_recovery = ErrorRecoveryManager()
        
        # Performance monitoring
        self.performance_monitoring = enable_performance_monitoring
        if self.performance_monitoring:
            self.logger = performance_monitor.logger
        else:
            self.logger = logging.getLogger(__name__)
        
        # Service state
        self.is_active = True
        self.processing_stats = {
            'total_chunks_processed': 0,
            'total_transcriptions': 0,
            'total_errors': 0,
            'average_processing_time_ms': 0.0,
            'buffer_releases_by_reason': {reason.value: 0 for reason in BufferReleaseReason}
        }
        
        self.logger.info("Enhanced buffered STT service initialized")
    
    async def start(self):
        """Start the service and background monitoring."""
        self.is_active = True
        
        if self.performance_monitoring:
            await performance_monitor.start_monitoring()
        
        self.logger.info("Enhanced buffered STT service started")
    
    async def stop(self):
        """Stop the service and cleanup resources."""
        self.is_active = False
        
        if self.performance_monitoring:
            await performance_monitor.stop_monitoring()
        
        self.logger.info("Enhanced buffered STT service stopped")
    
    async def process_chunk(self, audio_chunk: bytes, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Process audio chunk through enhanced pipeline.
        
        Args:
            audio_chunk: Raw audio data from browser
            context: Optional context for error recovery
            
        Returns:
            Transcription text if buffer is ready, None if still buffering
        """
        if not self.is_active or not audio_chunk:
            return None
        
        context = context or {}
        self.processing_stats['total_chunks_processed'] += 1
        
        # Process with error recovery
        return await self._process_chunk_with_recovery(audio_chunk, context)
    
    # Remove decorator for now - will handle error recovery manually
    async def _process_chunk_with_recovery(self, audio_chunk: bytes, context: Dict[str, Any]) -> Optional[str]:
        """Process chunk with error recovery wrapper."""
        # Set recovery manager reference
        if not hasattr(self._process_chunk_with_recovery, '__wrapped__'):
            # This is a bit hacky, but needed for the decorator
            pass
        
        try:
            # Add chunk to smart buffer (with simple timing if enabled)
            if self.performance_monitoring:
                async with performance_monitor.time_audio_processing('buffer_chunk'):
                    buffer_metrics = await self.smart_buffer.add_chunk(audio_chunk)
            else:
                buffer_metrics = await self.smart_buffer.add_chunk(audio_chunk)
            
            if buffer_metrics is None:
                # Still buffering
                self.logger.debug("Audio chunk buffered, waiting for more data")
                return None
            
            # Buffer is ready for processing
            return await self._process_buffer(buffer_metrics, context)
        
        except Exception as e:
            self.processing_stats['total_errors'] += 1
            
            # Handle error through recovery manager
            context.update({
                'operation': 'chunk_processing',
                'chunk_size': len(audio_chunk),
                'buffer_state': self.smart_buffer.get_buffer_stats()
            })
            
            fallback_handled = await self.error_recovery.handle_error(
                e, context, self._fallback_handler
            )
            
            if not fallback_handled:
                self.logger.error(f"Unhandled error in chunk processing", error=e)
                raise
            
            return None
    
    async def _process_buffer(self, buffer_metrics: BufferMetrics, context: Dict[str, Any]) -> str:
        """Process buffered audio through STT pipeline."""
        # Update release reason statistics
        self.processing_stats['buffer_releases_by_reason'][buffer_metrics.release_reason.value] += 1
        
        self.logger.info(f"Processing buffer: {buffer_metrics.release_reason.value}, "
                        f"{buffer_metrics.chunks_count} chunks, "
                        f"{buffer_metrics.duration_seconds:.1f}s, "
                        f"quality: {buffer_metrics.average_quality:.2f}")
        
        # Get combined audio data
        combined_audio = self.smart_buffer.get_combined_audio()
        
        # Clear buffer
        self.smart_buffer.clear()
        
        # Process through STT with performance monitoring
        if self.performance_monitoring:
            async with performance_monitor.time_api_call('speech_to_text'):
                transcription = await self._stt_with_context(combined_audio, context, buffer_metrics)
        else:
            transcription = await self._stt_with_context(combined_audio, context, buffer_metrics)
        
        if transcription:
            self.processing_stats['total_transcriptions'] += 1
            self.logger.info(f"Transcription completed: {transcription[:50]}...")
            if self.performance_monitoring:
                performance_monitor.metrics_collector.increment(
                    'transcription.completed', 1,
                    {'reason': buffer_metrics.release_reason.value}
                )
        
        return transcription
    
    async def _stt_with_context(self, audio_data: bytes, context: Dict[str, Any], buffer_metrics: BufferMetrics) -> str:
        """Speech-to-text with enhanced context and fallbacks."""
        # Add buffer context to STT call
        enhanced_context = {
            **context,
            'buffer_quality': buffer_metrics.average_quality,
            'buffer_format': buffer_metrics.dominant_format.value,
            'buffer_duration': buffer_metrics.duration_seconds
        }
        
        try:
            # Apply any recovery context modifications
            if context.get('fallback_format'):
                self.logger.info(f"Using fallback format: {context['fallback_format']}")
            
            if context.get('degradation_level'):
                self.logger.info(f"Applying degradation: {context['degradation_level']}")
                # Apply degradation settings here if needed
            
            # Import and call real STT service
            from .services import real_speech_to_text
            result = await real_speech_to_text(audio_data)
            
            if not result or not result.strip():
                raise Exception("Empty transcription result")
            
            return result.strip()
        
        except Exception as e:
            # Enhanced error context
            enhanced_context.update({
                'stt_operation': 'real_speech_to_text',
                'audio_size': len(audio_data),
                'error_type': type(e).__name__
            })
            
            # Let error recovery handle this
            handled = await self.error_recovery.handle_error(e, enhanced_context)
            
            if not handled:
                raise
            
            # If recovery succeeded, we should have updated context
            if context.get('use_fallback_audio'):
                self.logger.warning("Using fallback transcription due to STT failure")
                return "Error in speech recognition"
            
            # Retry with recovery context
            from .services import real_speech_to_text
            return await real_speech_to_text(audio_data)
    
    async def _fallback_handler(self, error: Exception, context: Dict[str, Any]):
        """Fallback handler for unrecoverable errors."""
        self.logger.error(f"Fallback handler activated for error: {error}")
        
        # Log comprehensive error context
        self.logger.error(f"Error context: {type(error).__name__} - {str(error)}")
        self.logger.error(f"Buffer stats: {self.smart_buffer.get_buffer_stats()}")
        self.logger.error(f"Processor stats: {self.audio_processor.get_stats()}")
        
        # Clear buffer to prevent stuck state
        if self.smart_buffer.chunks:
            self.smart_buffer.clear()
            self.logger.info("Cleared stuck buffer due to fallback")
        
        # Reset error recovery strategies for fresh start
        self.error_recovery.reset_strategies()
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        buffer_stats = self.smart_buffer.get_buffer_stats()
        processor_stats = self.audio_processor.get_stats()
        error_stats = self.error_recovery.get_error_stats()
        
        # Calculate derived metrics
        total_chunks = self.processing_stats['total_chunks_processed']
        total_errors = self.processing_stats['total_errors']
        success_rate = (total_chunks - total_errors) / max(1, total_chunks)
        
        service_stats = {
            **self.processing_stats,
            'success_rate': success_rate,
            'error_rate': total_errors / max(1, total_chunks),
            'transcription_rate': self.processing_stats['total_transcriptions'] / max(1, total_chunks),
            'is_active': self.is_active
        }
        
        comprehensive_stats = {
            'service': service_stats,
            'buffer': buffer_stats,
            'processor': processor_stats,
            'error_recovery': error_stats,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        # Add performance monitoring data if available
        if self.performance_monitoring:
            comprehensive_stats['performance'] = performance_monitor.get_comprehensive_report()
        
        return comprehensive_stats
    
    async def get_health_check(self) -> Dict[str, Any]:
        """Get service health check information."""
        stats = self.get_service_stats()
        
        # Determine health status
        success_rate = stats['service']['success_rate']
        error_rate = stats['service']['error_rate']
        
        if success_rate > 0.95 and error_rate < 0.05:
            health_status = "healthy"
        elif success_rate > 0.8 and error_rate < 0.15:
            health_status = "degraded"
        else:
            health_status = "unhealthy"
        
        return {
            'status': health_status,
            'is_active': self.is_active,
            'performance_monitoring': self.performance_monitoring,
            'success_rate': success_rate,
            'error_rate': error_rate,
            'buffer_active': len(self.smart_buffer.chunks) > 0,
            'recent_errors': len([
                e for e in self.error_recovery.error_history 
                if asyncio.get_event_loop().time() - e.timestamp < 300  # Last 5 minutes
            ]),
            'timestamp': asyncio.get_event_loop().time()
        }
    
    def reset_statistics(self):
        """Reset all service statistics."""
        self.processing_stats = {
            'total_chunks_processed': 0,
            'total_transcriptions': 0,
            'total_errors': 0,
            'average_processing_time_ms': 0.0,
            'buffer_releases_by_reason': {reason.value: 0 for reason in BufferReleaseReason}
        }
        
        # Reset component statistics
        self.smart_buffer.stats = {
            'total_releases': 0,
            'release_reasons': {reason.value: 0 for reason in BufferReleaseReason},
            'average_buffer_duration': 0.0,
            'quality_improvements': 0,
            'timeout_adaptations': 0
        }
        
        self.audio_processor.stats = {
            'total_chunks': 0,
            'format_counts': {fmt.value: 0 for fmt in self.audio_processor.stats['format_counts']},
            'conversion_successes': 0,
            'conversion_failures': 0
        }
        
        self.error_recovery.stats = {
            'total_errors': 0,
            'recovery_attempts': 0,
            'recovery_successes': 0,
            'errors_by_category': {cat.value: 0 for cat in self.error_recovery.stats['errors_by_category']},
            'errors_by_severity': {sev.value: 0 for sev in self.error_recovery.stats['errors_by_severity']}
        }
        
        self.logger.info("Service statistics reset")


# Global enhanced STT service instance
enhanced_stt_service = EnhancedBufferedSTTService()