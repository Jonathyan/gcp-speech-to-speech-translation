import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from backend.audio_buffer import WebMChunkBuffer


class TestWebMChunkBuffer:
    """Test WebM chunk buffering for complete audio segments."""

    @pytest.fixture
    def buffer(self):
        """Create a WebMChunkBuffer instance for testing."""
        return WebMChunkBuffer(
            min_duration_seconds=2.0,  # Wait for at least 2 seconds of audio
            max_buffer_size=500 * 1024,  # 500KB max buffer
            timeout_seconds=5.0  # Timeout after 5 seconds
        )

    def test_buffer_initialization(self, buffer):
        """Test that buffer initializes correctly."""
        assert buffer.min_duration_seconds == 2.0
        assert buffer.max_buffer_size == 500 * 1024
        assert buffer.timeout_seconds == 5.0
        assert len(buffer.chunks) == 0
        assert buffer.total_size == 0
        assert buffer.first_chunk_time is None

    def test_add_webm_chunk(self, buffer):
        """Test adding WebM chunks to buffer."""
        # Simulate WebM header chunk
        webm_header = b'\x1a\x45\xdf\xa3' + b'\x00' * 100
        buffer.add_chunk(webm_header)
        
        assert len(buffer.chunks) == 1
        assert buffer.total_size == len(webm_header)
        assert buffer.first_chunk_time is not None

    def test_add_non_webm_chunk(self, buffer):
        """Test adding non-WebM chunks to buffer."""
        # Simulate incomplete chunk (not WebM header)
        incomplete_chunk = b'\x43\xc3\x81\x03' + b'\x00' * 100
        buffer.add_chunk(incomplete_chunk)
        
        assert len(buffer.chunks) == 1
        assert buffer.total_size == len(incomplete_chunk)

    def test_buffer_ready_by_duration(self, buffer):
        """Test that buffer becomes ready after minimum duration."""
        chunk1 = b'\x1a\x45\xdf\xa3' + b'\x00' * 100
        buffer.add_chunk(chunk1)
        
        # Should not be ready immediately
        assert not buffer.is_ready()
        
        # Mock time passage
        with patch('time.time', return_value=time.time() + 3.0):
            assert buffer.is_ready()

    def test_buffer_ready_by_size(self, buffer):
        """Test that buffer becomes ready when max size is reached."""
        # Add chunks until we exceed max buffer size
        large_chunk = b'\x43\xc3\x81\x03' + b'\x00' * (600 * 1024)  # 600KB
        buffer.add_chunk(large_chunk)
        
        # Should be ready due to size limit
        assert buffer.is_ready()

    def test_buffer_ready_by_timeout(self, buffer):
        """Test that buffer becomes ready after timeout."""
        chunk1 = b'\x1a\x45\xdf\xa3' + b'\x00' * 100
        buffer.add_chunk(chunk1)
        
        # Mock timeout exceeded
        with patch('time.time', return_value=time.time() + 6.0):
            assert buffer.is_ready()

    def test_get_combined_audio(self, buffer):
        """Test combining buffered chunks into single audio blob."""
        chunk1 = b'\x1a\x45\xdf\xa3' + b'\x00' * 50
        chunk2 = b'\x43\xc3\x81\x03' + b'\x11' * 50  
        chunk3 = b'\x44\xd4\x82\x04' + b'\x22' * 50
        
        buffer.add_chunk(chunk1)
        buffer.add_chunk(chunk2)
        buffer.add_chunk(chunk3)
        
        combined = buffer.get_combined_audio()
        expected = chunk1 + chunk2 + chunk3
        
        assert combined == expected
        assert len(combined) == 150 + 12  # 3 chunks * 50 bytes + headers

    def test_clear_buffer(self, buffer):
        """Test clearing buffer after use."""
        chunk1 = b'\x1a\x45\xdf\xa3' + b'\x00' * 100
        buffer.add_chunk(chunk1)
        
        assert len(buffer.chunks) > 0
        assert buffer.total_size > 0
        
        buffer.clear()
        
        assert len(buffer.chunks) == 0
        assert buffer.total_size == 0
        assert buffer.first_chunk_time is None

    def test_webm_format_detection(self, buffer):
        """Test WebM format detection logic."""
        webm_chunk = b'\x1a\x45\xdf\xa3' + b'\x00' * 100
        non_webm_chunk = b'\x43\xc3\x81\x03' + b'\x00' * 100
        
        assert buffer._is_webm_header(webm_chunk)
        assert not buffer._is_webm_header(non_webm_chunk)

    def test_buffer_stats(self, buffer):
        """Test buffer statistics reporting."""
        chunk1 = b'\x1a\x45\xdf\xa3' + b'\x00' * 100
        chunk2 = b'\x43\xc3\x81\x03' + b'\x11' * 200
        
        buffer.add_chunk(chunk1)
        buffer.add_chunk(chunk2)
        
        stats = buffer.get_stats()
        
        assert stats['chunk_count'] == 2
        assert stats['total_size'] == len(chunk1) + len(chunk2)
        assert stats['has_webm_header'] == True
        assert 'buffer_duration' in stats


class TestWebMBufferIntegration:
    """Integration tests for WebM buffering with audio processing."""

    @pytest.fixture
    def mock_stt_service(self):
        """Mock Speech-to-Text service for testing."""
        mock = Mock()
        mock.recognize_audio = Mock(return_value="test transcription")
        return mock

    @pytest.mark.asyncio
    async def test_buffered_audio_processing(self, mock_stt_service):
        """Test that buffered audio is processed correctly."""
        from backend.services import BufferedSpeechToText
        
        processor = BufferedSpeechToText(
            buffer_duration=1.0,  # Short duration for testing
            stt_service=mock_stt_service
        )
        
        # Simulate WebM chunks
        webm_header = b'\x1a\x45\xdf\xa3' + b'\x00' * 1000
        webm_chunk1 = b'\x43\xc3\x81\x03' + b'\x00' * 1000
        webm_chunk2 = b'\x44\xd4\x82\x04' + b'\x00' * 1000
        
        # Add chunks - should not process yet
        result1 = await processor.process_chunk(webm_header)
        assert result1 is None  # Not ready yet
        
        result2 = await processor.process_chunk(webm_chunk1)
        assert result2 is None  # Still not ready
        
        # Wait for buffer to be ready
        await asyncio.sleep(1.1)  # Exceed buffer duration
        
        result3 = await processor.process_chunk(webm_chunk2)
        
        # Should now process the buffered audio
        assert result3 == "test transcription"
        mock_stt_service.recognize_audio.assert_called_once()

    @pytest.mark.asyncio
    async def test_buffer_timeout_handling(self):
        """Test that buffer handles timeouts gracefully."""
        from backend.services import BufferedSpeechToText
        
        processor = BufferedSpeechToText(
            buffer_duration=10.0,  # Long duration
            timeout_seconds=0.5    # Short timeout for testing
        )
        
        # Add a chunk
        webm_header = b'\x1a\x45\xdf\xa3' + b'\x00' * 1000
        result1 = await processor.process_chunk(webm_header)
        assert result1 is None
        
        # Wait for timeout
        await asyncio.sleep(0.6)
        
        # Next chunk should trigger processing due to timeout
        webm_chunk = b'\x43\xc3\x81\x03' + b'\x00' * 1000
        with patch('backend.services.real_speech_to_text') as mock_stt:
            mock_stt.return_value = "timeout test"
            result2 = await processor.process_chunk(webm_chunk)
            assert result2 == "timeout test"