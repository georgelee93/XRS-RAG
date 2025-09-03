"""
Supabase Client
Handles all Supabase operations (database and storage)
"""

import os
import logging
import uuid
from typing import Dict, Any, List, Optional, Union
from supabase import create_client, Client

from ..config import get_settings
from ..timezone_utils import now_kst_iso

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Manages Supabase database and storage operations"""
    
    def __init__(self):
        """Initialize Supabase client"""
        settings = get_settings()
        
        if settings.supabase_url and settings.supabase_anon_key:
            self.client: Client = create_client(
                settings.supabase_url,
                settings.supabase_anon_key
            )
            self.connected = True
            logger.info("Supabase client initialized")
        else:
            self.client = None
            self.connected = False
            logger.warning("Supabase credentials not configured")
    
    def is_connected(self) -> bool:
        """Check if Supabase is connected"""
        return self.connected
    
    # Database Operations
    
    async def create_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create document record in database"""
        if not self.connected:
            raise Exception("Supabase not connected")
        
        try:
            document_data["created_at"] = now_kst_iso()
            document_data["updated_at"] = now_kst_iso()
            
            result = self.client.table("documents").insert(document_data).execute()
            
            if result.data:
                logger.info(f"Document created: {document_data.get('openai_file_id')}")
                return result.data[0]
            else:
                raise Exception("No data returned from insert")
                
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            raise
    
    async def list_documents(self, status: str = "active") -> List[Dict[str, Any]]:
        """List documents from database"""
        if not self.connected:
            return []
        
        try:
            query = self.client.table("documents").select("*")
            
            if status:
                query = query.eq("status", status)
            
            result = query.order("created_at", desc=True).execute()
            
            # Transform to standard format
            documents = []
            for doc in result.data:
                documents.append({
                    "supabase_id": doc.get("document_id"),
                    "openai_file_id": doc.get("openai_file_id"),
                    "display_name": doc.get("filename"),
                    "storage_path": doc.get("storage_path"),
                    "file_size_bytes": doc.get("size_bytes", 0),
                    "file_type": self._get_file_type(doc.get("filename", "")),
                    "status": doc.get("status"),
                    "uploaded_at": doc.get("created_at"),
                    "uploaded_by_id": doc.get("user_id"),
                    "uploaded_by_email": doc.get("uploaded_by_email", "unknown")
                })
            
            logger.info(f"Retrieved {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []
    
    async def update_document(self, doc_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update document in database"""
        if not self.connected:
            raise Exception("Supabase not connected")
        
        try:
            updates["updated_at"] = now_kst_iso()
            
            # Use appropriate column based on ID format
            if doc_id.startswith("file-"):
                # OpenAI file ID
                result = self.client.table("documents").update(updates).eq(
                    "openai_file_id", doc_id
                ).execute()
            else:
                # UUID (document_id)
                result = self.client.table("documents").update(updates).eq(
                    "document_id", doc_id
                ).execute()
            
            if result.data:
                logger.info(f"Document updated: {doc_id}")
                return result.data[0]
            else:
                logger.warning(f"No document found: {doc_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            raise
    
    async def get_document_by_openai_id(self, openai_file_id: str) -> Optional[Dict[str, Any]]:
        """Get document by OpenAI file ID"""
        if not self.connected:
            return None
        
        try:
            result = self.client.table("documents").select("*").eq(
                "openai_file_id", openai_file_id
            ).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None
    
    # Storage Operations
    
    def upload_file(
        self,
        bucket: str,
        path: str,
        file_content: bytes,
        content_type: str = "application/octet-stream"
    ) -> str:
        """Upload file to Supabase Storage"""
        if not self.connected:
            raise Exception("Supabase not connected")
        
        try:
            # Upload to storage
            response = self.client.storage.from_(bucket).upload(
                path,
                file_content,
                {"content-type": content_type}
            )
            
            # Get public URL
            url = self.client.storage.from_(bucket).get_public_url(path)
            
            logger.info(f"File uploaded to storage: {path}")
            return url
            
        except Exception as e:
            logger.error(f"Storage upload failed: {e}")
            raise
    
    def download_file(self, bucket: str, path: str) -> bytes:
        """Download file from Supabase Storage"""
        if not self.connected:
            raise Exception("Supabase not connected")
        
        try:
            response = self.client.storage.from_(bucket).download(path)
            logger.info(f"File downloaded from storage: {path}")
            return response
            
        except Exception as e:
            logger.error(f"Storage download failed: {e}")
            raise
    
    def delete_file(self, bucket: str, path: str) -> bool:
        """Delete file from Supabase Storage"""
        if not self.connected:
            return False
        
        try:
            self.client.storage.from_(bucket).remove([path])
            logger.info(f"File deleted from storage: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Storage deletion failed: {e}")
            return False
    
    def _get_file_type(self, filename: str) -> str:
        """Extract file type from filename"""
        ext = os.path.splitext(filename)[1].lower()
        return ext.replace('.', '') if ext else 'unknown'
    
    def _ensure_uuid(self, value: Optional[Union[str, uuid.UUID]]) -> Optional[str]:
        """Convert value to UUID string format"""
        if not value:
            return None
        
        # Already a UUID object
        if isinstance(value, uuid.UUID):
            return str(value)
        
        # Try to parse as UUID string
        try:
            return str(uuid.UUID(value))
        except (ValueError, AttributeError):
            # Generate deterministic UUID from string
            # This allows consistent UUIDs for the same string input
            if isinstance(value, str):
                return str(uuid.uuid5(uuid.NAMESPACE_DNS, value))
            return None
    
    # Chat Session Operations
    
    async def create_or_get_session(
        self,
        session_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create or get a chat session"""
        if not self.connected:
            raise Exception("Supabase not connected")
        
        try:
            # If session_id provided, try to get existing
            if session_id:
                result = self.client.table("chat_sessions").select("*").eq(
                    "session_id", session_id
                ).execute()
                
                if result.data:
                    logger.info(f"Retrieved existing session: {session_id}")
                    return result.data[0]
            
            # Create new session
            import uuid
            new_session_id = session_id or str(uuid.uuid4())
            
            session_data = {
                "session_id": new_session_id,
                "thread_id": thread_id,
                "user_id": user_id,
                "metadata": {}
            }
            
            result = self.client.table("chat_sessions").insert(session_data).execute()
            
            if result.data:
                logger.info(f"Created new session: {new_session_id}")
                return result.data[0]
            else:
                raise Exception("Failed to create session")
                
        except Exception as e:
            logger.error(f"Session operation failed: {e}")
            raise
    
    async def save_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Save a chat message to database"""
        if not self.connected:
            raise Exception("Supabase not connected")
        
        try:
            # Ensure session_id is a valid UUID
            session_uuid = self._ensure_uuid(session_id)
            if not session_uuid:
                raise ValueError(f"Invalid session_id format: {session_id}")
            
            # Convert user_id to UUID if provided (it's nullable in DB)
            user_uuid = self._ensure_uuid(user_id) if user_id else None
            
            message_data = {
                "session_id": session_uuid,
                "role": role,
                "content": content,
                "tokens_used": tokens_used,
                "cost_usd": cost_usd,
                "metadata": metadata or {},
                "user_id": user_uuid,  # Now properly formatted as UUID or None
                "user_email": user_email
            }
            
            # Remove None values to let database use defaults
            message_data = {k: v for k, v in message_data.items() if v is not None}
            
            result = self.client.table("chat_messages").insert(message_data).execute()
            
            if result.data:
                logger.info(f"Message saved to session: {session_id}")
                
                # Update session's last_message_at
                self.client.table("chat_sessions").update({
                    "last_message_at": now_kst_iso(),
                    "updated_at": now_kst_iso()
                }).eq("session_id", session_id).execute()
                
                return result.data[0]
            else:
                raise Exception("Failed to save message")
                
        except Exception as e:
            logger.error(f"Failed to save chat message: {e}")
            logger.error(f"Message data: session_id={session_id}, user_id={user_id}")
            raise
    
    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get messages for a session"""
        if not self.connected:
            return []
        
        try:
            result = self.client.table("chat_messages").select("*").eq(
                "session_id", session_id
            ).order("created_at", desc=False).limit(limit).execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get session messages: {e}")
            return []