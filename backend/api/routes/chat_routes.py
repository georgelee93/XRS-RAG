"""
Chat Routes
Handles all chat-related API endpoints
"""

from fastapi import APIRouter, Depends, Form, HTTPException
from typing import Dict, Any, Optional
import logging

from core.auth import get_current_user
from core.services.chat_service import get_chat_service
from core.config import get_settings

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("")
async def send_message(
    message: str = Form(...),
    session_id: Optional[str] = Form(None),
    strategy: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    settings = Depends(get_settings)
):
    """
    Send a chat message and get AI response
    
    Args:
        message: The user's message
        session_id: Optional session ID for conversation continuity
        strategy: Optional chat strategy ("thread" or "direct")
        current_user: Authenticated user information
        
    Returns:
        AI response with session information
    """
    try:
        user_id = current_user["user_id"]
        user_email = current_user["email"]
        
        # Get chat service
        chat_service = get_chat_service()
        
        # Ensure service is initialized
        await chat_service.initialize()
        
        # Process message
        response = await chat_service.process_message(
            message=message,
            session_id=session_id,
            user_id=user_id,
            strategy=strategy
        )
        
        # Log the interaction
        logger.info(
            f"Chat message processed for user {user_email} "
            f"(session: {response.get('session_id')})"
        )
        
        return {
            "success": True,
            "response": response.get("response"),
            "session_id": response.get("session_id"),
            "usage": response.get("usage", {}),
            "metadata": response.get("metadata", {})
        }
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/strategies")
async def get_chat_strategies(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get available chat strategies"""
    try:
        chat_service = get_chat_service()
        await chat_service.initialize()
        
        strategies = chat_service.get_available_strategies()
        default = chat_service.default_strategy
        
        return {
            "success": True,
            "strategies": strategies,
            "default": default
        }
        
    except Exception as e:
        logger.error(f"Error getting strategies: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get strategies: {str(e)}"
        )


@router.post("/strategy")
async def set_default_strategy(
    strategy: str = Form(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Set the default chat strategy"""
    try:
        chat_service = get_chat_service()
        await chat_service.initialize()
        
        chat_service.set_default_strategy(strategy)
        
        return {
            "success": True,
            "message": f"Default strategy set to: {strategy}"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error setting strategy: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set strategy: {str(e)}"
        )