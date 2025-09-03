"""
Supabase client and database management
Handles all Supabase interactions for the application
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from gotrue.errors import AuthApiError
from postgrest.exceptions import APIError

from .utils import get_env_var

logger = logging.getLogger(__name__)


class SupabaseManager:
    """Manages all Supabase operations"""
    
    def __init__(self):
        self.url = get_env_var("SUPABASE_URL")
        self.key = get_env_var("SUPABASE_ANON_KEY")
        
        # Check if we have a service role key for admin operations
        # In Cloud Run, this might not be available during import
        self.service_key = get_env_var("SUPABASE_SERVICE_KEY", required=False)
        
        # Only use service key if it's actually set and not the placeholder
        if self.service_key and self.service_key != "your_service_role_key_here":
            active_key = self.service_key
            key_type = "service"
        else:
            active_key = self.key
            key_type = "anon"
            if self.service_key == "your_service_role_key_here":
                logger.warning("Service key placeholder found - using anon key. Please add your actual service role key.")
        
        # DEBUG: Log the key being used
        logger.info(f"Supabase URL: {self.url}")
        logger.info(f"Using {key_type} key (length: {len(active_key) if active_key else 0})")
        
        # Create client with explicit headers
        self.client: Client = create_client(self.url, active_key)
        
        # Verify headers are set
        if hasattr(self.client, '_headers'):
            logger.debug(f"Client headers: {self.client._headers}")
        
        logger.info(f"Supabase client initialized with {key_type} key")
    
    # Document Management
    async def create_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document record in the database"""
        try:
            logger.info(f"[SUPABASE DB] Creating document record")
            logger.debug(f"  - Filename: {document_data.get('filename')}")
            logger.debug(f"  - Storage path: {document_data.get('storage_path')}")
            logger.debug(f"  - OpenAI file ID: {document_data.get('file_id')}")
            logger.debug(f"  - User ID: {document_data.get('user_id')}")
            logger.debug(f"  - Uploaded by: {document_data.get('uploaded_by_email')}")
            
            insert_data = {
                "filename": document_data["filename"],
                "file_path": document_data.get("file_path"),
                "storage_path": document_data.get("storage_path"),
                "content_type": document_data.get("content_type"),
                "size_bytes": document_data.get("size"),
                "openai_file_id": document_data.get("file_id"),  # OpenAI file ID
                "metadata": document_data.get("metadata", {}),
                "text_preview": document_data.get("text_preview"),
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "user_id": document_data.get("user_id"),
                "uploaded_by_email": document_data.get("uploaded_by_email")
            }
            
            result = self.client.table("documents").insert(insert_data).execute()
            
            if result.data:
                logger.info(f"[SUPABASE DB] Document created successfully")
                logger.info(f"  - Document ID: {result.data[0]['document_id']}")
                return result.data[0]
            else:
                logger.warning(f"[SUPABASE DB] Insert returned no data")
                return None
            
        except APIError as e:
            logger.error(f"[SUPABASE DB] Error creating document")
            logger.error(f"  - Error: {str(e)}")
            logger.error(f"  - Error type: {type(e).__name__}")
            if hasattr(e, 'response'):
                logger.error(f"  - Response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
                logger.error(f"  - Response body: {e.response.text if hasattr(e.response, 'text') else 'N/A'}")
            raise
    
    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        logger.info(f"[SUPABASE DB] Fetching document")
        logger.info(f"  - Document ID: {doc_id}")
        
        try:
            result = self.client.table("documents").select("*").eq("document_id", doc_id).execute()
            
            if result.data:
                logger.info(f"[SUPABASE DB] Document found")
                logger.info(f"  - Filename: {result.data[0].get('filename')}")
                logger.info(f"  - Status: {result.data[0].get('status')}")
                logger.info(f"  - OpenAI File ID: {result.data[0].get('openai_file_id')}")
                return result.data[0]
            else:
                logger.warning(f"[SUPABASE DB] Document not found: {doc_id}")
                return None
            
        except APIError as e:
            logger.error(f"[SUPABASE DB] Error getting document")
            logger.error(f"  - Document ID: {doc_id}")
            logger.error(f"  - Error: {str(e)}")
            logger.error(f"  - Error type: {type(e).__name__}")
            return None
    
    async def list_documents(self, status: Optional[str] = "active") -> List[Dict[str, Any]]:
        """List all documents with optional status filter"""
        logger.info(f"[SUPABASE DB] Listing documents")
        logger.info(f"  - Status filter: {status if status else 'all'}")
        
        try:
            query = self.client.table("documents").select("*")
            if status:
                query = query.eq("status", status)
            
            result = query.order("created_at", desc=True).execute()
            
            logger.info(f"[SUPABASE DB] Documents retrieved successfully")
            logger.info(f"  - Total documents: {len(result.data)}")
            if result.data:
                logger.debug(f"  - First document: {result.data[0].get('filename')}")
                logger.debug(f"  - Last document: {result.data[-1].get('filename')}")
            
            return result.data
            
        except APIError as e:
            logger.error(f"[SUPABASE DB] Error listing documents")
            logger.error(f"  - Status filter: {status}")
            logger.error(f"  - Error: {str(e)}")
            logger.error(f"  - Error type: {type(e).__name__}")
            return []
    
    async def update_document(self, doc_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a document"""
        logger.info(f"[SUPABASE DB] Updating document")
        logger.info(f"  - Document ID: {doc_id}")
        logger.info(f"  - Update fields: {list(updates.keys())}")
        
        try:
            updates["updated_at"] = datetime.now().isoformat()
            result = self.client.table("documents").update(updates).eq("document_id", doc_id).execute()
            
            if result.data:
                logger.info(f"[SUPABASE DB] Document updated successfully")
                logger.info(f"  - Updated fields: {list(updates.keys())}")
                return result.data[0]
            else:
                logger.warning(f"[SUPABASE DB] No document updated (may not exist)")
                return None
            
        except APIError as e:
            logger.error(f"[SUPABASE DB] Error updating document")
            logger.error(f"  - Document ID: {doc_id}")
            logger.error(f"  - Updates attempted: {updates}")
            logger.error(f"  - Error: {str(e)}")
            logger.error(f"  - Error type: {type(e).__name__}")
            raise
    
    async def delete_document(self, doc_id: str, soft_delete: bool = True) -> bool:
        """Delete a document (soft delete by default)"""
        logger.info(f"[SUPABASE DB] Deleting document")
        logger.info(f"  - Document ID: {doc_id}")
        logger.info(f"  - Delete type: {'soft delete' if soft_delete else 'hard delete'}")
        
        try:
            if soft_delete:
                delete_data = {
                    "status": "deleted",
                    "deleted_at": datetime.now().isoformat()
                }
                logger.debug(f"  - Setting status to 'deleted' and deleted_at timestamp")
                result = self.client.table("documents").update(delete_data).eq("document_id", doc_id).execute()
            else:
                logger.warning(f"  - Performing hard delete (permanent)")
                result = self.client.table("documents").delete().eq("document_id", doc_id).execute()
            
            if result.data:
                logger.info(f"[SUPABASE DB] Document deleted successfully")
                logger.info(f"  - Deleted document: {result.data[0].get('filename') if result.data else 'unknown'}")
                return True
            else:
                logger.warning(f"[SUPABASE DB] No document deleted (may not exist)")
                return False
            
        except APIError as e:
            logger.error(f"[SUPABASE DB] Error deleting document")
            logger.error(f"  - Document ID: {doc_id}")
            logger.error(f"  - Delete type: {'soft' if soft_delete else 'hard'}")
            logger.error(f"  - Error: {str(e)}")
            logger.error(f"  - Error type: {type(e).__name__}")
            return False
    
    # File Storage
    def upload_file(self, bucket: str, file_path: str, file_content: bytes, 
                    content_type: str = "application/octet-stream") -> str:
        """Upload a file to Supabase Storage"""
        logger.info(f"[SUPABASE STORAGE] Starting file upload")
        logger.info(f"  - Bucket: {bucket}")
        logger.info(f"  - Path: {file_path}")
        logger.info(f"  - Size: {len(file_content):,} bytes ({len(file_content)/1024/1024:.2f} MB)")
        logger.info(f"  - Content-Type: {content_type}")
        logger.debug(f"  - Supabase URL: {self.url}")
        
        try:
            start_time = datetime.now()
            result = self.client.storage.from_(bucket).upload(
                file_path,
                file_content,
                {"content-type": content_type}
            )
            upload_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"[SUPABASE STORAGE] File uploaded successfully")
            logger.info(f"  - Upload time: {upload_time:.2f} seconds")
            logger.info(f"  - Upload speed: {len(file_content)/1024/1024/upload_time:.2f} MB/s")
            logger.info(f"  - Full path: {bucket}/{file_path}")
            
            return file_path
            
        except Exception as e:
            logger.error(f"[SUPABASE STORAGE] File upload failed")
            logger.error(f"  - Bucket: {bucket}")
            logger.error(f"  - Path: {file_path}")
            logger.error(f"  - Error: {str(e)}")
            logger.error(f"  - Error type: {type(e).__name__}")
            
            # Check for common errors
            if "already exists" in str(e).lower():
                logger.error(f"  - File already exists at this path")
            elif "unauthorized" in str(e).lower():
                logger.error(f"  - Authorization error - check Supabase credentials")
            elif "not found" in str(e).lower():
                logger.error(f"  - Bucket not found or not accessible")
            
            raise
    
    def download_file(self, bucket: str, file_path: str) -> bytes:
        """Download a file from Supabase Storage"""
        logger.info(f"[SUPABASE STORAGE] Starting file download")
        logger.info(f"  - Bucket: {bucket}")
        logger.info(f"  - Path: {file_path}")
        
        try:
            start_time = datetime.now()
            result = self.client.storage.from_(bucket).download(file_path)
            download_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"[SUPABASE STORAGE] File downloaded successfully")
            logger.info(f"  - Size: {len(result):,} bytes ({len(result)/1024/1024:.2f} MB)")
            logger.info(f"  - Download time: {download_time:.2f} seconds")
            logger.info(f"  - Download speed: {len(result)/1024/1024/download_time:.2f} MB/s")
            
            return result
            
        except Exception as e:
            logger.error(f"[SUPABASE STORAGE] File download failed")
            logger.error(f"  - Bucket: {bucket}")
            logger.error(f"  - Path: {file_path}")
            logger.error(f"  - Error: {str(e)}")
            logger.error(f"  - Error type: {type(e).__name__}")
            
            if "not found" in str(e).lower():
                logger.error(f"  - File not found in storage")
            
            raise
    
    def get_file_url(self, bucket: str, file_path: str, expires_in: int = 3600) -> str:
        """Get a signed URL for file download"""
        logger.info(f"[SUPABASE STORAGE] Creating signed URL")
        logger.info(f"  - Bucket: {bucket}")
        logger.info(f"  - Path: {file_path}")
        logger.info(f"  - Expires in: {expires_in} seconds ({expires_in/3600:.1f} hours)")
        
        try:
            result = self.client.storage.from_(bucket).create_signed_url(
                file_path, 
                expires_in=expires_in
            )
            
            logger.info(f"[SUPABASE STORAGE] Signed URL created successfully")
            logger.debug(f"  - URL length: {len(result['signedURL'])} chars")
            logger.info(f"  - Valid for: {expires_in} seconds")
            
            return result["signedURL"]
            
        except Exception as e:
            logger.error(f"[SUPABASE STORAGE] Failed to create signed URL")
            logger.error(f"  - Bucket: {bucket}")
            logger.error(f"  - Path: {file_path}")
            logger.error(f"  - Error: {str(e)}")
            logger.error(f"  - Error type: {type(e).__name__}")
            raise
    
    def delete_file(self, bucket: str, file_path: str) -> bool:
        """Delete a file from Supabase Storage"""
        logger.info(f"[SUPABASE STORAGE] Deleting file")
        logger.info(f"  - Bucket: {bucket}")
        logger.info(f"  - Path: {file_path}")
        
        try:
            result = self.client.storage.from_(bucket).remove([file_path])
            
            logger.info(f"[SUPABASE STORAGE] File deleted successfully")
            logger.info(f"  - Deleted: {bucket}/{file_path}")
            return True
            
        except Exception as e:
            logger.error(f"[SUPABASE STORAGE] File deletion failed")
            logger.error(f"  - Bucket: {bucket}")
            logger.error(f"  - Path: {file_path}")
            logger.error(f"  - Error: {str(e)}")
            logger.error(f"  - Error type: {type(e).__name__}")
            
            if "not found" in str(e).lower():
                logger.warning(f"  - File may not exist or already deleted")
            
            return False
    
    # Chat History
    async def create_chat_session(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new chat session"""
        logger.info(f"[SUPABASE DB] Creating new chat session")
        logger.info(f"  - User ID: {user_id if user_id else 'anonymous'}")
        
        try:
            session_data = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat()
            }
            result = self.client.table("chat_sessions").insert(session_data).execute()
            
            if result.data:
                logger.info(f"[SUPABASE DB] Chat session created successfully")
                logger.info(f"  - Session ID: {result.data[0].get('session_id')}")
                logger.info(f"  - Created at: {result.data[0].get('created_at')}")
                return result.data[0]
            else:
                logger.warning(f"[SUPABASE DB] Chat session creation returned no data")
                raise Exception("Failed to create chat session")
            
        except APIError as e:
            logger.error(f"[SUPABASE DB] Error creating chat session")
            logger.error(f"  - User ID: {user_id}")
            logger.error(f"  - Error: {str(e)}")
            logger.error(f"  - Error type: {type(e).__name__}")
            raise
    
    async def add_chat_message(self, session_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Add a message to chat history"""
        logger.info(f"[SUPABASE DB] Adding chat message")
        logger.info(f"  - Session ID: {session_id}")
        logger.info(f"  - Role: {message.get('role')}")
        logger.info(f"  - Content length: {len(message.get('content', ''))} chars")
        logger.debug(f"  - Has metadata: {bool(message.get('metadata'))}")
        
        try:
            message_data = {
                "session_id": session_id,
                "role": message["role"],
                "content": message["content"],
                "metadata": message.get("metadata", {}),
                "created_at": datetime.now().isoformat()
            }
            
            # Add user info if available
            if message.get("user_id"):
                message_data["user_id"] = message["user_id"]
                logger.info(f"  - User ID: {message['user_id']}")
            if message.get("user_email"):
                message_data["user_email"] = message["user_email"]
                logger.info(f"  - User email: {message['user_email']}")
            
            result = self.client.table("chat_messages").insert(message_data).execute()
            
            if result.data:
                logger.info(f"[SUPABASE DB] Chat message added successfully")
                logger.info(f"  - Message ID: {result.data[0].get('message_id')}")
                return result.data[0]
            else:
                logger.warning(f"[SUPABASE DB] Chat message insert returned no data")
                raise Exception("Failed to add chat message")
            
        except APIError as e:
            logger.error(f"[SUPABASE DB] Error adding chat message")
            logger.error(f"  - Session ID: {session_id}")
            logger.error(f"  - Role: {message.get('role')}")
            logger.error(f"  - Error: {str(e)}")
            logger.error(f"  - Error type: {type(e).__name__}")
            raise
    
    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for a session"""
        logger.info(f"[SUPABASE DB] Fetching chat history")
        logger.info(f"  - Session ID: {session_id}")
        logger.info(f"  - Limit: {limit}")
        
        try:
            result = self.client.table("chat_messages").select("*").eq(
                "session_id", session_id
            ).order("created_at", desc=False).limit(limit).execute()
            
            logger.info(f"[SUPABASE DB] Chat history retrieved successfully")
            logger.info(f"  - Total messages: {len(result.data)}")
            if result.data:
                logger.debug(f"  - First message role: {result.data[0].get('role')}")
                logger.debug(f"  - Last message role: {result.data[-1].get('role')}")
                
                # Log message distribution
                role_counts = {}
                for msg in result.data:
                    role = msg.get('role', 'unknown')
                    role_counts[role] = role_counts.get(role, 0) + 1
                logger.info(f"  - Message distribution: {role_counts}")
            
            return result.data
            
        except APIError as e:
            logger.error(f"[SUPABASE DB] Error getting chat history")
            logger.error(f"  - Session ID: {session_id}")
            logger.error(f"  - Limit: {limit}")
            logger.error(f"  - Error: {str(e)}")
            logger.error(f"  - Error type: {type(e).__name__}")
            return []
    
    # Health Check
    async def health_check(self) -> Dict[str, Any]:
        """Check Supabase connection health"""
        try:
            # Try a simple query
            result = self.client.table("documents").select("count").limit(1).execute()
            
            return {
                "healthy": True,
                "service": "supabase",
                "url": self.url,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "service": "supabase",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Global instance
supabase_manager: Optional[SupabaseManager] = None


def get_supabase_manager() -> SupabaseManager:
    """Get or create the global Supabase manager instance"""
    global supabase_manager
    if supabase_manager is None:
        logger.info("Creating new SupabaseManager instance")
        supabase_manager = SupabaseManager()
    return supabase_manager

def reset_supabase_manager():
    """Reset the global Supabase manager instance (for reloading config)"""
    global supabase_manager
    logger.info("Resetting SupabaseManager instance")
    supabase_manager = None