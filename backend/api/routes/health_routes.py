"""
Health Check Routes
System health and monitoring endpoints
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
import logging
import psutil
import os
from datetime import datetime

from core.config import get_settings
from core.services.database_service import get_database_service

router = APIRouter(prefix="/api/health", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "RAG Chatbot Backend",
        "version": "2.0.0"
    }


@router.get("/components")
async def component_health():
    """Detailed health check of all system components"""
    
    components = {}
    
    # Check database connection
    try:
        db_service = get_database_service()
        with db_service.get_client() as client:
            # Try a simple query
            result = client.table("documents").select("id").limit(1).execute()
        components["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        components["database"] = {
            "status": "unhealthy",
            "message": f"Database error: {str(e)}"
        }
    
    # Check OpenAI API
    try:
        settings = get_settings()
        if settings.openai_api_key:
            components["openai"] = {
                "status": "healthy",
                "message": "OpenAI API key configured"
            }
        else:
            components["openai"] = {
                "status": "unhealthy",
                "message": "OpenAI API key not configured"
            }
    except Exception as e:
        components["openai"] = {
            "status": "unhealthy",
            "message": f"Configuration error: {str(e)}"
        }
    
    # Check assistant configuration
    try:
        settings = get_settings()
        assistant_config = settings.get_assistant_config()
        if assistant_config.get("assistant_id") and assistant_config.get("vector_store_id"):
            components["assistant"] = {
                "status": "healthy",
                "message": "Assistant configured",
                "assistant_id": assistant_config["assistant_id"],
                "vector_store_id": assistant_config["vector_store_id"]
            }
        else:
            components["assistant"] = {
                "status": "warning",
                "message": "Assistant not fully configured"
            }
    except Exception as e:
        components["assistant"] = {
            "status": "unhealthy",
            "message": f"Assistant configuration error: {str(e)}"
        }
    
    # Overall health
    unhealthy_count = sum(1 for c in components.values() if c["status"] == "unhealthy")
    warning_count = sum(1 for c in components.values() if c["status"] == "warning")
    
    overall_status = "healthy"
    if unhealthy_count > 0:
        overall_status = "unhealthy"
    elif warning_count > 0:
        overall_status = "degraded"
    
    return {
        "healthy": overall_status == "healthy",
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "components": components
    }


@router.get("/metrics")
async def system_metrics():
    """Get system metrics and resource usage"""
    
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_usage = {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "free": memory.free
        }
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_usage = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent
        }
        
        # Process info
        process = psutil.Process(os.getpid())
        process_info = {
            "pid": process.pid,
            "memory_percent": process.memory_percent(),
            "cpu_percent": process.cpu_percent(),
            "num_threads": process.num_threads(),
            "create_time": datetime.fromtimestamp(process.create_time()).isoformat()
        }
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count
                },
                "memory": memory_usage,
                "disk": disk_usage,
                "process": process_info
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/readiness")
async def readiness_check():
    """
    Kubernetes-style readiness probe
    Returns 200 if the service is ready to accept requests
    """
    try:
        # Check if all critical components are ready
        db_service = get_database_service()
        settings = get_settings()
        
        # Try to access database
        with db_service.get_client() as client:
            client.table("documents").select("id").limit(1).execute()
        
        # Check OpenAI configuration
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        return {
            "ready": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail={
                "ready": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/liveness")
async def liveness_check():
    """
    Kubernetes-style liveness probe
    Returns 200 if the service is alive
    """
    return {
        "alive": True,
        "timestamp": datetime.now().isoformat()
    }