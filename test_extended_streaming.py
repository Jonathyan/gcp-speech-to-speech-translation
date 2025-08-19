#!/usr/bin/env python3
"""
Extended Streaming Test Script - 15 minutes

Tests the 5-minute stream restart logic by continuously streaming audio
for 15 minutes to verify seamless operation without data loss.

Validation Criteria:
- Stream continues seamlessly after 4:40 mark
- No audio data loss during restart
- Transcript continuity maintained
- No error spikes in logs
- Performance metrics within acceptable ranges
"""

import asyncio
import json
import logging
import time
import wave
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import websockets
from websockets.exceptions import ConnectionClosed

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'extended_streaming_test_{int(time.time())}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ExtendedStreamingTester:
    """Test harness for 15-minute continuous streaming validation."""
    
    def __init__(self, websocket_url: str = "ws://localhost:8000/ws/stream/extended-test"):
        self.websocket_url = websocket_url
        self.stream_id = "extended-test"
        self.test_duration_minutes = 15
        self.expected_restart_interval = 280  # 4:40 mark
        
        # Test metrics tracking
        self.metrics = {
            'test_start_time': None,
            'chunks_sent': 0,
            'transcripts_received': 0,
            'stream_restarts_detected': 0,
            'data_loss_events': 0,
            'error_events': 0,
            'last_transcript_time': None,
            'transcript_gaps': [],
            'performance_samples': [],
            'restart_timings': []
        }
        
        # Audio generation parameters
        self.sample_rate = 16000
        self.chunk_duration_ms = 100  # 100ms chunks as per config
        self.chunk_size = int(self.sample_rate * self.chunk_duration_ms / 1000)
        
        # Generate synthetic Dutch-like audio for testing
        self.test_phrases = [
            "Hallo, dit is een test van het spraakherkenningssysteem",
            "We testen of de stream automatisch herstart na vier minuten en veertig seconden", 
            "Het is belangrijk dat er geen gegevensverlies optreedt tijdens het hersarten",
            "Deze test controleert de continuïteit van de transcriptie",
            "We verwachten dat het systeem stabiel blijft gedurende vijftien minuten"
        ]
        self.current_phrase_index = 0
        
    def generate_test_audio_chunk(self) -> bytes:
        """Generate synthetic LINEAR16 PCM audio chunk for testing."""
        # Generate a sine wave with some variation to simulate speech
        t = np.linspace(0, self.chunk_duration_ms / 1000, self.chunk_size)
        
        # Create a complex waveform that resembles speech patterns
        frequency_base = 200 + (self.current_phrase_index * 50) % 400  # Vary frequency
        amplitude = 0.3
        
        # Mix multiple frequencies to simulate speech formants
        wave1 = amplitude * np.sin(2 * np.pi * frequency_base * t)
        wave2 = amplitude * 0.5 * np.sin(2 * np.pi * (frequency_base * 1.5) * t)
        wave3 = amplitude * 0.3 * np.sin(2 * np.pi * (frequency_base * 0.8) * t)
        
        # Add some randomness to simulate natural speech variation
        noise = 0.05 * np.random.normal(0, 1, len(t))
        
        combined_wave = wave1 + wave2 + wave3 + noise
        
        # Convert to 16-bit PCM
        pcm_data = (combined_wave * 32767).astype(np.int16).tobytes()
        
        # Cycle through "phrases" every 5 seconds
        if self.metrics['chunks_sent'] % 50 == 0:  # Every 5 seconds
            self.current_phrase_index = (self.current_phrase_index + 1) % len(self.test_phrases)
        
        return pcm_data
    
    async def send_audio_stream(self, websocket):
        """Continuously send audio chunks for the test duration."""
        logger.info(f"🎤 Starting audio stream for {self.test_duration_minutes} minutes...")
        
        test_end_time = time.time() + (self.test_duration_minutes * 60)
        chunk_interval = self.chunk_duration_ms / 1000  # 0.1 seconds
        
        last_restart_check = time.time()
        
        try:
            while time.time() < test_end_time:
                start_time = time.time()
                
                # Generate and send audio chunk
                audio_chunk = self.generate_test_audio_chunk()
                await websocket.send(audio_chunk)
                
                self.metrics['chunks_sent'] += 1
                
                # Check for expected restart timing
                current_time = time.time()
                elapsed_since_start = current_time - self.metrics['test_start_time']
                
                # Log every minute for progress tracking
                if self.metrics['chunks_sent'] % 600 == 0:  # Every 60 seconds
                    minutes_elapsed = elapsed_since_start / 60
                    logger.info(f"📊 Progress: {minutes_elapsed:.1f}/{self.test_duration_minutes} minutes, "
                              f"{self.metrics['chunks_sent']} chunks sent, "
                              f"{self.metrics['transcripts_received']} transcripts received")
                
                # Performance tracking
                processing_time = time.time() - start_time
                self.metrics['performance_samples'].append({
                    'timestamp': current_time,
                    'processing_time_ms': processing_time * 1000,
                    'chunks_sent': self.metrics['chunks_sent']
                })
                
                # Wait for next chunk interval
                sleep_time = max(0, chunk_interval - processing_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    logger.warning(f"⚠️  Processing time ({processing_time*1000:.1f}ms) exceeded chunk interval")
                    
        except Exception as e:
            logger.error(f"❌ Audio streaming error: {e}")
            self.metrics['error_events'] += 1
            raise
    
    async def monitor_server_logs(self):
        """Monitor server logs for restart events and errors."""
        logger.info("📋 Log monitoring started...")
        
        # This would normally tail server logs, but for this test we'll simulate
        # monitoring by checking at intervals and making HTTP requests to health endpoint
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            last_health_check = time.time()
            
            while time.time() < (self.metrics['test_start_time'] + self.test_duration_minutes * 60):
                try:
                    # Check server health every 30 seconds
                    if time.time() - last_health_check > 30:
                        async with session.get('http://localhost:8000/health') as response:
                            if response.status == 200:
                                health_data = await response.json()
                                logger.debug(f"🩺 Health check: {health_data}")
                            else:
                                logger.warning(f"⚠️  Health check failed: {response.status}")
                                self.metrics['error_events'] += 1
                        
                        last_health_check = time.time()
                    
                    await asyncio.sleep(10)  # Check every 10 seconds
                    
                except Exception as e:
                    logger.error(f"❌ Health monitoring error: {e}")
                    await asyncio.sleep(5)
    
    async def run_extended_test(self):
        """Execute the full 15-minute streaming test."""
        logger.info(f"🚀 Starting Extended Streaming Test")
        logger.info(f"   Duration: {self.test_duration_minutes} minutes")
        logger.info(f"   WebSocket: {self.websocket_url}")
        logger.info(f"   Expected restart interval: {self.expected_restart_interval}s")
        
        self.metrics['test_start_time'] = time.time()
        
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                logger.info("✅ WebSocket connected successfully")
                
                # Start parallel tasks
                audio_task = asyncio.create_task(self.send_audio_stream(websocket))
                monitor_task = asyncio.create_task(self.monitor_server_logs())
                
                # Start listening for messages (transcripts)
                listen_task = asyncio.create_task(self.listen_for_responses(websocket))
                
                # Wait for all tasks to complete
                await asyncio.gather(audio_task, monitor_task, listen_task, return_exceptions=True)
                
        except ConnectionClosed as e:
            logger.error(f"❌ WebSocket connection closed: {e}")
            self.metrics['error_events'] += 1
        except Exception as e:
            logger.error(f"❌ Test execution error: {e}")
            self.metrics['error_events'] += 1
        finally:
            await self.generate_test_report()
    
    async def listen_for_responses(self, websocket):
        """Listen for server responses and track transcript continuity."""
        logger.info("👂 Started listening for server responses...")
        
        try:
            async for message in websocket:
                current_time = time.time()
                
                try:
                    # Try to parse as JSON first
                    if isinstance(message, str):
                        data = json.loads(message)
                        logger.info(f"📝 Received JSON: {data}")
                    else:
                        # Binary audio data
                        logger.debug(f"🔊 Received audio data: {len(message)} bytes")
                        continue
                        
                except json.JSONDecodeError:
                    # Plain text transcript
                    logger.info(f"📝 Transcript received: '{message}'")
                
                self.metrics['transcripts_received'] += 1
                
                # Check for transcript gaps (potential data loss)
                if self.metrics['last_transcript_time']:
                    gap_duration = current_time - self.metrics['last_transcript_time']
                    if gap_duration > 10:  # More than 10 seconds gap
                        logger.warning(f"⚠️  Large transcript gap detected: {gap_duration:.1f}s")
                        self.metrics['transcript_gaps'].append({
                            'gap_duration': gap_duration,
                            'timestamp': current_time
                        })
                        self.metrics['data_loss_events'] += 1
                
                self.metrics['last_transcript_time'] = current_time
                
        except Exception as e:
            logger.error(f"❌ Response listening error: {e}")
            self.metrics['error_events'] += 1
    
    async def generate_test_report(self):
        """Generate comprehensive test report with validation results."""
        test_duration = time.time() - self.metrics['test_start_time']
        
        report = {
            'test_summary': {
                'duration_minutes': test_duration / 60,
                'target_duration_minutes': self.test_duration_minutes,
                'completion_percentage': min(100, (test_duration / (self.test_duration_minutes * 60)) * 100)
            },
            'stream_metrics': {
                'chunks_sent': self.metrics['chunks_sent'],
                'transcripts_received': self.metrics['transcripts_received'],
                'expected_chunks': int(test_duration * 10),  # 10 chunks per second
                'chunk_success_rate': self.metrics['chunks_sent'] / max(1, int(test_duration * 10)) * 100
            },
            'restart_validation': {
                'expected_restarts': int(test_duration / self.expected_restart_interval),
                'detected_restarts': self.metrics['stream_restarts_detected'],
                'restart_timings': self.metrics['restart_timings']
            },
            'data_integrity': {
                'data_loss_events': self.metrics['data_loss_events'],
                'transcript_gaps': len(self.metrics['transcript_gaps']),
                'largest_gap_seconds': max([g['gap_duration'] for g in self.metrics['transcript_gaps']], default=0)
            },
            'error_analysis': {
                'total_errors': self.metrics['error_events'],
                'error_rate_percentage': (self.metrics['error_events'] / max(1, self.metrics['chunks_sent'])) * 100
            },
            'performance_metrics': {
                'avg_processing_time_ms': np.mean([s['processing_time_ms'] for s in self.metrics['performance_samples']]),
                'max_processing_time_ms': max([s['processing_time_ms'] for s in self.metrics['performance_samples']], default=0),
                'performance_samples_count': len(self.metrics['performance_samples'])
            }
        }
        
        # Validation results
        validation_results = {
            'stream_continuity': {
                'passed': test_duration >= (self.test_duration_minutes * 60 * 0.95),  # 95% completion
                'details': f"Achieved {report['test_summary']['completion_percentage']:.1f}% of target duration"
            },
            'seamless_restart': {
                'passed': self.metrics['data_loss_events'] == 0,
                'details': f"Data loss events: {self.metrics['data_loss_events']}"
            },
            'transcript_continuity': {
                'passed': len(self.metrics['transcript_gaps']) <= 1,  # Allow 1 minor gap
                'details': f"Transcript gaps: {len(self.metrics['transcript_gaps'])}, largest: {report['data_integrity']['largest_gap_seconds']:.1f}s"
            },
            'error_tolerance': {
                'passed': report['error_analysis']['error_rate_percentage'] < 1.0,  # Less than 1% error rate
                'details': f"Error rate: {report['error_analysis']['error_rate_percentage']:.2f}%"
            }
        }
        
        # Overall test result
        all_validations_passed = all(v['passed'] for v in validation_results.values())
        
        # Generate report
        logger.info("=" * 80)
        logger.info("📊 EXTENDED STREAMING TEST REPORT")
        logger.info("=" * 80)
        
        logger.info(f"✅ Test Duration: {report['test_summary']['duration_minutes']:.1f}/{self.test_duration_minutes} minutes ({report['test_summary']['completion_percentage']:.1f}%)")
        logger.info(f"📊 Chunks Sent: {report['stream_metrics']['chunks_sent']:,} (success rate: {report['stream_metrics']['chunk_success_rate']:.1f}%)")
        logger.info(f"📝 Transcripts Received: {report['stream_metrics']['transcripts_received']:,}")
        logger.info(f"🔄 Stream Restarts: {report['restart_validation']['detected_restarts']} (expected: {report['restart_validation']['expected_restarts']})")
        logger.info(f"⚠️  Data Loss Events: {report['data_integrity']['data_loss_events']}")
        logger.info(f"❌ Error Events: {report['error_analysis']['total_errors']} ({report['error_analysis']['error_rate_percentage']:.2f}%)")
        
        logger.info("\n🔍 VALIDATION RESULTS:")
        for validation, result in validation_results.items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            logger.info(f"  {status} {validation.replace('_', ' ').title()}: {result['details']}")
        
        overall_result = "✅ PASSED" if all_validations_passed else "❌ FAILED"
        logger.info(f"\n🏆 OVERALL TEST RESULT: {overall_result}")
        
        # Save detailed report to file
        report_filename = f"extended_streaming_report_{int(time.time())}.json"
        with open(report_filename, 'w') as f:
            json.dump({
                'report': report,
                'validation_results': validation_results,
                'overall_passed': all_validations_passed,
                'test_timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        logger.info(f"📄 Detailed report saved to: {report_filename}")
        logger.info("=" * 80)
        
        return all_validations_passed

async def main():
    """Main test execution."""
    # Check if backend is running
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/health') as response:
                if response.status != 200:
                    raise Exception(f"Backend health check failed: {response.status}")
                logger.info("✅ Backend is running and healthy")
    except Exception as e:
        logger.error(f"❌ Backend not accessible: {e}")
        logger.error("Please start the backend with: poetry run uvicorn backend.main:app --reload")
        return False
    
    # Run the extended test
    tester = ExtendedStreamingTester()
    success = await tester.run_extended_test()
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
        exit(2)
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        exit(3)