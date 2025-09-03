"""
Session Manager for Chat Persistence
Handles creating, updating, and retrieving chat sessions
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from .supabase_client import get_supabase_manager

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages chat sessions and message history"""
    
    def __init__(self):
        self.supabase = get_supabase_manager()
        self._active_sessions = {}  # Cache for active sessions
    
    def create_session(self, user_id: Optional[str] = None, 
                           thread_id: Optional[str] = None,
                           title: Optional[str] = None) -> Dict[str, Any]:
        """Create a new chat session"""
        try:
            session_data = {
                "user_id": user_id,
                "thread_id": thread_id,
                "session_title": title or "New Chat",
                "metadata": {
                    "created_from": "web_app",
                    "client_info": {}
                }
            }
            
            # Create session in database
            result = self.supabase.client.table("chat_sessions").insert(session_data).execute()
            session = result.data[0]
            
            # Cache the session
            self._active_sessions[session["session_id"]] = session
            
            logger.info(f"Created new session: {session['session_id']}")
            return session
            
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID"""
        # Check cache first
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]
        
        try:
            result = self.supabase.client.table("chat_sessions").select("*").eq(
                "session_id", session_id
            ).execute()
            
            if result.data:
                session = result.data[0]
                self._active_sessions[session_id] = session
                return session
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            return None
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update session information"""
        try:
            # Don't update these fields directly
            updates.pop("session_id", None)
            updates.pop("created_at", None)
            
            result = self.supabase.client.table("chat_sessions").update(
                updates
            ).eq("session_id", session_id).execute()
            
            if result.data:
                session = result.data[0]
                self._active_sessions[session_id] = session
                return session
            
            raise ValueError(f"Session {session_id} not found")
            
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            raise
    
    def add_message(self, session_id: str, role: str, content: str,
                         tokens_used: int = 0, cost_usd: float = 0.0,
                         metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add a message to the chat history"""
        try:
            # Get the actual UUID id for this session_id
            session = self.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # Use the UUID id field, not the text session_id field
            actual_id = session["id"]
            
            message_data = {
                "session_id": actual_id,  # Use the UUID id for foreign key
                "role": role,
                "content": content,
                "tokens_used": tokens_used,
                "cost_usd": cost_usd,
                "metadata": metadata or {}
            }
            
            result = self.supabase.client.table("chat_messages").insert(
                message_data
            ).execute()
            
            # Update session's last_message_at
            self.update_session(session_id, {
                "last_message_at": datetime.now().isoformat()
            })
            
            # Update session title if it's the first user message
            if role == "user":
                self._maybe_update_session_title(session_id, content)
            
            return result.data[0]
            
        except Exception as e:
            logger.error(f"Error adding message: {str(e)}")
            raise
    
    def get_messages(self, session_id: str, limit: int = 50,
                          offset: int = 0) -> List[Dict[str, Any]]:
        """Get chat messages for a session"""
        try:
            # Get the actual UUID id for this session_id
            session = self.get_session(session_id)
            if not session:
                return []
            
            # Use the UUID id field, not the text session_id field
            actual_id = session["id"]
            
            result = self.supabase.client.table("chat_messages").select("*").eq(
                "session_id", actual_id  # Use the UUID id for foreign key
            ).order("created_at", desc=False).range(offset, offset + limit - 1).execute()
            
            # Filter out file reference information from user-facing response
            messages = []
            for msg in result.data:
                msg_copy = msg.copy()
                if "metadata" in msg_copy and msg_copy["metadata"]:
                    # Remove annotations that contain file citations from user response
                    if "annotations" in msg_copy["metadata"]:
                        msg_copy["metadata"].pop("annotations", None)
                messages.append(msg_copy)
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages: {str(e)}")
            return []
    
    def list_sessions(self, user_id: Optional[str] = None,
                          limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """List chat sessions with summary info"""
        try:
            # Use the view that includes message counts
            query = self.supabase.client.table("chat_sessions_summary").select("*")
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            result = query.order("created_at", desc=True).range(
                offset, offset + limit - 1
            ).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error listing sessions: {str(e)}")
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages"""
        try:
            # Messages will be cascade deleted due to foreign key constraint
            result = self.supabase.client.table("chat_sessions").delete().eq(
                "session_id", session_id
            ).execute()
            
            # Remove from cache
            self._active_sessions.pop(session_id, None)
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            return False
    
    def _maybe_update_session_title(self, session_id: str, first_message: str):
        """Update session title based on first user message"""
        try:
            # Check if this session already has a custom title
            session = self.get_session(session_id)
            if not session or session.get("session_title") != "New Chat":
                return
            
            # Generate title from first message (truncate to 50 chars)
            title = first_message[:50].strip()
            if len(first_message) > 50:
                title += "..."
            
            # Remove newlines and extra spaces
            title = " ".join(title.split())
            
            self.update_session(session_id, {"session_title": title})
            
        except Exception as e:
            logger.warning(f"Failed to update session title: {str(e)}")
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        try:
            messages = self.get_messages(session_id, limit=1000)
            
            total_tokens = sum(msg.get("tokens_used", 0) for msg in messages)
            total_cost = sum(msg.get("cost_usd", 0) for msg in messages)
            message_count = len(messages)
            
            return {
                "session_id": session_id,
                "message_count": message_count,
                "total_tokens": total_tokens,
                "total_cost_usd": total_cost,
                "average_tokens_per_message": total_tokens / message_count if message_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting session stats: {str(e)}")
            return {}
    
    def export_session(self, session_id: str) -> Dict[str, Any]:
        """Export a session with all messages"""
        try:
            session = self.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            messages = self.get_messages(session_id, limit=10000)
            stats = self.get_session_stats(session_id)
            
            return {
                "session": session,
                "messages": messages,
                "stats": stats,
                "exported_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error exporting session: {str(e)}")
            raise
    
    def search_sessions(self, query: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search sessions by title or content"""
        try:
            # Search in session titles
            sessions_query = self.supabase.client.table("chat_sessions").select("*").ilike(
                "session_title", f"%{query}%"
            )
            
            if user_id:
                sessions_query = sessions_query.eq("user_id", user_id)
            
            sessions_result = sessions_query.execute()
            
            # For more advanced search, you'd also search in messages
            # This would require a full-text search setup in Supabase
            
            return sessions_result.data
            
        except Exception as e:
            logger.error(f"Error searching sessions: {str(e)}")
            return []


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager