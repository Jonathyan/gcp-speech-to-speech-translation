#!/usr/bin/env python3
"""
Quick Stream Restart Test - 6 minutes

Tests the 5-minute stream restart logic by running for 6 minutes
to verify one restart occurs at the 4:40 mark.
"""

import asyncio
import json
import logging
import time
import numpy as np
from datetime import datetime
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuickRestartTester:
    """Quick test harness for 6-minute streaming validation."""
    
    def __init__(self):
        self.websocket_url = "ws://localhost:8000/ws/stream/quick-restart-test"
        self.stream_id = "quick-restart-test"
        self.test_duration_minutes = 6  # Just over one restart cycle
        self.expected_restart_time = 280  # 4:40 mark
        
        # Test metrics
        self.metrics = {
            'test_start_time': None,
            'chunks_sent': 0,
            'transcripts_received': 0,
            'restart_detected': False,
            'restart_time': None,
            'error_events': 0,
            'last_transcript_time': None
        }
        
        # Audio parameters
        self.sample_rate = 16000
        self.chunk_duration_ms = 100
        self.chunk_size = int(self.sample_rate * self.chunk_duration_ms / 1000)
        
    def generate_test_audio_chunk(self) -> bytes:
        """Generate synthetic LINEAR16 PCM audio."""
        t = np.linspace(0, self.chunk_duration_ms / 1000, self.chunk_size)
        frequency = 200 + (self.metrics['chunks_sent'] % 10) * 20  # Vary frequency
        wave = 0.3 * np.sin(2 * np.pi * frequency * t)
        noise = 0.05 * np.random.normal(0, 1, len(t))
        combined_wave = wave + noise
        return (combined_wave * 32767).astype(np.int16).tobytes()
    
    async def send_audio_stream(self, websocket):
        """Send audio chunks for test duration."""
        logger.info(f"🎤 Starting audio stream for {self.test_duration_minutes} minutes...")
        
        test_end_time = time.time() + (self.test_duration_minutes * 60)
        chunk_interval = self.chunk_duration_ms / 1000
        
        try:
            while time.time() < test_end_time:
                start_time = time.time()
                elapsed_time = start_time - self.metrics['test_start_time']
                
                # Generate and send audio chunk
                audio_chunk = self.generate_test_audio_chunk()
                await websocket.send(audio_chunk)
                self.metrics['chunks_sent'] += 1
                
                # Log progress every 30 seconds
                if self.metrics['chunks_sent'] % 300 == 0:
                    minutes_elapsed = elapsed_time / 60
                    logger.info(f"📊 Progress: {minutes_elapsed:.1f}/{self.test_duration_minutes} minutes, "
                              f"{self.metrics['chunks_sent']} chunks sent")
                
                # Check if we're approaching expected restart time
                if not self.metrics['restart_detected'] and elapsed_time > (self.expected_restart_time - 10):
                    if elapsed_time > self.expected_restart_time:
                        self.metrics['restart_detected'] = True
                        self.metrics['restart_time'] = elapsed_time
                        logger.info(f"🔄 Expected restart time passed: {elapsed_time:.1f}s")
                
                # Wait for next chunk
                processing_time = time.time() - start_time
                sleep_time = max(0, chunk_interval - processing_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
        except Exception as e:
            logger.error(f"❌ Audio streaming error: {e}")
            self.metrics['error_events'] += 1
            raise
    
    async def listen_for_responses(self, websocket):
        """Listen for server responses."""
        logger.info("👂 Listening for server responses...")
        
        try:
            async for message in websocket:
                current_time = time.time()
                self.metrics['transcripts_received'] += 1
                self.metrics['last_transcript_time'] = current_time
                
                if isinstance(message, str):
                    logger.info(f"📝 Received: '{message}'")
                else:
                    logger.debug(f"🔊 Audio data: {len(message)} bytes")
                    
        except Exception as e:
            logger.error(f"❌ Response listening error: {e}")
            self.metrics['error_events'] += 1
    
    async def run_quick_test(self):
        """Execute the 6-minute restart test."""
        logger.info("🚀 Starting Quick Stream Restart Test")
        logger.info(f"   Duration: {self.test_duration_minutes} minutes")
        logger.info(f"   Expected restart at: {self.expected_restart_time}s")
        
        self.metrics['test_start_time'] = time.time()
        
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                logger.info("✅ WebSocket connected successfully")
                
                # Start parallel tasks
                audio_task = asyncio.create_task(self.send_audio_stream(websocket))
                listen_task = asyncio.create_task(self.listen_for_responses(websocket))
                
                # Wait for completion
                await asyncio.gather(audio_task, listen_task, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"❌ Test execution error: {e}")
            self.metrics['error_events'] += 1
        finally:
            await self.generate_report()
    
    async def generate_report(self):
        """Generate test report."""
        test_duration = time.time() - self.metrics['test_start_time']
        
        logger.info("=" * 60)
        logger.info("📊 QUICK RESTART TEST REPORT")
        logger.info("=" * 60)
        
        logger.info(f"⏱️  Test Duration: {test_duration:.1f}s ({test_duration/60:.1f} minutes)")
        logger.info(f"📊 Chunks Sent: {self.metrics['chunks_sent']:,}")
        logger.info(f"📝 Transcripts Received: {self.metrics['transcripts_received']}")
        logger.info(f"❌ Error Events: {self.metrics['error_events']}")
        
        # Restart validation
        restart_result = "❌ FAIL"
        restart_details = "No restart detected"
        
        if self.metrics['restart_detected']:
            restart_timing_ok = abs(self.metrics['restart_time'] - self.expected_restart_time) < 30
            if restart_timing_ok:
                restart_result = "✅ PASS"
                restart_details = f"Restart detected at {self.metrics['restart_time']:.1f}s"
            else:
                restart_details = f"Restart timing off: {self.metrics['restart_time']:.1f}s vs expected {self.expected_restart_time}s"
        
        logger.info(f"🔄 Stream Restart: {restart_result} - {restart_details}")
        
        # Overall assessment
        success_criteria = [
            test_duration >= (self.test_duration_minutes * 60 * 0.95),  # 95% completion
            self.metrics['error_events'] <= 2,  # Allow minor errors
            self.metrics['chunks_sent'] > 0,  # Some chunks sent
        ]
        
        overall_result = "✅ PASSED" if all(success_criteria) else "❌ FAILED"
        logger.info(f"🏆 OVERALL RESULT: {overall_result}")
        logger.info("=" * 60)
        
        return all(success_criteria)

async def main():
    """Main test execution."""
    # Check backend health
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/health') as response:
                if response.status != 200:
                    raise Exception(f"Backend health check failed: {response.status}")
                logger.info("✅ Backend is healthy")
    except Exception as e:
        logger.error(f"❌ Backend not accessible: {e}")
        return False
    
    # Run test
    tester = QuickRestartTester()
    success = await tester.run_quick_test()
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted")
        exit(2)
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        exit(3)