"""
Main Application Entry Point
FastAPI application for RAG chatbot backend
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import get_settings
from core.logging_config import setup_logging
from api.routes import router
from core.exceptions import RAGException

# Setup logging
setup_logging("rag-backend")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting RAG backend service...")
    settings = get_settings()
    logger.info(f"Environment: {settings.app_env}")
    
    # Get assistant config
    assistant_config = settings.get_assistant_config()
    logger.info(f"OpenAI Assistant ID: {assistant_config.get('assistant_id', 'Not configured')}")
    
    logger.info(f"Supabase configured: {bool(settings.supabase_url)}")
    logger.info(f"BigQuery enabled: {settings.enable_bigquery}")
    
    # Log CORS configuration
    cors_origins = settings.get_cors_origins()
    logger.info(f"CORS origins ({len(cors_origins)}): {', '.join(cors_origins)}")
    
    yield
    
    logger.info("Shutting down RAG backend service...")


# Create FastAPI app
app = FastAPI(
    title="RAG Chatbot Backend",
    description="Backend service for document-based AI chatbot",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RAGException)
async def rag_exception_handler(request, exc: RAGException):
    """Handle custom RAG exceptions"""
    return JSONResponse(
        status_code=400,
        content=exc.to_dict()
    )


# Include routes
app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "RAG Chatbot Backend",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,  # Enable reload for development
        log_level="info"
    )