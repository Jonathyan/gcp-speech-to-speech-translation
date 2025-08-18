import logging
import subprocess
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class AudioFormat(Enum):
    """Supported audio formats."""
    WEBM = "webm"
    WAV = "wav" 
    OGG = "ogg"
    MP4 = "mp4"
    UNKNOWN = "unknown"


@dataclass
class AudioAnalysis:
    """Analysis results for an audio chunk."""
    format_type: AudioFormat
    confidence: float  # 0.0 to 1.0
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    duration_ms: Optional[float] = None
    is_complete: bool = False
    quality_score: float = 0.0


class AudioFormatDetector(ABC):
    """Base class for audio format detectors."""
    
    @abstractmethod
    def detect(self, chunk: bytes) -> AudioAnalysis:
        """Detect audio format and analyze chunk."""
        pass
    
    @abstractmethod
    def can_handle(self, format_type: AudioFormat) -> bool:
        """Check if this detector can handle the format."""
        pass


class WebMDetector(AudioFormatDetector):
    """Detector for WebM format audio chunks."""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        # WebM magic signatures
        self.webm_signatures = [
            b'\x1a\x45\xdf\xa3',  # EBML header
            b'\x18\x53\x80\x67',  # Segment
            b'\x1f\x43\xb6\x75',  # Cluster  
            b'\xa3',              # Simple block
            b'\xa1',              # Block
        ]
    
    def detect(self, chunk: bytes) -> AudioAnalysis:
        """Detect WebM format and analyze quality."""
        if len(chunk) < 16:
            return AudioAnalysis(
                format_type=AudioFormat.UNKNOWN,
                confidence=0.0,
                quality_score=0.0
            )
        
        # Check for WebM signatures
        confidence = 0.0
        header = chunk[:16]
        
        for signature in self.webm_signatures:
            if chunk.startswith(signature):
                confidence = 0.95
                break
            elif signature in chunk[:64]:  # Look in first 64 bytes
                confidence = 0.7
                break
        
        if confidence == 0.0:
            return AudioAnalysis(
                format_type=AudioFormat.UNKNOWN,
                confidence=0.0,
                quality_score=0.0
            )
        
        # Analyze WebM structure for quality
        quality_score = self._analyze_webm_quality(chunk)
        
        # Check if chunk appears complete
        is_complete = self._is_webm_chunk_complete(chunk)
        
        return AudioAnalysis(
            format_type=AudioFormat.WEBM,
            confidence=confidence,
            quality_score=quality_score,
            is_complete=is_complete,
            channels=1,  # Assume mono from MediaRecorder
            sample_rate=16000  # Assume 16kHz from config
        )
    
    def can_handle(self, format_type: AudioFormat) -> bool:
        return format_type == AudioFormat.WEBM
    
    def _analyze_webm_quality(self, chunk: bytes) -> float:
        """Analyze WebM chunk quality based on structure."""
        quality_score = 0.0
        
        # Check chunk size (larger chunks generally better quality)
        if len(chunk) > 10000:  # 10KB+
            quality_score += 0.4
        elif len(chunk) > 5000:  # 5KB+
            quality_score += 0.2
        
        # Check for multiple EBML elements (more complete)
        ebml_count = chunk.count(b'\x1a\x45')
        if ebml_count > 1:
            quality_score += 0.3
        
        # Check for audio data blocks
        if b'\xa3' in chunk or b'\xa1' in chunk:
            quality_score += 0.3
        
        return min(quality_score, 1.0)
    
    def _is_webm_chunk_complete(self, chunk: bytes) -> bool:
        """Check if WebM chunk appears to be complete."""
        # Look for complete EBML structure
        has_header = chunk.startswith(b'\x1a\x45\xdf\xa3')
        has_segment = b'\x18\x53\x80\x67' in chunk
        has_cluster = b'\x1f\x43\xb6\x75' in chunk
        has_blocks = b'\xa3' in chunk or b'\xa1' in chunk
        
        return has_header and has_segment and (has_cluster or has_blocks)


class WAVDetector(AudioFormatDetector):
    """Detector for WAV format audio chunks."""
    
    def detect(self, chunk: bytes) -> AudioAnalysis:
        """Detect WAV format."""
        if len(chunk) < 12:
            return AudioAnalysis(
                format_type=AudioFormat.UNKNOWN,
                confidence=0.0,
                quality_score=0.0
            )
        
        # Check RIFF header
        if not chunk.startswith(b'RIFF'):
            return AudioAnalysis(
                format_type=AudioFormat.UNKNOWN,
                confidence=0.0,
                quality_score=0.0
            )
        
        # Check WAVE format
        if chunk[8:12] != b'WAVE':
            return AudioAnalysis(
                format_type=AudioFormat.UNKNOWN,
                confidence=0.0,
                quality_score=0.0
            )
        
        # Parse WAV header for details
        sample_rate, channels, quality = self._parse_wav_header(chunk)
        
        return AudioAnalysis(
            format_type=AudioFormat.WAV,
            confidence=0.98,
            quality_score=quality,
            is_complete=len(chunk) > 44,  # At least header + some data
            sample_rate=sample_rate,
            channels=channels
        )
    
    def can_handle(self, format_type: AudioFormat) -> bool:
        return format_type == AudioFormat.WAV
    
    def _parse_wav_header(self, chunk: bytes) -> Tuple[Optional[int], Optional[int], float]:
        """Parse WAV header for sample rate and channels."""
        try:
            if len(chunk) < 44:
                return None, None, 0.5
            
            # Sample rate at offset 24
            sample_rate = int.from_bytes(chunk[24:28], 'little')
            
            # Channels at offset 22
            channels = int.from_bytes(chunk[22:24], 'little')
            
            # Quality based on sample rate and bit depth
            quality = 0.6
            if sample_rate >= 16000:
                quality += 0.2
            if sample_rate >= 44100:
                quality += 0.1
            if channels == 1:  # Mono preferred for STT
                quality += 0.1
            
            return sample_rate, channels, quality
            
        except Exception:
            return None, None, 0.3


class OGGDetector(AudioFormatDetector):
    """Detector for OGG format audio chunks."""
    
    def detect(self, chunk: bytes) -> AudioAnalysis:
        """Detect OGG format."""
        if len(chunk) < 4:
            return AudioAnalysis(
                format_type=AudioFormat.UNKNOWN,
                confidence=0.0,
                quality_score=0.0
            )
        
        # Check OGG signature
        if chunk.startswith(b'OggS'):
            return AudioAnalysis(
                format_type=AudioFormat.OGG,
                confidence=0.95,
                quality_score=0.8,
                is_complete=len(chunk) > 100,
                channels=1,
                sample_rate=16000
            )
        
        return AudioAnalysis(
            format_type=AudioFormat.UNKNOWN,
            confidence=0.0,
            quality_score=0.0
        )
    
    def can_handle(self, format_type: AudioFormat) -> bool:
        return format_type == AudioFormat.OGG


class MP4Detector(AudioFormatDetector):
    """Detector for MP4 format audio chunks."""
    
    def detect(self, chunk: bytes) -> AudioAnalysis:
        """Detect MP4 format."""
        if len(chunk) < 8:
            return AudioAnalysis(
                format_type=AudioFormat.UNKNOWN,
                confidence=0.0,
                quality_score=0.0
            )
        
        # Check for MP4 ftyp box
        if len(chunk) > 4 and chunk[4:8] == b'ftyp':
            return AudioAnalysis(
                format_type=AudioFormat.MP4,
                confidence=0.9,
                quality_score=0.7,
                is_complete=len(chunk) > 64,
                channels=1,
                sample_rate=16000
            )
        
        return AudioAnalysis(
            format_type=AudioFormat.UNKNOWN,
            confidence=0.0,
            quality_score=0.0
        )
    
    def can_handle(self, format_type: AudioFormat) -> bool:
        return format_type == AudioFormat.MP4


class AudioConverter(ABC):
    """Base class for audio format converters."""
    
    @abstractmethod
    async def convert(self, chunk: bytes, analysis: AudioAnalysis) -> bytes:
        """Convert audio chunk to LINEAR16 PCM format."""
        pass
    
    @abstractmethod
    def can_convert(self, format_type: AudioFormat) -> bool:
        """Check if this converter can handle the format."""
        pass


class WebMToLinear16Converter(AudioConverter):
    """Convert WebM chunks to LINEAR16 PCM format."""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
    
    async def convert(self, chunk: bytes, analysis: AudioAnalysis) -> bytes:
        """Convert WebM chunk to LINEAR16 using ffmpeg."""
        try:
            # Enhanced ffmpeg command for WebM
            cmd = [
                'ffmpeg',
                '-hide_banner',
                '-loglevel', 'error',
                '-f', 'webm',
                '-i', 'pipe:0',
                '-vn',  # No video
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-f', 's16le',
                'pipe:1'
            ]
            
            # Run conversion with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=chunk),
                timeout=10.0
            )
            
            if process.returncode == 0 and stdout:
                self._logger.debug(f"WebM converted: {len(chunk)} → {len(stdout)} bytes")
                return stdout
            else:
                error_msg = stderr.decode('utf-8', errors='ignore')
                self._logger.warning(f"WebM conversion failed: {error_msg}")
                return chunk  # Return original if conversion fails
                
        except asyncio.TimeoutError:
            self._logger.error("WebM conversion timeout")
            return chunk
        except Exception as e:
            self._logger.error(f"WebM conversion error: {e}")
            return chunk
    
    def can_convert(self, format_type: AudioFormat) -> bool:
        return format_type == AudioFormat.WEBM


class WAVToLinear16Converter(AudioConverter):
    """Convert WAV chunks to LINEAR16 PCM format."""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
    
    async def convert(self, chunk: bytes, analysis: AudioAnalysis) -> bytes:
        """Convert WAV to LINEAR16."""
        if analysis.sample_rate == 16000 and analysis.channels == 1:
            # Already in correct format, just strip header
            if len(chunk) > 44:
                return chunk[44:]  # Skip WAV header
        
        # Convert using ffmpeg
        try:
            cmd = [
                'ffmpeg',
                '-hide_banner',
                '-loglevel', 'error',
                '-f', 'wav',
                '-i', 'pipe:0',
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-f', 's16le',
                'pipe:1'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=chunk),
                timeout=5.0
            )
            
            if process.returncode == 0 and stdout:
                return stdout
            else:
                return chunk
                
        except Exception as e:
            self._logger.error(f"WAV conversion error: {e}")
            return chunk
    
    def can_convert(self, format_type: AudioFormat) -> bool:
        return format_type == AudioFormat.WAV


class RawAudioHandler(AudioConverter):
    """Handle unknown/raw audio formats."""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
    
    async def convert(self, chunk: bytes, analysis: AudioAnalysis) -> bytes:
        """Handle raw audio - return as-is for Google Cloud auto-detection."""
        self._logger.debug(f"Passing raw audio to Google Cloud: {len(chunk)} bytes")
        return chunk
    
    def can_convert(self, format_type: AudioFormat) -> bool:
        return format_type == AudioFormat.UNKNOWN


class EnhancedAudioProcessor:
    """Enhanced audio processor with multiple format detectors and converters."""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        
        # Initialize detectors
        self.detectors: List[AudioFormatDetector] = [
            WebMDetector(),
            WAVDetector(),
            OGGDetector(),
            MP4Detector()
        ]
        
        # Initialize converters
        self.converters: Dict[AudioFormat, AudioConverter] = {
            AudioFormat.WEBM: WebMToLinear16Converter(),
            AudioFormat.WAV: WAVToLinear16Converter(),
            AudioFormat.OGG: WebMToLinear16Converter(),  # Use WebM converter for OGG
            AudioFormat.MP4: WebMToLinear16Converter(),  # Use WebM converter for MP4
            AudioFormat.UNKNOWN: RawAudioHandler()
        }
        
        # Processing stats
        self.stats = {
            'total_chunks': 0,
            'format_counts': {fmt.value: 0 for fmt in AudioFormat},
            'conversion_successes': 0,
            'conversion_failures': 0
        }
    
    async def analyze_chunk(self, chunk: bytes) -> AudioAnalysis:
        """Analyze audio chunk to determine format and quality."""
        if not chunk:
            return AudioAnalysis(
                format_type=AudioFormat.UNKNOWN,
                confidence=0.0,
                quality_score=0.0
            )
        
        self.stats['total_chunks'] += 1
        
        # Try all detectors to find best match
        best_analysis = AudioAnalysis(
            format_type=AudioFormat.UNKNOWN,
            confidence=0.0,
            quality_score=0.0
        )
        
        for detector in self.detectors:
            try:
                analysis = detector.detect(chunk)
                if analysis.confidence > best_analysis.confidence:
                    best_analysis = analysis
            except Exception as e:
                self._logger.error(f"Detector error: {e}")
        
        # Update stats
        self.stats['format_counts'][best_analysis.format_type.value] += 1
        
        self._logger.debug(f"Audio analysis: {best_analysis.format_type.value} "
                          f"(confidence: {best_analysis.confidence:.2f}, "
                          f"quality: {best_analysis.quality_score:.2f})")
        
        return best_analysis
    
    async def process_chunk(self, chunk: bytes) -> Tuple[bytes, AudioAnalysis]:
        """Process audio chunk: analyze format and convert to LINEAR16."""
        # Analyze the chunk first
        analysis = await self.analyze_chunk(chunk)
        
        # Skip processing for very small or low-confidence chunks
        if len(chunk) < 100 or analysis.confidence < 0.3:
            self._logger.debug(f"Skipping processing: size={len(chunk)}, confidence={analysis.confidence}")
            return chunk, analysis
        
        # Get appropriate converter
        converter = self.converters.get(analysis.format_type)
        if not converter:
            self._logger.warning(f"No converter for format: {analysis.format_type}")
            converter = self.converters[AudioFormat.UNKNOWN]
        
        # Convert the audio
        try:
            converted_chunk = await converter.convert(chunk, analysis)
            if converted_chunk != chunk:  # Conversion happened
                self.stats['conversion_successes'] += 1
                self._logger.debug(f"Conversion successful: {len(chunk)} → {len(converted_chunk)} bytes")
            else:
                self._logger.debug("No conversion needed or conversion failed, using original")
            
            return converted_chunk, analysis
            
        except Exception as e:
            self.stats['conversion_failures'] += 1
            self._logger.error(f"Conversion failed: {e}")
            return chunk, analysis
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            **self.stats,
            'success_rate': (
                self.stats['conversion_successes'] / 
                max(1, self.stats['conversion_successes'] + self.stats['conversion_failures'])
            )
        }