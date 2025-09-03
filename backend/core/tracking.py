"""
Tracking Service
Centralized usage and analytics tracking
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from ..middleware.usage_tracking import get_usage_service

logger = logging.getLogger(__name__)


class TrackingService:
    """Centralized tracking operations"""
    
    def __init__(self):
        self.usage_service = get_usage_service()
    
    async def track_chat(
        self,
        user_id: Optional[str],
        user_email: Optional[str],
        session_id: str,
        message: str,
        response: str,
        duration: float,
        tokens_used: int = 0,
        cost: float = 0.0,
        model: str = "gpt-4-turbo-preview",
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """Track chat usage"""
        await self.usage_service.track_chat_usage(
            user_id=user_id,
            user_email=user_email,
            session_id=session_id,
            message=message,
            response=response,
            duration=duration,
            tokens_used=tokens_used,
            cost=cost,
            model=model,
            error=error
        )
        
        logger.debug(
            f"Tracked chat - Session: {session_id}, "
            f"Duration: {duration:.2f}s, Tokens: {tokens_used}"
        )
    
    async def track_document(
        self,
        user_id: Optional[str],
        user_email: Optional[str],
        operation: str,
        file_id: str,
        filename: str,
        file_size: int,
        duration: float,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """Track document operation"""
        await self.usage_service.track_document_usage(
            user_id=user_id,
            user_email=user_email,
            operation=operation,
            file_id=file_id,
            filename=filename,
            file_size=file_size,
            duration=duration,
            success=success,
            error=error
        )
        
        logger.debug(
            f"Tracked document {operation} - File: {filename}, "
            f"Size: {file_size} bytes, Duration: {duration:.2f}s"
        )
    
    async def track_api_call(
        self,
        endpoint: str,
        method: str,
        user_id: Optional[str],
        duration: float,
        status_code: int,
        error: Optional[str] = None
    ) -> None:
        """Track generic API call"""
        metadata = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration_seconds": duration
        }
        
        if error:
            metadata["error"] = error
        
        self.usage_service.tracker.log_usage(
            service="api",
            operation=f"{method}_{endpoint}",
            tokens=0,
            cost_usd=0.0,
            duration_ms=int(duration * 1000),
            success=(status_code < 400),
            error_message=error,
            related_id=user_id,
            metadata=metadata
        )
    
    def get_usage_summary(self, days: int = 7, service: Optional[str] = None) -> Dict[str, Any]:
        """Get usage summary"""
        return self.usage_service.tracker.get_usage_summary(days, service)
    
    def check_usage_limits(
        self,
        daily_limit: float = 100.0,
        monthly_limit: float = 3000.0
    ) -> Dict[str, Any]:
        """Check if usage is within limits"""
        return self.usage_service.tracker.check_usage_limits(daily_limit, monthly_limit)