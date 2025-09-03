"""
Usage and Analytics Routes
Handles usage tracking and analytics endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from core.auth import get_current_user
from core.services.usage_service import get_usage_service

router = APIRouter(prefix="/api/usage", tags=["usage"])
logger = logging.getLogger(__name__)


@router.get("/summary")
async def get_usage_summary(
    days: int = Query(30, ge=1, le=365),
    user_only: bool = Query(False),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get usage summary for a time period
    
    Args:
        days: Number of days to look back
        user_only: If true, only show current user's usage
        current_user: Authenticated user information
        
    Returns:
        Usage summary statistics
    """
    try:
        usage_service = get_usage_service()
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get user ID if filtering by user
        user_id = current_user["user_id"] if user_only else None
        
        summary = usage_service.get_usage_summary(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "success": True,
            "summary": summary,
            "user_id": user_id,
            "days": days
        }
        
    except Exception as e:
        logger.error(f"Error getting usage summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get usage summary: {str(e)}"
        )


@router.get("/quota")
async def get_user_quota(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current user's usage quota and consumption
    
    Args:
        current_user: Authenticated user information
        
    Returns:
        Quota information and current usage
    """
    try:
        usage_service = get_usage_service()
        quota_info = usage_service.get_user_quota(current_user["user_id"])
        
        return {
            "success": True,
            **quota_info
        }
        
    except Exception as e:
        logger.error(f"Error getting user quota: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user quota: {str(e)}"
        )


@router.get("/metrics")
async def get_system_metrics(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get system-wide usage metrics (admin only)
    
    Args:
        current_user: Authenticated user information
        
    Returns:
        System metrics and statistics
    """
    try:
        # TODO: Add admin role check here
        # if not is_admin(current_user):
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        usage_service = get_usage_service()
        metrics = usage_service.get_system_metrics()
        
        return {
            "success": True,
            "metrics": metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting system metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system metrics: {str(e)}"
        )


@router.get("/history")
async def get_usage_history(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get detailed usage history for current user
    
    Args:
        limit: Maximum number of records to return
        offset: Offset for pagination
        current_user: Authenticated user information
        
    Returns:
        Detailed usage history records
    """
    try:
        usage_service = get_usage_service()
        db_service = usage_service.db_service
        
        with db_service.get_client() as client:
            result = client.table("usage_logs") \
                .select("*") \
                .eq("user_id", current_user["user_id"]) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            
            logs = result.data if result.data else []
            
            return {
                "success": True,
                "history": logs,
                "total": len(logs),
                "limit": limit,
                "offset": offset
            }
            
    except Exception as e:
        logger.error(f"Error getting usage history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get usage history: {str(e)}"
        )


@router.post("/track")
async def track_custom_usage(
    operation: str,
    tokens_used: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Track custom usage event
    
    Args:
        operation: Type of operation
        tokens_used: Number of tokens consumed
        metadata: Additional metadata
        current_user: Authenticated user information
        
    Returns:
        Tracking confirmation
    """
    try:
        usage_service = get_usage_service()
        
        # Generate a session ID if not in metadata
        session_id = metadata.get("session_id") if metadata else None
        if not session_id:
            session_id = f"custom_{datetime.utcnow().timestamp()}"
        
        success = usage_service.track_usage(
            user_id=current_user["user_id"],
            session_id=session_id,
            tokens_used=tokens_used,
            operation=operation
        )
        
        if success:
            return {
                "success": True,
                "message": "Usage tracked successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to track usage"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking usage: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track usage: {str(e)}"
        )