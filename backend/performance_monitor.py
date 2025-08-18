import logging
import time
import asyncio
import psutil
import threading
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import json
from enum import Enum


class MetricType(Enum):
    """Types of metrics being collected."""
    COUNTER = "counter"
    GAUGE = "gauge" 
    HISTOGRAM = "histogram"
    TIMING = "timing"


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: Union[int, float]
    timestamp: float
    tags: Dict[str, str]
    metric_type: MetricType


class PerformanceHistogram:
    """Performance histogram for tracking latency distributions."""
    
    def __init__(self, max_samples: int = 1000):
        self.samples = deque(maxlen=max_samples)
        self.lock = threading.Lock()
    
    def add_sample(self, value: float):
        """Add a sample to the histogram."""
        with self.lock:
            self.samples.append(value)
    
    def get_percentile(self, percentile: float) -> float:
        """Get the specified percentile value."""
        if not self.samples:
            return 0.0
        
        with self.lock:
            sorted_samples = sorted(self.samples)
            index = int((percentile / 100.0) * len(sorted_samples))
            index = min(index, len(sorted_samples) - 1)
            return sorted_samples[index]
    
    def get_stats(self) -> Dict[str, float]:
        """Get comprehensive histogram statistics."""
        if not self.samples:
            return {
                'count': 0,
                'min': 0.0,
                'max': 0.0,
                'avg': 0.0,
                'p50': 0.0,
                'p95': 0.0,
                'p99': 0.0
            }
        
        with self.lock:
            samples_list = list(self.samples)
            return {
                'count': len(samples_list),
                'min': min(samples_list),
                'max': max(samples_list),
                'avg': sum(samples_list) / len(samples_list),
                'p50': self.get_percentile(50),
                'p95': self.get_percentile(95),
                'p99': self.get_percentile(99)
            }


class MetricsCollector:
    """Collects and aggregates performance metrics."""
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.metrics_history: deque = deque(maxlen=max_history)
        
        # Metric storage
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, PerformanceHistogram] = defaultdict(PerformanceHistogram)
        self.timings: Dict[str, List[float]] = defaultdict(list)
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Performance tracking
        self.start_time = time.time()
        
        self._logger = logging.getLogger(__name__)
    
    def increment(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        tags = tags or {}
        
        with self.lock:
            key = f"{name}:{':'.join(f'{k}={v}' for k, v in sorted(tags.items()))}"
            self.counters[key] += value
            
            metric_point = MetricPoint(
                name=name,
                value=value,
                timestamp=time.time(),
                tags=tags,
                metric_type=MetricType.COUNTER
            )
            self.metrics_history.append(metric_point)
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric value."""
        tags = tags or {}
        
        with self.lock:
            key = f"{name}:{':'.join(f'{k}={v}' for k, v in sorted(tags.items()))}"
            self.gauges[key] = value
            
            metric_point = MetricPoint(
                name=name,
                value=value,
                timestamp=time.time(),
                tags=tags,
                metric_type=MetricType.GAUGE
            )
            self.metrics_history.append(metric_point)
    
    def add_timing(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None):
        """Add a timing measurement."""
        tags = tags or {}
        
        with self.lock:
            key = f"{name}:{':'.join(f'{k}={v}' for k, v in sorted(tags.items()))}"
            self.timings[key].append(duration_ms)
            
            # Keep only recent timings
            if len(self.timings[key]) > 1000:
                self.timings[key] = self.timings[key][-1000:]
            
            # Add to histogram
            self.histograms[key].add_sample(duration_ms)
            
            metric_point = MetricPoint(
                name=name,
                value=duration_ms,
                timestamp=time.time(),
                tags=tags,
                metric_type=MetricType.TIMING
            )
            self.metrics_history.append(metric_point)
    
    @asynccontextmanager
    async def time_operation(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.add_timing(name, duration_ms, tags)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        with self.lock:
            uptime = time.time() - self.start_time
            
            # Process timing statistics
            timing_stats = {}
            for key, timings in self.timings.items():
                if timings:
                    timing_stats[key] = {
                        'count': len(timings),
                        'avg': sum(timings) / len(timings),
                        'min': min(timings),
                        'max': max(timings),
                        'recent': timings[-10:] if len(timings) >= 10 else timings
                    }
            
            # Process histogram statistics
            histogram_stats = {}
            for key, histogram in self.histograms.items():
                histogram_stats[key] = histogram.get_stats()
            
            return {
                'uptime_seconds': uptime,
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'timing_stats': timing_stats,
                'histogram_stats': histogram_stats,
                'total_metrics_collected': len(self.metrics_history),
                'collection_timestamp': time.time()
            }


class SystemMetricsCollector:
    """Collects system-level performance metrics."""
    
    def __init__(self):
        self.process = psutil.Process()
        self._logger = logging.getLogger(__name__)
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics."""
        try:
            # CPU metrics
            cpu_percent = self.process.cpu_percent()
            cpu_times = self.process.cpu_times()
            
            # Memory metrics
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            
            # Disk I/O metrics (if available)
            try:
                io_counters = self.process.io_counters()
                io_metrics = {
                    'read_bytes': io_counters.read_bytes,
                    'write_bytes': io_counters.write_bytes,
                    'read_count': io_counters.read_count,
                    'write_count': io_counters.write_count
                }
            except (AttributeError, OSError):
                io_metrics = {}
            
            # Thread metrics
            num_threads = self.process.num_threads()
            
            # File descriptors (Unix only)
            try:
                num_fds = self.process.num_fds()
            except (AttributeError, OSError):
                num_fds = None
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'user_time': cpu_times.user,
                    'system_time': cpu_times.system
                },
                'memory': {
                    'rss_bytes': memory_info.rss,
                    'vms_bytes': memory_info.vms,
                    'percent': memory_percent
                },
                'io': io_metrics,
                'threads': num_threads,
                'file_descriptors': num_fds,
                'timestamp': time.time()
            }
        except Exception as e:
            self._logger.error(f"Error collecting system metrics: {e}")
            return {}


class PerformanceLogger:
    """Enhanced logging with performance context."""
    
    def __init__(self, name: str, metrics_collector: MetricsCollector):
        self.logger = logging.getLogger(name)
        self.metrics_collector = metrics_collector
        
        # Configure structured logging format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - '
            '[%(filename)s:%(lineno)d] - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        self.logger.setLevel(logging.INFO)
    
    def info(self, message: str, **kwargs):
        """Log info message with metrics."""
        self.metrics_collector.increment('log.info')
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with metrics."""
        self.metrics_collector.increment('log.warning')
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message with metrics."""
        self.metrics_collector.increment('log.error')
        if error:
            self.logger.error(f"{message}: {error}", extra=kwargs, exc_info=True)
        else:
            self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log critical message with metrics."""
        self.metrics_collector.increment('log.critical')
        if error:
            self.logger.critical(f"{message}: {error}", extra=kwargs, exc_info=True)
        else:
            self.logger.critical(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with metrics."""
        self.metrics_collector.increment('log.debug')
        self.logger.debug(message, extra=kwargs)
    
    def log_performance_event(self, 
                             event_type: str,
                             duration_ms: Optional[float] = None,
                             success: bool = True,
                             **context):
        """Log a performance event with structured data."""
        tags = {
            'event_type': event_type,
            'success': str(success).lower()
        }
        
        if duration_ms is not None:
            self.metrics_collector.add_timing(f'performance.{event_type}', duration_ms, tags)
        
        self.metrics_collector.increment(f'events.{event_type}', tags=tags)
        
        log_message = f"Performance event: {event_type}"
        if duration_ms is not None:
            log_message += f" ({duration_ms:.2f}ms)"
        if context:
            log_message += f" - {context}"
        
        if success:
            self.info(log_message)
        else:
            self.error(log_message)


class PerformanceMonitor:
    """Comprehensive performance monitoring system."""
    
    def __init__(self, enable_system_metrics: bool = True):
        self.metrics_collector = MetricsCollector()
        self.system_collector = SystemMetricsCollector() if enable_system_metrics else None
        self.logger = PerformanceLogger(__name__, self.metrics_collector)
        
        # Background monitoring
        self._monitoring_task = None
        self._monitoring_interval = 60.0  # seconds
        self._is_monitoring = False
        
        # Performance thresholds
        self.thresholds = {
            'cpu_percent_warning': 80.0,
            'memory_percent_warning': 85.0,
            'response_time_warning_ms': 2000.0,
            'error_rate_warning': 0.05  # 5%
        }
    
    async def start_monitoring(self):
        """Start background performance monitoring."""
        if self._is_monitoring:
            return
        
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop background performance monitoring."""
        if not self._is_monitoring:
            return
        
        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while self._is_monitoring:
            try:
                await self._collect_periodic_metrics()
                await self._check_thresholds()
                await asyncio.sleep(self._monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in monitoring loop", error=e)
                await asyncio.sleep(self._monitoring_interval)
    
    async def _collect_periodic_metrics(self):
        """Collect periodic system and application metrics."""
        if self.system_collector:
            system_metrics = self.system_collector.collect_system_metrics()
            
            # Store system metrics as gauges
            if system_metrics:
                self.metrics_collector.set_gauge('system.cpu.percent', system_metrics['cpu']['percent'])
                self.metrics_collector.set_gauge('system.memory.percent', system_metrics['memory']['percent'])
                self.metrics_collector.set_gauge('system.memory.rss_mb', system_metrics['memory']['rss_bytes'] / (1024*1024))
                self.metrics_collector.set_gauge('system.threads', system_metrics['threads'])
                
                if system_metrics['file_descriptors']:
                    self.metrics_collector.set_gauge('system.file_descriptors', system_metrics['file_descriptors'])
    
    async def _check_thresholds(self):
        """Check performance thresholds and alert if exceeded."""
        metrics_summary = self.metrics_collector.get_metrics_summary()
        
        # Check CPU threshold
        cpu_gauge_key = 'system.cpu.percent:'
        for key, value in metrics_summary['gauges'].items():
            if key.startswith(cpu_gauge_key) and value > self.thresholds['cpu_percent_warning']:
                self.logger.warning(f"High CPU usage: {value:.1f}%")
        
        # Check memory threshold
        memory_gauge_key = 'system.memory.percent:'
        for key, value in metrics_summary['gauges'].items():
            if key.startswith(memory_gauge_key) and value > self.thresholds['memory_percent_warning']:
                self.logger.warning(f"High memory usage: {value:.1f}%")
        
        # Check response times
        for key, stats in metrics_summary['histogram_stats'].items():
            if stats['p95'] > self.thresholds['response_time_warning_ms']:
                self.logger.warning(f"High response time: {key} p95={stats['p95']:.1f}ms")
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        metrics_summary = self.metrics_collector.get_metrics_summary()
        
        # Add system metrics if available
        system_metrics = {}
        if self.system_collector:
            system_metrics = self.system_collector.collect_system_metrics()
        
        # Calculate health scores
        health_scores = self._calculate_health_scores(metrics_summary, system_metrics)
        
        return {
            'timestamp': time.time(),
            'metrics': metrics_summary,
            'system': system_metrics,
            'health_scores': health_scores,
            'thresholds': self.thresholds,
            'monitoring_active': self._is_monitoring
        }
    
    def _calculate_health_scores(self, 
                                metrics_summary: Dict[str, Any], 
                                system_metrics: Dict[str, Any]) -> Dict[str, float]:
        """Calculate health scores (0.0 to 1.0) for various system aspects."""
        scores = {}
        
        # CPU health score
        if system_metrics and 'cpu' in system_metrics:
            cpu_percent = system_metrics['cpu']['percent']
            scores['cpu'] = max(0.0, 1.0 - (cpu_percent / 100.0))
        
        # Memory health score
        if system_metrics and 'memory' in system_metrics:
            memory_percent = system_metrics['memory']['percent']
            scores['memory'] = max(0.0, 1.0 - (memory_percent / 100.0))
        
        # Response time health score
        response_times = []
        for stats in metrics_summary.get('histogram_stats', {}).values():
            if stats.get('p95'):
                response_times.append(stats['p95'])
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            scores['response_time'] = max(0.0, 1.0 - (avg_response_time / 5000.0))  # 5s max
        
        # Overall health score
        if scores:
            scores['overall'] = sum(scores.values()) / len(scores)
        
        return scores
    
    # Context managers for common operations
    @asynccontextmanager
    async def time_audio_processing(self, operation: str):
        """Time audio processing operations."""
        async with self.metrics_collector.time_operation('audio_processing', {'operation': operation}):
            yield
    
    @asynccontextmanager
    async def time_api_call(self, api_name: str):
        """Time API calls."""
        async with self.metrics_collector.time_operation('api_call', {'api': api_name}):
            yield


# Global performance monitor instance
performance_monitor = PerformanceMonitor()