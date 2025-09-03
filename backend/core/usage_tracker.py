"""
Usage Tracker for API Calls and Cost Management
Tracks all API usage for monitoring and billing
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time

from .supabase_client import get_supabase_manager

logger = logging.getLogger(__name__)


class UsageTracker:
    """Tracks API usage and costs"""
    
    # Cost per 1K tokens (as of 2024)
    PRICING = {
        "gpt-4-1106-preview": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
        "text-embedding-ada-002": {"input": 0.0001, "output": 0.0},
        "assistant": {"input": 0.01, "output": 0.03}  # Assistant API pricing
    }
    
    def __init__(self):
        self.supabase = get_supabase_manager()
        self._pending_logs = []  # Buffer for batch inserts
        self._last_flush = time.time()
    
    def log_usage(self, service: str, operation: str, 
                  tokens: int = 0, cost_usd: float = 0.0,
                  duration_ms: int = 0, success: bool = True,
                  error_message: Optional[str] = None,
                  related_id: Optional[str] = None,
                  metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log API usage"""
        try:
            usage_data = {
                "service": service,
                "operation": operation,
                "related_id": related_id,
                "tokens": tokens,
                "cost_usd": cost_usd,
                "duration_ms": duration_ms,
                "success": success,
                "error_message": error_message,
                "metadata": metadata or {}
            }
            
            # Add to buffer
            self._pending_logs.append(usage_data)
            
            # Flush if buffer is full or time elapsed
            if len(self._pending_logs) >= 10 or (time.time() - self._last_flush) > 60:
                self._flush_logs()
            
        except Exception as e:
            logger.error(f"Error logging usage: {str(e)}")
    
    def _flush_logs(self):
        """Flush pending logs to database"""
        if not self._pending_logs:
            return
        
        try:
            result = self.supabase.client.table("usage_logs").insert(
                self._pending_logs
            ).execute()
            
            logger.info(f"Flushed {len(self._pending_logs)} usage logs")
            self._pending_logs = []
            self._last_flush = time.time()
            
        except Exception as e:
            logger.error(f"Error flushing usage logs: {str(e)}")
    
    def track_openai_completion(self, model: str, usage_data: Dict[str, int],
                              operation: str = "chat", 
                              related_id: Optional[str] = None,
                              duration_ms: int = 0) -> None:
        """Track OpenAI completion usage"""
        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        total_tokens = usage_data.get("total_tokens", prompt_tokens + completion_tokens)
        
        # Calculate cost
        pricing = self.PRICING.get(model, self.PRICING["gpt-3.5-turbo"])
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        self.log_usage(
            service="openai",
            operation=operation,
            tokens=total_tokens,
            cost_usd=total_cost,
            duration_ms=duration_ms,
            success=True,
            related_id=related_id,
            metadata={
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens
            }
        )
    
    def track_assistant_usage(self, thread_id: str, run_id: str,
                            tokens: int = 0, duration_ms: int = 0) -> None:
        """Track OpenAI Assistant API usage"""
        # Assistant API pricing is estimated
        cost = (tokens / 1000) * self.PRICING["assistant"]["input"]
        
        self.log_usage(
            service="openai",
            operation="assistant",
            tokens=tokens,
            cost_usd=cost,
            duration_ms=duration_ms,
            success=True,
            related_id=thread_id,
            metadata={
                "run_id": run_id,
                "thread_id": thread_id
            }
        )
    
    def track_document_upload(self, doc_id: str, file_size: int,
                            duration_ms: int = 0, success: bool = True,
                            error: Optional[str] = None) -> None:
        """Track document upload operation"""
        self.log_usage(
            service="openai",
            operation="upload",
            tokens=0,
            cost_usd=0.0,  # File uploads are typically free
            duration_ms=duration_ms,
            success=success,
            error_message=error,
            related_id=doc_id,
            metadata={
                "file_size": file_size
            }
        )
    
    def track_supabase_operation(self, operation: str, table: str,
                               duration_ms: int = 0, success: bool = True,
                               error: Optional[str] = None) -> None:
        """Track Supabase database operation"""
        self.log_usage(
            service="supabase",
            operation=operation,
            tokens=0,
            cost_usd=0.0,  # Supabase has different pricing model
            duration_ms=duration_ms,
            success=success,
            error_message=error,
            metadata={
                "table": table
            }
        )
    
    def get_usage_summary(self, days: int = 7, 
                         service: Optional[str] = None) -> Dict[str, Any]:
        """Get usage summary for specified period"""
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Query usage logs
            query = self.supabase.client.table("usage_logs").select("*").gte(
                "created_at", start_date.isoformat()
            )
            
            if service:
                query = query.eq("service", service)
            
            result = query.execute()
            logs = result.data
            
            # Calculate summary
            total_tokens = sum(log.get("tokens", 0) for log in logs)
            total_cost = sum(log.get("cost_usd", 0) for log in logs)
            total_operations = len(logs)
            success_count = sum(1 for log in logs if log.get("success", True))
            error_count = total_operations - success_count
            
            # Group by service and operation
            by_service = {}
            for log in logs:
                svc = log["service"]
                op = log["operation"]
                
                if svc not in by_service:
                    by_service[svc] = {}
                
                if op not in by_service[svc]:
                    by_service[svc][op] = {
                        "count": 0,
                        "tokens": 0,
                        "cost": 0,
                        "errors": 0
                    }
                
                by_service[svc][op]["count"] += 1
                by_service[svc][op]["tokens"] += log.get("tokens", 0)
                by_service[svc][op]["cost"] += log.get("cost_usd", 0)
                if not log.get("success", True):
                    by_service[svc][op]["errors"] += 1
            
            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": days
                },
                "summary": {
                    "total_operations": total_operations,
                    "total_tokens": total_tokens,
                    "total_cost_usd": total_cost,
                    "success_count": success_count,
                    "error_count": error_count,
                    "success_rate": success_count / total_operations if total_operations > 0 else 0
                },
                "by_service": by_service
            }
            
        except Exception as e:
            logger.error(f"Error getting usage summary: {str(e)}")
            return {}
    
    def get_daily_usage(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily usage statistics"""
        try:
            # Use the daily_usage_summary view
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            result = self.supabase.client.table("daily_usage_summary").select("*").gte(
                "date", start_date.date().isoformat()
            ).order("date", desc=True).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting daily usage: {str(e)}")
            return []
    
    def check_usage_limits(self, daily_limit: float = 100.0,
                          monthly_limit: float = 3000.0) -> Dict[str, Any]:
        """Check if usage is within limits"""
        try:
            # Get today's usage
            today_summary = self.get_usage_summary(days=1)
            today_cost = today_summary.get("summary", {}).get("total_cost_usd", 0)
            
            # Get this month's usage
            month_summary = self.get_usage_summary(days=30)
            month_cost = month_summary.get("summary", {}).get("total_cost_usd", 0)
            
            return {
                "daily": {
                    "used": today_cost,
                    "limit": daily_limit,
                    "percentage": (today_cost / daily_limit * 100) if daily_limit > 0 else 0,
                    "exceeded": today_cost > daily_limit
                },
                "monthly": {
                    "used": month_cost,
                    "limit": monthly_limit,
                    "percentage": (month_cost / monthly_limit * 100) if monthly_limit > 0 else 0,
                    "exceeded": month_cost > monthly_limit
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking usage limits: {str(e)}")
            return {}
    
    def __del__(self):
        """Flush pending logs on cleanup"""
        self._flush_logs()


# Global usage tracker instance
_usage_tracker: Optional[UsageTracker] = None


def get_usage_tracker() -> UsageTracker:
    """Get or create the global usage tracker"""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker