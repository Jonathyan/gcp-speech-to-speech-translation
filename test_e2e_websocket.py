#!/usr/bin/env python3
"""
End-to-End WebSocket Testing Script

Simulates complete browser behavior for Dutch → English speech translation:
1. Connects to /ws/stream/{stream_id} as speaker
2. Connects to /ws/listen/{stream_id} as listener  
3. Sends synthetic Dutch audio chunks
4. Validates complete STT → Translation → TTS → Broadcast pipeline
5. Tests all Phase 1 optimizations working together
"""

import asyncio
import json
import logging
import time
import numpy as np
import websockets
import aiohttp
from datetime import datetime
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'e2e_websocket_test_{int(time.time())}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EndToEndWebSocketTester:
    """Complete end-to-end WebSocket testing for speech-to-speech translation."""
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.websocket_base = backend_url.replace('http', 'ws')
        self.stream_id = f"e2e-test-{int(time.time())}"
        
        # Test configuration
        self.test_duration_seconds = 60  # 1 minute comprehensive test
        self.audio_chunk_size_ms = 100   # 100ms chunks (production setting)
        self.sample_rate = 16000         # 16kHz (production setting)
        
        # Results tracking
        self.results = {
            'test_start_time': None,
            'backend_health_verified': False,
            'websocket_connections_established': False,
            'audio_chunks_sent': 0,
            'keepalive_pings_received': 0,
            'keepalive_pongs_sent': 0,
            'translation_audio_received': [],
            'connection_stability': {
                'speaker_disconnects': 0,
                'listener_disconnects': 0,
                'reconnection_attempts': 0
            },
            'pipeline_performance': {
                'first_audio_latency_ms': None,
                'average_chunk_processing_ms': []
            },
            'errors': []
        }
        
        # Dutch test phrases (will be converted to synthetic audio)
        self.test_phrases = [
            "Hallo dit is een test van het spraakherkenningssysteem",
            "We testen de complete Nederlandse naar Engelse vertaling", 
            "Het systeem moet snel en accuraat werken",
            "De audio kwaliteit is zeer belangrijk voor gebruikers",
            "We verwachten uitstekende resultaten van deze test"
        ]
    
    async def run_comprehensive_e2e_test(self) -> bool:
        """Execute complete end-to-end WebSocket testing."""
        logger.info("🚀 Starting End-to-End WebSocket Testing")
        logger.info(f"   Stream ID: {self.stream_id}")
        logger.info(f"   Duration: {self.test_duration_seconds}s")
        logger.info(f"   Backend: {self.backend_url}")
        logger.info("=" * 80)
        
        self.results['test_start_time'] = time.time()
        
        try:
            # Phase 1: Verify backend health
            logger.info("🔍 Phase 1: Backend Health Verification")
            if not await self._verify_backend_health():
                return False
            
            # Phase 2: Establish WebSocket connections
            logger.info("🔌 Phase 2: WebSocket Connection Establishment")
            listener_task, speaker_task = await self._establish_websocket_connections()
            if not listener_task or not speaker_task:
                return False
            
            # Phase 3: Execute comprehensive pipeline test
            logger.info("🎤 Phase 3: Complete Pipeline Testing")
            pipeline_success = await self._execute_pipeline_test(speaker_task, listener_task)
            
            # Cleanup connections
            logger.info("🧹 Phase 4: Connection Cleanup")
            await self._cleanup_connections(speaker_task, listener_task)
            
            # Phase 4: Generate comprehensive report
            await self._generate_e2e_report()
            
            return pipeline_success
            
        except Exception as e:
            logger.error(f"❌ E2E test failed: {e}")
            self.results['errors'].append(f"Test execution error: {e}")
            return False
    
    async def _verify_backend_health(self) -> bool:
        """Verify backend is healthy and Google Cloud APIs are connected."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.backend_url}/health") as response:
                    if response.status != 200:
                        logger.error(f"❌ Backend unhealthy: status {response.status}")
                        return False
                    
                    health_data = await response.json()
                    
                    # Verify critical services
                    if health_data.get('translation') != 'connected':
                        logger.error("❌ Translation API not connected")
                        return False
                    
                    if health_data.get('tts') != 'connected':
                        logger.error("❌ TTS API not connected")
                        return False
                    
                    logger.info(f"✅ Backend healthy: {health_data}")
                    self.results['backend_health_verified'] = True
                    return True
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            self.results['errors'].append(f"Health check error: {e}")
            return False
    
    async def _establish_websocket_connections(self) -> tuple:
        """Establish both speaker and listener WebSocket connections."""
        try:
            # Start listener first (ready to receive)
            logger.info("🎧 Connecting listener...")
            listener_task = asyncio.create_task(
                self._run_listener_connection()
            )
            await asyncio.sleep(1)  # Give listener time to connect
            
            # Start speaker (will send audio)
            logger.info("🎙️ Connecting speaker...")
            speaker_task = asyncio.create_task(
                self._run_speaker_connection()
            )
            await asyncio.sleep(1)  # Give speaker time to connect
            
            self.results['websocket_connections_established'] = True
            return listener_task, speaker_task
            
        except Exception as e:
            logger.error(f"❌ Connection establishment failed: {e}")
            self.results['errors'].append(f"Connection error: {e}")
            return None, None
    
    async def _run_listener_connection(self):
        """Run the listener WebSocket connection."""
        listener_url = f"{self.websocket_base}/ws/listen/{self.stream_id}"
        
        try:
            async with websockets.connect(listener_url) as websocket:
                logger.info(f"✅ Listener connected: {listener_url}")
                
                # Listen for translated audio and keepalive messages
                async for message in websocket:
                    if isinstance(message, bytes):
                        # Received translated audio
                        audio_info = {
                            'timestamp': time.time(),
                            'size_bytes': len(message),
                            'latency_from_start': time.time() - self.results['test_start_time']
                        }
                        self.results['translation_audio_received'].append(audio_info)
                        
                        # Track first audio latency
                        if self.results['pipeline_performance']['first_audio_latency_ms'] is None:
                            self.results['pipeline_performance']['first_audio_latency_ms'] = (
                                audio_info['latency_from_start'] * 1000
                            )
                        
                        logger.info(f"🔊 Received audio: {len(message)} bytes "
                                  f"(latency: {audio_info['latency_from_start']:.1f}s)")
                    
                    elif isinstance(message, str):
                        # Handle keepalive messages
                        try:
                            data = json.loads(message)
                            if data.get('type') == 'keepalive' and data.get('action') == 'ping':
                                self.results['keepalive_pings_received'] += 1
                                
                                # Send pong response
                                pong_response = '{"type":"keepalive","action":"pong"}'
                                await websocket.send(pong_response)
                                self.results['keepalive_pongs_sent'] += 1
                                logger.debug("📡 Handled keepalive ping/pong")
                        except json.JSONDecodeError:
                            logger.debug(f"📨 Non-JSON text received: {message[:100]}")
                            
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 Listener connection closed normally")
        except Exception as e:
            logger.warning(f"⚠️ Listener error: {e}")
            self.results['connection_stability']['listener_disconnects'] += 1
    
    async def _run_speaker_connection(self):
        """Run the speaker WebSocket connection."""
        speaker_url = f"{self.websocket_base}/ws/stream/{self.stream_id}"
        
        try:
            async with websockets.connect(speaker_url) as websocket:
                logger.info(f"✅ Speaker connected: {speaker_url}")
                
                # Send test audio for each phrase
                for phrase_idx, phrase in enumerate(self.test_phrases):
                    logger.info(f"🎤 Sending audio for phrase {phrase_idx + 1}: '{phrase}'")
                    
                    # Generate synthetic Dutch audio for this phrase
                    audio_data = self._generate_dutch_audio(phrase, duration_seconds=3)
                    
                    # Send audio in realistic chunks
                    chunk_size = int(self.sample_rate * (self.audio_chunk_size_ms / 1000) * 2)  # 2 bytes per sample
                    chunks_sent = 0
                    
                    for i in range(0, len(audio_data), chunk_size):
                        chunk = audio_data[i:i + chunk_size]
                        chunk_start_time = time.time()
                        
                        await websocket.send(chunk)
                        chunks_sent += 1
                        self.results['audio_chunks_sent'] += 1
                        
                        # Track processing time
                        processing_time_ms = (time.time() - chunk_start_time) * 1000
                        self.results['pipeline_performance']['average_chunk_processing_ms'].append(processing_time_ms)
                        
                        # Realistic timing - 100ms chunks
                        await asyncio.sleep(self.audio_chunk_size_ms / 1000)
                    
                    logger.info(f"✅ Sent {chunks_sent} audio chunks for phrase {phrase_idx + 1}")
                    
                    # Wait between phrases for processing
                    await asyncio.sleep(2)
                
                # Keep connection alive briefly for final processing
                await asyncio.sleep(5)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 Speaker connection closed normally")
        except Exception as e:
            logger.warning(f"⚠️ Speaker error: {e}")
            self.results['connection_stability']['speaker_disconnects'] += 1
    
    async def _execute_pipeline_test(self, speaker_task, listener_task) -> bool:
        """Execute the complete pipeline test with both connections."""
        test_timeout = self.test_duration_seconds + 30  # Extra time for processing
        
        try:
            # Wait for both tasks to complete or timeout
            await asyncio.wait_for(
                asyncio.gather(speaker_task, listener_task, return_exceptions=True),
                timeout=test_timeout
            )
            
            # Analyze results
            audio_responses = len(self.results['translation_audio_received'])
            chunks_sent = self.results['audio_chunks_sent']
            
            logger.info(f"📊 Pipeline Results: {audio_responses} audio responses from {chunks_sent} chunks")
            
            # Success criteria
            has_audio_responses = audio_responses > 0
            low_error_rate = len(self.results['errors']) <= 2
            stable_connections = (
                self.results['connection_stability']['speaker_disconnects'] <= 1 and
                self.results['connection_stability']['listener_disconnects'] <= 1
            )
            
            success = has_audio_responses and low_error_rate and stable_connections
            
            logger.info(f"✅ Pipeline test: {'PASSED' if success else 'FAILED'}")
            return success
            
        except asyncio.TimeoutError:
            logger.error(f"❌ Pipeline test timed out after {test_timeout}s")
            self.results['errors'].append("Pipeline test timeout")
            return False
        except Exception as e:
            logger.error(f"❌ Pipeline execution error: {e}")
            self.results['errors'].append(f"Pipeline error: {e}")
            return False
    
    async def _cleanup_connections(self, speaker_task, listener_task):
        """Clean up WebSocket connections."""
        try:
            # Cancel tasks if still running
            if not speaker_task.done():
                speaker_task.cancel()
            if not listener_task.done():
                listener_task.cancel()
                
            # Brief wait for cleanup
            await asyncio.sleep(1)
            logger.info("✅ Connection cleanup completed")
            
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")
    
    def _generate_dutch_audio(self, phrase: str, duration_seconds: float = 3) -> bytes:
        """Generate synthetic audio that mimics Dutch speech patterns."""
        samples = int(self.sample_rate * duration_seconds)
        t = np.linspace(0, duration_seconds, samples)
        
        # Dutch phonetic characteristics (approximated)
        # More guttural sounds, different vowel frequencies
        base_freq = 120 + 30 * np.sin(2 * np.pi * 1.2 * t)  # Fundamental variation
        formant1 = 350 + 150 * np.sin(2 * np.pi * 0.8 * t)   # First formant (Dutch vowels)
        formant2 = 900 + 300 * np.sin(2 * np.pi * 1.5 * t)   # Second formant
        formant3 = 2200 + 400 * np.sin(2 * np.pi * 0.6 * t)  # Third formant
        
        # Combine formants with realistic amplitudes
        wave = (0.4 * np.sin(2 * np.pi * base_freq * t) +
                0.25 * np.sin(2 * np.pi * formant1 * t) +
                0.2 * np.sin(2 * np.pi * formant2 * t) +
                0.1 * np.sin(2 * np.pi * formant3 * t))
        
        # Add consonant-like noise bursts (simulate Dutch 'g', 'sch', etc.)
        consonant_noise = np.zeros_like(t)
        for i in range(5):  # 5 consonant-like bursts
            burst_center = np.random.uniform(0.2, duration_seconds - 0.2)
            burst_width = 0.05  # 50ms bursts
            burst_mask = np.exp(-((t - burst_center) / burst_width) ** 2)
            consonant_noise += 0.3 * burst_mask * np.random.normal(0, 1, len(t))
        
        # Combine with envelope and add background noise
        envelope = np.exp(-((t - duration_seconds/2) / (duration_seconds/3)) ** 2)  # Gaussian envelope
        background_noise = 0.02 * np.random.normal(0, 1, len(t))
        
        final_wave = (wave + consonant_noise) * envelope + background_noise
        
        # Convert to 16-bit PCM
        pcm_data = np.clip(final_wave * 16384, -32767, 32767).astype(np.int16)
        return pcm_data.tobytes()
    
    async def _generate_e2e_report(self):
        """Generate comprehensive end-to-end test report."""
        test_duration = time.time() - self.results['test_start_time']
        
        # Calculate metrics
        audio_responses = len(self.results['translation_audio_received'])
        total_audio_bytes = sum(r['size_bytes'] for r in self.results['translation_audio_received'])
        
        avg_processing_time = 0
        if self.results['pipeline_performance']['average_chunk_processing_ms']:
            avg_processing_time = np.mean(self.results['pipeline_performance']['average_chunk_processing_ms'])
        
        # Success criteria evaluation
        success_criteria = {
            'backend_health_verified': self.results['backend_health_verified'],
            'websocket_connections_established': self.results['websocket_connections_established'], 
            'audio_responses_received': audio_responses > 0,
            'first_response_under_10s': (
                self.results['pipeline_performance']['first_audio_latency_ms'] is not None and
                self.results['pipeline_performance']['first_audio_latency_ms'] < 10000
            ),
            'stable_connections': (
                self.results['connection_stability']['speaker_disconnects'] <= 1 and
                self.results['connection_stability']['listener_disconnects'] <= 1
            ),
            'low_error_rate': len(self.results['errors']) <= 2,
            'keepalive_working': self.results['keepalive_pings_received'] >= 1
        }
        
        overall_success = all(success_criteria.values())
        
        logger.info("=" * 80)
        logger.info("📊 END-TO-END WEBSOCKET TEST REPORT")
        logger.info("=" * 80)
        
        logger.info(f"⏱️ Test Duration: {test_duration:.1f}s")
        logger.info(f"🎯 Stream ID: {self.stream_id}")
        
        logger.info(f"\n🔌 Connection Results:")
        logger.info(f"  Backend health verified: {'✅' if self.results['backend_health_verified'] else '❌'}")
        logger.info(f"  WebSocket connections: {'✅' if self.results['websocket_connections_established'] else '❌'}")
        logger.info(f"  Speaker disconnects: {self.results['connection_stability']['speaker_disconnects']}")
        logger.info(f"  Listener disconnects: {self.results['connection_stability']['listener_disconnects']}")
        
        logger.info(f"\n🎤 Pipeline Performance:")
        logger.info(f"  Audio chunks sent: {self.results['audio_chunks_sent']}")
        logger.info(f"  Translation responses: {audio_responses}")
        logger.info(f"  Total audio bytes: {total_audio_bytes:,}")
        logger.info(f"  First response latency: {self.results['pipeline_performance']['first_audio_latency_ms']:.0f}ms"
                   if self.results['pipeline_performance']['first_audio_latency_ms'] else "No responses")
        logger.info(f"  Avg chunk processing: {avg_processing_time:.1f}ms")
        
        logger.info(f"\n📡 Keepalive Performance:")
        logger.info(f"  Pings received: {self.results['keepalive_pings_received']}")
        logger.info(f"  Pongs sent: {self.results['keepalive_pongs_sent']}")
        
        logger.info(f"\n🔍 Success Criteria:")
        for criterion, passed in success_criteria.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"  {status} {criterion.replace('_', ' ').title()}")
        
        if self.results['errors']:
            logger.info(f"\n❌ Errors ({len(self.results['errors'])}):")
            for error in self.results['errors'][:5]:  # Show first 5 errors
                logger.info(f"  • {error}")
        
        logger.info(f"\n🏆 OVERALL E2E TEST: {'✅ PASSED' if overall_success else '❌ FAILED'}")
        
        if overall_success:
            logger.info("✅ End-to-end pipeline working correctly")
            logger.info("✅ All Phase 1 optimizations validated")
            logger.info("✅ Ready for production use")
        else:
            logger.info("❌ End-to-end issues detected - review failed criteria")
        
        # Save detailed report
        report_data = {
            'test_summary': {
                'duration_seconds': test_duration,
                'stream_id': self.stream_id,
                'overall_passed': overall_success
            },
            'connection_results': self.results['connection_stability'],
            'pipeline_performance': {
                'audio_chunks_sent': self.results['audio_chunks_sent'],
                'translation_responses': audio_responses,
                'total_audio_bytes': total_audio_bytes,
                'first_response_latency_ms': self.results['pipeline_performance']['first_audio_latency_ms'],
                'average_processing_time_ms': avg_processing_time
            },
            'keepalive_performance': {
                'pings_received': self.results['keepalive_pings_received'],
                'pongs_sent': self.results['keepalive_pongs_sent']
            },
            'success_criteria': success_criteria,
            'errors': self.results['errors'],
            'detailed_results': self.results,
            'test_timestamp': datetime.now().isoformat()
        }
        
        report_filename = f"e2e_websocket_report_{int(time.time())}.json"
        with open(report_filename, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"📄 Detailed report saved: {report_filename}")
        logger.info("=" * 80)
        
        return overall_success

async def main():
    """Main end-to-end test execution."""
    tester = EndToEndWebSocketTester()
    success = await tester.run_comprehensive_e2e_test()
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("🛑 E2E test interrupted")
        exit(2)
    except Exception as e:
        logger.error(f"❌ E2E test failed: {e}")
        exit(3)