"""
API routes for 청암 챗봇
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Response, Depends, Request
from typing import List, Optional, Dict, Any
import json
import logging
import os
import asyncio
import aiofiles
from urllib.parse import unquote
import unicodedata

from core.auth import get_current_user, get_current_admin, get_auth_service
from core.audit import audit_service
from core.async_logging import get_async_monitoring

# Import dependency injection
from core.dependencies import (
    RetrievalClientDep,
    DocManagerDep,
    ChatInterfaceDep,
    RetrievalEngineDep,
    MonitoringDep,
    get_retrieval_client,
    get_doc_manager,
    get_chat_interface,
    get_retrieval_engine,
    get_monitoring
)

# Initialize router with /api prefix
router = APIRouter(prefix="/api")

# Initialize logger
logger = logging.getLogger(__name__)

# Note: Dependencies are now managed by core.dependencies module
# This eliminates global state and race conditions

# Import after defining getters
from core.supabase_client import get_supabase_manager
from core.config import get_settings

@router.post("/documents/upload")
async def upload_documents(
    doc_manager: DocManagerDep,
    files: List[UploadFile] = File(...),
    current_user: Dict[str, Any] = Depends(get_current_admin),  # 관리자만 문서 업로드 가능
    request: Request = None
):
    """Upload documents to the RAG system (Admin only)"""
    # Supported file types for OpenAI Assistant API
    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.md', '.docx'}
    SUPPORTED_MIME_TYPES = {
        'application/pdf',
        'text/plain',
        'text/markdown',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    
    try:
        results = []
        user_id = current_user["user_id"]
        user_email = current_user["email"]
        
        for file in files:
            try:
                # Check file extension
                file_ext = os.path.splitext(file.filename)[1].lower()
                if file_ext not in SUPPORTED_EXTENSIONS:
                    results.append({
                        "filename": file.filename,
                        "status": "error",
                        "error": f"Unsupported file type. Supported formats: PDF, TXT, MD, DOCX"
                    })
                    logger.warning(f"User {user_email} attempted to upload unsupported file type: {file.filename}")
                    continue
                
                # Also check MIME type if available
                if file.content_type and file.content_type not in SUPPORTED_MIME_TYPES:
                    # Some browsers might send different MIME types, so rely more on extension
                    logger.warning(f"MIME type mismatch for {file.filename}: {file.content_type}")
                
                content = await file.read()
                
                # Include user info in upload
                result = await doc_manager.upload_document(
                    file_content=content,
                    filename=file.filename,
                    content_type=file.content_type,
                    user_id=user_id,
                    uploaded_by_email=user_email
                )
                
                # Log the upload
                await audit_service.log_document_upload(
                    user_id=user_id,
                    user_email=user_email,
                    document_id=result.get("document_id", result.get("doc_id")),
                    filename=file.filename,
                    size_bytes=len(content),
                    content_type=file.content_type
                )
                
                results.append(result)
                logger.info(f"User {user_email} uploaded: {file.filename}")
                
            except Exception as file_error:
                logger.error(f"Error uploading file {file.filename}: {str(file_error)}")
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": str(file_error)
                })
        
        # Log the upload event
        await get_monitoring().log_event("documents_uploaded", {"count": len(files), "user": user_email})
        
        # Check if any uploads failed
        failed_uploads = [r for r in results if r.get("status") == "error"]
        success = len(failed_uploads) == 0
        
        return {
            "success": success,
            "documents": results,
            "failed_count": len(failed_uploads),
            "message": f"Failed to upload {len(failed_uploads)} file(s)" if failed_uploads else "All files uploaded successfully"
        }
    except Exception as e:
        logger.error(f"Upload endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def get_documents(
    doc_manager: DocManagerDep,
    current_user: Dict[str, Any] = Depends(get_current_user),  # 일반 사용자도 문서 목록 조회 가능
    request: Request = None
):
    """Get list of documents (All authenticated users can view)"""
    try:
        user_id = current_user["user_id"]
        user_email = current_user["email"]
        
        # Check if user is admin
        is_admin = await get_auth_service().is_admin(user_id)
        
        # Get documents based on user role
        if is_admin:
            # Admin can see all documents
            documents = await doc_manager.list_documents()
        else:
            # Regular users can only see active documents (no management info)
            documents = await doc_manager.list_documents_for_users()
        
        # Log the access - document list view
        # Note: log_document_access requires document_id, so we'll use a different approach
        await audit_service.log_action(
            user_id=user_id,
            user_email=user_email,
            action_type="document_list_view",
            action_details={
                "document_count": len(documents),
                "user_role": "admin" if is_admin else "user"
            }
        )
        
        logger.info(f"User {user_email} accessed document list ({len(documents)} documents)")
        return {"documents": documents, "total": len(documents), "user_role": "admin" if is_admin else "user"}
        
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    doc_manager: DocManagerDep,
    current_user: Dict[str, Any] = Depends(get_current_admin),  # 관리자만 문서 삭제 가능
    request: Request = None
):
    """Delete a document (Admin only)"""
    try:
        user_id = current_user["user_id"]
        user_email = current_user["email"]
        
        # Get document info before deletion for audit
        doc_info = await doc_manager.get_document(doc_id)
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete the document
        result = await doc_manager.delete_document(doc_id)
        
        if result.get("status") == "success":
            # Log the deletion
            await audit_service.log_action(
                user_id=user_id,
                user_email=user_email,
                action_type="document_delete",
                action_details={
                    "document_id": doc_id,
                    "filename": doc_info.get("filename", "Unknown"),
                    "size_bytes": doc_info.get("size_bytes", 0)
                }
            )
            
            logger.info(f"Document {doc_id} deleted by {user_email}")
            return {"success": True, "status": "success", "message": "Document deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to delete document"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/chat")
async def chat(
    chat_interface: ChatInterfaceDep,
    message: str = Form(...), 
    session_id: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    settings = Depends(get_settings)
):
    """Chat with the assistant - Thread mode or Direct mode based on configuration"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        user_id = current_user["user_id"]
        user_email = current_user["email"]
        
        # Start async monitoring
        async_monitor = get_async_monitoring()
        
        # Log request start (non-blocking)
        async_monitor.log_event_nowait("chat_request_start", {
            "message_length": len(message),
            "session_id": session_id,
            "user": user_email
        })
        
        # Debug: log the chat interface type and mode
        logger.info(f"Chat interface type: {type(chat_interface).__name__}")
        logger.info(f"Thread mode enabled: {settings.use_threads}")
        
        # Choose interface based on configuration
        if not settings.use_threads:
            # Use Direct Chat without threads
            from core.direct_chat_interface import DirectChatInterface
            from core.dependencies import get_retrieval_client
            
            retrieval_client = get_retrieval_client()
            direct_chat = DirectChatInterface(
                retrieval_client=retrieval_client,
                model=settings.chat_model,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens
            )
            
            response = await direct_chat.process_message(
                message=message,
                session_id=session_id,
                user_id=user_id
            )
            logger.info("[CHAT] Using Direct mode (no threads)")
        else:
            # Use traditional Assistant API with threads
            response = await chat_interface.process_message(
                message=message,
                session_id=session_id,
                user_id=user_id,
                user_email=user_email
            )
            logger.info("[CHAT] Using Thread mode")
        
        # Calculate processing time
        processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        # Log metrics asynchronously (don't block response)
        asyncio.create_task(async_monitor.log_chat_metrics(
            session_id=session_id or f"user_{user_id}",
            message_length=len(message),
            response_length=len(response.get("response", "")),
            total_time_ms=processing_time,
            api_calls=response.get("metadata", {}).get("api_breakdown", {})
        ))
        
        # Audit logging asynchronously 
        asyncio.create_task(audit_service.log_chat_message(
            session_id=session_id or f"user_{user_id}",
            user_id=user_id,
            user_email=user_email,
            message=message,
            response=response.get("response", ""),
            tokens_used=response.get("usage", {}).get("total_tokens", 0),
            cost=response.get("usage", {}).get("cost", 0.0)
        ))
        
        # Track performance metric
        async_monitor.track_metric("chat_response_time_ms", processing_time)
        
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        
        # Log error asynchronously
        get_async_monitoring().log_event_nowait("chat_error", {
            "error": str(e),
            "message": message[:100],
            "processing_time_ms": (asyncio.get_event_loop().time() - start_time) * 1000
        })
        
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
async def search(
    retrieval_engine: RetrievalEngineDep,
    monitoring: MonitoringDep,
    query: str = Form(...), 
    limit: int = Form(10)
):
    """Search through documents using hybrid search"""
    try:
        results = await retrieval_engine.search(
            query=query,
            limit=limit
        )
        
        await monitoring.log_event("search_query", {
            "query": query,
            "results_count": len(results)
        })
        
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_stats(monitoring: MonitoringDep):
    """Get system statistics and usage metrics"""
    try:
        stats = await monitoring.get_statistics()
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health/components")
async def health_check_detailed(
    retrieval_client: RetrievalClientDep,
    monitoring: MonitoringDep
):
    """Detailed health check of all system components"""
    try:
        # Simple health check - just verify basic connectivity
        components = {}
        
        # Check OpenAI connection
        try:
            if retrieval_client.assistant_id:
                components["openai"] = {"healthy": True, "status": "connected"}
            else:
                components["openai"] = {"healthy": True, "status": "no assistant"}
        except:
            components["openai"] = {"healthy": False, "status": "error"}
        
        # Check Supabase connection
        try:
            supabase_manager = get_supabase_manager()
            if supabase_manager and supabase_manager.client:
                components["supabase"] = {"healthy": True, "status": "connected"}
            else:
                components["supabase"] = {"healthy": False, "status": "not initialized"}
        except:
            components["supabase"] = {"healthy": False, "status": "error"}
        
        # Overall health
        all_healthy = all(comp.get("healthy", False) for comp in components.values())
        
        return {
            "healthy": all_healthy,
            "components": components
        }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e)
        }

@router.get("/logs")
async def get_logs(level: Optional[str] = None, category: Optional[str] = None, limit: int = 100):
    """Get system logs with optional filtering"""
    try:
        logs = await get_monitoring().get_logs(level=level, category=category, limit=limit)
        return {
            "success": True,
            "logs": logs,
            "total": len(logs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{doc_id:path}/download")
async def download_document(
    doc_id: str,
    doc_manager: DocManagerDep
):
    """Download a document by its ID"""
    try:
        logger.info(f"Downloading document via Supabase: {doc_id}")
        result = await doc_manager.download_document(doc_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Return a redirect to the signed URL
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=result["url"], status_code=307)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        logger.error(f"Download error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Session Management Endpoints =====

@router.get("/sessions")
async def list_chat_sessions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0
):
    """List chat sessions for the authenticated user only"""
    from core.session_manager import get_session_manager
    session_manager = get_session_manager()
    
    # 로그인한 사용자의 ID로만 세션 조회
    user_id = current_user["user_id"]
    
    sessions = session_manager.list_sessions(
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    return {
        "success": True,
        "sessions": sessions,
        "total": len(sessions),
        "user_id": user_id
    }


@router.get("/sessions/{session_id}")
async def get_session_details(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a specific session with its messages (user's own sessions only)"""
    from core.session_manager import get_session_manager
    session_manager = get_session_manager()
    
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 사용자가 자신의 세션만 조회할 수 있도록 제한
    if session.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied: You can only access your own sessions")
    
    messages = session_manager.get_messages(session_id)
    stats = session_manager.get_session_stats(session_id)
    
    return {
        "success": True,
        "session": session,
        "messages": messages,
        "stats": stats
    }


@router.post("/sessions/{session_id}/title")
async def update_session_title(
    session_id: str, 
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update session title (user's own sessions only)"""
    from core.session_manager import get_session_manager
    session_manager = get_session_manager()
    
    title = request.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    
    # 먼저 세션이 사용자의 것인지 확인
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 사용자가 자신의 세션만 수정할 수 있도록 제한
    if session.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied: You can only update your own sessions")
    
    try:
        updated_session = session_manager.update_session(
            session_id, 
            {"session_title": title}
        )
        return {
            "success": True,
            "session": updated_session
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a chat session and all its messages (user's own sessions only)"""
    from core.session_manager import get_session_manager
    session_manager = get_session_manager()
    
    # 먼저 세션이 사용자의 것인지 확인
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 사용자가 자신의 세션만 삭제할 수 있도록 제한
    if session.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied: You can only delete your own sessions")
    
    success = session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "success": True,
        "message": "Session deleted successfully"
    }


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Export session data including all messages (user's own sessions only)"""
    from core.session_manager import get_session_manager
    session_manager = get_session_manager()
    
    # 먼저 세션이 사용자의 것인지 확인
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 사용자가 자신의 세션만 내보낼 수 있도록 제한
    if session.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied: You can only export your own sessions")
    
    try:
        export_data = session_manager.export_session(session_id)
        return export_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Usage Tracking Endpoints =====

@router.get("/usage/summary")
async def get_usage_summary(
    days: int = 7,
    service: Optional[str] = None
):
    """Get usage summary for specified period"""
    from core.usage_tracker import get_usage_tracker
    usage_tracker = get_usage_tracker()
    
    summary = usage_tracker.get_usage_summary(days=days, service=service)
    return summary


@router.get("/usage/daily")
async def get_daily_usage(days: int = 30):
    """Get daily usage statistics"""
    from core.usage_tracker import get_usage_tracker
    usage_tracker = get_usage_tracker()
    
    daily_usage = usage_tracker.get_daily_usage(days=days)
    return {
        "success": True,
        "days": days,
        "usage": daily_usage
    }


@router.get("/usage/limits")
async def check_usage_limits(
    daily_limit: float = 100.0,
    monthly_limit: float = 3000.0
):
    """Check if usage is within limits"""
    from core.usage_tracker import get_usage_tracker
    usage_tracker = get_usage_tracker()
    
    limits = usage_tracker.check_usage_limits(
        daily_limit=daily_limit,
        monthly_limit=monthly_limit
    )
    
    return {
        "success": True,
        "limits": limits,
        "alerts": {
            "daily_exceeded": limits.get("daily", {}).get("exceeded", False),
            "monthly_exceeded": limits.get("monthly", {}).get("exceeded", False)
        }
    }


# ===== BigQuery Integration Endpoints =====

@router.get("/bigquery/schemas")
async def get_bigquery_schemas():
    """Get available BigQuery schemas"""
    try:
        from core.schema_manager import SchemaManager
        schema_manager = SchemaManager()
        
        dataset_id = os.getenv("BIGQUERY_DATASET")
        schemas = await schema_manager.get_available_schemas(dataset_id)
        
        return {
            "success": True,
            "schemas": schemas,
            "count": len(schemas)
        }
    except Exception as e:
        logger.error(f"Error getting schemas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bigquery/query")
async def execute_bigquery_query(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Execute BigQuery query from natural language"""
    try:
        user_id = current_user["user_id"]
        user_email = current_user["email"]
        from core.bigquery_ai_query import BigQueryAI
        bigquery_ai = BigQueryAI()
        
        query = request.get("query")
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        language = request.get("language", "auto")
        
        result = await bigquery_ai.process_query(query, language)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Query failed"))
        
        # Log the query
        if result.get("success"):
            await audit_service.log_bigquery_query(
                user_id=user_id,
                user_email=user_email,
                natural_language_query=query,
                generated_sql=result.get("metadata", {}).get("sql", ""),
                rows_returned=result.get("metadata", {}).get("rows", 0),
                execution_time_ms=result.get("metadata", {}).get("execution_time_ms", 0),
                success=True
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing BigQuery query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bigquery/tables")
async def list_bigquery_tables():
    """List available BigQuery tables"""
    try:
        from core.schema_manager import SchemaManager
        schema_manager = SchemaManager()
        
        dataset_id = os.getenv("BIGQUERY_DATASET")
        schemas = await schema_manager.get_available_schemas(dataset_id)
        
        # Extract table information
        tables = []
        for schema in schemas:
            tables.append({
                "table_id": schema.get("table_id"),
                "table_name": schema.get("table_name"),
                "description": schema.get("table_description", ""),
                "row_count": schema.get("schema_json", {}).get("row_count", 0),
                "column_count": len(schema.get("columns_info", []))
            })
        
        return {
            "success": True,
            "tables": tables,
            "count": len(tables)
        }
    except Exception as e:
        logger.error(f"Error listing tables: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bigquery/schemas/refresh")
async def refresh_schemas(
    force: bool = False,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Manually refresh BigQuery schemas via admin interface"""
    try:
        logger.info(f"Admin {current_admin['email']} refreshing BigQuery schemas")
        from core.bigquery_schema_registry import BigQuerySchemaRegistry
        from core.schema_manager import SchemaManager
        
        # Initialize components
        schema_registry = BigQuerySchemaRegistry()
        schema_manager = SchemaManager()
        
        # Check if BigQuery is enabled
        if not schema_registry.enabled:
            raise HTTPException(status_code=503, detail="BigQuery integration is not enabled")
        
        # Get dataset from environment
        dataset_id = os.getenv("BIGQUERY_DATASET")
        project_id = os.getenv("GCP_PROJECT_ID")
        
        if not dataset_id or not project_id:
            raise HTTPException(status_code=500, detail="BigQuery configuration missing")
        
        # Refresh schemas
        refresh_result = await schema_registry.refresh_schemas(dataset_id)
        
        if not refresh_result.get("success"):
            raise HTTPException(status_code=500, detail=refresh_result.get("error", "Refresh failed"))
        
        # Store schemas in Supabase
        schemas = refresh_result.get("schemas", {})
        if schemas:
            await schema_manager.store_schemas(schemas, dataset_id, project_id)
        
        return {
            "success": True,
            "message": "Schemas refreshed successfully",
            "count": refresh_result.get("count", 0),
            "timestamp": refresh_result.get("timestamp")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing schemas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bigquery/schemas/status")
async def get_schema_status():
    """Get current schema status for admin dashboard"""
    try:
        from core.schema_manager import SchemaManager
        from core.bigquery_schema_registry import BigQuerySchemaRegistry
        
        schema_manager = SchemaManager()
        schema_registry = BigQuerySchemaRegistry()
        
        dataset_id = os.getenv("BIGQUERY_DATASET")
        
        # Get stored schemas
        schemas = await schema_manager.get_available_schemas(dataset_id)
        
        # Get last update time
        last_updated = None
        if schemas:
            last_updated = max(s.get("last_updated", "") for s in schemas)
        
        return {
            "success": True,
            "enabled": schema_registry.enabled,
            "dataset_id": dataset_id,
            "project_id": os.getenv("GCP_PROJECT_ID"),
            "schema_count": len(schemas),
            "last_updated": last_updated,
            "tables": [s.get("table_id") for s in schemas]
        }
        
    except Exception as e:
        logger.error(f"Error getting schema status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bigquery/schemas/changes")
async def get_schema_changes(limit: int = 50):
    """Get recent schema changes for admin dashboard"""
    try:
        from core.schema_manager import SchemaManager
        schema_manager = SchemaManager()
        
        changes = await schema_manager.get_recent_schema_changes(limit)
        
        return {
            "success": True,
            "changes": changes,
            "count": len(changes)
        }
        
    except Exception as e:
        logger.error(f"Error getting schema changes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bigquery/schemas/validate")
async def validate_schema_changes():
    """Validate pending schema changes"""
    try:
        from core.bigquery_schema_registry import BigQuerySchemaRegistry
        schema_registry = BigQuerySchemaRegistry()
        
        # Test connection
        connection_ok = schema_registry.test_connection()
        
        return {
            "success": True,
            "connection_valid": connection_ok,
            "message": "Connection validated" if connection_ok else "Connection failed"
        }
        
    except Exception as e:
        logger.error(f"Error validating schema: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# USER MANAGEMENT ENDPOINTS (Admin Only)
# =====================================================

@router.get("/users")
async def get_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Get list of users (Admin only)"""
    try:
        logger.info(f"Admin {current_admin['email']} fetching user list")
        
        supabase = get_supabase_manager()
        
        # Build query for user profiles
        query = supabase.client.table("user_profiles").select("*")
        
        # Apply filters
        if role and role != 'all':
            query = query.eq("role", role)
        
        if status and status != 'all':
            query = query.eq("status", status)
        
        if search:
            # Search in full_name or email
            query = query.or_(f"full_name.ilike.%{search}%,email.ilike.%{search}%")
        
        # Apply pagination and ordering
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        
        result = query.execute()
        
        # Get total count
        count_query = supabase.client.table("user_profiles").select("*", count="exact")
        if role and role != 'all':
            count_query = count_query.eq("role", role)
        if status and status != 'all':
            count_query = count_query.eq("status", status)
        if search:
            count_query = count_query.or_(f"full_name.ilike.%{search}%,email.ilike.%{search}%")
        
        count_result = count_query.execute()
        total_count = len(count_result.data) if count_result.data else 0
        
        # Format user data and get last_sign_in_at from auth.users
        users = []
        for user in result.data:
            # Get last_sign_in_at from auth.users table
            last_sign_in_at = None
            try:
                auth_user = supabase.client.auth.admin.get_user_by_id(user.get("id"))
                if auth_user and auth_user.user:
                    last_sign_in_at = auth_user.user.last_sign_in_at
            except Exception as e:
                logger.debug(f"Could not get last_sign_in_at for user {user.get('id')}: {e}")
            
            users.append({
                "id": user.get("id"),
                "username": user.get("username"),
                "full_name": user.get("full_name"),  # full_name 추가
                "email": user.get("email"),
                "role": user.get("role", "user"),
                "status": user.get("status", "request"),
                "created_at": user.get("created_at"),
                "updated_at": user.get("updated_at"),
                "last_activity": last_sign_in_at or user.get("updated_at")
            })
        
        # Log audit event
        await audit_service.log_admin_action(
            admin_id=current_admin["user_id"],
            admin_email=current_admin["email"],
            action="view_users",
            details={"count": len(users), "filters": {"search": search, "role": role}}
        )
        
        return {
            "success": True,
            "users": users,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users")
async def create_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Create a new user (Admin only)"""
    try:
        logger.info(f"Admin {current_admin['email']} creating new user: {email}")
        
        supabase = get_supabase_manager()
        
        # Create user in Supabase Auth
        auth_response = supabase.client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,  # Auto-confirm email for admin-created users
            "user_metadata": {
                "username": username,
                "role": role
            }
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Failed to create user")
        
        # Create user profile
        profile_data = {
            "id": auth_response.user.id,
            "username": username,
            "email": email,
            "role": role,
            "created_at": "now()",
            "updated_at": "now()"
        }
        
        profile_result = supabase.client.table("user_profiles").insert(profile_data).execute()
        
        # Log audit event
        await audit_service.log_admin_action(
            admin_id=current_admin["user_id"],
            admin_email=current_admin["email"],
            action="create_user",
            details={"new_user_email": email, "new_user_role": role}
        )
        
        return {
            "success": True,
            "message": "User created successfully",
            "user": {
                "id": auth_response.user.id,
                "username": username,
                "email": email,
                "role": role
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    username: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Update user information (Admin only)"""
    try:
        logger.info(f"Admin {current_admin['email']} updating user: {user_id}")
        
        # Prevent admin from modifying their own role
        if user_id == current_admin["user_id"] and role:
            raise HTTPException(status_code=400, detail="Cannot modify your own role")
        
        supabase = get_supabase_manager()
        
        # Update user profile
        update_data = {}
        if username:
            update_data["username"] = username
        if email:
            update_data["email"] = email
        if role:
            update_data["role"] = role
        
        if update_data:
            update_data["updated_at"] = "now()"
            
            result = supabase.client.table("user_profiles").update(update_data).eq("id", user_id).execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="User not found")
            
            # If email is being updated, also update in Auth
            if email:
                supabase.client.auth.admin.update_user_by_id(
                    user_id,
                    {"email": email}
                )
            
            # Log audit event
            await audit_service.log_admin_action(
                admin_id=current_admin["user_id"],
                admin_email=current_admin["email"],
                action="update_user",
                details={"updated_user_id": user_id, "changes": update_data}
            )
            
            return {
                "success": True,
                "message": "User updated successfully",
                "user": result.data[0]
            }
        else:
            return {
                "success": False,
                "message": "No data to update"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Delete a user (Admin only)"""
    try:
        logger.info(f"Admin {current_admin['email']} deleting user: {user_id}")
        
        # Prevent admin from deleting themselves
        if user_id == current_admin["user_id"]:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        supabase = get_supabase_manager()
        
        # Get user info before deletion
        user_result = supabase.client.table("user_profiles").select("*").eq("id", user_id).single().execute()
        
        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_email = user_result.data.get("email")
        
        # Delete from user_profiles first (due to foreign key constraints)
        profile_result = supabase.client.table("user_profiles").delete().eq("id", user_id).execute()
        
        # Delete from Auth
        try:
            supabase.client.auth.admin.delete_user(user_id)
        except Exception as auth_error:
            logger.warning(f"Failed to delete user from Auth: {auth_error}")
            # Continue even if Auth deletion fails
        
        # Log audit event
        await audit_service.log_admin_action(
            admin_id=current_admin["user_id"],
            admin_email=current_admin["email"],
            action="delete_user",
            details={"deleted_user_id": user_id, "deleted_user_email": user_email}
        )
        
        return {
            "success": True,
            "message": f"User {user_email} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/stats")
async def get_user_stats(
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Get user statistics (Admin only)"""
    try:
        supabase = get_supabase_manager()
        
        # Get all users
        all_users = supabase.client.table("user_profiles").select("*").execute()
        
        # Calculate stats
        total_users = len(all_users.data) if all_users.data else 0
        admins = sum(1 for u in all_users.data if u.get("role") == "admin") if all_users.data else 0
        regular_users = total_users - admins
        
        # Count by status
        pending_users = sum(1 for u in all_users.data if u.get("status") == "request") if all_users.data else 0
        active_users = sum(1 for u in all_users.data if u.get("status") == "active") if all_users.data else 0
        rejected_users = sum(1 for u in all_users.data if u.get("status") == "rejected") if all_users.data else 0
        
        # Get active sessions (from chat_sessions table)
        from datetime import datetime, timedelta
        cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        
        active_sessions = supabase.client.table("chat_sessions").select(
            "*", count="exact"
        ).gte("updated_at", cutoff_time).execute()
        
        active_count = len(active_sessions.data) if active_sessions.data else 0
        
        return {
            "success": True,
            "stats": {
                "total_users": total_users,
                "admins": admins,
                "regular_users": regular_users,
                "active_sessions_24h": active_count,
                "pending_users": pending_users,
                "active_users": active_users,
                "rejected_users": rejected_users
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{user_id}/approve")
async def approve_user(
    user_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Approve a pending user (Admin only)"""
    try:
        logger.info(f"Admin {current_admin['email']} approving user: {user_id}")
        
        supabase = get_supabase_manager()
        
        # Update user status to active
        result = supabase.client.table("user_profiles").update({
            "status": "active",
            "updated_at": "now()"
        }).eq("id", user_id).eq("status", "request").execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found or already processed")
        
        # Log audit event
        await audit_service.log_admin_action(
            admin_id=current_admin["user_id"],
            admin_email=current_admin["email"],
            action="approve_user",
            details={"approved_user_id": user_id}
        )
        
        return {
            "success": True,
            "message": "User approved successfully",
            "user": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{user_id}/reject")
async def reject_user(
    user_id: str,
    reason: Optional[str] = Form(None),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Reject a pending user (Admin only)"""
    try:
        logger.info(f"Admin {current_admin['email']} rejecting user: {user_id}")
        
        supabase = get_supabase_manager()
        
        # Update user status to rejected
        result = supabase.client.table("user_profiles").update({
            "status": "rejected",
            "updated_at": "now()"
        }).eq("id", user_id).eq("status", "request").execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found or already processed")
        
        # Log audit event
        await audit_service.log_admin_action(
            admin_id=current_admin["user_id"],
            admin_email=current_admin["email"],
            action="reject_user",
            details={"rejected_user_id": user_id, "reason": reason}
        )
        
        return {
            "success": True,
            "message": "User rejected successfully",
            "user": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))