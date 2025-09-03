"""
Main router module that combines all route modules
"""

from fastapi import APIRouter

# Import all route modules
from .auth_routes import router as auth_router
from .chat_routes import router as chat_router
from .document_routes import router as document_router
from .session_routes import router as session_router
from .health_routes import router as health_router
from .usage_routes import router as usage_router

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(auth_router)
router.include_router(chat_router)
router.include_router(document_router)
router.include_router(session_router)
router.include_router(health_router)
router.include_router(usage_router)

# Export all routers for direct access if needed
__all__ = [
    'router',
    'auth_router',
    'chat_router', 
    'document_router',
    'session_router',
    'health_router',
    'usage_router'
]