"""Authentication API Router."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.garmin_service import GarminService, AuthenticationError
from config import settings

router = APIRouter()

# Global garmin service instance (for session management)
_garmin_service: Optional[GarminService] = None


class LoginRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    use_saved_tokens: bool = True


class LoginResponse(BaseModel):
    success: bool
    user: Optional[dict] = None
    message: str


class UserResponse(BaseModel):
    authenticated: bool
    user: Optional[dict] = None


def get_garmin_service() -> GarminService:
    """Get or create garmin service instance."""
    global _garmin_service
    if _garmin_service is None or not _garmin_service.is_authenticated:
        _garmin_service = GarminService()
    return _garmin_service


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login to Garmin Connect."""
    global _garmin_service
    
    try:
        garmin = GarminService()
        
        email = request.email or settings.garmin_email
        password = request.password or settings.garmin_password
        
        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )
        
        success = garmin.login(
            email=email,
            password=password,
            use_saved_tokens=request.use_saved_tokens
        )
        
        if success:
            _garmin_service = garmin
            return LoginResponse(
                success=True,
                user=garmin.user_profile,
                message="Successfully connected to Garmin Connect"
            )
        else:
            return LoginResponse(
                success=False,
                message="Failed to connect. Please check your credentials."
            )
            
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection error: {str(e)}"
        )


@router.get("/status", response_model=UserResponse)
async def get_auth_status():
    """Check authentication status."""
    global _garmin_service
    
    if _garmin_service and _garmin_service.is_authenticated:
        return UserResponse(
            authenticated=True,
            user=_garmin_service.user_profile
        )
    return UserResponse(authenticated=False)


@router.post("/logout")
async def logout():
    """Logout from Garmin Connect."""
    global _garmin_service
    
    if _garmin_service:
        _garmin_service.logout()
        _garmin_service = None
    
    return {"success": True, "message": "Logged out successfully"}


@router.get("/config")
async def get_config():
    """Get app configuration status."""
    return {
        "has_garmin_credentials": bool(settings.garmin_email and settings.garmin_password),
        "has_gemini_key": bool(settings.gemini_api_key),
        "has_saved_tokens": Path(settings.garmin_token_path).exists()
    }
