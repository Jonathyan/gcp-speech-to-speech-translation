import logging
import time
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from .audio_processor import EnhancedAudioProcessor, AudioAnalysis, AudioFormat


class BufferReleaseReason(Enum):
    """Reasons why a buffer was released for processing."""
    QUALITY_THRESHOLD = "quality_threshold"
    MIN_DURATION = "min_duration" 
    MAX_SIZE = "max_size"
    TIMEOUT = "timeout"
    SILENCE_DETECTED = "silence_detected"
    FORCE_FLUSH = "force_flush"


@dataclass
class BufferChunk:
    """Represents a chunk of audio data in the buffer."""
    data: bytes
    analysis: AudioAnalysis
    timestamp: float
    sequence: int


@dataclass 
class BufferMetrics:
    """Metrics about buffer performance and decisions."""
    chunks_count: int
    total_size: int
    duration_seconds: float
    average_quality: float
    best_quality: float
    dominant_format: AudioFormat
    release_reason: BufferReleaseReason
    processing_time_ms: float
    buffer_efficiency: float  # Useful data vs total data ratio


class SmartAudioBuffer:
    """Smart audio buffer with quality-based early release and adaptive behavior."""
    
    def __init__(self, 
                 min_duration_seconds: float = 2.5,  # INCREASED: Need longer audio for STT
                 quality_threshold: float = 0.8,
                 max_buffer_size: int = 300 * 1024,  # 300KB
                 timeout_seconds: float = 6.0,  # INCREASED: More time for quality audio
                 silence_threshold: float = 0.1,
                 adaptive_timeout: bool = True):
        """
        Initialize smart audio buffer.
        
        Args:
            min_duration_seconds: Minimum buffer duration before release
            quality_threshold: Quality score threshold for early release
            max_buffer_size: Maximum buffer size before forced release
            timeout_seconds: Maximum wait time before timeout release  
            silence_threshold: Threshold for silence detection
            adaptive_timeout: Enable adaptive timeout based on quality
        """
        self.min_duration_seconds = min_duration_seconds
        self.quality_threshold = quality_threshold
        self.max_buffer_size = max_buffer_size
        self.timeout_seconds = timeout_seconds
        self.silence_threshold = silence_threshold
        self.adaptive_timeout = adaptive_timeout
        
        # Buffer state
        self.chunks: List[BufferChunk] = []
        self.total_size = 0
        self.first_chunk_time: Optional[float] = None
        self.sequence_counter = 0
        
        # Quality tracking
        self._quality_history: List[float] = []
        self._format_counts: Dict[AudioFormat, int] = {}
        
        # Adaptive behavior
        self._recent_releases: List[Tuple[float, BufferReleaseReason]] = []
        self._performance_history: List[float] = []
        
        # Components
        self.audio_processor = EnhancedAudioProcessor()
        self._logger = logging.getLogger(__name__)
        
        # Statistics
        self.stats = {
            'total_releases': 0,
            'release_reasons': {reason.value: 0 for reason in BufferReleaseReason},
            'average_buffer_duration': 0.0,
            'quality_improvements': 0,
            'timeout_adaptations': 0
        }

    async def add_chunk(self, chunk_data: bytes) -> Optional[BufferMetrics]:
        """
        Add audio chunk to buffer and check if ready for processing.
        
        Args:
            chunk_data: Raw audio data
            
        Returns:
            BufferMetrics if buffer is ready for processing, None otherwise
        """
        if not chunk_data:
            return None
        
        current_time = time.time()
        
        # Process the chunk through enhanced audio processor
        processed_data, analysis = await self.audio_processor.process_chunk(chunk_data)
        
        # Create buffer chunk
        buffer_chunk = BufferChunk(
            data=processed_data,
            analysis=analysis,
            timestamp=current_time,
            sequence=self.sequence_counter
        )
        
        self.sequence_counter += 1
        
        # Add to buffer
        self.chunks.append(buffer_chunk)
        self.total_size += len(processed_data)
        
        if self.first_chunk_time is None:
            self.first_chunk_time = current_time
        
        # Update tracking
        self._quality_history.append(analysis.quality_score)
        format_count = self._format_counts.get(analysis.format_type, 0)
        self._format_counts[analysis.format_type] = format_count + 1
        
        self._logger.debug(f"Added chunk: {len(chunk_data)}→{len(processed_data)} bytes, "
                          f"quality: {analysis.quality_score:.2f}, "
                          f"format: {analysis.format_type.value}")
        
        # Calculate buffer duration for logging
        buffer_duration = current_time - (self.first_chunk_time or current_time)
        
        # Check if buffer is ready for processing
        release_decision = await self._evaluate_release_conditions()
        
        if release_decision:
            self._logger.info(f"Buffer release triggered: {release_decision.value}, "
                            f"chunks: {len(self.chunks)}, duration: {buffer_duration:.1f}s, "
                            f"timing_state_preserved: {self.first_chunk_time is not None}")
            return await self._release_buffer(release_decision)
        
        # Log buffer state for debugging
        self._logger.debug(f"Buffer accumulating: {len(self.chunks)} chunks, "
                         f"duration: {buffer_duration:.1f}s, size: {self.total_size} bytes, "
                         f"first_chunk_time: {self.first_chunk_time}")
        
        return None

    async def _evaluate_release_conditions(self) -> Optional[BufferReleaseReason]:
        """Evaluate if buffer should be released for processing."""
        if not self.chunks or self.first_chunk_time is None:
            return None
        
        current_time = time.time()
        buffer_duration = current_time - self.first_chunk_time
        
        # 1. Force release if max size exceeded
        if self.total_size >= self.max_buffer_size:
            self._logger.debug(f"Max size release: {self.total_size} >= {self.max_buffer_size}")
            return BufferReleaseReason.MAX_SIZE
        
        # 2. Quality-based early release
        if await self._should_early_release_for_quality():
            self._logger.debug("Quality threshold early release")
            return BufferReleaseReason.QUALITY_THRESHOLD
        
        # 3. Silence detection
        if await self._detect_silence():
            self._logger.debug("Silence detected release")
            return BufferReleaseReason.SILENCE_DETECTED
        
        # 4. Adaptive timeout
        timeout_threshold = self._get_adaptive_timeout()
        if buffer_duration >= timeout_threshold:
            self._logger.debug(f"Timeout release: {buffer_duration:.1f}s >= {timeout_threshold:.1f}s")
            return BufferReleaseReason.TIMEOUT
        
        # 5. Minimum duration met
        if buffer_duration >= self.min_duration_seconds:
            # Additional checks for optimal release point
            if await self._is_good_release_point():
                self._logger.debug(f"Min duration release: {buffer_duration:.1f}s")
                return BufferReleaseReason.MIN_DURATION
        
        return None

    async def _should_early_release_for_quality(self) -> bool:
        """Check if buffer should be released early based on quality."""
        if len(self._quality_history) < 3:  # Need some samples
            return False
        
        # Calculate recent average quality
        recent_quality = sum(self._quality_history[-3:]) / 3
        
        # Early release conditions
        conditions = [
            # High recent quality above threshold
            recent_quality >= self.quality_threshold,
            
            # Have sufficient duration (at least 1 second)
            self._get_buffer_duration() >= 1.0,
            
            # Have some complete chunks
            sum(1 for chunk in self.chunks if chunk.analysis.is_complete) >= 2,
            
            # Buffer is reasonably sized
            self.total_size >= 10000  # At least 10KB
        ]
        
        return all(conditions)

    async def _detect_silence(self) -> bool:
        """Detect silence periods that indicate natural speech breaks."""
        if len(self.chunks) < 5:  # Need several chunks to detect patterns
            return False
        
        # Check recent chunks for low quality (potential silence)
        recent_chunks = self.chunks[-3:]
        low_quality_count = sum(
            1 for chunk in recent_chunks 
            if chunk.analysis.quality_score < self.silence_threshold
        )
        
        # Silence detected if most recent chunks are low quality
        if low_quality_count >= 2:
            # But only if we have reasonable buffer duration
            if self._get_buffer_duration() >= self.min_duration_seconds * 0.8:
                return True
        
        return False

    def _get_adaptive_timeout(self) -> float:
        """Calculate adaptive timeout based on recent performance."""
        if not self.adaptive_timeout:
            return self.timeout_seconds
        
        base_timeout = self.timeout_seconds
        
        # Adjust based on recent quality trends
        if len(self._quality_history) >= 5:
            recent_avg = sum(self._quality_history[-5:]) / 5
            if recent_avg > 0.7:
                # High quality audio, can wait a bit longer
                base_timeout *= 1.2
            elif recent_avg < 0.3:
                # Low quality audio, don't wait as long
                base_timeout *= 0.8
        
        # Adjust based on recent release patterns
        if len(self._recent_releases) >= 3:
            recent_timeouts = [
                time_taken for time_taken, reason in self._recent_releases[-3:]
                if reason == BufferReleaseReason.TIMEOUT
            ]
            if len(recent_timeouts) >= 2:
                # Too many timeouts, reduce timeout
                base_timeout *= 0.9
        
        # Clamp to reasonable bounds
        return max(1.0, min(base_timeout, self.timeout_seconds * 1.5))

    async def _is_good_release_point(self) -> bool:
        """Check if this is a good point to release the buffer."""
        # Look for natural speech boundaries
        if len(self.chunks) < 2:
            return True
        
        # Check if recent chunks show decreasing quality (end of speech)
        recent_qualities = [chunk.analysis.quality_score for chunk in self.chunks[-3:]]
        if len(recent_qualities) >= 2:
            quality_trend = recent_qualities[-1] - recent_qualities[-2]
            if quality_trend < -0.2:  # Significant quality drop
                return True
        
        # Check for format consistency (good chunk sequence)
        recent_formats = [chunk.analysis.format_type for chunk in self.chunks[-3:]]
        dominant_format = max(set(recent_formats), key=recent_formats.count)
        format_consistency = recent_formats.count(dominant_format) / len(recent_formats)
        
        return format_consistency >= 0.7

    async def _release_buffer(self, reason: BufferReleaseReason) -> BufferMetrics:
        """Release buffer and return metrics."""
        if not self.chunks:
            raise ValueError("Cannot release empty buffer")
        
        release_start = time.time()
        
        # Calculate metrics
        duration = self._get_buffer_duration()
        average_quality = sum(self._quality_history) / len(self._quality_history) if self._quality_history else 0.0
        best_quality = max(self._quality_history) if self._quality_history else 0.0
        
        # Determine dominant format
        if self._format_counts:
            dominant_format = max(self._format_counts.items(), key=lambda x: x[1])[0]
        else:
            dominant_format = AudioFormat.UNKNOWN
        
        # Calculate buffer efficiency (useful data vs overhead)
        total_original_size = sum(len(chunk.data) for chunk in self.chunks)
        efficiency = min(1.0, total_original_size / max(1, self.total_size))
        
        processing_time = (time.time() - release_start) * 1000  # Convert to ms
        
        metrics = BufferMetrics(
            chunks_count=len(self.chunks),
            total_size=self.total_size,
            duration_seconds=duration,
            average_quality=average_quality,
            best_quality=best_quality,
            dominant_format=dominant_format,
            release_reason=reason,
            processing_time_ms=processing_time,
            buffer_efficiency=efficiency
        )
        
        # Update statistics
        self.stats['total_releases'] += 1
        self.stats['release_reasons'][reason.value] += 1
        
        # Update performance history
        self._recent_releases.append((time.time(), reason))
        if len(self._recent_releases) > 10:
            self._recent_releases.pop(0)
        
        self._performance_history.append(duration)
        if len(self._performance_history) > 20:
            self._performance_history.pop(0)
        
        # Update average buffer duration
        if self._performance_history:
            self.stats['average_buffer_duration'] = sum(self._performance_history) / len(self._performance_history)
        
        self._logger.info(f"Buffer released: {reason.value}, "
                         f"{metrics.chunks_count} chunks, "
                         f"{metrics.total_size} bytes, "
                         f"{metrics.duration_seconds:.1f}s, "
                         f"quality: {metrics.average_quality:.2f}")
        
        return metrics

    def get_combined_audio(self) -> bytes:
        """Get all buffered audio data combined."""
        if not self.chunks:
            return b''
        
        combined = b''.join(chunk.data for chunk in self.chunks)
        self._logger.debug(f"Combined {len(self.chunks)} chunks into {len(combined)} bytes")
        return combined

    def clear(self):
        """Clear the buffer after processing."""
        chunks_count = len(self.chunks)
        total_size = self.total_size
        
        self.chunks.clear()
        self.total_size = 0
        # CRITICAL FIX: DON'T reset first_chunk_time to preserve timing state for subsequent chunks
        # self.first_chunk_time = None  # This was breaking multi-sentence translation!
        self.sequence_counter = 0
        self._quality_history.clear()
        self._format_counts.clear()
        
        self._logger.info(f"Buffer cleared: {chunks_count} chunks, {total_size} bytes (preserving timing state)")

    def force_release(self) -> Optional[BufferMetrics]:
        """Force release of buffer contents."""
        if not self.chunks:
            return None
        
        return asyncio.create_task(self._release_buffer(BufferReleaseReason.FORCE_FLUSH))

    def _get_buffer_duration(self) -> float:
        """Get current buffer duration in seconds."""
        if self.first_chunk_time is None:
            return 0.0
        return time.time() - self.first_chunk_time

    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get detailed buffer statistics."""
        current_metrics = {
            'current_chunks': len(self.chunks),
            'current_size': self.total_size,
            'current_duration': self._get_buffer_duration(),
            'current_quality_avg': (
                sum(self._quality_history) / len(self._quality_history) 
                if self._quality_history else 0.0
            ),
            'format_distribution': dict(self._format_counts),
            'recent_releases': len(self._recent_releases),
        }
        
        # Add audio processor stats
        processor_stats = self.audio_processor.get_stats()
        
        return {
            **self.stats,
            **current_metrics,
            'processor_stats': processor_stats,
            'adaptive_timeout_current': self._get_adaptive_timeout()
        }