"""
Fallback Orchestrator for Phase 2 Hybrid Streaming

This module manages fallback between streaming and buffered modes,
handling processing errors and recovery attempts.
"""
import asyncio
import logging
import time
from typing import Dict, Optional, Any, List
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict, deque

from .connection_quality_monitor import ConnectionMetrics


class ProcessingMode(Enum):
    """Processing modes for STT."""
    STREAMING = "streaming"
    BUFFERED = "buffered"
    HYBRID = "hybrid"


class FallbackReason(Enum):
    """Reasons for fallback."""
    STREAMING_ERROR = "streaming_error"
    CONNECTION_QUALITY = "connection_quality"
    API_QUOTA = "api_quota"
    TIMEOUT = "timeout"
    RESOURCE_LIMIT = "resource_limit"
    USER_PREFERENCE = "user_preference"


@dataclass
class FallbackEvent:
    """Record of a fallback event."""
    stream_id: str
    timestamp: float
    from_mode: ProcessingMode
    to_mode: ProcessingMode
    reason: FallbackReason
    error_message: Optional[str] = None
    metrics_snapshot: Optional[Dict[str, Any]] = None


@dataclass
class StreamStatus:
    """Status tracking for individual streams."""
    stream_id: str
    current_mode: ProcessingMode
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    consecutive_failures: int = 0
    total_processing_time: float = 0.0
    recovery_attempts: int = 0


class FallbackOrchestrator:
    """Orchestrator for managing fallback between processing modes."""
    
    def __init__(self,
                 failure_threshold: int = 3,
                 recovery_interval_seconds: float = 60.0,
                 max_recovery_attempts: int = 5,
                 quality_threshold: float = 0.6):
        """
        Initialize fallback orchestrator.
        
        Args:
            failure_threshold: Number of failures before forcing fallback
            recovery_interval_seconds: Time to wait before recovery attempts
            max_recovery_attempts: Maximum recovery attempts per stream
            quality_threshold: Quality threshold for mode decisions
        """
        self.failure_threshold = failure_threshold
        self.recovery_interval = recovery_interval_seconds
        self.max_recovery_attempts = max_recovery_attempts
        self.quality_threshold = quality_threshold
        
        # Stream tracking
        self.stream_status: Dict[str, StreamStatus] = {}
        self.fallback_history: deque = deque(maxlen=1000)
        self.global_mode = ProcessingMode.STREAMING  # Default global preference
        
        # Failure tracking by reason
        self.failure_counters = defaultdict(int)
        self.last_failure_time: Dict[str, float] = {}
        
        # Performance metrics
        self.stats = {
            'total_fallbacks': 0,
            'total_recoveries': 0,
            'streaming_time': 0.0,
            'buffered_time': 0.0,
            'mode_switches': 0,
            'forced_fallbacks': 0
        }
        
        self._logger = logging.getLogger(__name__)
    
    async def decide_processing_mode(self,
                                   stream_id: str,
                                   connection_metrics: Optional[ConnectionMetrics] = None,
                                   audio_characteristics: Optional[Dict[str, Any]] = None) -> ProcessingMode:
        """
        Decide appropriate processing mode for stream.
        
        Args:
            stream_id: Stream identifier
            connection_metrics: Current connection quality metrics
            audio_characteristics: Audio stream characteristics
            
        Returns:
            Recommended processing mode
        """
        # Get or create stream status
        status = self._get_stream_status(stream_id)
        
        # Check for forced fallback conditions
        if await self._should_force_fallback(stream_id, status):
            return ProcessingMode.BUFFERED
        
        # Quality-based decision
        if connection_metrics:
            quality_score = self._calculate_connection_quality_score(connection_metrics)
            
            # Poor connection quality -> buffered
            if quality_score < self.quality_threshold:
                self._logger.debug(f"Stream {stream_id}: Poor connection quality ({quality_score:.2f}), using buffered mode")
                return ProcessingMode.BUFFERED
        
        # Audio characteristics consideration
        if audio_characteristics:
            if self._audio_favors_streaming(audio_characteristics):
                return ProcessingMode.STREAMING
            elif self._audio_favors_buffering(audio_characteristics):
                return ProcessingMode.BUFFERED
        
        # Default to current mode or global preference
        if status.current_mode != ProcessingMode.HYBRID:
            return status.current_mode
        
        return self.global_mode
    
    async def handle_processing_error(self,
                                    stream_id: str,
                                    error: Exception,
                                    current_mode: ProcessingMode) -> bool:
        """
        Handle processing error and determine if fallback is needed.
        
        Args:
            stream_id: Stream identifier
            error: The error that occurred
            current_mode: Current processing mode
            
        Returns:
            True if fallback was triggered
        """
        status = self._get_stream_status(stream_id)
        reason = self._classify_error(error)
        
        # Update failure tracking
        failure_time = time.time()
        status.failure_count += 1
        status.consecutive_failures += 1
        status.last_failure_time = failure_time
        
        self.failure_counters[reason.value] += 1
        self.last_failure_time[stream_id] = failure_time
        
        self._logger.warning(f"Stream {stream_id}: Processing error ({reason.value}): {error}")
        
        # Determine if fallback is needed
        should_fallback = (
            status.consecutive_failures >= self.failure_threshold or
            reason in [FallbackReason.API_QUOTA, FallbackReason.RESOURCE_LIMIT] or
            current_mode == ProcessingMode.STREAMING  # Always fallback from streaming on error
        )
        
        if should_fallback:
            await self._execute_fallback(stream_id, current_mode, ProcessingMode.BUFFERED, reason, str(error))
            return True
        
        return False
    
    async def record_success(self, stream_id: str, processing_time_ms: float) -> None:
        """Record successful processing for stream."""
        status = self._get_stream_status(stream_id)
        
        status.last_success_time = time.time()
        status.consecutive_failures = 0  # Reset consecutive failure counter
        status.total_processing_time += processing_time_ms
        
        self._logger.debug(f"Stream {stream_id}: Successful processing ({processing_time_ms:.1f}ms)")
    
    async def record_failure(self, stream_id: str, reason: FallbackReason) -> None:
        """Record failure for stream without error object."""
        status = self._get_stream_status(stream_id)
        
        failure_time = time.time()
        status.failure_count += 1
        status.consecutive_failures += 1
        status.last_failure_time = failure_time
        
        self.failure_counters[reason.value] += 1
        self.last_failure_time[stream_id] = failure_time
        
        # Force fallback if threshold exceeded
        if status.consecutive_failures >= self.failure_threshold:
            await self._execute_fallback(
                stream_id, 
                status.current_mode, 
                ProcessingMode.BUFFERED, 
                reason
            )
    
    async def should_attempt_recovery(self, stream_id: str) -> bool:
        """Check if stream should attempt recovery to streaming mode."""
        status = self._get_stream_status(stream_id)
        
        # Only recover from buffered mode
        if status.current_mode != ProcessingMode.BUFFERED:
            return False
        
        # Check recovery attempts limit
        if status.recovery_attempts >= self.max_recovery_attempts:
            self._logger.debug(f"Stream {stream_id}: Max recovery attempts reached")
            return False
        
        # Check recovery interval - use both global and stream-specific failure times
        last_failure = max(
            status.last_failure_time or 0,
            self.last_failure_time.get(stream_id, 0)
        )
        
        if last_failure > 0:
            time_since_failure = time.time() - last_failure
            if time_since_failure < self.recovery_interval:
                self._logger.debug(f"Stream {stream_id}: Recovery interval not met ({time_since_failure:.1f}s < {self.recovery_interval}s)")
                return False
        
        # Check global conditions
        if not self._global_conditions_favor_recovery():
            return False
        
        return True
    
    async def attempt_recovery(self, stream_id: str) -> bool:
        """
        Attempt recovery to streaming mode.
        
        Returns:
            True if recovery was initiated
        """
        if not await self.should_attempt_recovery(stream_id):
            return False
        
        status = self._get_stream_status(stream_id)
        status.recovery_attempts += 1
        
        await self._execute_fallback(
            stream_id,
            ProcessingMode.BUFFERED,
            ProcessingMode.STREAMING,
            FallbackReason.USER_PREFERENCE,  # Recovery attempt
            "Recovery attempt"
        )
        
        self.stats['total_recoveries'] += 1
        self._logger.info(f"Stream {stream_id}: Recovery attempt #{status.recovery_attempts}")
        
        return True
    
    def get_mode_for_stream(self, stream_id: str) -> ProcessingMode:
        """Get current processing mode for stream."""
        status = self.stream_status.get(stream_id)
        if not status:
            return self.global_mode
        return status.current_mode
    
    def set_mode_for_stream(self, stream_id: str, mode: ProcessingMode) -> None:
        """Set processing mode for stream."""
        status = self._get_stream_status(stream_id)
        old_mode = status.current_mode
        status.current_mode = mode
        
        if old_mode != mode:
            self.stats['mode_switches'] += 1
            self._logger.info(f"Stream {stream_id}: Mode set to {mode.value}")
    
    def get_stream_stats(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for specific stream."""
        status = self.stream_status.get(stream_id)
        if not status:
            return None
        
        return {
            'stream_id': stream_id,
            'current_mode': status.current_mode.value,
            'failure_count': status.failure_count,
            'consecutive_failures': status.consecutive_failures,
            'last_failure_time': status.last_failure_time,
            'last_success_time': status.last_success_time,
            'total_processing_time': status.total_processing_time,
            'recovery_attempts': status.recovery_attempts,
            'uptime_seconds': time.time() - (status.last_failure_time or time.time())
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global orchestrator statistics."""
        return {
            **self.stats,
            'active_streams': len(self.stream_status),
            'failure_counters': dict(self.failure_counters),
            'recent_fallbacks': len([e for e in self.fallback_history if time.time() - e.timestamp < 300]),
            'global_mode': self.global_mode.value,
            'thresholds': {
                'failure_threshold': self.failure_threshold,
                'recovery_interval': self.recovery_interval,
                'quality_threshold': self.quality_threshold
            }
        }
    
    def reset_stream(self, stream_id: str) -> None:
        """Reset stream status and history."""
        if stream_id in self.stream_status:
            del self.stream_status[stream_id]
        
        if stream_id in self.last_failure_time:
            del self.last_failure_time[stream_id]
        
        self._logger.info(f"Stream {stream_id}: Status reset")
    
    def _set_failure_time(self, stream_id: str, failure_time: float) -> None:
        """Set failure time for both stream status and global tracking."""
        status = self._get_stream_status(stream_id)
        status.last_failure_time = failure_time
        self.last_failure_time[stream_id] = failure_time
    
    def _get_stream_status(self, stream_id: str) -> StreamStatus:
        """Get or create stream status."""
        if stream_id not in self.stream_status:
            self.stream_status[stream_id] = StreamStatus(
                stream_id=stream_id,
                current_mode=self.global_mode
            )
        return self.stream_status[stream_id]
    
    async def _should_force_fallback(self, stream_id: str, status: StreamStatus) -> bool:
        """Check if fallback should be forced for stream."""
        # Force fallback if consecutive failures exceed threshold
        if status.consecutive_failures >= self.failure_threshold:
            return True
        
        # Check global failure rate
        recent_failures = sum(1 for t in self.last_failure_time.values() 
                            if time.time() - t < 300)  # Last 5 minutes
        
        if recent_failures > 10:  # Too many global failures
            return True
        
        return False
    
    def _calculate_connection_quality_score(self, metrics: ConnectionMetrics) -> float:
        """Calculate overall connection quality score."""
        # Weight different metrics
        latency_score = max(0, 1 - (metrics.average_latency_ms / 1000))  # Normalize to 0-1
        reliability_score = metrics.success_rate
        
        # Combined score
        return (latency_score * 0.4 + reliability_score * 0.6)
    
    def _audio_favors_streaming(self, characteristics: Dict[str, Any]) -> bool:
        """Check if audio characteristics favor streaming mode."""
        frequency = characteristics.get('frequency', 0)
        size = characteristics.get('size', 0)
        
        # High frequency or large chunks favor streaming
        return frequency > 8 or size > 5000
    
    def _audio_favors_buffering(self, characteristics: Dict[str, Any]) -> bool:
        """Check if audio characteristics favor buffered mode."""
        frequency = characteristics.get('frequency', 0)
        size = characteristics.get('size', 0)
        
        # Low frequency and small chunks favor buffering
        return frequency < 3 and size < 2000
    
    def _classify_error(self, error: Exception) -> FallbackReason:
        """Classify error to determine fallback reason."""
        error_message = str(error).lower()
        
        if 'quota' in error_message or 'rate limit' in error_message:
            return FallbackReason.API_QUOTA
        elif 'timeout' in error_message:
            return FallbackReason.TIMEOUT
        elif 'connection' in error_message or 'network' in error_message:
            return FallbackReason.CONNECTION_QUALITY
        elif 'resource' in error_message or 'memory' in error_message:
            return FallbackReason.RESOURCE_LIMIT
        else:
            return FallbackReason.STREAMING_ERROR
    
    async def _execute_fallback(self,
                               stream_id: str,
                               from_mode: ProcessingMode,
                               to_mode: ProcessingMode,
                               reason: FallbackReason,
                               error_message: Optional[str] = None) -> None:
        """Execute fallback for stream."""
        status = self._get_stream_status(stream_id)
        
        # Update stream status
        old_mode = status.current_mode
        status.current_mode = to_mode
        
        # Record fallback event
        event = FallbackEvent(
            stream_id=stream_id,
            timestamp=time.time(),
            from_mode=from_mode,
            to_mode=to_mode,
            reason=reason,
            error_message=error_message
        )
        
        self.fallback_history.append(event)
        
        # Update stats
        self.stats['total_fallbacks'] += 1
        self.stats['mode_switches'] += 1
        
        if reason != FallbackReason.USER_PREFERENCE:
            self.stats['forced_fallbacks'] += 1
        
        self._logger.info(f"Stream {stream_id}: Fallback executed - {from_mode.value} → {to_mode.value} ({reason.value})")
    
    def _global_conditions_favor_recovery(self) -> bool:
        """Check if global conditions favor recovery attempts."""
        # Check recent global failure rate
        recent_failures = sum(1 for t in self.last_failure_time.values() 
                            if time.time() - t < 180)  # Last 3 minutes
        
        # Don't attempt recovery if too many recent failures
        if recent_failures > 5:
            return False
        
        # Check if we have too many active recovery attempts
        active_recoveries = sum(1 for status in self.stream_status.values()
                              if status.current_mode == ProcessingMode.STREAMING and 
                              status.recovery_attempts > 0)
        
        if active_recoveries > 3:  # Limit concurrent recoveries
            return False
        
        return True
    
    def get_recent_fallback_events(self, limit: int = 10) -> List[FallbackEvent]:
        """Get recent fallback events."""
        return list(self.fallback_history)[-limit:]
    
    def cleanup_old_streams(self, max_age_seconds: float = 3600) -> int:
        """Clean up old stream statuses."""
        cutoff_time = time.time() - max_age_seconds
        old_streams = []
        
        for stream_id, status in self.stream_status.items():
            last_activity = max(
                status.last_failure_time or 0,
                status.last_success_time or 0
            )
            
            if last_activity < cutoff_time:
                old_streams.append(stream_id)
        
        for stream_id in old_streams:
            del self.stream_status[stream_id]
            if stream_id in self.last_failure_time:
                del self.last_failure_time[stream_id]
        
        self._logger.info(f"Cleaned up {len(old_streams)} old stream statuses")
        return len(old_streams)