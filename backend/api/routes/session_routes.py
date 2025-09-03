"""
Session Routes
Handles all session management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, Any, Optional
import logging

from core.auth import get_current_user
from core.session_manager import get_session_manager
from core.config import get_settings

router = APIRouter(prefix="/api/sessions", tags=["sessions"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List chat sessions for the authenticated user
    
    Args:
        limit: Maximum number of sessions to return
        offset: Offset for pagination
        current_user: Authenticated user information
        
    Returns:
        List of session records
    """
    try:
        session_manager = get_session_manager()
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
            "user_id": user_id,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"List sessions error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sessions: {str(e)}"
        )


@router.get("/{session_id}")
async def get_session_details(
    session_id: str,
    include_messages: bool = Query(True),
    message_limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get details for a specific session
    
    Args:
        session_id: ID of the session
        include_messages: Whether to include message history
        message_limit: Maximum number of messages to return
        current_user: Authenticated user information
        
    Returns:
        Session details with optional message history
    """
    try:
        session_manager = get_session_manager()
        
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        # Check ownership
        if session.get("user_id") != current_user["user_id"]:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only access your own sessions"
            )
        
        response = {
            "success": True,
            "session": session
        }
        
        # Include messages if requested
        if include_messages:
            messages = session_manager.get_messages(
                session_id,
                limit=message_limit
            )
            response["messages"] = messages
        
        # Get session statistics
        stats = session_manager.get_session_stats(session_id)
        response["stats"] = stats
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session: {str(e)}"
        )


@router.post("/{session_id}/title")
async def update_session_title(
    session_id: str,
    title: str = Body(..., embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update the title of a session"""
    try:
        session_manager = get_session_manager()
        
        # Get session to check ownership
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        if session.get("user_id") != current_user["user_id"]:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only update your own sessions"
            )
        
        # Update title
        updated_session = session_manager.update_session(
            session_id,
            {"session_title": title}
        )
        
        return {
            "success": True,
            "message": "Session title updated",
            "session": updated_session
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update session title error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update session title: {str(e)}"
        )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a session and all its messages"""
    try:
        session_manager = get_session_manager()
        
        # Get session to check ownership
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        if session.get("user_id") != current_user["user_id"]:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only delete your own sessions"
            )
        
        # Delete session
        success = session_manager.delete_session(session_id)
        
        if success:
            return {
                "success": True,
                "message": "Session deleted successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete session"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete session error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete session: {str(e)}"
        )


@router.post("/{session_id}/export")
async def export_session(
    session_id: str,
    format: str = Query("json", regex="^(json|txt|md)$"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Export session data in various formats
    
    Args:
        session_id: ID of the session to export
        format: Export format (json, txt, or md)
        current_user: Authenticated user information
        
    Returns:
        Exported session data in requested format
    """
    try:
        session_manager = get_session_manager()
        
        # Get session and check ownership
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        if session.get("user_id") != current_user["user_id"]:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only export your own sessions"
            )
        
        # Get all messages
        messages = session_manager.get_messages(session_id, limit=1000)
        
        if format == "json":
            # Return raw JSON
            return {
                "session": session,
                "messages": messages,
                "exported_at": datetime.now().isoformat()
            }
        
        elif format == "txt":
            # Format as plain text
            text_lines = [
                f"Session: {session.get('session_title', 'Untitled')}",
                f"Created: {session.get('created_at')}",
                f"Messages: {len(messages)}",
                "-" * 50,
                ""
            ]
            
            for msg in messages:
                role = "User" if msg["role"] == "user" else "Assistant"
                text_lines.append(f"{role}: {msg.get('content', '')}")
                text_lines.append("")
            
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(
                content="\n".join(text_lines),
                media_type="text/plain",
                headers={
                    "Content-Disposition": f"attachment; filename=session_{session_id}.txt"
                }
            )
        
        elif format == "md":
            # Format as Markdown
            md_lines = [
                f"# {session.get('session_title', 'Chat Session')}",
                f"*Created: {session.get('created_at')}*",
                f"*Total Messages: {len(messages)}*",
                "",
                "---",
                ""
            ]
            
            for msg in messages:
                if msg["role"] == "user":
                    md_lines.append(f"**User**: {msg.get('content', '')}")
                else:
                    md_lines.append(f"**Assistant**: {msg.get('content', '')}")
                md_lines.append("")
            
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(
                content="\n".join(md_lines),
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename=session_{session_id}.md"
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export session error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export session: {str(e)}"
        )


from datetime import datetime  # Import at the end to avoid circular imports