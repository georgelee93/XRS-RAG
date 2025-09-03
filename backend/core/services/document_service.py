"""
Unified Document Service
Consolidates all document management functionality
"""

import logging
from typing import List, Dict, Any, Optional, BinaryIO, Union
from pathlib import Path
import hashlib
from datetime import datetime

from ..config import get_settings
from ..supabase_client import get_supabase_manager
from ..retrieval_client import RetrievalAPIClient

logger = logging.getLogger(__name__)


class UnifiedDocumentService:
    """
    Unified document service that handles all document operations
    Consolidates functionality from multiple document managers
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase = get_supabase_manager()
        self.retrieval_client = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the document service"""
        if self._initialized:
            return
            
        try:
            # Initialize retrieval client for vector store operations
            self.retrieval_client = RetrievalAPIClient()
            await self.retrieval_client.initialize_assistant()
            
            self._initialized = True
            logger.info("Document service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize document service: {str(e)}")
            raise
    
    async def upload_document(
        self,
        file: Union[BinaryIO, bytes],
        filename: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload a document to storage and vector store
        
        Args:
            file: File binary stream or bytes content
            filename: Name of the file
            user_id: Optional user ID who uploaded the file
            metadata: Optional metadata for the document
            
        Returns:
            Document information including ID and status
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Handle both file objects and bytes
            if isinstance(file, bytes):
                file_content = file
            else:
                file_content = file.read()
                if hasattr(file, 'seek'):
                    file.seek(0)  # Reset file pointer if possible
            
            # Calculate file hash for deduplication
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # Check if document already exists
            existing = self._check_duplicate(file_hash)
            if existing:
                logger.info(f"Document already exists: {filename}")
                return existing
            
            # Create a completely safe filename using only hash and extension
            import re
            # Get file extension
            if '.' in filename:
                ext = '.' + filename.rsplit('.', 1)[-1].lower()
                # Remove any non-ASCII from extension too
                ext = re.sub(r'[^a-zA-Z0-9\.]', '', ext)
            else:
                ext = '.bin'
            
            # Create safe filename using hash and timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"{file_hash[:12]}_{timestamp}{ext}"
            
            # Upload to Supabase storage
            storage_path = f"documents/{file_hash}/{safe_filename}"
            storage_result = self.supabase.client.storage.from_("documents").upload(
                storage_path,
                file_content,
                {
                    "content-type": self._get_content_type(filename),
                    "upsert": "true"
                }
            )
            
            # Create document record in database
            doc_metadata = metadata or {}
            doc_metadata["file_hash"] = file_hash  # Store hash in metadata
            doc_metadata["original_filename"] = filename  # Store original name
            
            doc_data = {
                "file_name": filename,  # Use correct column name
                "file_type": self._get_content_type(filename).split('/')[-1],  # Extract type
                "file_size": len(file_content),
                "storage_path": storage_path,
                "user_id": user_id,
                "metadata": doc_metadata,
                "status": "processing",
                "upload_timestamp": datetime.now().isoformat()
            }
            
            doc_record = self.supabase.client.table("documents").insert(doc_data).execute()
            document = doc_record.data[0]
            
            # Add to vector store asynchronously
            asyncio.create_task(self._add_to_vector_store(document["id"], file_content, filename))
            
            logger.info(f"Document uploaded successfully: {filename} (ID: {document['id']})")
            return document
            
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}")
            raise
    
    async def list_documents(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List documents with optional filtering
        
        Args:
            user_id: Optional filter by user
            limit: Maximum number of documents to return
            offset: Offset for pagination
            
        Returns:
            List of document records
        """
        try:
            query = self.supabase.client.table("documents").select("*")
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            query = query.order("created_at", desc=True)
            query = query.range(offset, offset + limit - 1)
            
            result = query.execute()
            return result.data
            
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            return []
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID"""
        try:
            result = self.supabase.client.table("documents").select("*").eq(
                "id", document_id
            ).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting document: {str(e)}")
            return None
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from storage and vector store
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get document details
            document = await self.get_document(document_id)
            if not document:
                logger.warning(f"Document not found: {document_id}")
                return False
            
            # Remove from vector store if it has a vector store file ID
            if document.get("vector_store_file_id"):
                try:
                    await self.retrieval_client.remove_from_vector_store(
                        document["vector_store_file_id"]
                    )
                except Exception as e:
                    logger.warning(f"Failed to remove from vector store: {e}")
            
            # Delete from storage
            if document.get("storage_path"):
                try:
                    self.supabase.client.storage.from_("documents").remove(
                        [document["storage_path"]]
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete from storage: {e}")
            
            # Delete database record
            self.supabase.client.table("documents").delete().eq(
                "id", document_id
            ).execute()
            
            logger.info(f"Document deleted successfully: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            return False
    
    async def sync_with_vector_store(self) -> Dict[str, Any]:
        """
        Synchronize documents with the vector store
        
        Returns:
            Sync statistics
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get all documents from database
            documents = await self.list_documents(limit=1000)
            
            # Get files in vector store
            vector_files = await self.retrieval_client.list_vector_store_files()
            vector_file_ids = {f["id"] for f in vector_files}
            
            stats = {
                "total_documents": len(documents),
                "in_vector_store": 0,
                "added": 0,
                "failed": 0
            }
            
            for doc in documents:
                if doc.get("vector_store_file_id") in vector_file_ids:
                    stats["in_vector_store"] += 1
                else:
                    # Try to add to vector store
                    try:
                        # Download file from storage
                        file_content = self.supabase.client.storage.from_("documents").download(
                            doc["storage_path"]
                        )
                        
                        # Add to vector store
                        vector_file_id = await self.retrieval_client.add_to_vector_store(
                            file_content,
                            doc["filename"]
                        )
                        
                        # Update document record
                        self.supabase.client.table("documents").update({
                            "vector_store_file_id": vector_file_id,
                            "status": "active"
                        }).eq("id", doc["id"]).execute()
                        
                        stats["added"] += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to sync document {doc['id']}: {e}")
                        stats["failed"] += 1
            
            logger.info(f"Vector store sync completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error syncing with vector store: {str(e)}")
            raise
    
    def _check_duplicate(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Check if a document with the same hash already exists"""
        try:
            # Use metadata field to store and check file hash since file_hash column doesn't exist
            result = self.supabase.client.table("documents").select("*").execute()
            
            # Check if any document has the same hash in metadata
            for doc in result.data or []:
                if doc.get("metadata", {}).get("file_hash") == file_hash:
                    return doc
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking duplicate: {str(e)}")
            return None
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension"""
        ext = Path(filename).suffix.lower()
        content_types = {
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
        }
        return content_types.get(ext, "application/octet-stream")
    
    async def _add_to_vector_store(self, document_id: str, file_content: bytes, filename: str):
        """Add document to vector store (async background task)"""
        try:
            if not self.retrieval_client:
                return
            
            # Add to vector store
            openai_file_id = await self.retrieval_client.add_to_vector_store(
                file_content,
                filename
            )
            
            # Update document status with OpenAI file ID
            self.supabase.client.table("documents").update({
                "openai_file_id": openai_file_id,
                "vector_store_file_id": openai_file_id,  # Store in both for compatibility
                "status": "active"
            }).eq("id", document_id).execute()
            
            logger.info(f"Document added to vector store: {document_id}")
            
        except Exception as e:
            logger.error(f"Failed to add document to vector store: {str(e)}")
            
            # Update document status to error
            self.supabase.client.table("documents").update({
                "status": "error",
                "error_message": str(e)
            }).eq("id", document_id).execute()


# Singleton instance
_document_service_instance: Optional[UnifiedDocumentService] = None


def get_document_service() -> UnifiedDocumentService:
    """Get or create the singleton document service instance"""
    global _document_service_instance
    if _document_service_instance is None:
        _document_service_instance = UnifiedDocumentService()
    return _document_service_instance


import asyncio  # Import at the end to avoid circular imports