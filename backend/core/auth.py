"""
Authentication and authorization module for the RAG application
Handles JWT token verification and user role management
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWTError
import os
import logging
from datetime import datetime, timedelta
import httpx

from .supabase_client import get_supabase_manager
from .config import get_settings

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)

class AuthError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=401, detail=detail)

class AuthService:
    def __init__(self):
        self.supabase = get_supabase_manager()
        # Use get_env_var with required=False for Cloud Run compatibility
        from .utils import get_env_var
        self.jwt_secret = get_env_var("SUPABASE_JWT_SECRET", required=False)
        
        # Debug: Check Supabase client configuration
        logger.info(f"AuthService initialized with Supabase URL: {self.supabase.url}")
        logger.info(f"Supabase client type: {type(self.supabase.client)}")
        
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token from Supabase"""
        try:
            # Decode JWT token
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"],
                audience="authenticated"
            )
            
            # Get user from Supabase
            user_id = payload.get("sub")
            if not user_id:
                raise AuthError("Invalid token: no user ID")
            
            # Get user profile
            profile = await self.get_user_profile(user_id)
            
            # Check if user is active (only if status field exists)
            if profile and "status" in profile and profile.get("status") != "active":
                status = profile.get("status", "unknown")
                if status == "request":
                    raise AuthError("Your account is pending approval. Please wait for admin approval.")
                elif status == "rejected":
                    raise AuthError("Your account has been rejected. Please contact support.")
                else:
                    raise AuthError("Your account is not active. Please contact support.")
            
            return {
                "user_id": user_id,
                "username": profile.get("username") if profile else None,
                "email": payload.get("email"),
                "role": profile.get("role", "user") if profile else "user",
                "status": profile.get("status", "active") if profile else "active",
                "profile": profile
            }
            
        except PyJWTError as e:
            logger.error(f"JWT decode error: {str(e)}")
            raise AuthError("Invalid token")
        except Exception as e:
            logger.error(f"Auth error: {str(e)}")
            raise AuthError("Authentication failed")
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from database"""
        try:
            # Debug: Check if client has proper headers
            logger.debug(f"Supabase client headers: {self.supabase.client.headers if hasattr(self.supabase.client, 'headers') else 'No headers attribute'}")
            logger.debug(f"Fetching profile for user_id: {user_id}")
            
            result = self.supabase.client.table("user_profiles").select("*").eq(
                "id", user_id
            ).single().execute()
            
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Error fetching user profile: {str(e)}")
            logger.error(f"Full error details: {e}")
            return None
    
    async def is_admin(self, user_id: str) -> bool:
        """Check if user is admin"""
        profile = await self.get_user_profile(user_id)
        return profile.get("role") == "admin" if profile else False

# Lazy initialization of auth service
_auth_service = None

def get_auth_service() -> AuthService:
    """Get or create auth service instance"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service

# Dependency functions
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """Get current authenticated user"""
    if not credentials:
        raise AuthError("Authentication required")
    
    auth_service = get_auth_service()
    return await auth_service.verify_token(credentials.credentials)

async def get_current_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current admin user"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def require_admin_role(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Require admin role for access"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Payload data for the token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "aud": "authenticated"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.supabase_jwt_secret or settings.supabase_anon_key,
        algorithm="HS256"
    )
    
    return encoded_jwt