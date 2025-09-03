"""
Asynchronous Logging System
Provides non-blocking logging for improved performance
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class AsyncLogger:
    """Asynchronous logger that doesn't block main execution"""
    
    def __init__(self, log_dir: str = "logs"):
        """Initialize async logger"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.queue = asyncio.Queue()
        self.worker_task = None
        
    async def start(self):
        """Start the background logging worker"""
        if not self.worker_task:
            self.worker_task = asyncio.create_task(self._worker())
            logger.info("Async logging worker started")
    
    async def stop(self):
        """Stop the background logging worker"""
        if self.worker_task:
            await self.queue.put(None)  # Sentinel to stop worker
            await self.worker_task
            self.worker_task = None
            logger.info("Async logging worker stopped")
    
    async def _worker(self):
        """Background worker that processes log entries"""
        while True:
            try:
                entry = await self.queue.get()
                
                if entry is None:  # Sentinel value to stop
                    break
                
                # Process the log entry
                await self._write_log_entry(entry)
                
            except Exception as e:
                logger.error(f"Error in async logging worker: {e}")
    
    async def _write_log_entry(self, entry: Dict[str, Any]):
        """Write a log entry to file"""
        try:
            # Determine log file based on entry type
            log_type = entry.get("type", "general")
            date_str = datetime.now().strftime("%Y%m%d")
            log_file = self.log_dir / f"{log_type}_{date_str}.log"
            
            # Format the entry
            timestamp = entry.get("timestamp", datetime.now().isoformat())
            log_line = json.dumps({
                "timestamp": timestamp,
                **entry
            })
            
            # Write to file asynchronously
            async with asyncio.Lock():  # Ensure thread-safe file access
                with open(log_file, "a") as f:
                    f.write(log_line + "\n")
                    
        except Exception as e:
            logger.error(f"Failed to write log entry: {e}")
    
    async def log(self, entry_type: str, data: Dict[str, Any]):
        """Add a log entry to the queue (non-blocking)"""
        entry = {
            "type": entry_type,
            "timestamp": datetime.now().isoformat(),
            **data
        }
        
        # Add to queue without waiting
        try:
            self.queue.put_nowait(entry)
        except asyncio.QueueFull:
            logger.warning("Async logging queue full, dropping entry")
    
    def log_nowait(self, entry_type: str, data: Dict[str, Any]):
        """Log without awaiting (fire and forget)"""
        asyncio.create_task(self.log(entry_type, data))


class AsyncMonitoringSystem:
    """Enhanced monitoring with async logging"""
    
    def __init__(self):
        """Initialize async monitoring"""
        self.async_logger = AsyncLogger()
        self.metrics = {}
        self.started = False
    
    async def start(self):
        """Start the monitoring system"""
        if not self.started:
            await self.async_logger.start()
            self.started = True
            logger.info("Async monitoring system started")
    
    async def stop(self):
        """Stop the monitoring system"""
        if self.started:
            await self.async_logger.stop()
            self.started = False
            logger.info("Async monitoring system stopped")
    
    async def log_event_async(self, event_type: str, data: Dict[str, Any]):
        """Log an event asynchronously"""
        if not self.started:
            await self.start()
        
        await self.async_logger.log(event_type, data)
    
    def log_event_nowait(self, event_type: str, data: Dict[str, Any]):
        """Log an event without waiting (fire and forget)"""
        asyncio.create_task(self.log_event_async(event_type, data))
    
    async def log_api_call(self, 
                          service: str,
                          endpoint: str,
                          duration_ms: float,
                          success: bool,
                          metadata: Optional[Dict] = None):
        """Log API call metrics"""
        await self.log_event_async("api_call", {
            "service": service,
            "endpoint": endpoint,
            "duration_ms": duration_ms,
            "success": success,
            "metadata": metadata or {}
        })
    
    async def log_chat_metrics(self,
                              session_id: str,
                              message_length: int,
                              response_length: int,
                              total_time_ms: float,
                              api_calls: Dict[str, float]):
        """Log detailed chat metrics"""
        await self.log_event_async("chat_metrics", {
            "session_id": session_id,
            "message_length": message_length,
            "response_length": response_length,
            "total_time_ms": total_time_ms,
            "api_breakdown": api_calls
        })
    
    async def log_performance(self,
                            operation: str,
                            duration_ms: float,
                            metadata: Optional[Dict] = None):
        """Log performance metrics"""
        await self.log_event_async("performance", {
            "operation": operation,
            "duration_ms": duration_ms,
            "metadata": metadata or {}
        })
    
    def track_metric(self, metric_name: str, value: float):
        """Track a metric value (in-memory)"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        self.metrics[metric_name].append({
            "value": value,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 1000 entries per metric
        if len(self.metrics[metric_name]) > 1000:
            self.metrics[metric_name] = self.metrics[metric_name][-1000:]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of tracked metrics"""
        summary = {}
        
        for metric_name, values in self.metrics.items():
            if values:
                metric_values = [v["value"] for v in values]
                summary[metric_name] = {
                    "count": len(metric_values),
                    "min": min(metric_values),
                    "max": max(metric_values),
                    "avg": sum(metric_values) / len(metric_values),
                    "latest": metric_values[-1]
                }
        
        return summary


# Global instance
_async_monitoring = None

def get_async_monitoring() -> AsyncMonitoringSystem:
    """Get or create async monitoring instance"""
    global _async_monitoring
    if _async_monitoring is None:
        _async_monitoring = AsyncMonitoringSystem()
    return _async_monitoring