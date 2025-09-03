"""
Dependency Injection Container
Manages application dependencies and lifecycle
"""

from functools import lru_cache
from typing import Optional
import logging

from core.retrieval_client import RetrievalAPIClient
from core.document_manager_supabase import DocumentManagerSupabase
from core.enhanced_chat_interface import EnhancedChatInterface
from core.enhanced_chat_interface_parallel import ParallelEnhancedChatInterface
from core.retrieval_engine import HybridRAGEngine
from core.monitoring import MonitoringSystem
from core.supabase_client import get_supabase_manager
from core.session_manager import get_session_manager
from core.bigquery_ai_query import BigQueryAI
import os

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Centralized dependency injection container.
    Manages singleton instances and dependency lifecycle.
    """
    
    def __init__(self):
        """Initialize the container with no instances"""
        self._retrieval_client: Optional[RetrievalAPIClient] = None
        self._doc_manager: Optional[DocumentManagerSupabase] = None
        self._chat_interface: Optional[EnhancedChatInterface] = None
        self._retrieval_engine: Optional[HybridRAGEngine] = None
        self._monitoring: Optional[MonitoringSystem] = None
        self._bigquery_ai: Optional[BigQueryAI] = None
        logger.info("Dependency container initialized")
    
    @property
    def retrieval_client(self) -> RetrievalAPIClient:
        """Get or create retrieval client singleton"""
        if self._retrieval_client is None:
            self._retrieval_client = RetrievalAPIClient()
            logger.info("Created RetrievalAPIClient instance")
        return self._retrieval_client
    
    @property
    def doc_manager(self) -> DocumentManagerSupabase:
        """Get or create document manager singleton"""
        if self._doc_manager is None:
            self._doc_manager = DocumentManagerSupabase(self.retrieval_client)
            logger.info("Created DocumentManagerSupabase instance")
        return self._doc_manager
    
    @property
    def chat_interface(self) -> EnhancedChatInterface:
        """Get or create chat interface singleton"""
        if self._chat_interface is None:
            use_parallel = os.getenv("USE_PARALLEL_PROCESSING", "true").lower() == "true"
            
            if use_parallel:
                self._chat_interface = ParallelEnhancedChatInterface(self.retrieval_client)
                logger.info("Created ParallelEnhancedChatInterface instance")
            else:
                self._chat_interface = EnhancedChatInterface(self.retrieval_client)
                logger.info("Created EnhancedChatInterface instance")
        
        return self._chat_interface
    
    @property
    def retrieval_engine(self) -> HybridRAGEngine:
        """Get or create retrieval engine singleton"""
        if self._retrieval_engine is None:
            self._retrieval_engine = HybridRAGEngine(self.retrieval_client)
            logger.info("Created HybridRAGEngine instance")
        return self._retrieval_engine
    
    @property
    def monitoring(self) -> MonitoringSystem:
        """Get or create monitoring system singleton"""
        if self._monitoring is None:
            self._monitoring = MonitoringSystem()
            logger.info("Created MonitoringSystem instance")
        return self._monitoring
    
    @property
    def bigquery_ai(self) -> BigQueryAI:
        """Get or create BigQuery AI singleton"""
        if self._bigquery_ai is None:
            self._bigquery_ai = BigQueryAI()
            logger.info("Created BigQueryAI instance")
        return self._bigquery_ai
    
    @property
    def supabase_manager(self):
        """Get Supabase manager (uses existing singleton pattern for now)"""
        return get_supabase_manager()
    
    @property
    def session_manager(self):
        """Get session manager (uses existing singleton pattern for now)"""
        return get_session_manager()
    
    def reset(self):
        """Reset all instances (useful for testing)"""
        self._retrieval_client = None
        self._doc_manager = None
        self._chat_interface = None
        self._retrieval_engine = None
        self._monitoring = None
        self._bigquery_ai = None
        logger.info("Dependency container reset")
    
    async def cleanup(self):
        """Cleanup resources on shutdown"""
        logger.info("Cleaning up dependencies...")
        
        # Cleanup any resources that need it
        if self._monitoring:
            try:
                # If monitoring has cleanup method
                if hasattr(self._monitoring, 'cleanup'):
                    await self._monitoring.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up monitoring: {e}")
        
        # Reset all instances
        self.reset()
        logger.info("Dependencies cleaned up")


# Global container instance
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get the global dependency container"""
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container


# FastAPI dependency functions
from fastapi import Depends
from typing import Annotated


def get_retrieval_client() -> RetrievalAPIClient:
    """FastAPI dependency for retrieval client"""
    return get_container().retrieval_client


def get_doc_manager() -> DocumentManagerSupabase:
    """FastAPI dependency for document manager"""
    return get_container().doc_manager


def get_chat_interface() -> EnhancedChatInterface:
    """FastAPI dependency for chat interface"""
    return get_container().chat_interface


def get_retrieval_engine() -> HybridRAGEngine:
    """FastAPI dependency for retrieval engine"""
    return get_container().retrieval_engine


def get_monitoring() -> MonitoringSystem:
    """FastAPI dependency for monitoring"""
    return get_container().monitoring


# Type hints for cleaner route definitions
RetrievalClientDep = Annotated[RetrievalAPIClient, Depends(get_retrieval_client)]
DocManagerDep = Annotated[DocumentManagerSupabase, Depends(get_doc_manager)]
ChatInterfaceDep = Annotated[EnhancedChatInterface, Depends(get_chat_interface)]
RetrievalEngineDep = Annotated[HybridRAGEngine, Depends(get_retrieval_engine)]
MonitoringDep = Annotated[MonitoringSystem, Depends(get_monitoring)]