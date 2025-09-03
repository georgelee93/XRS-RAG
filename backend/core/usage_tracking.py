"""
Usage Tracking Middleware
Provides decorator and middleware for tracking API usage
"""

import time
import logging
from functools import wraps
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from ..usage_tracker import UsageTracker

logger = logging.getLogger(__name__)


class UsageTrackingService:
    """Centralized usage tracking service"""
    
    def __init__(self):
        self.tracker = UsageTracker()
    
    async def track_chat_usage(
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
        error: Optional[str] = None
    ) -> None:
        """Track chat API usage with all relevant metrics"""
        
        # Prepare metadata
        metadata = {
            "session_id": session_id,
            "user_email": user_email,
            "message_length": len(message),
            "response_length": len(response),
            "duration_seconds": duration,
            "success": error is None
        }
        
        if error:
            metadata["error"] = error
        
        # Track usage
        self.tracker.track_usage(
            user_id=user_id or "anonymous",
            operation="chat",
            tokens_used=tokens_used,
            cost=cost,
            model=model,
            metadata=metadata
        )
        
        logger.info(
            f"Tracked chat usage - User: {user_id or 'anonymous'}, "
            f"Session: {session_id}, Duration: {duration:.2f}s, "
            f"Tokens: {tokens_used}"
        )
    
    async def track_document_usage(
        self,
        user_id: Optional[str],
        user_email: Optional[str],
        operation: str,  # upload, delete, download
        file_id: str,
        filename: str,
        file_size: int,
        duration: float,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """Track document operation usage"""
        
        metadata = {
            "file_id": file_id,
            "filename": filename,
            "file_size_bytes": file_size,
            "user_email": user_email,
            "duration_seconds": duration,
            "success": success
        }
        
        if error:
            metadata["error"] = error
        
        self.tracker.track_usage(
            user_id=user_id or "anonymous",
            operation=f"document_{operation}",
            tokens_used=0,
            cost=0.0,
            model="n/a",
            metadata=metadata
        )
        
        logger.info(
            f"Tracked document {operation} - User: {user_id or 'anonymous'}, "
            f"File: {filename}, Size: {file_size} bytes"
        )


# Global instance
_usage_service: Optional[UsageTrackingService] = None


def get_usage_service() -> UsageTrackingService:
    """Get or create the global usage tracking service"""
    global _usage_service
    if _usage_service is None:
        _usage_service = UsageTrackingService()
    return _usage_service


def track_api_usage(operation: str = "api_call"):
    """
    Decorator for tracking API usage
    
    Usage:
        @track_api_usage(operation="chat")
        async def chat_endpoint(request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            error = None
            result = None
            
            try:
                # Execute the function
                result = await func(*args, **kwargs)
                return result
                
            except Exception as e:
                error = str(e)
                raise
                
            finally:
                # Track usage after execution
                duration = time.time() - start_time
                
                # Extract user info from kwargs if available
                current_user = kwargs.get("current_user")
                user_id = current_user.get("user_id") if current_user else None
                user_email = current_user.get("email") if current_user else None
                
                # Track the usage
                service = get_usage_service()
                await service.tracker.track_usage(
                    user_id=user_id or "anonymous",
                    operation=operation,
                    tokens_used=0,
                    cost=0.0,
                    model="api",
                    metadata={
                        "duration_seconds": duration,
                        "success": error is None,
                        "error": error,
                        "user_email": user_email
                    }
                )
        
        return wrapper
    return decorator


class UsageTrackingMiddleware:
    """
    FastAPI middleware for automatic usage tracking
    
    Usage:
        app.add_middleware(UsageTrackingMiddleware)
    """
    
    def __init__(self, app):
        self.app = app
        self.service = get_usage_service()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        
        # Process the request
        await self.app(scope, receive, send)
        
        # Track usage for API calls
        if scope["path"].startswith("/api/"):
            duration = time.time() - start_time
            
            # Log basic metrics (detailed tracking happens in endpoints)
            logger.debug(
                f"API Request: {scope['method']} {scope['path']} "
                f"Duration: {duration:.3f}s"
            )