#!/usr/bin/env python3
"""
Monitoring Module for Twilio RIVA Voice Agent
Provides real-time monitoring, metrics collection, and alerting
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
import aiohttp
from aiohttp import web
import psutil
from performance_optimizer import PerformanceOptimizer

logger = logging.getLogger(__name__)

class MonitoringServer:
    """HTTP server for monitoring endpoints and metrics"""
    
    def __init__(self, performance_optimizer: PerformanceOptimizer, port: int = 9090):
        self.performance_optimizer = performance_optimizer
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.call_registry = CallRegistry()
        self.alert_manager = AlertManager()
        self.setup_routes()
        
    def setup_routes(self):
        """Setup HTTP routes for monitoring"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/metrics', self.get_metrics)
        self.app.router.add_get('/stats', self.get_stats)
        self.app.router.add_get('/calls', self.get_calls)
        self.app.router.add_get('/alerts', self.get_alerts)
        self.app.router.add_get('/performance', self.get_performance)
        self.app.router.add_get('/resources', self.get_resources)
        
    async def start(self):
        """Start the monitoring server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"Monitoring server started on port {self.port}")
        
    async def stop(self):
        """Stop the monitoring server"""
        if self.runner:
            await self.runner.cleanup()
            logger.info("Monitoring server stopped")
            
    async def health_check(self, request):
        """Health check endpoint"""
        try:
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': self.performance_optimizer.metrics.get_stats()['uptime_seconds'],
                'components': self.check_components()
            }
            
            # Determine overall health
            if all(comp['status'] == 'healthy' for comp in health_status['components'].values()):
                health_status['status'] = 'healthy'
                status_code = 200
            elif any(comp['status'] == 'critical' for comp in health_status['components'].values()):
                health_status['status'] = 'critical'
                status_code = 503
            else:
                health_status['status'] = 'degraded'
                status_code = 200
                
            return web.json_response(health_status, status=status_code)
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return web.json_response({'status': 'error', 'error': str(e)}, status=500)
            
    def check_components(self) -> Dict[str, Any]:
        """Check health of individual components"""
        components = {}
        
        # Check WebSocket server
        components['websocket'] = {
            'status': 'healthy',  # Implement actual check
            'message': 'WebSocket server is running'
        }
        
        # Check RIVA connection
        components['riva'] = {
            'status': 'healthy',  # Implement actual check
            'message': 'RIVA services are accessible'
        }
        
        # Check OpenAI connection
        components['openai'] = {
            'status': 'healthy',  # Implement actual check
            'message': 'OpenAI API is accessible'
        }
        
        # Check system resources
        resources = self.performance_optimizer.resource_monitor.get_stats()
        if resources and resources.get('system'):
            system_stats = resources['system']
            if system_stats.get('cpu_percent', 0) > 90:
                components['resources'] = {
                    'status': 'critical',
                    'message': 'High CPU usage detected'
                }
            elif system_stats.get('memory_percent', 0) > 90:
                components['resources'] = {
                    'status': 'critical',
                    'message': 'High memory usage detected'
                }
            else:
                components['resources'] = {
                    'status': 'healthy',
                    'message': 'System resources within normal limits'
                }
        else:
            components['resources'] = {
                'status': 'unknown',
                'message': 'Resource stats not available'
            }
            
        return components
        
    async def get_metrics(self, request):
        """Get Prometheus-compatible metrics"""
        metrics_lines = []
        
        # Get performance stats
        stats = self.performance_optimizer.metrics.get_stats()
        
        # Call metrics
        metrics_lines.append(f"# HELP voice_agent_calls_total Total number of calls")
        metrics_lines.append(f"# TYPE voice_agent_calls_total counter")
        metrics_lines.append(f'voice_agent_calls_total{{status="success"}} {stats["successful_calls"]}')
        metrics_lines.append(f'voice_agent_calls_total{{status="failed"}} {stats["failed_calls"]}')
        
        # Success rate
        metrics_lines.append(f"# HELP voice_agent_success_rate Call success rate")
        metrics_lines.append(f"# TYPE voice_agent_success_rate gauge")
        metrics_lines.append(f'voice_agent_success_rate {stats["success_rate"]}')
        
        # Latency metrics
        for component, latencies in stats.get('latencies', {}).items():
            metrics_lines.append(f"# HELP voice_agent_latency_{component}_ms Latency for {component}")
            metrics_lines.append(f"# TYPE voice_agent_latency_{component}_ms summary")
            metrics_lines.append(f'voice_agent_latency_{component}_ms{{quantile="0.5"}} {latencies.get("p50", 0)}')
            metrics_lines.append(f'voice_agent_latency_{component}_ms{{quantile="0.95"}} {latencies.get("p95", 0)}')
            metrics_lines.append(f'voice_agent_latency_{component}_ms{{quantile="0.99"}} {latencies.get("p99", 0)}')
            metrics_lines.append(f'voice_agent_latency_{component}_ms_sum {latencies.get("avg", 0) * stats["total_calls"]}')
            metrics_lines.append(f'voice_agent_latency_{component}_ms_count {stats["total_calls"]}')
        
        # Resource metrics
        resources = self.performance_optimizer.resource_monitor.get_stats()
        if resources and resources.get('system'):
            system_stats = resources['system']
            metrics_lines.append(f"# HELP system_cpu_usage_percent System CPU usage")
            metrics_lines.append(f"# TYPE system_cpu_usage_percent gauge")
            metrics_lines.append(f'system_cpu_usage_percent {system_stats.get("cpu_percent", 0)}')
            
            metrics_lines.append(f"# HELP system_memory_usage_percent System memory usage")
            metrics_lines.append(f"# TYPE system_memory_usage_percent gauge")
            metrics_lines.append(f'system_memory_usage_percent {system_stats.get("memory_percent", 0)}')
            
        return web.Response(text='\n'.join(metrics_lines), content_type='text/plain')
        
    async def get_stats(self, request):
        """Get detailed statistics"""
        stats = {
            'performance': self.performance_optimizer.metrics.get_stats(),
            'resources': self.performance_optimizer.resource_monitor.get_stats(),
            'calls': self.call_registry.get_stats(),
            'alerts': self.alert_manager.get_active_alerts()
        }
        return web.json_response(stats)
        
    async def get_calls(self, request):
        """Get active and recent calls"""
        return web.json_response(self.call_registry.get_calls())
        
    async def get_alerts(self, request):
        """Get active alerts"""
        return web.json_response(self.alert_manager.get_active_alerts())
        
    async def get_performance(self, request):
        """Get performance metrics"""
        return web.json_response(self.performance_optimizer.metrics.get_stats())
        
    async def get_resources(self, request):
        """Get resource usage"""
        return web.json_response(self.performance_optimizer.resource_monitor.get_stats())

class CallRegistry:
    """Registry for tracking active and recent calls"""
    
    def __init__(self, history_size: int = 100):
        self.active_calls = {}
        self.completed_calls = deque(maxlen=history_size)
        self.call_stats = defaultdict(int)
        
    def register_call(self, call_id: str, phone_number: str):
        """Register a new call"""
        self.active_calls[call_id] = {
            'call_id': call_id,
            'phone_number': phone_number,
            'start_time': datetime.now().isoformat(),
            'duration': 0,
            'status': 'active',
            'events': []
        }
        self.call_stats['total_calls'] += 1
        
    def update_call(self, call_id: str, event: str, data: Any = None):
        """Update call with an event"""
        if call_id in self.active_calls:
            call = self.active_calls[call_id]
            call['events'].append({
                'timestamp': datetime.now().isoformat(),
                'event': event,
                'data': data
            })
            
            # Update duration
            start_time = datetime.fromisoformat(call['start_time'])
            call['duration'] = (datetime.now() - start_time).total_seconds()
            
    def complete_call(self, call_id: str, status: str = 'completed'):
        """Mark a call as completed"""
        if call_id in self.active_calls:
            call = self.active_calls.pop(call_id)
            call['status'] = status
            call['end_time'] = datetime.now().isoformat()
            
            # Calculate final duration
            start_time = datetime.fromisoformat(call['start_time'])
            call['duration'] = (datetime.now() - start_time).total_seconds()
            
            self.completed_calls.append(call)
            
            # Update stats
            self.call_stats[f'{status}_calls'] += 1
            self.call_stats['total_duration'] += call['duration']
            
    def get_calls(self) -> Dict[str, Any]:
        """Get active and recent calls"""
        return {
            'active': list(self.active_calls.values()),
            'completed': list(self.completed_calls),
            'stats': dict(self.call_stats)
        }
        
    def get_stats(self) -> Dict[str, Any]:
        """Get call statistics"""
        active_count = len(self.active_calls)
        completed_count = len(self.completed_calls)
        
        stats = {
            'active_calls': active_count,
            'completed_calls_in_history': completed_count,
            'total_calls': self.call_stats['total_calls'],
            'average_duration': 0
        }
        
        if self.call_stats['completed_calls'] > 0:
            stats['average_duration'] = self.call_stats['total_duration'] / self.call_stats['completed_calls']
            
        return stats

class AlertManager:
    """Manage system alerts and notifications"""
    
    def __init__(self):
        self.alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.alert_rules = self.setup_alert_rules()
        
    def setup_alert_rules(self) -> List[Dict[str, Any]]:
        """Setup alert rules"""
        return [
            {
                'name': 'high_cpu_usage',
                'condition': lambda stats: stats.get('system', {}).get('cpu_percent', 0) > 80,
                'severity': 'warning',
                'message': 'CPU usage is above 80%'
            },
            {
                'name': 'critical_cpu_usage',
                'condition': lambda stats: stats.get('system', {}).get('cpu_percent', 0) > 95,
                'severity': 'critical',
                'message': 'CPU usage is critically high (>95%)'
            },
            {
                'name': 'high_memory_usage',
                'condition': lambda stats: stats.get('system', {}).get('memory_percent', 0) > 85,
                'severity': 'warning',
                'message': 'Memory usage is above 85%'
            },
            {
                'name': 'high_latency',
                'condition': lambda stats: any(
                    lat.get('p95', 0) > 1000 
                    for lat in stats.get('latencies', {}).values()
                ),
                'severity': 'warning',
                'message': 'High latency detected (P95 > 1000ms)'
            },
            {
                'name': 'low_success_rate',
                'condition': lambda stats: stats.get('success_rate', 1) < 0.95 and stats.get('total_calls', 0) > 10,
                'severity': 'warning',
                'message': 'Call success rate is below 95%'
            }
        ]
        
    def check_alerts(self, performance_stats: Dict[str, Any], resource_stats: Dict[str, Any]):
        """Check alert conditions and trigger alerts"""
        combined_stats = {
            **performance_stats,
            **resource_stats
        }
        
        for rule in self.alert_rules:
            alert_id = rule['name']
            
            try:
                if rule['condition'](combined_stats):
                    # Alert condition met
                    if alert_id not in self.alerts:
                        # New alert
                        self.trigger_alert(alert_id, rule['severity'], rule['message'])
                else:
                    # Alert condition cleared
                    if alert_id in self.alerts:
                        self.clear_alert(alert_id)
                        
            except Exception as e:
                logger.error(f"Error checking alert rule {alert_id}: {e}")
                
    def trigger_alert(self, alert_id: str, severity: str, message: str):
        """Trigger a new alert"""
        alert = {
            'id': alert_id,
            'severity': severity,
            'message': message,
            'triggered_at': datetime.now().isoformat(),
            'status': 'active'
        }
        
        self.alerts[alert_id] = alert
        self.alert_history.append(alert.copy())
        
        logger.warning(f"Alert triggered: [{severity}] {message}")
        
        # Here you could add webhook notifications, email, etc.
        
    def clear_alert(self, alert_id: str):
        """Clear an existing alert"""
        if alert_id in self.alerts:
            alert = self.alerts.pop(alert_id)
            alert['status'] = 'resolved'
            alert['resolved_at'] = datetime.now().isoformat()
            self.alert_history.append(alert)
            
            logger.info(f"Alert cleared: {alert_id}")
            
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        return list(self.alerts.values())
        
    def get_alert_history(self) -> List[Dict[str, Any]]:
        """Get alert history"""
        return list(self.alert_history)

class MetricsCollector:
    """Background metrics collector"""
    
    def __init__(self, performance_optimizer: PerformanceOptimizer, alert_manager: AlertManager):
        self.performance_optimizer = performance_optimizer
        self.alert_manager = alert_manager
        self.running = False
        self.collection_interval = 10  # seconds
        
    async def start(self):
        """Start metrics collection"""
        self.running = True
        asyncio.create_task(self._collection_loop())
        logger.info("Metrics collector started")
        
    async def stop(self):
        """Stop metrics collection"""
        self.running = False
        logger.info("Metrics collector stopped")
        
    async def _collection_loop(self):
        """Main collection loop"""
        while self.running:
            try:
                # Collect metrics
                performance_stats = self.performance_optimizer.metrics.get_stats()
                resource_stats = self.performance_optimizer.resource_monitor.get_stats()
                
                # Check alerts
                self.alert_manager.check_alerts(performance_stats, resource_stats)
                
                # Log summary
                if performance_stats.get('total_calls', 0) > 0:
                    logger.info(
                        f"Metrics: Calls={performance_stats['total_calls']}, "
                        f"Success={performance_stats['success_rate']:.2%}, "
                        f"CPU={resource_stats.get('system', {}).get('cpu_percent', 0):.1f}%, "
                        f"Mem={resource_stats.get('system', {}).get('memory_percent', 0):.1f}%"
                    )
                    
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                
            await asyncio.sleep(self.collection_interval)

# Export main components
__all__ = [
    'MonitoringServer',
    'CallRegistry',
    'AlertManager',
    'MetricsCollector'
]
