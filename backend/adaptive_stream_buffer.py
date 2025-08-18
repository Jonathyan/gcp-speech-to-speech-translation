"""
Adaptive Stream Buffer for Phase 2 Hybrid Streaming

This module implements intelligent buffering that can dynamically switch
between streaming and buffered modes based on audio characteristics and
connection quality.
"""
import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass
from collections import deque
import statistics


class StreamingMode(Enum):
    """Streaming processing modes."""
    BUFFERED = "buffered"
    STREAMING = "streaming"
    HYBRID = "hybrid"


class BufferStrategy(Enum):
    """Buffer strategy recommendations."""
    STREAMING = "streaming"
    BUFFERED = "buffered"
    ADAPTIVE = "adaptive"


@dataclass
class AudioChunkMetrics:
    """Metrics for individual audio chunks."""
    size: int
    timestamp: float
    format_detected: Optional[str]
    quality_score: float = 0.0
    processing_time_ms: float = 0.0


@dataclass
class BufferAnalytics:
    """Analytics for buffer performance."""
    average_chunk_size: float
    chunk_frequency: float  # chunks per second
    total_duration: float
    quality_score: float
    buffer_efficiency: float
    recommended_mode: StreamingMode


class AdaptiveStreamBuffer:
    """Adaptive stream buffer that switches between streaming and buffered modes."""
    
    def __init__(self,
                 streaming_threshold_bytes: int = 5000,
                 buffered_timeout_seconds: float = 2.0,
                 frequency_threshold_per_second: float = 8.0,
                 quality_threshold: float = 0.7,
                 analysis_window_seconds: float = 5.0):
        """
        Initialize adaptive stream buffer.
        
        Args:
            streaming_threshold_bytes: Chunk size threshold for streaming mode
            buffered_timeout_seconds: Timeout for buffered mode release
            frequency_threshold_per_second: Chunk frequency threshold for streaming
            quality_threshold: Quality threshold for mode decisions
            analysis_window_seconds: Window for performance analysis
        """
        self.streaming_threshold = streaming_threshold_bytes
        self.buffered_timeout = buffered_timeout_seconds
        self.frequency_threshold = frequency_threshold_per_second
        self.quality_threshold = quality_threshold
        self.analysis_window = analysis_window_seconds
        
        # Current state
        self.current_mode = StreamingMode.BUFFERED
        self.chunks: List[AudioChunkMetrics] = []
        self.start_time: Optional[float] = None
        
        # Analytics
        self.metrics_history: deque = deque(maxlen=100)
        self.mode_switches: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.stats = {
            'total_chunks': 0,
            'mode_switches': 0,
            'streaming_chunks': 0,
            'buffered_chunks': 0,
            'average_processing_time': 0.0
        }
        
        self._logger = logging.getLogger(__name__)
    
    async def add_chunk(self, audio_chunk: bytes, 
                       format_detected: Optional[str] = None,
                       quality_score: float = 0.0) -> StreamingMode:
        """
        Add audio chunk and determine processing mode.
        
        Args:
            audio_chunk: Raw audio data
            format_detected: Detected audio format
            quality_score: Quality score for the chunk
            
        Returns:
            Recommended streaming mode for this chunk
        """
        chunk_metrics = AudioChunkMetrics(
            size=len(audio_chunk),
            timestamp=time.time(),
            format_detected=format_detected,
            quality_score=quality_score
        )
        
        self.chunks.append(chunk_metrics)
        self.stats['total_chunks'] += 1
        
        if self.start_time is None:
            self.start_time = chunk_metrics.timestamp
        
        # Analyze current conditions and decide mode
        recommended_mode = await self._analyze_and_decide_mode()
        
        # Switch mode if needed
        if recommended_mode != self.current_mode:
            await self._switch_mode(recommended_mode, chunk_metrics)
        
        return self.current_mode
    
    async def _analyze_and_decide_mode(self) -> StreamingMode:
        """Analyze current conditions and recommend processing mode."""
        if len(self.chunks) < 2:
            return StreamingMode.BUFFERED  # Start conservative
        
        # Get recent chunks for analysis
        recent_chunks = self._get_recent_chunks(self.analysis_window)
        
        if not recent_chunks:
            return self.current_mode
        
        # Calculate metrics
        analytics = self._calculate_analytics(recent_chunks)
        
        # Decision logic
        return self._decide_mode_from_analytics(analytics, recent_chunks)
    
    def _get_recent_chunks(self, window_seconds: float) -> List[AudioChunkMetrics]:
        """Get chunks within the specified time window."""
        if not self.chunks:
            return []
        
        cutoff_time = time.time() - window_seconds
        return [chunk for chunk in self.chunks if chunk.timestamp >= cutoff_time]
    
    def _calculate_analytics(self, chunks: List[AudioChunkMetrics]) -> BufferAnalytics:
        """Calculate analytics for a set of chunks."""
        if not chunks:
            return BufferAnalytics(0, 0, 0, 0, 0, StreamingMode.BUFFERED)
        
        # Basic metrics
        total_size = sum(chunk.size for chunk in chunks)
        average_chunk_size = total_size / len(chunks)
        
        # Frequency calculation
        time_span = chunks[-1].timestamp - chunks[0].timestamp
        chunk_frequency = len(chunks) / max(time_span, 0.1)  # Avoid division by zero
        
        # Quality metrics
        quality_scores = [chunk.quality_score for chunk in chunks if chunk.quality_score > 0]
        average_quality = statistics.mean(quality_scores) if quality_scores else 0.0
        
        # Duration calculation
        total_duration = time_span
        
        # Buffer efficiency (simplified)
        expected_chunks = time_span * 4  # Expect ~4 chunks per second
        buffer_efficiency = min(len(chunks) / max(expected_chunks, 1), 1.0)
        
        return BufferAnalytics(
            average_chunk_size=average_chunk_size,
            chunk_frequency=chunk_frequency,
            total_duration=total_duration,
            quality_score=average_quality,
            buffer_efficiency=buffer_efficiency,
            recommended_mode=StreamingMode.BUFFERED  # Will be set by decision logic
        )
    
    def _decide_mode_from_analytics(self, analytics: BufferAnalytics, recent_chunks: List[AudioChunkMetrics]) -> StreamingMode:
        """Decide processing mode based on analytics."""
        # Streaming conditions
        streaming_score = 0
        
        # Large chunks favor streaming (check both average and recent max)
        recent_chunk_sizes = [chunk.size for chunk in recent_chunks[-3:]]  # Last 3 chunks
        max_recent_size = max(recent_chunk_sizes) if recent_chunk_sizes else 0
        
        if analytics.average_chunk_size > self.streaming_threshold:
            streaming_score += 3
        elif max_recent_size > self.streaming_threshold:
            streaming_score += 2  # Individual large chunk
        
        # High frequency favors streaming
        if analytics.chunk_frequency > self.frequency_threshold:
            streaming_score += 2
        
        # Good quality favors streaming
        if analytics.quality_score > self.quality_threshold:
            streaming_score += 2
        
        # Good buffer efficiency favors streaming
        if analytics.buffer_efficiency > 0.8:
            streaming_score += 1
        
        # Buffered conditions (negative scores favor buffered)
        buffered_score = 0
        
        # Small chunks favor buffered (but not if frequency is very high)
        if analytics.average_chunk_size < self.streaming_threshold * 0.5:
            if analytics.chunk_frequency < self.frequency_threshold:  # Only penalize if frequency is also low
                buffered_score += 2
        
        # Low frequency favors buffered
        if analytics.chunk_frequency < self.frequency_threshold * 0.5:
            buffered_score += 3
        
        # Poor quality favors buffered
        if analytics.quality_score < self.quality_threshold * 0.5:
            buffered_score += 2
        
        # Debug logging
        self._logger.debug(f"Mode decision: streaming_score={streaming_score}, buffered_score={buffered_score}, "
                         f"current_mode={self.current_mode}, chunk_size={analytics.average_chunk_size}, "
                         f"frequency={analytics.chunk_frequency}")
        
        # Decision with light hysteresis (prevent rapid switching)
        if self.current_mode == StreamingMode.STREAMING:
            # Threshold to switch back to buffered
            return StreamingMode.BUFFERED if buffered_score > streaming_score else StreamingMode.STREAMING
        else:
            # Threshold to switch to streaming (slight bias towards current mode)
            return StreamingMode.STREAMING if streaming_score >= buffered_score else StreamingMode.BUFFERED
    
    async def _switch_mode(self, new_mode: StreamingMode, trigger_chunk: AudioChunkMetrics):
        """Switch to new processing mode."""
        old_mode = self.current_mode
        self.current_mode = new_mode
        self.stats['mode_switches'] += 1
        
        # Record mode switch
        switch_info = {
            'timestamp': trigger_chunk.timestamp,
            'from_mode': old_mode.value,
            'to_mode': new_mode.value,
            'trigger_chunk_size': trigger_chunk.size,
            'chunks_in_buffer': len(self.chunks),
            'reason': self._get_switch_reason(trigger_chunk)
        }
        
        self.mode_switches.append(switch_info)
        
        self._logger.info(f"Mode switched: {old_mode.value} → {new_mode.value}, "
                         f"reason: {switch_info['reason']}")
    
    def _get_switch_reason(self, chunk: AudioChunkMetrics) -> str:
        """Get human-readable reason for mode switch."""
        recent_chunks = self._get_recent_chunks(2.0)  # Last 2 seconds
        
        if not recent_chunks:
            return "initialization"
        
        analytics = self._calculate_analytics(recent_chunks)
        
        reasons = []
        
        if analytics.average_chunk_size > self.streaming_threshold:
            reasons.append("large_chunks")
        
        if analytics.chunk_frequency > self.frequency_threshold:
            reasons.append("high_frequency")
        
        if analytics.quality_score > self.quality_threshold:
            reasons.append("good_quality")
        
        if analytics.average_chunk_size < self.streaming_threshold * 0.5:
            reasons.append("small_chunks")
        
        if analytics.chunk_frequency < self.frequency_threshold * 0.5:
            reasons.append("low_frequency")
        
        return ",".join(reasons) if reasons else "threshold_analysis"
    
    def evaluate_strategies(self, conditions: Dict[str, Any]) -> Set[BufferStrategy]:
        """Evaluate and recommend buffer strategies based on conditions."""
        strategies = set()
        
        chunk_frequency = conditions.get('chunk_frequency', 0)
        average_chunk_size = conditions.get('average_chunk_size', 0)
        connection_quality = conditions.get('connection_quality', 0.5)
        
        # Streaming strategy conditions
        if (chunk_frequency > self.frequency_threshold and 
            average_chunk_size > self.streaming_threshold and
            connection_quality > 0.7):
            strategies.add(BufferStrategy.STREAMING)
        
        # Buffered strategy conditions
        if (chunk_frequency < self.frequency_threshold * 0.5 or
            average_chunk_size < self.streaming_threshold * 0.5 or
            connection_quality < 0.4):
            strategies.add(BufferStrategy.BUFFERED)
        
        # Adaptive strategy (middle ground)
        if (self.frequency_threshold * 0.5 <= chunk_frequency <= self.frequency_threshold and
            connection_quality >= 0.4):
            strategies.add(BufferStrategy.ADAPTIVE)
        
        # Default to buffered if no clear strategy
        if not strategies:
            strategies.add(BufferStrategy.BUFFERED)
        
        return strategies
    
    def should_release_buffer(self) -> bool:
        """Check if buffer should be released in buffered mode."""
        if not self.chunks or not self.start_time:
            return False
        
        # Timeout-based release
        time_since_start = time.time() - self.start_time
        if time_since_start >= self.buffered_timeout:
            return True
        
        # Size-based release
        total_size = sum(chunk.size for chunk in self.chunks)
        if total_size > self.streaming_threshold * 2:  # 2x threshold
            return True
        
        # Quality-based release
        recent_chunks = self._get_recent_chunks(1.0)
        if recent_chunks:
            analytics = self._calculate_analytics(recent_chunks)
            if analytics.quality_score > self.quality_threshold * 1.2:  # High quality
                return True
        
        return False
    
    def get_buffered_audio(self) -> bytes:
        """Get combined audio data for buffered processing."""
        if not self.chunks:
            return b''
        
        # For this implementation, we don't actually store the audio data
        # This would return the combined audio in a real implementation
        total_size = sum(chunk.size for chunk in self.chunks)
        
        # Simulate combined audio
        return b'x' * total_size
    
    def clear(self):
        """Clear the buffer and reset state."""
        self.chunks.clear()
        self.start_time = None
        # Note: Don't reset current_mode to preserve mode between buffers
    
    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get comprehensive buffer statistics."""
        recent_chunks = self._get_recent_chunks(self.analysis_window)
        analytics = self._calculate_analytics(recent_chunks) if recent_chunks else None
        
        return {
            'current_mode': self.current_mode.value,
            'chunks_in_buffer': len(self.chunks),
            'buffer_age_seconds': (time.time() - self.start_time) if self.start_time else 0,
            'total_buffer_size': sum(chunk.size for chunk in self.chunks),
            'analytics': {
                'average_chunk_size': analytics.average_chunk_size if analytics else 0,
                'chunk_frequency': analytics.chunk_frequency if analytics else 0,
                'quality_score': analytics.quality_score if analytics else 0,
                'buffer_efficiency': analytics.buffer_efficiency if analytics else 0
            } if analytics else None,
            'stats': self.stats.copy(),
            'recent_mode_switches': self.mode_switches[-5:] if self.mode_switches else []
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get detailed performance report."""
        if not self.chunks:
            return {'status': 'no_data'}
        
        # Calculate overall performance metrics
        total_duration = (self.chunks[-1].timestamp - self.chunks[0].timestamp) if len(self.chunks) > 1 else 0
        
        # Mode distribution
        mode_distribution = {}
        for switch in self.mode_switches:
            mode = switch['to_mode']
            mode_distribution[mode] = mode_distribution.get(mode, 0) + 1
        
        # Recent performance
        recent_chunks = self._get_recent_chunks(self.analysis_window)
        recent_analytics = self._calculate_analytics(recent_chunks) if recent_chunks else None
        
        return {
            'status': 'active',
            'total_runtime_seconds': total_duration,
            'total_chunks_processed': len(self.chunks),
            'mode_switches_count': len(self.mode_switches),
            'mode_distribution': mode_distribution,
            'current_mode': self.current_mode.value,
            'recent_analytics': {
                'chunk_frequency': recent_analytics.chunk_frequency,
                'average_chunk_size': recent_analytics.average_chunk_size,
                'quality_score': recent_analytics.quality_score
            } if recent_analytics else None,
            'configuration': {
                'streaming_threshold_bytes': self.streaming_threshold,
                'buffered_timeout_seconds': self.buffered_timeout,
                'frequency_threshold_per_second': self.frequency_threshold,
                'quality_threshold': self.quality_threshold
            }
        }