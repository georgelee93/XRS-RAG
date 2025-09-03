"""
Chat Interface
Handles chat conversations with the AI assistant
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .openai import OpenAIAssistantManager
from ..storage.supabase import SupabaseClient
from ..session_manager import SessionManager

logger = logging.getLogger(__name__)


class ChatInterface:
    """Manages chat conversations with document context"""
    
    def __init__(self):
        """Initialize chat interface"""
        self.assistant = OpenAIAssistantManager()
        self.supabase = SupabaseClient()
        self.session_manager = SessionManager()
        self.initialized = False
        
        logger.info("Chat Interface initialized")
    
    async def initialize(self) -> None:
        """Initialize all components"""
        if self.initialized:
            return
        
        await self.assistant.initialize()
        self.initialized = True
        logger.info("Chat Interface ready")
    
    async def send_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send message to assistant and get response
        
        Args:
            message: User's message
            session_id: Session ID for conversation continuity
            user_id: User ID (optional)
            metadata: Additional metadata (optional)
        
        Returns:
            Response with message and session info
        """
        await self.initialize()
        
        start_time = datetime.now()
        
        try:
            # Get or create session
            session = await self.session_manager.get_or_create_session(
                session_id, 
                user_id
            )
            session_id = session["session_id"]
            
            # Check if thread exists in OpenAI, create if not
            thread_id = session.get("thread_id")
            if not thread_id or not thread_id.startswith("thread_"):
                # Create actual OpenAI thread
                thread = await self.assistant.create_thread()
                thread_id = thread.id
                
                # Update session with real thread ID
                self.session_manager.update_session(
                    session_id, 
                    {"thread_id": thread_id}
                )
                logger.info(f"Created new OpenAI thread: {thread_id}")
            else:
                # Verify thread exists
                try:
                    # Try to retrieve the thread to verify it exists
                    await self.assistant.client.beta.threads.retrieve(thread_id)
                except Exception as e:
                    logger.warning(f"Thread {thread_id} not found, creating new one")
                    thread = await self.assistant.create_thread()
                    thread_id = thread.id
                    self.session_manager.update_session(
                        session_id,
                        {"thread_id": thread_id}
                    )
            
            logger.info(f"Processing message in session: {session_id}")
            
            # Files are already in the assistant's vector store
            # No need to attach them to individual messages
            file_count = 0
            if self.assistant.file_registry:
                file_count = len(self.assistant.file_registry)
                logger.info(f"Assistant has {file_count} files in vector store")
            
            # Send message without file attachments (files are accessed via vector store)
            response_text = await self.assistant.send_message(
                thread_id=thread_id,
                message=message,
                file_ids=None  # Don't attach files to messages, use vector store instead
            )
            
            # Calculate elapsed time for response
            elapsed_time = (datetime.now() - start_time).total_seconds()
            
            # Save to database if connected
            if self.supabase.is_connected():
                await self._save_conversation(
                    session_id=session_id,
                    user_message=message,
                    assistant_response=response_text,
                    user_id=user_id,
                    metadata=metadata
                )
            
            return {
                "success": True,
                "response": response_text,
                "session_id": session_id,
                "thread_id": thread_id,
                "duration": f"{elapsed_time:.2f}s",
                "duration_seconds": elapsed_time,
                "files_used": file_count,
                "tokens_used": 0,  # TODO: Get from OpenAI response
                "model": "gpt-4-turbo-preview"
            }
            
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    async def _save_conversation(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Save conversation to database"""
        try:
            # Save user message
            await self.supabase.save_chat_message(
                session_id=session_id,
                role="user",
                content=user_message,
                user_id=user_id,
                metadata=metadata
            )
            
            # Save assistant response
            await self.supabase.save_chat_message(
                session_id=session_id,
                role="assistant",
                content=assistant_response,
                user_id=user_id,
                metadata=metadata
            )
            
            logger.info(f"Conversation saved for session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            # Don't raise - we don't want to fail the chat if saving fails
    
    async def get_session_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        try:
            # First try to get from Supabase (our saved messages)
            if self.supabase.is_connected():
                messages = await self.supabase.get_session_messages(session_id, limit)
                if messages:
                    logger.info(f"Retrieved {len(messages)} messages from Supabase for session {session_id}")
                    return [
                        {
                            "role": msg.get("role"),
                            "content": msg.get("content"),
                            "created_at": msg.get("created_at")
                        }
                        for msg in messages
                    ]
            
            # Fallback to OpenAI thread if no Supabase messages
            session = self.session_manager.get_session(session_id)  # Not async
            if not session:
                logger.warning(f"No session found: {session_id}")
                return []
            
            thread_id = session.get("thread_id")
            if not thread_id:
                logger.warning(f"No thread_id in session: {session_id}")
                return []
            
            # Get messages from OpenAI thread
            try:
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
                
                logger.info(f"Retrieved {len(history)} messages from OpenAI for session {session_id}")
                return history
            except Exception as e:
                logger.error(f"Failed to get OpenAI thread messages: {e}")
                return []
            
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []