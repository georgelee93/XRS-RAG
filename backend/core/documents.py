"""
Document Manager
Handles document storage and management across OpenAI and Supabase
"""

import os
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..assistant.openai import OpenAIAssistantManager
from .supabase import SupabaseClient
from ..timezone_utils import now_kst_iso

logger = logging.getLogger(__name__)


class DocumentManager:
    """Manages documents across OpenAI and Supabase Storage"""
    
    def __init__(self):
        """Initialize document manager with both OpenAI and Supabase"""
        self.assistant = OpenAIAssistantManager()
        self.supabase = SupabaseClient()
        self.initialized = False
        
        logger.info("Document Manager initialized")
    
    async def initialize(self) -> None:
        """Initialize all components"""
        if self.initialized:
            return
        
        await self.assistant.initialize()
        self.initialized = True
        logger.info("Document Manager ready")
    
    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload document to both OpenAI and Supabase Storage
        
        Args:
            file_content: File bytes
            filename: Original filename
            user_id: User ID (optional)
            user_email: User email (optional)
        
        Returns:
            Upload result with file IDs and status
        """
        await self.initialize()
        
        try:
            # Upload to OpenAI for AI processing
            openai_result = await self.assistant.upload_file(file_content, filename)
            openai_file_id = openai_result["file_id"]
            
            logger.info(f"Uploaded to OpenAI: {openai_file_id}")
            
            # Generate storage-safe filename
            storage_path = self._generate_storage_path(filename)
            
            # Upload to Supabase Storage for downloads
            storage_url = None
            if self.supabase.is_connected():
                try:
                    storage_url = self.supabase.upload_file(
                        bucket="documents",
                        path=storage_path,
                        file_content=file_content,
                        content_type=self._get_content_type(filename)
                    )
                    logger.info(f"Uploaded to Storage: {storage_path}")
                except Exception as e:
                    logger.error(f"Storage upload failed: {e}")
            
            # Save metadata to database
            if self.supabase.is_connected():
                try:
                    await self.supabase.create_document({
                        "openai_file_id": openai_file_id,
                        "filename": filename,
                        "storage_path": storage_path,
                        "size_bytes": len(file_content),
                        "user_id": user_id,
                        "uploaded_by_email": user_email or "anonymous",
                        "status": "active"
                    })
                    logger.info(f"Metadata saved to database")
                except Exception as e:
                    logger.error(f"Failed to save metadata: {e}")
            
            return {
                "status": "success",
                "openai_file_id": openai_file_id,
                "display_name": filename,
                "storage_path": storage_path,
                "storage_url": storage_url,
                "file_size_bytes": len(file_content)
            }
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "display_name": filename
            }
    
    async def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all active documents
        Uses Supabase as source of truth for display
        """
        await self.initialize()
        
        try:
            # Get documents from Supabase (has correct filenames)
            if self.supabase.is_connected():
                return await self.supabase.list_documents(status="active")
            else:
                # Fallback to OpenAI
                return await self.assistant.list_documents()
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []
    
    async def delete_document(
        self,
        openai_file_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Delete document from OpenAI and mark as deleted in Supabase
        
        Args:
            openai_file_id: OpenAI file ID (format: file-xxxxx)
            user_id: User performing deletion (optional)
        
        Returns:
            True if successful
        """
        await self.initialize()
        
        try:
            logger.info(f"Deleting document: {openai_file_id}")
            
            # Try to delete from OpenAI
            openai_deleted = False
            try:
                # Check if file exists in OpenAI
                files = await self.assistant.list_documents()
                file_exists = any(f["file_id"] == openai_file_id for f in files)
                
                if file_exists:
                    openai_deleted = await self.assistant.delete_file(openai_file_id)
                    logger.info(f"Deleted from OpenAI: {openai_file_id}")
                else:
                    logger.info(f"File already deleted from OpenAI: {openai_file_id}")
                    openai_deleted = True
            except Exception as e:
                logger.error(f"OpenAI deletion error: {e}")
            
            # Always mark as deleted in database
            if self.supabase.is_connected():
                try:
                    await self.supabase.update_document(openai_file_id, {
                        "status": "deleted",
                        "deleted_at": now_kst_iso()
                    })
                    logger.info(f"Marked as deleted in database: {openai_file_id}")
                    return True
                except Exception as e:
                    logger.error(f"Database update failed: {e}")
                    return openai_deleted
            
            return openai_deleted
            
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False
    
    async def get_document_content(self, openai_file_id: str) -> Optional[bytes]:
        """
        Download document content from Supabase Storage
        
        Args:
            openai_file_id: OpenAI file ID
        
        Returns:
            File content bytes or None
        """
        await self.initialize()
        
        try:
            if not self.supabase.is_connected():
                logger.error("Supabase not connected for downloads")
                return None
            
            # Get storage path from database
            doc_info = await self.supabase.get_document_by_openai_id(openai_file_id)
            if not doc_info:
                logger.error(f"Document not found: {openai_file_id}")
                return None
            
            storage_path = doc_info.get("storage_path")
            if not storage_path:
                logger.error(f"No storage path for: {openai_file_id}")
                return None
            
            # Download from storage
            content = self.supabase.download_file("documents", storage_path)
            logger.info(f"Downloaded {len(content)} bytes")
            return content
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
    
    def _generate_storage_path(self, filename: str) -> str:
        """Generate ASCII-safe storage path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(filename)[0]
        file_ext = os.path.splitext(filename)[1]
        
        # Use hash of filename for ASCII safety
        name_hash = hashlib.md5(base_name.encode('utf-8')).hexdigest()[:12]
        
        return f"{timestamp}_{name_hash}{file_ext}"
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type from filename"""
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword'
        }
        return content_types.get(ext, 'application/octet-stream')