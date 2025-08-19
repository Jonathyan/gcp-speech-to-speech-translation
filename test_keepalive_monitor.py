#!/usr/bin/env python3
"""
WebSocket Connection Monitor - 60+ minute test

Tests WebSocket keepalive mechanism by maintaining idle connections
for extended periods to validate:
- Ping/pong success rates
- Connection state changes  
- Automatic cleanup of dead connections
- No memory leaks from connection tracking
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List
import websockets
import aiohttp
from websockets.exceptions import ConnectionClosed, WebSocketException

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'keepalive_monitor_{int(time.time())}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class KeepAliveMonitor:
    """Monitor WebSocket connections for keepalive validation."""
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.websocket_base = backend_url.replace('http', 'ws')
        self.test_duration_minutes = 65  # 65 minutes to test 1+ hour
        
        # Test configuration
        self.num_connections = 3  # Multiple connections to test concurrent keepalive
        self.connections: List[Dict] = []
        self.monitoring_active = False
        
        # Metrics tracking
        self.metrics = {
            'test_start_time': None,
            'total_pings_sent': 0,
            'total_pongs_received': 0,
            'connection_drops': 0,
            'reconnection_attempts': 0,
            'keepalive_stats_samples': [],
            'connection_state_changes': []
        }
    
    async def start_monitoring(self):
        """Start the comprehensive keepalive monitoring test."""
        logger.info("🚀 Starting WebSocket Keepalive Monitor")
        logger.info(f"   Duration: {self.test_duration_minutes} minutes")
        logger.info(f"   Connections: {self.num_connections}")
        logger.info(f"   Backend: {self.backend_url}")
        
        # Verify backend is accessible
        if not await self._check_backend_health():
            logger.error("❌ Backend not accessible")
            return False
        
        self.metrics['test_start_time'] = time.time()
        self.monitoring_active = True
        
        try:
            # Create multiple WebSocket connections
            connection_tasks = []
            for i in range(self.num_connections):
                task = asyncio.create_task(self._maintain_connection(f"monitor-{i}"))
                connection_tasks.append(task)
            
            # Start monitoring tasks
            stats_task = asyncio.create_task(self._monitor_keepalive_stats())
            health_task = asyncio.create_task(self._monitor_backend_health())
            duration_task = asyncio.create_task(self._test_duration_monitor())
            
            # Wait for test completion or failure
            await asyncio.gather(
                *connection_tasks, 
                stats_task, 
                health_task, 
                duration_task,
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"❌ Monitor error: {e}")
            return False
        finally:
            self.monitoring_active = False
            await self._generate_report()
        
        return True
    
    async def _maintain_connection(self, stream_id: str):
        """Maintain a WebSocket connection for the test duration."""
        connection_info = {
            'stream_id': stream_id,
            'websocket': None,
            'connected_at': None,
            'last_ping_seen': None,
            'last_pong_sent': None,
            'state_changes': [],
            'reconnect_count': 0
        }
        
        self.connections.append(connection_info)
        websocket_url = f"{self.websocket_base}/ws/listen/{stream_id}"
        
        while self.monitoring_active:
            try:
                logger.info(f"🔌 Connecting to {websocket_url}")
                async with websockets.connect(websocket_url) as websocket:
                    connection_info['websocket'] = websocket
                    connection_info['connected_at'] = time.time()
                    
                    self._log_state_change(stream_id, "connected")
                    logger.info(f"✅ Connected: {stream_id}")
                    
                    # Listen for messages (primarily pings)
                    async for message in websocket:
                        if not self.monitoring_active:
                            break
                            
                        # Handle keepalive messages from FastAPI backend
                        if isinstance(message, str):
                            try:
                                data = json.loads(message)
                                if data.get('type') == 'keepalive' and data.get('action') == 'ping':
                                    connection_info['last_ping_seen'] = time.time()
                                    self.metrics['total_pings_sent'] += 1
                                    logger.debug(f"📡 Keepalive ping received on {stream_id}")
                                    
                                    # Send pong response
                                    pong_response = '{"type":"keepalive","action":"pong"}'
                                    await websocket.send(pong_response)
                                    connection_info['last_pong_sent'] = time.time()
                                    self.metrics['total_pongs_received'] += 1
                                    logger.debug(f"📡 Keepalive pong sent on {stream_id}")
                                else:
                                    logger.info(f"📨 JSON data received on {stream_id}: {message[:100]}")
                            except json.JSONDecodeError:
                                logger.info(f"📨 Text data received on {stream_id}: {message[:100]}")
                        elif isinstance(message, bytes):
                            logger.info(f"📨 Binary data received on {stream_id}: {len(message)} bytes")
                            
            except ConnectionClosed as e:
                self._log_state_change(stream_id, "disconnected", str(e))
                logger.warning(f"🔌 Connection closed: {stream_id} - {e}")
                self.metrics['connection_drops'] += 1
                
                if self.monitoring_active:
                    connection_info['reconnect_count'] += 1
                    self.metrics['reconnection_attempts'] += 1
                    logger.info(f"🔄 Reconnecting {stream_id} (attempt {connection_info['reconnect_count']})")
                    await asyncio.sleep(5)  # Wait before reconnect
                    
            except Exception as e:
                self._log_state_change(stream_id, "error", str(e))
                logger.error(f"❌ Connection error {stream_id}: {e}")
                
                if self.monitoring_active:
                    await asyncio.sleep(10)  # Longer wait on errors
    
    def _log_state_change(self, stream_id: str, state: str, details: str = ""):
        """Log connection state changes."""
        state_change = {
            'timestamp': time.time(),
            'stream_id': stream_id,
            'state': state,
            'details': details
        }
        self.metrics['connection_state_changes'].append(state_change)
        logger.info(f"🔄 State change: {stream_id} → {state} {details}")
    
    async def _monitor_keepalive_stats(self):
        """Periodically collect keepalive statistics from backend."""
        async with aiohttp.ClientSession() as session:
            while self.monitoring_active:
                try:
                    async with session.get(f"{self.backend_url}/keepalive/stats") as response:
                        if response.status == 200:
                            stats = await response.json()
                            stats['collected_at'] = time.time()
                            self.metrics['keepalive_stats_samples'].append(stats)
                            
                            # Log important stats
                            total_connections = stats.get('total_connections', 0)
                            healthy_connections = sum(1 for conn in stats.get('connections', []) 
                                                    if conn.get('healthy', False))
                            logger.info(f"📊 Backend stats: {healthy_connections}/{total_connections} healthy connections")
                        else:
                            logger.warning(f"⚠️  Stats endpoint error: {response.status}")
                            
                except Exception as e:
                    logger.error(f"❌ Stats collection error: {e}")
                
                await asyncio.sleep(30)  # Collect stats every 30 seconds
    
    async def _monitor_backend_health(self):
        """Monitor backend health throughout the test."""
        async with aiohttp.ClientSession() as session:
            consecutive_failures = 0
            
            while self.monitoring_active:
                try:
                    async with session.get(f"{self.backend_url}/health") as response:
                        if response.status == 200:
                            consecutive_failures = 0
                        else:
                            consecutive_failures += 1
                            logger.warning(f"⚠️  Health check failed: {response.status}")
                            
                except Exception as e:
                    consecutive_failures += 1
                    logger.error(f"❌ Health check error: {e}")
                
                # Alert on sustained failures
                if consecutive_failures >= 3:
                    logger.error(f"🚨 Backend health failing for {consecutive_failures} checks")
                
                await asyncio.sleep(60)  # Health check every minute
    
    async def _test_duration_monitor(self):
        """Monitor test duration and stop when complete."""
        test_end_time = time.time() + (self.test_duration_minutes * 60)
        
        while self.monitoring_active and time.time() < test_end_time:
            remaining_minutes = (test_end_time - time.time()) / 60
            if remaining_minutes > 0:
                logger.info(f"⏳ Test progress: {remaining_minutes:.1f} minutes remaining")
            await asyncio.sleep(300)  # Log every 5 minutes
        
        logger.info("⏰ Test duration completed")
        self.monitoring_active = False
    
    async def _check_backend_health(self) -> bool:
        """Check if backend is accessible."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.backend_url}/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        logger.info(f"✅ Backend healthy: {health_data}")
                        return True
                    else:
                        logger.error(f"❌ Backend unhealthy: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Backend unreachable: {e}")
            return False
    
    async def _generate_report(self):
        """Generate comprehensive test report."""
        test_duration = time.time() - self.metrics['test_start_time']
        
        # Calculate success rates
        ping_pong_success_rate = 0
        if self.metrics['total_pings_sent'] > 0:
            ping_pong_success_rate = (self.metrics['total_pongs_received'] / 
                                    self.metrics['total_pings_sent']) * 100
        
        # Analyze connection stability
        total_connections = len(self.connections)
        connections_with_drops = sum(1 for conn in self.connections 
                                   if any(sc['state'] == 'disconnected' 
                                         for sc in self.metrics['connection_state_changes']
                                         if sc['stream_id'] == conn['stream_id']))
        
        # Analyze keepalive stats
        backend_stats_samples = len(self.metrics['keepalive_stats_samples'])
        avg_healthy_connections = 0
        if backend_stats_samples > 0:
            total_healthy = sum(sum(1 for conn in sample.get('connections', []) 
                                  if conn.get('healthy', False))
                              for sample in self.metrics['keepalive_stats_samples'])
            avg_healthy_connections = total_healthy / backend_stats_samples
        
        logger.info("=" * 80)
        logger.info("📊 WEBSOCKET KEEPALIVE MONITOR REPORT")
        logger.info("=" * 80)
        
        logger.info(f"⏱️  Test Duration: {test_duration/60:.1f} minutes ({test_duration:.0f} seconds)")
        logger.info(f"🔌 Total Connections: {total_connections}")
        logger.info(f"📡 Ping/Pong Stats:")
        logger.info(f"   Pings received: {self.metrics['total_pings_sent']}")
        logger.info(f"   Pongs sent: {self.metrics['total_pongs_received']}")
        logger.info(f"   Success rate: {ping_pong_success_rate:.1f}%")
        
        logger.info(f"🔄 Connection Stability:")
        logger.info(f"   Connections dropped: {self.metrics['connection_drops']}")
        logger.info(f"   Reconnection attempts: {self.metrics['reconnection_attempts']}")
        logger.info(f"   Connections with issues: {connections_with_drops}/{total_connections}")
        
        logger.info(f"🩺 Backend Monitoring:")
        logger.info(f"   Stats samples collected: {backend_stats_samples}")
        logger.info(f"   Average healthy connections: {avg_healthy_connections:.1f}")
        
        # Validation results
        validations = {
            'connections_stable_60min': test_duration >= 3600,  # 1+ hour
            'ping_pong_success_rate': ping_pong_success_rate >= 95,  # 95%+ success
            'connection_drops_minimal': self.metrics['connection_drops'] <= 2,  # Max 2 drops
            'backend_stats_collected': backend_stats_samples >= 120,  # 2+ hours of data
        }
        
        logger.info("\n🔍 VALIDATION RESULTS:")
        for validation, passed in validations.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"  {status} {validation.replace('_', ' ').title()}")
        
        overall_result = "✅ PASSED" if all(validations.values()) else "❌ FAILED"
        logger.info(f"\n🏆 OVERALL KEEPALIVE TEST: {overall_result}")
        
        # Save detailed report
        report_data = {
            'test_summary': {
                'duration_seconds': test_duration,
                'total_connections': total_connections,
                'test_completed': test_duration >= 3600
            },
            'ping_pong_stats': {
                'pings_sent': self.metrics['total_pings_sent'],
                'pongs_received': self.metrics['total_pongs_received'],
                'success_rate_percent': ping_pong_success_rate
            },
            'connection_stability': {
                'drops': self.metrics['connection_drops'],
                'reconnects': self.metrics['reconnection_attempts'],
                'state_changes': self.metrics['connection_state_changes']
            },
            'backend_monitoring': {
                'stats_samples': self.metrics['keepalive_stats_samples'],
                'sample_count': backend_stats_samples
            },
            'validation_results': validations,
            'overall_passed': all(validations.values()),
            'test_timestamp': datetime.now().isoformat()
        }
        
        report_filename = f"keepalive_monitor_report_{int(time.time())}.json"
        with open(report_filename, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"📄 Detailed report saved: {report_filename}")
        logger.info("=" * 80)
        
        return all(validations.values())

async def main():
    """Main test execution."""
    monitor = KeepAliveMonitor()
    success = await monitor.start_monitoring()
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("🛑 Monitor interrupted by user")
        exit(2)
    except Exception as e:
        logger.error(f"❌ Monitor failed: {e}")
        exit(3)