"""
Document Routes
Handles all document management API endpoints
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from typing import Dict, Any, List, Optional
import logging

from core.auth import get_current_user
from core.services.document_service import get_document_service
from core.config import get_settings

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
    settings = Depends(get_settings)
):
    """
    Upload one or more documents
    
    Args:
        files: List of files to upload
        current_user: Authenticated user information
        
    Returns:
        Upload results for each file
    """
    try:
        user_id = current_user["user_id"]
        document_service = get_document_service()
        await document_service.initialize()
        
        results = []
        
        for file in files:
            # Check file size
            if file.size and file.size > settings.max_file_size:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": f"File too large (max {settings.max_file_size / 1024 / 1024}MB)"
                })
                continue
            
            # Check file extension
            file_ext = file.filename.split('.')[-1].lower()
            allowed_extensions = [ext.replace('.', '') for ext in settings.supported_file_extensions]
            
            if file_ext not in allowed_extensions:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
                })
                continue
            
            try:
                # Read file content once
                file_content = await file.read()
                
                # Upload document with the content we just read
                document = await document_service.upload_document(
                    file=file_content,  # Pass the content, not the exhausted file object
                    filename=file.filename,
                    user_id=user_id,
                    metadata={
                        "content_type": file.content_type,
                        "uploaded_by": current_user["email"]
                    }
                )
                
                results.append({
                    "filename": file.filename,
                    "success": True,
                    "document_id": document["id"],
                    "status": document.get("status", "processing")
                })
                
            except Exception as e:
                logger.error(f"Error uploading {file.filename}: {str(e)}")
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })
        
        # Count successes
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "success": success_count > 0,
            "message": f"Uploaded {success_count}/{len(files)} files successfully",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload documents: {str(e)}"
        )


@router.get("")
async def list_documents(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user_only: bool = Query(False),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List documents
    
    Args:
        limit: Maximum number of documents to return
        offset: Offset for pagination
        user_only: If true, only return documents uploaded by current user
        current_user: Authenticated user information
        
    Returns:
        List of document records
    """
    try:
        document_service = get_document_service()
        
        # Filter by user if requested
        user_id = current_user["user_id"] if user_only else None
        
        documents = await document_service.list_documents(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        # Transform documents to match frontend expectations
        transformed_docs = []
        for doc in documents:
            # Format file size for display
            file_size_bytes = doc.get("file_size", 0)
            if file_size_bytes > 1024 * 1024:
                file_size_display = f"{file_size_bytes / (1024 * 1024):.2f} MB"
            elif file_size_bytes > 1024:
                file_size_display = f"{file_size_bytes / 1024:.2f} KB"
            else:
                file_size_display = f"{file_size_bytes} B"
            
            transformed_docs.append({
                "supabase_id": doc.get("id"),
                "openai_file_id": doc.get("openai_file_id"),
                "display_name": doc.get("file_name"),
                "storage_path": doc.get("storage_path"),
                "file_size": file_size_display,  # Human-readable string
                "file_size_bytes": file_size_bytes,  # Raw integer
                "file_type": doc.get("file_type"),
                "status": doc.get("status"),
                "uploaded_at": doc.get("upload_timestamp") or doc.get("created_at"),
                "uploaded_by_id": doc.get("user_id"),
                "uploaded_by_email": doc.get("metadata", {}).get("uploaded_by")
            })
        
        return {
            "success": True,
            "documents": transformed_docs,
            "total": len(transformed_docs),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"List documents error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {str(e)}"
        )


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get details for a specific document"""
    try:
        document_service = get_document_service()
        document = await document_service.get_document(document_id)
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
        
        return {
            "success": True,
            "document": document
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get document: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a document"""
    try:
        document_service = get_document_service()
        await document_service.initialize()
        
        # Check if document exists and user has permission
        document = await document_service.get_document(document_id)
        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )
        
        # Check ownership (optional - depends on requirements)
        # if document.get("user_id") != current_user["user_id"]:
        #     raise HTTPException(
        #         status_code=403,
        #         detail="You don't have permission to delete this document"
        #     )
        
        success = await document_service.delete_document(document_id)
        
        if success:
            return {
                "success": True,
                "message": "Document deleted successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete document"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.post("/sync")
async def sync_documents(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Synchronize documents with vector store"""
    try:
        document_service = get_document_service()
        await document_service.initialize()
        
        stats = await document_service.sync_with_vector_store()
        
        return {
            "success": True,
            "message": "Synchronization completed",
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Sync error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync documents: {str(e)}"
        )