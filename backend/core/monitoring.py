"""
Monitoring Module
Tracks usage, costs, errors, and performance metrics
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
from dataclasses import dataclass, asdict
from collections import defaultdict
import aiofiles

from .utils import get_env_var, format_timestamp


logger = logging.getLogger(__name__)


@dataclass
class UsageMetric:
    """Represents a single usage metric"""
    timestamp: datetime
    service: str  # 'retrieval', 'chat', 'bigquery'
    operation: str  # 'search', 'upload', 'query', etc.
    tokens: int = 0
    cost: float = 0.0
    duration_ms: int = 0
    success: bool = True
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UsageMonitor:
    """Monitors API usage and costs"""
    
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Cost limits from environment
        self.daily_limit = float(get_env_var("DAILY_COST_LIMIT", default="50.0"))
        self.monthly_limit = float(get_env_var("MONTHLY_COST_LIMIT", default="1000.0"))
        
        # In-memory metrics for current session
        self.current_metrics: List[UsageMetric] = []
        
        # Aggregated stats
        self.stats = defaultdict(lambda: {
            "total_cost": 0.0,
            "total_tokens": 0,
            "total_requests": 0,
            "errors": 0
        })
    
    async def log_usage(self, metric: UsageMetric):
        """Log a usage metric"""
        # Add to current metrics
        self.current_metrics.append(metric)
        
        # Update aggregated stats
        service_stats = self.stats[metric.service]
        service_stats["total_cost"] += metric.cost
        service_stats["total_tokens"] += metric.tokens
        service_stats["total_requests"] += 1
        if not metric.success:
            service_stats["errors"] += 1
        
        # Write to log file
        await self._write_to_log(metric)
        
        # Check cost limits
        await self._check_cost_limits()
    
    async def _write_to_log(self, metric: UsageMetric):
        """Write metric to log file"""
        log_file = self.log_dir / f"usage_{datetime.now().strftime('%Y%m%d')}.log"
        
        log_entry = {
            "timestamp": metric.timestamp.isoformat(),
            "service": metric.service,
            "operation": metric.operation,
            "tokens": metric.tokens,
            "cost": metric.cost,
            "duration_ms": metric.duration_ms,
            "success": metric.success,
            "error": metric.error,
            "metadata": metric.metadata
        }
        
        async with aiofiles.open(log_file, 'a') as f:
            await f.write(json.dumps(log_entry) + '\n')
    
    async def _check_cost_limits(self):
        """Check if cost limits are exceeded"""
        daily_cost = await self.get_daily_cost()
        monthly_cost = await self.get_monthly_cost()
        
        if daily_cost > self.daily_limit * 0.8:
            logger.warning(f"Approaching daily cost limit: ${daily_cost:.2f} / ${self.daily_limit:.2f}")
            if daily_cost > self.daily_limit:
                await self._send_alert("DAILY_COST_LIMIT_EXCEEDED", {
                    "current": daily_cost,
                    "limit": self.daily_limit
                })
        
        if monthly_cost > self.monthly_limit * 0.8:
            logger.warning(f"Approaching monthly cost limit: ${monthly_cost:.2f} / ${self.monthly_limit:.2f}")
            if monthly_cost > self.monthly_limit:
                await self._send_alert("MONTHLY_COST_LIMIT_EXCEEDED", {
                    "current": monthly_cost,
                    "limit": self.monthly_limit
                })
    
    async def get_daily_cost(self) -> float:
        """Get total cost for current day"""
        today = datetime.now().date()
        total = sum(
            m.cost for m in self.current_metrics 
            if m.timestamp.date() == today
        )
        
        # Also check log files
        log_file = self.log_dir / f"usage_{today.strftime('%Y%m%d')}.log"
        if log_file.exists():
            async with aiofiles.open(log_file, 'r') as f:
                async for line in f:
                    try:
                        entry = json.loads(line)
                        total += entry.get("cost", 0.0)
                    except:
                        pass
        
        return total
    
    async def get_monthly_cost(self) -> float:
        """Get total cost for current month"""
        current_month = datetime.now().strftime('%Y%m')
        total = 0.0
        
        # Check all log files for current month
        for log_file in self.log_dir.glob(f"usage_{current_month}*.log"):
            async with aiofiles.open(log_file, 'r') as f:
                async for line in f:
                    try:
                        entry = json.loads(line)
                        total += entry.get("cost", 0.0)
                    except:
                        pass
        
        return total
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        return {
            "services": dict(self.stats),
            "session_total_cost": sum(m.cost for m in self.current_metrics),
            "session_total_tokens": sum(m.tokens for m in self.current_metrics),
            "session_requests": len(self.current_metrics),
            "session_errors": sum(1 for m in self.current_metrics if not m.success)
        }
    
    async def _send_alert(self, alert_type: str, data: Dict[str, Any]):
        """Send alert (webhook, email, etc.)"""
        webhook_url = get_env_var("MONITORING_WEBHOOK_URL", required=False)
        
        if webhook_url:
            # Send to webhook
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "alert_type": alert_type,
                    "timestamp": datetime.now().isoformat(),
                    "data": data
                }
                try:
                    async with session.post(webhook_url, json=payload) as resp:
                        if resp.status != 200:
                            logger.error(f"Failed to send alert: {resp.status}")
                except Exception as e:
                    logger.error(f"Error sending alert: {str(e)}")
        
        # Also log to error file
        error_log = self.log_dir / "alerts.log"
        async with aiofiles.open(error_log, 'a') as f:
            await f.write(f"{datetime.now().isoformat()} - {alert_type}: {json.dumps(data)}\n")


class ErrorMonitor:
    """Monitors and tracks errors"""
    
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Error categories
        self.error_counts = defaultdict(int)
        self.recent_errors: List[Dict[str, Any]] = []
        self.max_recent_errors = 100
    
    async def log_error(self, error: Exception, context: Dict[str, Any]):
        """Log an error with context"""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        }
        
        # Update counts
        self.error_counts[error_data["error_type"]] += 1
        
        # Add to recent errors
        self.recent_errors.append(error_data)
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors.pop(0)
        
        # Write to error log
        error_log = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        async with aiofiles.open(error_log, 'a') as f:
            await f.write(json.dumps(error_data) + '\n')
        
        # Check for critical errors
        if self._is_critical_error(error):
            await self._send_critical_alert(error_data)
    
    def _is_critical_error(self, error: Exception) -> bool:
        """Determine if error is critical"""
        critical_types = [
            "APIConnectionError",
            "RateLimitError",
            "AuthenticationError",
            "ServiceUnavailableError"
        ]
        return type(error).__name__ in critical_types
    
    async def _send_critical_alert(self, error_data: Dict[str, Any]):
        """Send alert for critical errors"""
        logger.critical(f"Critical error: {error_data['error_type']} - {error_data['error_message']}")
        
        # Send to monitoring webhook if configured
        webhook_url = get_env_var("MONITORING_WEBHOOK_URL", required=False)
        if webhook_url:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "alert_type": "CRITICAL_ERROR",
                    "error": error_data
                }
                try:
                    await session.post(webhook_url, json=payload)
                except:
                    pass
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_types": dict(self.error_counts),
            "recent_errors": self.recent_errors[-10:]  # Last 10 errors
        }


class PerformanceMonitor:
    """Monitors system performance metrics"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.percentiles = [50, 95, 99]
    
    def record_latency(self, operation: str, duration_ms: int):
        """Record operation latency"""
        self.metrics[operation].append(duration_ms)
        
        # Keep only recent metrics (last 1000)
        if len(self.metrics[operation]) > 1000:
            self.metrics[operation] = self.metrics[operation][-1000:]
    
    def get_latency_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get latency statistics"""
        if operation:
            data = self.metrics.get(operation, [])
            if not data:
                return {}
            
            return self._calculate_stats(data, operation)
        else:
            # All operations
            stats = {}
            for op, data in self.metrics.items():
                if data:
                    stats[op] = self._calculate_stats(data, op)
            return stats
    
    def _calculate_stats(self, data: List[int], operation: str) -> Dict[str, Any]:
        """Calculate statistics for latency data"""
        import numpy as np
        
        data_array = np.array(data)
        
        return {
            "operation": operation,
            "count": len(data),
            "mean": float(np.mean(data_array)),
            "min": float(np.min(data_array)),
            "max": float(np.max(data_array)),
            "percentiles": {
                f"p{p}": float(np.percentile(data_array, p)) 
                for p in self.percentiles
            }
        }


class MonitoringDashboard:
    """Aggregates all monitoring data for dashboard display"""
    
    def __init__(self, usage_monitor: UsageMonitor, 
                 error_monitor: ErrorMonitor,
                 performance_monitor: PerformanceMonitor):
        
        self.usage_monitor = usage_monitor
        self.error_monitor = error_monitor
        self.performance_monitor = performance_monitor
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all monitoring data for dashboard"""
        return {
            "timestamp": datetime.now().isoformat(),
            "usage": {
                "current_stats": self.usage_monitor.get_current_stats(),
                "daily_cost": await self.usage_monitor.get_daily_cost(),
                "monthly_cost": await self.usage_monitor.get_monthly_cost(),
                "cost_limits": {
                    "daily": self.usage_monitor.daily_limit,
                    "monthly": self.usage_monitor.monthly_limit
                }
            },
            "errors": self.error_monitor.get_error_summary(),
            "performance": self.performance_monitor.get_latency_stats(),
            "health": await self._get_system_health()
        }
    
    async def _get_system_health(self) -> Dict[str, Any]:
        """Determine overall system health"""
        daily_cost = await self.usage_monitor.get_daily_cost()
        error_rate = self._calculate_error_rate()
        
        # Determine health status
        if daily_cost > self.usage_monitor.daily_limit or error_rate > 0.1:
            status = "critical"
        elif daily_cost > self.usage_monitor.daily_limit * 0.8 or error_rate > 0.05:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "error_rate": error_rate,
            "cost_usage_percent": (daily_cost / self.usage_monitor.daily_limit) * 100
        }
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate"""
        stats = self.usage_monitor.get_current_stats()
        total_requests = stats.get("session_requests", 0)
        total_errors = stats.get("session_errors", 0)
        
        if total_requests == 0:
            return 0.0
        
        return total_errors / total_requests


class MonitoringSystem:
    """Main monitoring system that combines all monitors"""
    
    def __init__(self, log_dir: str = "./logs"):
        self.usage_monitor = UsageMonitor(log_dir)
        self.error_monitor = ErrorMonitor(log_dir)
        self.performance_monitor = PerformanceMonitor()
        self.dashboard = MonitoringDashboard(
            self.usage_monitor,
            self.error_monitor,
            self.performance_monitor
        )
    
    async def log_event(self, event_type: str, data: Dict[str, Any]):
        """Log an event to the appropriate monitor"""
        if event_type in ["chat_message", "documents_uploaded", "search_query"]:
            # Usage events
            metric = UsageMetric(
                timestamp=datetime.now(),
                service=data.get("service", "unknown"),
                operation=event_type,
                metadata=data
            )
            await self.usage_monitor.log_usage(metric)
        
        elif event_type.startswith("error_"):
            # Error events
            await self.error_monitor.log_error(
                error_type=event_type,
                error_message=data.get("message", "Unknown error"),
                context=data
            )
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics from all monitors"""
        return await self.dashboard.get_dashboard_data()
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of monitoring system"""
        try:
            status = self.dashboard.get_system_health()
            return {
                "healthy": status["status"] == "healthy",
                "service": "monitoring",
                "status": status
            }
        except Exception as e:
            return {
                "healthy": False,
                "service": "monitoring",
                "error": str(e)
            }
    
    async def get_logs(self, level: Optional[str] = None, 
                      category: Optional[str] = None, 
                      limit: int = 100) -> List[Dict[str, Any]]:
        """Get logs with optional filtering"""
        logs = []
        
        # Read from today's log files
        today = datetime.now().strftime('%Y%m%d')
        
        # Read usage logs
        usage_log = self.usage_monitor.log_dir / f"usage_{today}.log"
        if usage_log.exists():
            async with aiofiles.open(usage_log, 'r') as f:
                async for line in f:
                    try:
                        entry = json.loads(line)
                        log_entry = {
                            "timestamp": entry.get("timestamp"),
                            "level": "INFO",
                            "category": entry.get("service", "USAGE"),
                            "message": f"{entry.get('operation')} - ${entry.get('cost', 0):.2f} ({entry.get('tokens', 0)} tokens)",
                            "data": entry
                        }
                        logs.append(log_entry)
                    except:
                        pass
        
        # Read error logs
        error_log = self.error_monitor.log_dir / f"errors_{today}.log"
        if error_log.exists():
            async with aiofiles.open(error_log, 'r') as f:
                async for line in f:
                    try:
                        entry = json.loads(line)
                        log_entry = {
                            "timestamp": entry.get("timestamp"),
                            "level": "ERROR",
                            "category": "ERROR",
                            "message": f"{entry.get('error_type')} - {entry.get('error_message')}",
                            "data": entry
                        }
                        logs.append(log_entry)
                    except:
                        pass
        
        # Apply filters
        if level:
            logs = [log for log in logs if log.get("level") == level]
        if category:
            logs = [log for log in logs if log.get("category") == category]
        
        # Sort by timestamp descending and limit
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return logs[:limit]
