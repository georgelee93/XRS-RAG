"""
Conversation Service
Centralized orchestration of all chat-related operations
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..assistant.openai import OpenAIAssistantManager
from ..session_manager import SessionManager
from .database import DatabaseService
from .tracking import TrackingService

logger = logging.getLogger(__name__)


class ConversationService:
    """Orchestrates all conversation operations"""
    
    def __init__(self):
        self.assistant = OpenAIAssistantManager()
        self.session_manager = SessionManager()
        self.database = DatabaseService()
        self.tracking = TrackingService()
        self.initialized = False
        
    async def initialize(self) -> None:
        """Initialize all components"""
        if self.initialized:
            return
        
        await self.assistant.initialize()
        self.initialized = True
        logger.info("ConversationService initialized")
    
    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message - single entry point for all chat operations
        
        This method:
        1. Ensures all services are initialized
        2. Creates/retrieves session
        3. Sends message to OpenAI
        4. Saves conversation to database
        5. Tracks usage
        6. Returns unified response
        """
        await self.initialize()
        
        start_time = datetime.now()
        error_message = None
        response_text = ""
        tokens_used = 0
        cost_usd = 0.0
        
        try:
            # Step 1: Get or create session with proper UUID handling
            session = await self._get_or_create_session(session_id, user_id)
            session_id = session["session_id"]
            thread_id = session.get("thread_id")
            
            # Step 2: Ensure OpenAI thread exists
            thread_id = await self._ensure_thread(session_id, thread_id)
            
            logger.info(f"Processing message in session: {session_id}")
            
            # Step 3: Send message to OpenAI
            response_text = await self.assistant.send_message(
                thread_id=thread_id,
                message=message,
                file_ids=None  # Files are in vector store
            )
            
            # Calculate metrics
            elapsed_time = (datetime.now() - start_time).total_seconds()
            
            # Step 4: Save conversation to database (with transaction)
            if self.database.is_connected():
                await self.database.save_conversation(
                    session_id=session_id,
                    user_message=message,
                    assistant_response=response_text,
                    user_id=user_id,
                    user_email=user_email,
                    tokens_used=tokens_used,
                    cost_usd=cost_usd,
                    metadata=metadata
                )
            
            # Step 5: Track usage
            await self.tracking.track_chat(
                user_id=user_id,
                user_email=user_email,
                session_id=session_id,
                message=message,
                response=response_text,
                duration=elapsed_time,
                tokens_used=tokens_used,
                cost=cost_usd,
                success=True
            )
            
            # Step 6: Return unified response
            return {
                "success": True,
                "response": response_text,
                "session_id": session_id,
                "thread_id": thread_id,
                "duration": f"{elapsed_time:.2f}s",
                "duration_seconds": elapsed_time,
                "files_used": len(self.assistant.file_registry) if self.assistant.file_registry else 0,
                "tokens_used": tokens_used,
                "model": "gpt-4-turbo-preview"
            }
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Conversation failed: {error_message}")
            
            # Track failed attempt
            elapsed_time = (datetime.now() - start_time).total_seconds()
            await self.tracking.track_chat(
                user_id=user_id,
                user_email=user_email,
                session_id=session_id if 'session_id' in locals() else None,
                message=message,
                response="",
                duration=elapsed_time,
                success=False,
                error=error_message
            )
            
            return {
                "success": False,
                "error": error_message,
                "session_id": session_id if 'session_id' in locals() else None
            }
    
    async def _get_or_create_session(
        self,
        session_id: Optional[str],
        user_id: Optional[str]
    ) -> Dict[str, Any]:
        """Get or create session with proper UUID handling"""
        try:
            # Use session manager for consistency
            session = await self.session_manager.get_or_create_session(
                session_id, 
                user_id
            )
            return session
        except Exception as e:
            # If session manager fails, use database service directly
            logger.warning(f"Session manager failed, using database service: {e}")
            return await self.database.create_or_get_session(
                session_id=session_id,
                user_id=user_id
            )
    
    async def _ensure_thread(self, session_id: str, thread_id: Optional[str]) -> str:
        """Ensure OpenAI thread exists"""
        if not thread_id or not thread_id.startswith("thread_"):
            # Create new OpenAI thread
            thread = await self.assistant.create_thread()
            thread_id = thread.id
            
            # Update session with thread ID
            self.session_manager.update_session(
                session_id, 
                {"thread_id": thread_id}
            )
            logger.info(f"Created new OpenAI thread: {thread_id}")
        else:
            # Verify thread exists
            try:
                await self.assistant.client.beta.threads.retrieve(thread_id)
            except Exception as e:
                logger.warning(f"Thread {thread_id} not found, creating new one: {e}")
                thread = await self.assistant.create_thread()
                thread_id = thread.id
                self.session_manager.update_session(
                    session_id,
                    {"thread_id": thread_id}
                )
        
        return thread_id
    
    async def get_session_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        try:
            # First try database
            if self.database.is_connected():
                messages = await self.database.get_session_messages(session_id, limit)
                if messages:
                    logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
                    return messages
            
            # Fallback to OpenAI thread
            session = self.session_manager.get_session(session_id)
            if not session:
                logger.warning(f"No session found: {session_id}")
                return []
            
            thread_id = session.get("thread_id")
            if not thread_id:
                return []
            
            # Get messages from OpenAI
            messages = await self.assistant.client.beta.threads.messages.list(
                thread_id=thread_id,
                limit=limit
            )
            
            history = []
            for msg in messages.data:
                content = msg.content[0] if msg.content else None
                if content and hasattr(content, 'text'):
                    history.append({
                        "role": msg.role,
                        "content": content.text.value,
                        "created_at": msg.created_at
                    })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
    
    async def get_usage_stats(
        self,
        days: int = 7,
        check_limits: bool = True
    ) -> Dict[str, Any]:
        """Get usage statistics"""
        stats = {
            "summary": self.tracking.get_usage_summary(days),
            "limits": {}
        }
        
        if check_limits:
            stats["limits"] = self.tracking.check_usage_limits()
        
        return stats


# Singleton instance
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """Get or create the global conversation service"""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service