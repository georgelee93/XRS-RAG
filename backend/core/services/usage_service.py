"""
Usage and Analytics Service
Handles usage tracking and analytics for the RAG chatbot
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from core.config import get_settings
from core.services.database_service import get_database_service

logger = logging.getLogger(__name__)


class UsageService:
    """Service for tracking and analyzing usage metrics"""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize usage service"""
        if self._initialized:
            return
        
        self.settings = get_settings()
        self.db_service = get_database_service()
        self._initialized = True
    
    def track_usage(
        self,
        user_id: str,
        session_id: str,
        tokens_used: int,
        model: str = "gpt-4",
        operation: str = "chat"
    ) -> bool:
        """
        Track usage for a specific operation
        
        Args:
            user_id: ID of the user
            session_id: Session identifier
            tokens_used: Number of tokens consumed
            model: Model used
            operation: Type of operation (chat, document, etc.)
            
        Returns:
            Success status
        """
        try:
            with self.db_service.get_client() as client:
                result = client.table("usage_logs").insert({
                    "user_id": user_id,
                    "session_id": session_id,
                    "tokens_used": tokens_used,
                    "model": model,
                    "operation": operation,
                    "created_at": datetime.utcnow().isoformat()
                }).execute()
                
                return bool(result.data)
                
        except Exception as e:
            logger.error(f"Error tracking usage: {str(e)}")
            return False
    
    def get_usage_summary(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get usage summary statistics
        
        Args:
            user_id: Optional user ID to filter by
            start_date: Start date for the period
            end_date: End date for the period
            
        Returns:
            Usage summary statistics
        """
        try:
            with self.db_service.get_client() as client:
                query = client.table("usage_logs").select("*")
                
                # Apply filters
                if user_id:
                    query = query.eq("user_id", user_id)
                
                if start_date:
                    query = query.gte("created_at", start_date.isoformat())
                
                if end_date:
                    query = query.lte("created_at", end_date.isoformat())
                
                result = query.execute()
                logs = result.data if result.data else []
                
                # Calculate summary
                total_tokens = sum(log.get("tokens_used", 0) for log in logs)
                total_sessions = len(set(log.get("session_id") for log in logs))
                total_operations = len(logs)
                
                # Group by model
                model_usage = {}
                for log in logs:
                    model = log.get("model", "unknown")
                    model_usage[model] = model_usage.get(model, 0) + log.get("tokens_used", 0)
                
                # Group by operation
                operation_counts = {}
                for log in logs:
                    operation = log.get("operation", "unknown")
                    operation_counts[operation] = operation_counts.get(operation, 0) + 1
                
                return {
                    "total_tokens": total_tokens,
                    "total_sessions": total_sessions,
                    "total_operations": total_operations,
                    "model_usage": model_usage,
                    "operation_counts": operation_counts,
                    "period": {
                        "start": start_date.isoformat() if start_date else None,
                        "end": end_date.isoformat() if end_date else None
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting usage summary: {str(e)}")
            return {
                "error": str(e),
                "total_tokens": 0,
                "total_sessions": 0,
                "total_operations": 0,
                "model_usage": {},
                "operation_counts": {}
            }
    
    def get_user_quota(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's usage quota and current usage
        
        Args:
            user_id: User identifier
            
        Returns:
            Quota information and current usage
        """
        try:
            # Get current month's usage
            now = datetime.utcnow()
            start_of_month = datetime(now.year, now.month, 1)
            
            summary = self.get_usage_summary(
                user_id=user_id,
                start_date=start_of_month,
                end_date=now
            )
            
            # Get user's quota from settings or database
            # For now, using default quotas
            default_quota = {
                "monthly_tokens": 1000000,  # 1M tokens per month
                "daily_operations": 1000,    # 1000 operations per day
                "max_file_size": 10 * 1024 * 1024,  # 10MB
                "max_files": 100
            }
            
            # Calculate remaining quota
            remaining_tokens = default_quota["monthly_tokens"] - summary["total_tokens"]
            
            # Get today's operations
            start_of_day = datetime(now.year, now.month, now.day)
            today_summary = self.get_usage_summary(
                user_id=user_id,
                start_date=start_of_day,
                end_date=now
            )
            
            remaining_operations = default_quota["daily_operations"] - today_summary["total_operations"]
            
            return {
                "quota": default_quota,
                "usage": {
                    "monthly_tokens": summary["total_tokens"],
                    "daily_operations": today_summary["total_operations"]
                },
                "remaining": {
                    "tokens": max(0, remaining_tokens),
                    "operations": max(0, remaining_operations)
                },
                "period": {
                    "month": now.strftime("%Y-%m"),
                    "day": now.strftime("%Y-%m-%d")
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting user quota: {str(e)}")
            return {
                "error": str(e),
                "quota": {},
                "usage": {},
                "remaining": {}
            }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system-wide usage metrics
        
        Returns:
            System metrics and statistics
        """
        try:
            with self.db_service.get_client() as client:
                # Get total users
                users_result = client.table("users").select("id", count="exact").execute()
                total_users = users_result.count if hasattr(users_result, 'count') else 0
                
                # Get total documents
                docs_result = client.table("documents").select("id", count="exact").execute()
                total_documents = docs_result.count if hasattr(docs_result, 'count') else 0
                
                # Get total sessions
                sessions_result = client.table("sessions").select("id", count="exact").execute()
                total_sessions = sessions_result.count if hasattr(sessions_result, 'count') else 0
                
                # Get recent activity (last 24 hours)
                yesterday = datetime.utcnow() - timedelta(days=1)
                recent_summary = self.get_usage_summary(
                    start_date=yesterday,
                    end_date=datetime.utcnow()
                )
                
                return {
                    "users": {
                        "total": total_users,
                        "active_today": len(set(
                            log.get("user_id") for log in 
                            recent_summary.get("logs", [])
                        ))
                    },
                    "documents": {
                        "total": total_documents
                    },
                    "sessions": {
                        "total": total_sessions,
                        "active_today": recent_summary.get("total_sessions", 0)
                    },
                    "usage": {
                        "tokens_24h": recent_summary.get("total_tokens", 0),
                        "operations_24h": recent_summary.get("total_operations", 0)
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {
                "error": str(e),
                "users": {"total": 0, "active_today": 0},
                "documents": {"total": 0},
                "sessions": {"total": 0, "active_today": 0},
                "usage": {"tokens_24h": 0, "operations_24h": 0},
                "timestamp": datetime.utcnow().isoformat()
            }


# Singleton instance getter
def get_usage_service() -> UsageService:
    """Get or create usage service instance"""
    return UsageService()