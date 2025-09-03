"""
Unified Database Service
Single Supabase client with proper connection pooling and management
"""

import logging
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import threading

from supabase import create_client, Client
from ..config import get_settings

logger = logging.getLogger(__name__)


class UnifiedDatabaseService:
    """
    Unified database service with singleton pattern
    Manages single Supabase client with proper connection pooling
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the database service (only runs once due to singleton)"""
        if self._initialized:
            return
            
        self.settings = get_settings()
        self.client: Optional[Client] = None
        self._initialize_client()
        self._initialized = True
    
    def _initialize_client(self):
        """Initialize Supabase client with proper configuration"""
        try:
            # Use service key if available for admin operations
            if self.settings.supabase_service_key:
                self.client = create_client(
                    self.settings.supabase_url,
                    self.settings.supabase_service_key
                )
                logger.info("Database service initialized with service key")
            else:
                # Fall back to anon key for regular operations
                self.client = create_client(
                    self.settings.supabase_url,
                    self.settings.supabase_anon_key
                )
                logger.info("Database service initialized with anon key")
                
        except Exception as e:
            logger.error(f"Failed to initialize database client: {str(e)}")
            raise
    
    def reset_connection(self):
        """Reset the database connection"""
        try:
            self._initialize_client()
            logger.info("Database connection reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset database connection: {str(e)}")
            raise
    
    @contextmanager
    def get_client(self):
        """
        Context manager for database operations
        Ensures proper connection handling
        """
        if not self.client:
            self._initialize_client()
        
        try:
            yield self.client
        except Exception as e:
            logger.error(f"Database operation failed: {str(e)}")
            # Attempt to reset connection on error
            self.reset_connection()
            raise
    
    # Convenience methods for common operations
    
    def select(self, table: str, columns: str = "*", **filters) -> List[Dict[str, Any]]:
        """Select records from a table"""
        with self.get_client() as client:
            query = client.table(table).select(columns)
            
            for key, value in filters.items():
                if value is not None:
                    query = query.eq(key, value)
            
            result = query.execute()
            return result.data if result.data else []
    
    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a record into a table"""
        with self.get_client() as client:
            result = client.table(table).insert(data).execute()
            return result.data[0] if result.data else {}
    
    def update(self, table: str, data: Dict[str, Any], **filters) -> Dict[str, Any]:
        """Update records in a table"""
        with self.get_client() as client:
            query = client.table(table).update(data)
            
            for key, value in filters.items():
                if value is not None:
                    query = query.eq(key, value)
            
            result = query.execute()
            return result.data[0] if result.data else {}
    
    def delete(self, table: str, **filters) -> bool:
        """Delete records from a table"""
        with self.get_client() as client:
            query = client.table(table).delete()
            
            for key, value in filters.items():
                if value is not None:
                    query = query.eq(key, value)
            
            result = query.execute()
            return bool(result.data)
    
    def upsert(self, table: str, data: Dict[str, Any], on_conflict: str = None) -> Dict[str, Any]:
        """Upsert a record into a table"""
        with self.get_client() as client:
            result = client.table(table).upsert(
                data,
                on_conflict=on_conflict
            ).execute()
            return result.data[0] if result.data else {}
    
    # Storage operations
    
    def upload_file(self, bucket: str, path: str, file_data: bytes, content_type: str = None) -> Dict[str, Any]:
        """Upload a file to storage"""
        with self.get_client() as client:
            options = {"upsert": "true"}
            if content_type:
                options["content-type"] = content_type
            
            result = client.storage.from_(bucket).upload(path, file_data, options)
            return result
    
    def download_file(self, bucket: str, path: str) -> bytes:
        """Download a file from storage"""
        with self.get_client() as client:
            return client.storage.from_(bucket).download(path)
    
    def delete_file(self, bucket: str, paths: List[str]) -> bool:
        """Delete files from storage"""
        with self.get_client() as client:
            result = client.storage.from_(bucket).remove(paths)
            return bool(result)
    
    def list_files(self, bucket: str, path: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """List files in storage"""
        with self.get_client() as client:
            result = client.storage.from_(bucket).list(path, {"limit": limit})
            return result if result else []
    
    # Auth operations (if needed)
    
    def sign_in_with_password(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in a user with email and password"""
        with self.get_client() as client:
            result = client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return result.dict() if result else {}
    
    def sign_up(self, email: str, password: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Sign up a new user"""
        with self.get_client() as client:
            options = {"email": email, "password": password}
            if metadata:
                options["options"] = {"data": metadata}
            
            result = client.auth.sign_up(options)
            return result.dict() if result else {}
    
    def sign_out(self) -> bool:
        """Sign out the current user"""
        with self.get_client() as client:
            client.auth.sign_out()
            return True
    
    def get_user(self, jwt: str) -> Optional[Dict[str, Any]]:
        """Get user from JWT token"""
        with self.get_client() as client:
            result = client.auth.get_user(jwt)
            return result.dict() if result else None


# Global instance getter
_database_service: Optional[UnifiedDatabaseService] = None


def get_database_service() -> UnifiedDatabaseService:
    """Get or create the singleton database service instance"""
    global _database_service
    if _database_service is None:
        _database_service = UnifiedDatabaseService()
    return _database_service


# Alias for backward compatibility
get_supabase_manager = get_database_service