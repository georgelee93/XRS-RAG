"""
Database Service
Centralized database operations with transaction support
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager
from datetime import datetime

from ..storage.supabase import SupabaseClient
from ..timezone_utils import now_kst_iso

logger = logging.getLogger(__name__)


class DatabaseService:
    """Centralized database operations"""
    
    def __init__(self):
        self.supabase = SupabaseClient()
        self._transaction_data = []
        
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.supabase.is_connected()
    
    def _ensure_uuid(self, value: Optional[Union[str, uuid.UUID]]) -> Optional[str]:
        """Convert value to UUID string format"""
        if not value:
            return None
        
        if isinstance(value, uuid.UUID):
            return str(value)
        
        try:
            return str(uuid.UUID(value))
        except (ValueError, AttributeError):
            if isinstance(value, str):
                return str(uuid.uuid5(uuid.NAMESPACE_DNS, value))
            return None
    
    @asynccontextmanager
    async def transaction(self):
        """Transaction context manager"""
        self._transaction_data = []
        try:
            yield self
            await self._commit_transaction()
        except Exception as e:
            await self._rollback_transaction()
            raise e
        finally:
            self._transaction_data = []
    
    async def _commit_transaction(self):
        """Commit all transaction operations"""
        for operation in self._transaction_data:
            await operation()
        self._transaction_data = []
    
    async def _rollback_transaction(self):
        """Rollback transaction (clear pending operations)"""
        logger.warning(f"Rolling back {len(self._transaction_data)} operations")
        self._transaction_data = []
    
    async def create_or_get_session(
        self,
        session_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        in_transaction: bool = False
    ) -> Dict[str, Any]:
        """Create or retrieve a chat session"""
        session_uuid = self._ensure_uuid(session_id) if session_id else str(uuid.uuid4())
        user_uuid = self._ensure_uuid(user_id) if user_id else None
        
        async def _execute():
            return await self.supabase.create_or_get_session(
                session_id=session_uuid,
                thread_id=thread_id,
                user_id=user_uuid
            )
        
        if in_transaction:
            self._transaction_data.append(_execute)
            return {"session_id": session_uuid, "thread_id": thread_id}
        else:
            return await _execute()
    
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        in_transaction: bool = False
    ) -> Dict[str, Any]:
        """Save a chat message"""
        session_uuid = self._ensure_uuid(session_id)
        user_uuid = self._ensure_uuid(user_id) if user_id else None
        
        async def _execute():
            return await self.supabase.save_chat_message(
                session_id=session_uuid,
                role=role,
                content=content,
                user_id=user_uuid,
                user_email=user_email,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                metadata=metadata
            )
        
        if in_transaction:
            self._transaction_data.append(_execute)
            return {"message_id": str(uuid.uuid4()), "status": "pending"}
        else:
            return await _execute()
    
    async def save_conversation(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save a complete conversation (user + assistant messages)"""
        try:
            async with self.transaction():
                await self.save_message(
                    session_id=session_id,
                    role="user",
                    content=user_message,
                    user_id=user_id,
                    user_email=user_email,
                    metadata=metadata,
                    in_transaction=True
                )
                
                await self.save_message(
                    session_id=session_id,
                    role="assistant",
                    content=assistant_response,
                    user_id=user_id,
                    user_email=user_email,
                    tokens_used=tokens_used,
                    cost_usd=cost_usd,
                    metadata=metadata,
                    in_transaction=True
                )
            
            logger.info(f"Conversation saved for session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            return False
    
    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get messages for a session"""
        session_uuid = self._ensure_uuid(session_id)
        return await self.supabase.get_session_messages(session_uuid, limit)
    
    async def log_usage(
        self,
        service: str,
        operation: str,
        tokens: int = 0,
        cost_usd: float = 0.0,
        duration_ms: int = 0,
        success: bool = True,
        error_message: Optional[str] = None,
        related_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        in_transaction: bool = False
    ) -> None:
        """Log usage data"""
        from ..usage_tracker import get_usage_tracker
        tracker = get_usage_tracker()
        
        async def _execute():
            tracker.log_usage(
                service=service,
                operation=operation,
                tokens=tokens,
                cost_usd=cost_usd,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
                related_id=related_id,
                metadata=metadata
            )
        
        if in_transaction:
            self._transaction_data.append(_execute)
        else:
            await _execute()
    
    async def create_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create document record"""
        return await self.supabase.create_document(document_data)
    
    async def list_documents(self, status: str = "active") -> List[Dict[str, Any]]:
        """List documents"""
        return await self.supabase.list_documents(status)
    
    async def update_document(self, doc_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update document"""
        return await self.supabase.update_document(doc_id, updates)
    
    async def get_document_by_openai_id(self, openai_file_id: str) -> Optional[Dict[str, Any]]:
        """Get document by OpenAI file ID"""
        return await self.supabase.get_document_by_openai_id(openai_file_id)