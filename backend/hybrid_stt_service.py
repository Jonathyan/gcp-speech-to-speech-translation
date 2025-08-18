"""
Hybrid STT Service for Phase 2

This module integrates all Phase 2 components with the existing Phase 1 system,
providing a unified interface for hybrid streaming and buffered speech-to-text.
"""
import asyncio
import logging
import time
from typing import Dict, Optional, Any, Callable, List
from dataclasses import dataclass

# Phase 2 imports
from .streaming_stt_manager import AsyncStreamingSpeechToText, StreamingConfig
from .adaptive_stream_buffer import AdaptiveStreamBuffer, StreamingMode
from .connection_quality_monitor import ConnectionQualityMonitor
from .fallback_orchestrator import FallbackOrchestrator, ProcessingMode, FallbackReason

# Phase 1 imports (mock for now - these would import from existing codebase)
class EnhancedSpeechToTextService:
    """Mock Phase 1 enhanced STT service."""
    
    async def process_chunk(self, chunk: bytes, stream_id: str = None) -> Optional[str]:
        """Process audio chunk using buffered STT."""
        # Simulate Phase 1 processing
        await asyncio.sleep(0.1)
        if len(chunk) > 1000:
            return f"Buffered transcription for {len(chunk)} bytes"
        return None


@dataclass
class ProcessingResult:
    """Result from processing audio chunk."""
    transcription: Optional[str]
    mode_used: ProcessingMode
    processing_time_ms: float
    buffer_mode: StreamingMode
    quality_metrics: Optional[Dict[str, Any]] = None


class HybridSTTService:
    """
    Hybrid STT Service that orchestrates both streaming and buffered modes.
    
    This service integrates Phase 2 streaming capabilities with the existing
    Phase 1 buffered system, providing seamless fallback and mode switching.
    """
    
    def __init__(self,
                 enable_streaming: bool = True,
                 quality_threshold: float = 0.7,
                 streaming_timeout: float = 5.0):
        """
        Initialize hybrid STT service.
        
        Args:
            enable_streaming: Enable streaming mode (Phase 2)
            quality_threshold: Quality threshold for mode decisions
            streaming_timeout: Timeout for streaming operations
        """
        # Phase 2 components
        self.streaming_manager = AsyncStreamingSpeechToText(max_concurrent_sessions=20)
        self.adaptive_buffer = AdaptiveStreamBuffer()
        self.quality_monitor = ConnectionQualityMonitor(
            quality_threshold=quality_threshold
        )
        self.fallback_orchestrator = FallbackOrchestrator(
            quality_threshold=quality_threshold
        )
        
        # Phase 1 integration
        self.enhanced_stt_service = EnhancedSpeechToTextService()
        
        # Configuration
        self.enable_streaming = enable_streaming
        self.streaming_timeout = streaming_timeout
        
        # Stream management
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        self.transcription_callbacks: Dict[str, Callable] = {}
        
        # Performance metrics
        self.metrics = {
            'total_chunks': 0,
            'streaming_chunks': 0,
            'buffered_chunks': 0,
            'fallbacks': 0,
            'successful_transcriptions': 0,
            'failed_transcriptions': 0
        }
        
        self._logger = logging.getLogger(__name__)
        
        # Background monitoring will be started on first use
        self._monitoring_started = False
    
    async def process_audio_chunk(self,
                                 stream_id: str,
                                 audio_chunk: bytes,
                                 callback: Optional[Callable] = None) -> Optional[ProcessingResult]:
        """
        Process audio chunk using appropriate mode (streaming or buffered).
        
        Args:
            stream_id: Unique stream identifier
            audio_chunk: Raw audio data
            callback: Optional callback for real-time transcriptions
            
        Returns:
            ProcessingResult with transcription and metadata
        """
        start_time = time.time()
        
        try:
            # Start background monitoring if not started
            await self._ensure_monitoring_started()
            
            self.metrics['total_chunks'] += 1
            
            # Register callback if provided
            if callback:
                self.transcription_callbacks[stream_id] = callback
            
            # Update connection quality metrics
            processing_start = time.time()
            
            # Add chunk to adaptive buffer for analysis
            buffer_mode = await self.adaptive_buffer.add_chunk(
                audio_chunk,
                quality_score=self.quality_monitor.calculate_quality_score().overall_score
            )
            
            # Get current connection metrics
            connection_metrics = self.quality_monitor.get_current_metrics()
            
            # Decide processing mode
            audio_characteristics = {
                'frequency': self.adaptive_buffer.get_buffer_stats().get('analytics', {}).get('chunk_frequency', 0),
                'size': len(audio_chunk)
            }
            
            processing_mode = await self.fallback_orchestrator.decide_processing_mode(
                stream_id,
                connection_metrics,
                audio_characteristics
            )
            
            transcription = None
            
            # Process based on decided mode
            if processing_mode == ProcessingMode.STREAMING and self.enable_streaming:
                try:
                    transcription = await self._process_streaming(stream_id, audio_chunk)
                    if transcription:
                        self.metrics['streaming_chunks'] += 1
                        # Update orchestrator to reflect successful streaming
                        self.fallback_orchestrator.set_mode_for_stream(stream_id, ProcessingMode.STREAMING)
                except Exception as streaming_error:
                    self._logger.warning(f"Streaming failed for {stream_id}, falling back to buffered: {streaming_error}")
                    # Don't re-raise, just continue to buffered fallback
                    transcription = None
            
            # Fallback to buffered mode if streaming failed or not suitable
            if transcription is None:
                transcription = await self._process_buffered(stream_id, audio_chunk, buffer_mode)
                if transcription:
                    self.metrics['buffered_chunks'] += 1
                processing_mode = ProcessingMode.BUFFERED
                
                # Update orchestrator to reflect actual mode used
                self.fallback_orchestrator.set_mode_for_stream(stream_id, ProcessingMode.BUFFERED)
            
            # Record processing outcome
            processing_time = (time.time() - processing_start) * 1000
            
            if transcription:
                await self.fallback_orchestrator.record_success(stream_id, processing_time)
                self.metrics['successful_transcriptions'] += 1
            else:
                self.metrics['failed_transcriptions'] += 1
            
            # Update quality monitoring
            self.quality_monitor.record_request_timing(
                processing_start,
                time.time(),
                transcription is not None
            )
            
            return ProcessingResult(
                transcription=transcription,
                mode_used=processing_mode,
                processing_time_ms=processing_time,
                buffer_mode=buffer_mode,
                quality_metrics={
                    'connection_quality': connection_metrics.__dict__,
                    'buffer_stats': self.adaptive_buffer.get_buffer_stats()
                }
            )
            
        except Exception as e:
            self._logger.error(f"Error processing chunk for stream {stream_id}: {e}")
            
            # Handle error through fallback orchestrator
            current_mode = self.fallback_orchestrator.get_mode_for_stream(stream_id)
            await self.fallback_orchestrator.handle_processing_error(
                stream_id, e, current_mode
            )
            
            self.metrics['failed_transcriptions'] += 1
            raise
    
    async def _process_streaming(self, stream_id: str, audio_chunk: bytes) -> Optional[str]:
        """Process audio chunk using streaming mode."""
        try:
            # Get or create streaming session
            session = await self._get_or_create_streaming_session(stream_id)
            
            # Send audio to streaming session
            await session.send_audio(audio_chunk)
            
            # For this implementation, we simulate getting a response
            # In real implementation, this would be handled by callbacks
            # from the streaming session
            
            return None  # Streaming responses come via callbacks
            
        except Exception as e:
            self._logger.error(f"Streaming processing error for {stream_id}: {e}")
            
            # Record the error for fallback logic
            await self.fallback_orchestrator.handle_processing_error(
                stream_id, e, ProcessingMode.STREAMING
            )
            
            raise
    
    async def _process_buffered(self,
                               stream_id: str,
                               audio_chunk: bytes,
                               buffer_mode: StreamingMode) -> Optional[str]:
        """Process audio chunk using buffered mode."""
        try:
            # Check if buffer should be released
            if buffer_mode == StreamingMode.BUFFERED and self.adaptive_buffer.should_release_buffer():
                # Get accumulated audio from buffer
                buffered_audio = self.adaptive_buffer.get_buffered_audio()
                
                # Process using Phase 1 enhanced STT service
                transcription = await self.enhanced_stt_service.process_chunk(
                    buffered_audio, stream_id
                )
                
                # Clear buffer after processing
                self.adaptive_buffer.clear()
                
                return transcription
            
            # For streaming buffer mode, process chunk immediately
            elif buffer_mode == StreamingMode.STREAMING:
                return await self.enhanced_stt_service.process_chunk(audio_chunk, stream_id)
            
            # Still buffering, no transcription yet
            return None
            
        except Exception as e:
            self._logger.error(f"Buffered processing error for {stream_id}: {e}")
            raise
    
    async def _get_or_create_streaming_session(self, stream_id: str):
        """Get existing or create new streaming session."""
        session = await self.streaming_manager.get_session(stream_id)
        
        if not session:
            # Create new streaming session
            config = StreamingConfig(
                language_code="nl-NL",  # Dutch input
                interim_results=True
            )
            
            session = await self.streaming_manager.create_session(stream_id, config)
            
            # Set callback for handling streaming transcriptions
            session.set_callback(self._handle_streaming_transcription)
            
            # Start the session
            await session.start()
            
            self._logger.info(f"Created new streaming session for {stream_id}")
        
        return session
    
    async def _handle_streaming_transcription(self,
                                            stream_id: str,
                                            transcript: str,
                                            is_final: bool):
        """Handle real-time transcription from streaming session."""
        self._logger.debug(f"Stream {stream_id}: '{transcript}' (final: {is_final})")
        
        # Call registered callback if available
        if stream_id in self.transcription_callbacks:
            try:
                await self.transcription_callbacks[stream_id](stream_id, transcript, is_final)
            except Exception as e:
                self._logger.error(f"Error in transcription callback for {stream_id}: {e}")
        
        # Record successful transcription
        if is_final and transcript.strip():
            await self.fallback_orchestrator.record_success(stream_id, 0.0)  # Real-time, no processing time
    
    def get_current_mode(self, stream_id: str) -> ProcessingMode:
        """Get current processing mode for stream."""
        return self.fallback_orchestrator.get_mode_for_stream(stream_id)
    
    async def close_stream(self, stream_id: str) -> None:
        """Close and cleanup stream."""
        try:
            # Close streaming session if exists
            await self.streaming_manager.close_session(stream_id)
            
            # Reset fallback orchestrator for this stream
            self.fallback_orchestrator.reset_stream(stream_id)
            
            # Remove callback
            if stream_id in self.transcription_callbacks:
                del self.transcription_callbacks[stream_id]
            
            # Clean up stream state
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
            
            self._logger.info(f"Stream {stream_id} closed and cleaned up")
            
        except Exception as e:
            self._logger.error(f"Error closing stream {stream_id}: {e}")
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        return {
            'hybrid_service': {
                **self.metrics,
                'active_streams': len(self.active_streams),
                'streaming_enabled': self.enable_streaming
            },
            'streaming_manager': self.streaming_manager.get_stats(),
            'adaptive_buffer': self.adaptive_buffer.get_buffer_stats(),
            'quality_monitor': self.quality_monitor.get_detailed_report(),
            'fallback_orchestrator': self.fallback_orchestrator.get_global_stats()
        }
    
    def get_stream_status(self, stream_id: str) -> Dict[str, Any]:
        """Get detailed status for specific stream."""
        return {
            'current_mode': self.get_current_mode(stream_id).value,
            'buffer_stats': self.adaptive_buffer.get_buffer_stats(),
            'fallback_stats': self.fallback_orchestrator.get_stream_stats(stream_id),
            'has_streaming_session': stream_id in [s.stream_id for s in self.streaming_manager.sessions.values()],
            'has_callback': stream_id in self.transcription_callbacks
        }
    
    async def set_global_mode(self, mode: ProcessingMode) -> None:
        """Set global default processing mode."""
        self.fallback_orchestrator.global_mode = mode
        self._logger.info(f"Global processing mode set to: {mode.value}")
        
        # Update streaming availability
        if mode == ProcessingMode.BUFFERED:
            self.enable_streaming = False
        elif mode == ProcessingMode.STREAMING:
            self.enable_streaming = True
    
    async def force_recovery_attempt(self, stream_id: str) -> bool:
        """Force recovery attempt for specific stream."""
        return await self.fallback_orchestrator.attempt_recovery(stream_id)
    
    async def _ensure_monitoring_started(self) -> None:
        """Start background monitoring if not already started."""
        if not self._monitoring_started:
            await self.quality_monitor.start_background_monitoring()
            self._monitoring_started = True
    
    async def shutdown(self) -> None:
        """Shutdown all components gracefully."""
        self._logger.info("Shutting down Hybrid STT Service")
        
        try:
            # Stop background monitoring if started
            if self._monitoring_started:
                await self.quality_monitor.stop_background_monitoring()
            
            # Shutdown streaming manager
            await self.streaming_manager.shutdown()
            
            # Clean up orchestrator
            self.fallback_orchestrator.cleanup_old_streams(0)  # Clean all
            
            self._logger.info("Hybrid STT Service shutdown complete")
            
        except Exception as e:
            self._logger.error(f"Error during shutdown: {e}")


class HybridSTTServiceBuilder:
    """Builder for creating configured HybridSTTService instances."""
    
    def __init__(self):
        self.config = {
            'enable_streaming': True,
            'quality_threshold': 0.7,
            'streaming_timeout': 5.0,
            'streaming_threshold_bytes': 5000,
            'buffered_timeout_seconds': 2.0,
            'failure_threshold': 3,
            'recovery_interval_seconds': 60.0
        }
    
    def with_streaming_disabled(self):
        """Disable streaming mode (buffered only)."""
        self.config['enable_streaming'] = False
        return self
    
    def with_quality_threshold(self, threshold: float):
        """Set quality threshold for mode decisions."""
        self.config['quality_threshold'] = threshold
        return self
    
    def with_streaming_config(self, threshold_bytes: int, timeout_seconds: float):
        """Configure streaming parameters."""
        self.config['streaming_threshold_bytes'] = threshold_bytes
        self.config['streaming_timeout'] = timeout_seconds
        return self
    
    def with_fallback_config(self, failure_threshold: int, recovery_interval: float):
        """Configure fallback parameters."""
        self.config['failure_threshold'] = failure_threshold
        self.config['recovery_interval_seconds'] = recovery_interval
        return self
    
    def build(self) -> HybridSTTService:
        """Build configured HybridSTTService instance."""
        service = HybridSTTService(
            enable_streaming=self.config['enable_streaming'],
            quality_threshold=self.config['quality_threshold'],
            streaming_timeout=self.config['streaming_timeout']
        )
        
        # Configure adaptive buffer
        service.adaptive_buffer = AdaptiveStreamBuffer(
            streaming_threshold_bytes=self.config['streaming_threshold_bytes'],
            buffered_timeout_seconds=self.config['buffered_timeout_seconds']
        )
        
        # Configure fallback orchestrator
        service.fallback_orchestrator = FallbackOrchestrator(
            failure_threshold=self.config['failure_threshold'],
            recovery_interval_seconds=self.config['recovery_interval_seconds'],
            quality_threshold=self.config['quality_threshold']
        )
        
        return service