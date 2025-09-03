"""
Authentication Routes
Handles user authentication and authorization
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import jwt

from core.config import get_settings
from core.services.database_service import get_database_service
from core.auth import get_current_user, create_access_token

router = APIRouter(prefix="/api/auth", tags=["authentication"])
logger = logging.getLogger(__name__)
security = HTTPBearer()


@router.post("/login")
async def login(
    email: str = Body(...),
    password: str = Body(...),
    settings = Depends(get_settings)
):
    """
    User login endpoint
    
    Args:
        email: User email
        password: User password
        
    Returns:
        Access token and user information
    """
    try:
        db_service = get_database_service()
        
        # Authenticate with Supabase
        auth_result = db_service.sign_in_with_password(email, password)
        
        if not auth_result or not auth_result.get("session"):
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )
        
        session = auth_result["session"]
        user = auth_result["user"]
        
        # Create our own JWT token for API access
        access_token = create_access_token(
            data={
                "sub": user["id"],
                "email": user["email"],
                "user_id": user["id"]
            },
            expires_delta=timedelta(hours=24)
        )
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "created_at": user.get("created_at")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/register")
async def register(
    email: str = Body(...),
    password: str = Body(...),
    full_name: Optional[str] = Body(None),
    settings = Depends(get_settings)
):
    """
    User registration endpoint
    
    Args:
        email: User email
        password: User password
        full_name: Optional full name
        
    Returns:
        Registration result
    """
    try:
        db_service = get_database_service()
        
        # Register with Supabase
        metadata = {}
        if full_name:
            metadata["full_name"] = full_name
        
        auth_result = db_service.sign_up(
            email=email,
            password=password,
            metadata=metadata
        )
        
        if not auth_result:
            raise HTTPException(
                status_code=400,
                detail="Registration failed"
            )
        
        return {
            "success": True,
            "message": "Registration successful. Please check your email to verify your account.",
            "user": {
                "email": email
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        
        # Check for common errors
        error_message = str(e).lower()
        if "already registered" in error_message or "already exists" in error_message:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
        
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/logout")
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    User logout endpoint
    
    Args:
        current_user: Authenticated user information
        
    Returns:
        Logout confirmation
    """
    try:
        db_service = get_database_service()
        db_service.sign_out()
        
        return {
            "success": True,
            "message": "Logged out successfully"
        }
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        # Logout should always succeed from the client's perspective
        return {
            "success": True,
            "message": "Logged out successfully"
        }


@router.get("/me")
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current user information
    
    Args:
        current_user: Authenticated user information
        
    Returns:
        User profile information
    """
    try:
        return {
            "success": True,
            "user": {
                "id": current_user["user_id"],
                "email": current_user["email"],
                "authenticated": True
            }
        }
        
    except Exception as e:
        logger.error(f"Get user info error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user information: {str(e)}"
        )


@router.post("/refresh")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings = Depends(get_settings)
):
    """
    Refresh access token
    
    Args:
        credentials: Current bearer token
        
    Returns:
        New access token
    """
    try:
        token = credentials.credentials
        
        # Decode the current token (even if expired, for refresh)
        try:
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                options={"verify_exp": False}  # Don't verify expiration for refresh
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
        
        # Check if token is not too old (e.g., within 7 days)
        if "exp" in payload:
            exp_timestamp = payload["exp"]
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
            if datetime.now() - exp_datetime > timedelta(days=7):
                raise HTTPException(
                    status_code=401,
                    detail="Token too old for refresh. Please login again."
                )
        
        # Create new token
        new_token = create_access_token(
            data={
                "sub": payload.get("sub"),
                "email": payload.get("email"),
                "user_id": payload.get("user_id")
            },
            expires_delta=timedelta(hours=24)
        )
        
        return {
            "success": True,
            "access_token": new_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh token: {str(e)}"
        )


@router.post("/verify")
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Verify if a token is valid
    
    Args:
        credentials: Bearer token to verify
        
    Returns:
        Token validation result
    """
    try:
        # This will raise an exception if the token is invalid
        user = await get_current_user(credentials)
        
        return {
            "success": True,
            "valid": True,
            "user": {
                "id": user["user_id"],
                "email": user["email"]
            }
        }
        
    except HTTPException as e:
        return {
            "success": False,
            "valid": False,
            "error": e.detail
        }
    except Exception as e:
        return {
            "success": False,
            "valid": False,
            "error": str(e)
        }