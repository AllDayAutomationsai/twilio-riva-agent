#!/usr/bin/env python3
"""
Performance Optimization Module for Twilio RIVA Voice Agent
Implements caching, connection pooling, and resource management
"""

import asyncio
import time
from collections import deque
from typing import Dict, Any, Optional, Callable
from functools import lru_cache, wraps
import logging
import psutil
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """Main performance optimization manager"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.metrics = PerformanceMetrics()
        self.cache_manager = CacheManager()
        self.resource_monitor = ResourceMonitor()
        self.connection_pool = ConnectionPool()
        
    def initialize(self):
        """Initialize all performance optimization components"""
        self.resource_monitor.start()
        logger.info("Performance optimizer initialized")
        
    def cleanup(self):
        """Clean up resources"""
        self.resource_monitor.stop()
        self.connection_pool.close_all()
        logger.info("Performance optimizer cleaned up")

class PerformanceMetrics:
    """Collect and track performance metrics"""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.latencies = {
            'asr': deque(maxlen=window_size),
            'llm': deque(maxlen=window_size),
            'tts': deque(maxlen=window_size),
            'e2e': deque(maxlen=window_size)  # end-to-end
        }
        self.success_count = 0
        self.error_count = 0
        self.call_count = 0
        self.start_time = time.time()
        self._lock = threading.Lock()
        
    def record_latency(self, component: str, latency_ms: float):
        """Record latency for a component"""
        with self._lock:
            if component in self.latencies:
                self.latencies[component].append(latency_ms)
                
    def record_call(self, success: bool = True):
        """Record a call attempt"""
        with self._lock:
            self.call_count += 1
            if success:
                self.success_count += 1
            else:
                self.error_count += 1
                
    def get_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        with self._lock:
            stats = {
                'uptime_seconds': time.time() - self.start_time,
                'total_calls': self.call_count,
                'successful_calls': self.success_count,
                'failed_calls': self.error_count,
                'success_rate': self.success_count / max(1, self.call_count),
                'latencies': {}
            }
            
            for component, latencies in self.latencies.items():
                if latencies:
                    stats['latencies'][component] = {
                        'avg': sum(latencies) / len(latencies),
                        'min': min(latencies),
                        'max': max(latencies),
                        'p50': self._percentile(list(latencies), 50),
                        'p95': self._percentile(list(latencies), 95),
                        'p99': self._percentile(list(latencies), 99)
                    }
                    
        return stats
        
    def _percentile(self, data: list, percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (len(sorted_data) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1
        if upper >= len(sorted_data):
            return sorted_data[lower]
        return sorted_data[lower] + (sorted_data[upper] - sorted_data[lower]) * (index - lower)

class CacheManager:
    """Manage caching for frequently used data"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.timestamps = {}
        self._lock = threading.Lock()
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        with self._lock:
            if key in self.cache:
                if time.time() - self.timestamps[key] < self.ttl_seconds:
                    return self.cache[key]
                else:
                    # Expired, remove from cache
                    del self.cache[key]
                    del self.timestamps[key]
        return None
        
    def set(self, key: str, value: Any):
        """Set value in cache"""
        with self._lock:
            self.cache[key] = value
            self.timestamps[key] = time.time()
            
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self.cache.clear()
            self.timestamps.clear()
            
    def cleanup_expired(self):
        """Remove expired entries from cache"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, timestamp in self.timestamps.items()
                if current_time - timestamp >= self.ttl_seconds
            ]
            for key in expired_keys:
                del self.cache[key]
                del self.timestamps[key]

class ResourceMonitor:
    """Monitor system resources and provide alerts"""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0
        }
        self.current_stats = {}
        
    def start(self):
        """Start resource monitoring"""
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        
    def stop(self):
        """Stop resource monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
            
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            self._check_resources()
            time.sleep(self.check_interval)
            
    def _check_resources(self):
        """Check current resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Network stats
            network = psutil.net_io_counters()
            
            # Process-specific stats
            process = psutil.Process()
            process_memory = process.memory_info().rss / 1024 / 1024  # MB
            process_cpu = process.cpu_percent()
            
            self.current_stats = {
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'memory_available_mb': memory.available / 1024 / 1024,
                    'disk_percent': disk_percent,
                    'disk_free_gb': disk.free / 1024 / 1024 / 1024,
                    'network_sent_mb': network.bytes_sent / 1024 / 1024,
                    'network_recv_mb': network.bytes_recv / 1024 / 1024
                },
                'process': {
                    'memory_mb': process_memory,
                    'cpu_percent': process_cpu,
                    'num_threads': process.num_threads()
                }
            }
            
            # Check thresholds and log warnings
            if cpu_percent > self.thresholds['cpu_percent']:
                logger.warning(f"High CPU usage: {cpu_percent:.1f}%")
            if memory_percent > self.thresholds['memory_percent']:
                logger.warning(f"High memory usage: {memory_percent:.1f}%")
            if disk_percent > self.thresholds['disk_percent']:
                logger.warning(f"High disk usage: {disk_percent:.1f}%")
                
        except Exception as e:
            logger.error(f"Error monitoring resources: {e}")
            
    def get_stats(self) -> Dict[str, Any]:
        """Get current resource statistics"""
        return self.current_stats.copy()

class ConnectionPool:
    """Manage connection pooling for various services"""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.pools = {}
        self._lock = threading.Lock()
        
    def get_connection(self, service: str, factory: Callable):
        """Get a connection from the pool or create a new one"""
        with self._lock:
            if service not in self.pools:
                self.pools[service] = {
                    'connections': [],
                    'in_use': set(),
                    'factory': factory
                }
                
            pool = self.pools[service]
            
            # Try to get an available connection
            for conn in pool['connections']:
                if conn not in pool['in_use']:
                    pool['in_use'].add(conn)
                    return conn
                    
            # Create new connection if under limit
            if len(pool['connections']) < self.max_connections:
                conn = factory()
                pool['connections'].append(conn)
                pool['in_use'].add(conn)
                return conn
                
            # Wait for a connection to become available
            logger.warning(f"Connection pool for {service} is full")
            return None
            
    def release_connection(self, service: str, connection):
        """Release a connection back to the pool"""
        with self._lock:
            if service in self.pools:
                pool = self.pools[service]
                if connection in pool['in_use']:
                    pool['in_use'].remove(connection)
                    
    def close_all(self):
        """Close all connections in all pools"""
        with self._lock:
            for service, pool in self.pools.items():
                for conn in pool['connections']:
                    try:
                        if hasattr(conn, 'close'):
                            conn.close()
                    except Exception as e:
                        logger.error(f"Error closing connection for {service}: {e}")
            self.pools.clear()

def async_performance_tracker(component: str):
    """Decorator to track performance of async functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                latency_ms = (time.perf_counter() - start_time) * 1000
                
                # Get performance optimizer if available in args
                for arg in args:
                    if hasattr(arg, 'performance_optimizer'):
                        arg.performance_optimizer.metrics.record_latency(component, latency_ms)
                        break
                        
                return result
            except Exception as e:
                # Record failure
                for arg in args:
                    if hasattr(arg, 'performance_optimizer'):
                        arg.performance_optimizer.metrics.record_call(success=False)
                        break
                raise e
        return wrapper
    return decorator

def performance_tracker(component: str):
    """Decorator to track performance of sync functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                latency_ms = (time.perf_counter() - start_time) * 1000
                
                # Get performance optimizer if available in args
                for arg in args:
                    if hasattr(arg, 'performance_optimizer'):
                        arg.performance_optimizer.metrics.record_latency(component, latency_ms)
                        break
                        
                return result
            except Exception as e:
                # Record failure
                for arg in args:
                    if hasattr(arg, 'performance_optimizer'):
                        arg.performance_optimizer.metrics.record_call(success=False)
                        break
                raise e
        return wrapper
    return decorator

# Optimized buffer management
class AudioBufferManager:
    """Manage audio buffers efficiently"""
    
    def __init__(self, max_buffer_size: int = 100):
        self.max_buffer_size = max_buffer_size
        self.buffers = {}
        self._lock = threading.Lock()
        
    def add_audio(self, stream_id: str, audio_data: bytes):
        """Add audio data to buffer"""
        with self._lock:
            if stream_id not in self.buffers:
                self.buffers[stream_id] = deque(maxlen=self.max_buffer_size)
            self.buffers[stream_id].append(audio_data)
            
    def get_audio(self, stream_id: str, max_chunks: int = None) -> list:
        """Get audio chunks from buffer"""
        with self._lock:
            if stream_id not in self.buffers:
                return []
                
            buffer = self.buffers[stream_id]
            if max_chunks is None:
                chunks = list(buffer)
                buffer.clear()
            else:
                chunks = []
                for _ in range(min(max_chunks, len(buffer))):
                    chunks.append(buffer.popleft())
                    
            return chunks
            
    def clear_buffer(self, stream_id: str):
        """Clear buffer for a stream"""
        with self._lock:
            if stream_id in self.buffers:
                self.buffers[stream_id].clear()
                
    def remove_stream(self, stream_id: str):
        """Remove a stream buffer"""
        with self._lock:
            if stream_id in self.buffers:
                del self.buffers[stream_id]

# Export the main components
__all__ = [
    'PerformanceOptimizer',
    'PerformanceMetrics',
    'CacheManager',
    'ResourceMonitor',
    'ConnectionPool',
    'AudioBufferManager',
    'async_performance_tracker',
    'performance_tracker'
]
