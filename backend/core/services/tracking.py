"""
Tracking Service
Centralized usage and analytics tracking
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from core.services.usage_service import get_usage_service

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
        self.usage_service.track_usage(
            user_id=user_id or "anonymous",
            session_id=session_id,
            tokens_used=tokens_used,
            model=model,
            operation="chat"
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
        self.usage_service.track_usage(
            user_id=user_id or "anonymous",
            session_id=f"doc_{file_id}",
            tokens_used=0,
            operation=f"document_{operation}"
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
        self.usage_service.track_usage(
            user_id=user_id or "anonymous",
            session_id=f"api_{method}_{endpoint}_{datetime.now().timestamp()}",
            tokens_used=0,
            operation=f"api_{method}"
        )
    
    def get_usage_summary(self, days: int = 7, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get usage summary"""
        from datetime import timedelta
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        return self.usage_service.get_usage_summary(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
    
    def check_usage_limits(self, user_id: str) -> Dict[str, Any]:
        """Check if usage is within limits"""
        return self.usage_service.get_user_quota(user_id)