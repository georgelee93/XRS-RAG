"""
Custom Exceptions
Standardized error handling across the application
"""

from typing import Optional, Any, Dict
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for the application"""
    
    # Authentication errors
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_FORBIDDEN = "AUTH_FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    
    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    DOC_NOT_FOUND = "DOC_NOT_FOUND"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    
    # Operation errors
    UPLOAD_FAILED = "UPLOAD_FAILED"
    STORAGE_ERROR = "STORAGE_ERROR"
    OPENAI_ERROR = "OPENAI_ERROR"
    DB_ERROR = "DB_ERROR"
    
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"
    
    # Rate limiting
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"


class RAGException(Exception):
    """Base exception for RAG application"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 400
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "success": False,
            "error": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class AuthenticationError(RAGException):
    """Authentication failed"""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, ErrorCode.AUTH_REQUIRED, status_code=401)


class AuthorizationError(RAGException):
    """Authorization failed"""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, ErrorCode.AUTH_FORBIDDEN, status_code=403)


class DocumentNotFoundError(RAGException):
    """Document not found"""
    
    def __init__(self, document_id: str):
        super().__init__(
            f"Document not found: {document_id}",
            ErrorCode.DOC_NOT_FOUND,
            {"document_id": document_id},
            status_code=404
        )


class SessionNotFoundError(RAGException):
    """Session not found"""
    
    def __init__(self, session_id: str):
        super().__init__(
            f"Session not found: {session_id}",
            ErrorCode.SESSION_NOT_FOUND,
            {"session_id": session_id},
            status_code=404
        )


class UploadError(RAGException):
    """File upload failed"""
    
    def __init__(self, filename: str, reason: str):
        super().__init__(
            f"Upload failed for {filename}: {reason}",
            ErrorCode.UPLOAD_FAILED,
            {"filename": filename, "reason": reason},
            status_code=400
        )


class StorageError(RAGException):
    """Storage operation failed"""
    
    def __init__(self, operation: str, reason: str):
        super().__init__(
            f"Storage {operation} failed: {reason}",
            ErrorCode.STORAGE_ERROR,
            {"operation": operation, "reason": reason},
            status_code=500
        )


class OpenAIError(RAGException):
    """OpenAI API error"""
    
    def __init__(self, operation: str, reason: str):
        super().__init__(
            f"OpenAI {operation} failed: {reason}",
            ErrorCode.OPENAI_ERROR,
            {"operation": operation, "reason": reason},
            status_code=502
        )


class DatabaseError(RAGException):
    """Database operation failed"""
    
    def __init__(self, operation: str, reason: str):
        super().__init__(
            f"Database {operation} failed: {reason}",
            ErrorCode.DB_ERROR,
            {"operation": operation, "reason": reason},
            status_code=500
        )


class ConfigurationError(RAGException):
    """Configuration error"""
    
    def __init__(self, setting: str, reason: str):
        super().__init__(
            f"Configuration error for {setting}: {reason}",
            ErrorCode.CONFIG_ERROR,
            {"setting": setting, "reason": reason},
            status_code=500
        )


class ValidationError(RAGException):
    """Validation error"""
    
    def __init__(self, field: str, reason: str):
        super().__init__(
            f"Validation failed for {field}: {reason}",
            ErrorCode.VALIDATION_ERROR,
            {"field": field, "reason": reason},
            status_code=422
        )


class RateLimitError(RAGException):
    """Rate limit exceeded"""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after} seconds",
            ErrorCode.RATE_LIMITED,
            {"retry_after": retry_after},
            status_code=429
        )


class QuotaExceededError(RAGException):
    """Quota exceeded"""
    
    def __init__(self, resource: str, limit: int, current: int):
        super().__init__(
            f"Quota exceeded for {resource}. Limit: {limit}, Current: {current}",
            ErrorCode.QUOTA_EXCEEDED,
            {"resource": resource, "limit": limit, "current": current},
            status_code=429
        )