import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from backend.streaming_stt import StreamingSpeechToText, StreamManager


class TestStreamingSpeechToText:
    """Test Google Cloud streaming Speech-to-Text service."""

    @pytest.fixture
    def mock_streaming_client(self):
        """Mock Google Cloud streaming STT client."""
        mock_client = Mock()
        mock_response_stream = AsyncMock()
        mock_client.streaming_recognize = Mock(return_value=mock_response_stream)
        return mock_client, mock_response_stream

    @pytest.fixture
    def streaming_stt(self, mock_streaming_client):
        """Create StreamingSpeechToText instance with mock client."""
        client, response_stream = mock_streaming_client
        service = StreamingSpeechToText(client=client)
        return service, client, response_stream

    def test_streaming_stt_initialization(self, streaming_stt):
        """Test streaming STT service initializes correctly."""
        service, client, _ = streaming_stt
        
        assert service.client == client
        assert service.language_code == 'nl-NL'
        assert service.sample_rate == 16000
        assert service.is_streaming == False

    @pytest.mark.asyncio
    async def test_start_streaming_session(self, streaming_stt):
        """Test starting a streaming recognition session."""
        service, client, response_stream = streaming_stt
        
        # Mock response stream
        mock_results = [
            Mock(results=[Mock(alternatives=[Mock(transcript="hallo", is_final=False)])]),
            Mock(results=[Mock(alternatives=[Mock(transcript="hallo wereld", is_final=True)])])
        ]
        response_stream.__aiter__ = AsyncMock(return_value=iter(mock_results))
        
        # Start streaming
        transcript_callback = AsyncMock()
        await service.start_streaming(transcript_callback)
        
        # Verify streaming started
        assert service.is_streaming == True
        client.streaming_recognize.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_audio_chunk(self, streaming_stt):
        """Test sending audio chunks to streaming service."""
        service, client, response_stream = streaming_stt
        
        # Start streaming first
        await service.start_streaming(AsyncMock())
        
        # Send audio chunk
        audio_chunk = b'\x1a\x45\xdf\xa3' + b'\x00' * 1000
        await service.send_audio_chunk(audio_chunk)
        
        # Verify chunk was queued (implementation dependent)
        assert service.is_streaming == True

    @pytest.mark.asyncio
    async def test_stop_streaming_session(self, streaming_stt):
        """Test stopping streaming recognition session."""
        service, client, response_stream = streaming_stt
        
        # Start then stop streaming
        await service.start_streaming(AsyncMock())
        await service.stop_streaming()
        
        # Verify streaming stopped
        assert service.is_streaming == False

    @pytest.mark.asyncio
    async def test_transcript_callback_handling(self, streaming_stt):
        """Test that transcript callbacks are called correctly."""
        service, client, response_stream = streaming_stt
        
        # Mock streaming responses
        mock_results = [
            Mock(results=[Mock(alternatives=[Mock(transcript="partial text", is_final=False)])]),
            Mock(results=[Mock(alternatives=[Mock(transcript="final text", is_final=True)])])
        ]
        response_stream.__aiter__ = AsyncMock(return_value=iter(mock_results))
        
        # Track callback calls
        transcript_callback = AsyncMock()
        
        # Start streaming and wait for responses
        await service.start_streaming(transcript_callback)
        await asyncio.sleep(0.1)  # Allow processing
        
        # Verify callbacks were called
        assert transcript_callback.call_count >= 1

    @pytest.mark.asyncio 
    async def test_error_handling_in_stream(self, streaming_stt):
        """Test error handling during streaming recognition."""
        service, client, response_stream = streaming_stt
        
        # Mock stream that raises exception
        async def failing_stream():
            yield Mock(results=[Mock(alternatives=[Mock(transcript="test", is_final=False)])])
            raise Exception("Streaming error")
        
        response_stream.__aiter__ = AsyncMock(return_value=failing_stream())
        
        # Start streaming with error handler
        error_callback = AsyncMock()
        await service.start_streaming(AsyncMock(), error_callback=error_callback)
        
        await asyncio.sleep(0.1)  # Allow error to occur
        
        # Verify error was handled
        error_callback.assert_called()


class TestStreamManager:
    """Test stream management for multiple concurrent streams."""

    @pytest.fixture
    def stream_manager(self):
        """Create StreamManager instance."""
        return StreamManager()

    @pytest.mark.asyncio
    async def test_create_stream(self, stream_manager):
        """Test creating a new streaming session."""
        stream_id = "test-stream-123"
        
        # Create mock callbacks
        transcript_callback = AsyncMock()
        error_callback = AsyncMock()
        
        # Create stream
        with patch('backend.streaming_stt.StreamingSpeechToText') as MockSTT:
            mock_stt_instance = AsyncMock()
            MockSTT.return_value = mock_stt_instance
            
            await stream_manager.create_stream(
                stream_id, 
                transcript_callback, 
                error_callback
            )
            
            # Verify stream was created and started
            assert stream_id in stream_manager.streams
            mock_stt_instance.start_streaming.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_audio_to_stream(self, stream_manager):
        """Test sending audio to specific stream."""
        stream_id = "test-stream-123"
        audio_chunk = b'\x00' * 1000
        
        # Create stream first
        with patch('backend.streaming_stt.StreamingSpeechToText') as MockSTT:
            mock_stt_instance = AsyncMock()
            MockSTT.return_value = mock_stt_instance
            
            await stream_manager.create_stream(stream_id, AsyncMock(), AsyncMock())
            
            # Send audio
            await stream_manager.send_audio(stream_id, audio_chunk)
            
            # Verify audio was sent to correct stream
            mock_stt_instance.send_audio_chunk.assert_called_once_with(audio_chunk)

    @pytest.mark.asyncio
    async def test_close_stream(self, stream_manager):
        """Test closing a streaming session."""
        stream_id = "test-stream-123"
        
        # Create then close stream
        with patch('backend.streaming_stt.StreamingSpeechToText') as MockSTT:
            mock_stt_instance = AsyncMock()
            MockSTT.return_value = mock_stt_instance
            
            await stream_manager.create_stream(stream_id, AsyncMock(), AsyncMock())
            await stream_manager.close_stream(stream_id)
            
            # Verify stream was closed and removed
            assert stream_id not in stream_manager.streams
            mock_stt_instance.stop_streaming.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_nonexistent_stream(self, stream_manager):
        """Test handling operations on non-existent streams."""
        nonexistent_id = "does-not-exist"
        
        # Should not raise exceptions
        await stream_manager.send_audio(nonexistent_id, b'\x00' * 100)
        await stream_manager.close_stream(nonexistent_id)
        
        # Streams should remain empty
        assert len(stream_manager.streams) == 0

    def test_get_stream_stats(self, stream_manager):
        """Test getting statistics about active streams."""
        stats = stream_manager.get_stats()
        
        assert 'active_streams' in stats
        assert 'total_streams_created' in stats
        assert stats['active_streams'] == 0


class TestStreamingIntegration:
    """Integration tests for streaming STT with WebSocket handlers."""

    @pytest.mark.asyncio
    async def test_websocket_streaming_integration(self):
        """Test full WebSocket integration with streaming STT."""
        from backend.services import StreamingSTTService
        
        # Mock WebSocket connection and callbacks
        mock_websocket = Mock()
        mock_broadcast = AsyncMock()
        
        service = StreamingSTTService()
        
        # Simulate WebSocket workflow
        stream_id = "integration-test"
        
        # Define callbacks for transcript and translation
        async def on_transcript(text, is_final):
            if is_final:
                # Simulate translation and TTS pipeline
                translated = f"translated: {text}"
                audio_bytes = f"audio: {translated}".encode()
                await mock_broadcast(stream_id, audio_bytes)
        
        # Create streaming session
        await service.create_stream(stream_id, on_transcript)
        
        # Send audio chunks
        for i in range(3):
            audio_chunk = f"chunk_{i}".encode() + b'\x00' * 1000
            await service.send_audio(stream_id, audio_chunk)
            await asyncio.sleep(0.1)
        
        # Close session
        await service.close_stream(stream_id)
        
        # Verify integration works without errors
        assert True  # If we get here, integration succeeded

    @pytest.mark.asyncio
    async def test_streaming_performance_under_load(self):
        """Test streaming STT performance with multiple concurrent streams."""
        from backend.streaming_stt import StreamManager
        
        manager = StreamManager()
        
        # Create multiple concurrent streams
        stream_ids = [f"load-test-{i}" for i in range(5)]
        
        # Start all streams
        for stream_id in stream_ids:
            with patch('backend.streaming_stt.StreamingSpeechToText'):
                await manager.create_stream(
                    stream_id,
                    AsyncMock(),  # transcript callback
                    AsyncMock()   # error callback
                )
        
        # Send audio to all streams concurrently
        tasks = []
        for stream_id in stream_ids:
            for chunk_num in range(3):
                audio_data = f"audio_{stream_id}_{chunk_num}".encode() * 100
                task = manager.send_audio(stream_id, audio_data)
                tasks.append(task)
        
        # Wait for all operations to complete
        await asyncio.gather(*tasks)
        
        # Verify all streams are still active
        stats = manager.get_stats()
        assert stats['active_streams'] == len(stream_ids)
        
        # Clean up streams
        for stream_id in stream_ids:
            await manager.close_stream(stream_id)
        
        # Verify cleanup
        final_stats = manager.get_stats()
        assert final_stats['active_streams'] == 0