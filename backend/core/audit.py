"""
Audit logging service for tracking user activities and system events
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging
from fastapi import Request

from .supabase_client import get_supabase_manager

logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self):
        self.supabase = get_supabase_manager()
    
    async def log_action(
        self,
        user_id: Optional[str],
        user_email: Optional[str],
        action_type: str,
        action_details: Dict[str, Any],
        request: Optional[Request] = None
    ):
        """Log user action to audit trail"""
        try:
            audit_data = {
                "user_id": user_id,
                "user_email": user_email,
                "action_type": action_type,
                "action_details": action_details,
                "created_at": datetime.now().isoformat()
            }
            
            # Add request metadata if available
            if request:
                audit_data["ip_address"] = request.client.host if request.client else None
                audit_data["user_agent"] = request.headers.get("user-agent")
            
            result = self.supabase.client.table("audit_logs").insert(audit_data).execute()
            
            logger.info(f"Audit log created: {action_type} by {user_email or 'anonymous'}")
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
    
    async def log_chat_message(
        self,
        session_id: str,
        user_id: Optional[str],
        user_email: Optional[str],
        message: str,
        response: str,
        tokens_used: int = 0,
        cost: float = 0.0
    ):
        """Log chat interaction with full details"""
        await self.log_action(
            user_id=user_id,
            user_email=user_email,
            action_type="chat_message",
            action_details={
                "session_id": session_id,
                "message_preview": message[:100],
                "response_preview": response[:100],
                "tokens_used": tokens_used,
                "cost_usd": cost,
                "message_length": len(message),
                "response_length": len(response)
            }
        )
    
    async def log_document_upload(
        self,
        user_id: str,
        user_email: str,
        document_id: str,
        filename: str,
        size_bytes: int,
        content_type: str
    ):
        """Log document upload"""
        await self.log_action(
            user_id=user_id,
            user_email=user_email,
            action_type="document_upload",
            action_details={
                "document_id": document_id,
                "filename": filename,
                "size_bytes": size_bytes,
                "content_type": content_type,
                "size_mb": round(size_bytes / 1024 / 1024, 2)
            }
        )
    
    async def log_document_access(
        self,
        document_id: str,
        user_id: Optional[str],
        user_email: Optional[str],
        action: str  # 'view', 'download', 'chat_reference'
    ):
        """Log document access"""
        try:
            # Log to document_access_logs
            access_data = {
                "document_id": document_id,
                "user_id": user_id,
                "user_email": user_email,
                "action": action,
                "accessed_at": datetime.now().isoformat()
            }
            
            self.supabase.client.table("document_access_logs").insert(access_data).execute()
            
            # Update document stats
            self.supabase.client.rpc(
                "increment_document_access",
                {"doc_id": document_id}
            ).execute()
            
        except Exception as e:
            logger.error(f"Failed to log document access: {str(e)}")
    
    async def log_bigquery_query(
        self,
        user_id: str,
        user_email: str,
        natural_language_query: str,
        generated_sql: str,
        rows_returned: int,
        execution_time_ms: int,
        success: bool,
        error: Optional[str] = None
    ):
        """Log BigQuery query execution"""
        await self.log_action(
            user_id=user_id,
            user_email=user_email,
            action_type="bigquery_query",
            action_details={
                "natural_language_query": natural_language_query,
                "generated_sql": generated_sql,
                "rows_returned": rows_returned,
                "execution_time_ms": execution_time_ms,
                "success": success,
                "error": error
            }
        )
    
    async def log_document_delete(
        self,
        user_id: str,
        user_email: str,
        document_id: str,
        filename: str
    ):
        """Log document deletion"""
        await self.log_action(
            user_id=user_id,
            user_email=user_email,
            action_type="document_delete",
            action_details={
                "document_id": document_id,
                "filename": filename
            }
        )
    
    async def log_login(
        self,
        user_id: str,
        user_email: str,
        success: bool,
        request: Optional[Request] = None
    ):
        """Log login attempt"""
        await self.log_action(
            user_id=user_id if success else None,
            user_email=user_email,
            action_type="login_attempt",
            action_details={
                "success": success,
                "timestamp": datetime.now().isoformat()
            },
            request=request
        )
    
    async def log_admin_action(
        self,
        admin_id: str,
        admin_email: str,
        action: str,
        details: Dict[str, Any],
        request: Optional[Request] = None
    ):
        """Log admin action to audit trail"""
        await self.log_action(
            user_id=admin_id,
            user_email=admin_email,
            action_type=f"admin_{action}",
            action_details=details,
            request=request
        )
    
    async def get_user_activity_summary(self, user_id: str) -> Dict[str, Any]:
        """Get activity summary for a user"""
        try:
            # Get chat stats
            chat_stats = self.supabase.client.table("audit_logs").select(
                "created_at, action_details"
            ).eq("user_id", user_id).eq("action_type", "chat_message").execute()
            
            # Get document stats
            doc_stats = self.supabase.client.table("audit_logs").select(
                "created_at, action_details"
            ).eq("user_id", user_id).eq("action_type", "document_upload").execute()
            
            # Calculate totals
            total_messages = len(chat_stats.data) if chat_stats.data else 0
            total_tokens = sum(
                log.get("action_details", {}).get("tokens_used", 0) 
                for log in (chat_stats.data or [])
            )
            total_cost = sum(
                log.get("action_details", {}).get("cost_usd", 0) 
                for log in (chat_stats.data or [])
            )
            
            return {
                "total_messages": total_messages,
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 2),
                "documents_uploaded": len(doc_stats.data) if doc_stats.data else 0,
                "last_activity": max(
                    [log["created_at"] for log in (chat_stats.data or []) + (doc_stats.data or [])],
                    default=None
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to get user activity: {str(e)}")
            return {}
    
    async def get_recent_activity(self, limit: int = 50) -> list:
        """Get recent activity across all users (admin only)"""
        try:
            result = self.supabase.client.table("audit_logs").select(
                "*"
            ).order("created_at", desc=True).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to get recent activity: {str(e)}")
            return []

# Initialize audit service
# Lazy initialization
_audit_service = None

def get_audit_service():
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service

# For backward compatibility
audit_service = get_audit_service()