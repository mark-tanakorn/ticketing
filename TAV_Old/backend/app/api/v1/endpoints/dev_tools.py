"""
Dev Tools Endpoint

Development-only endpoints for testing and debugging.
⚠️ These endpoints should be DISABLED in production!
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.jwt_manager import JwtTokenManager
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/dev",
    tags=["Dev Tools"],
    responses={
        403: {"description": "Forbidden - Dev tools disabled in production"},
    }
)


class TokenGenerateRequest(BaseModel):
    """Request to generate a test JWT token"""
    user_id: int = Field(
        ...,
        description="User ID (integer) - Can be any number, doesn't need to exist in TAV database",
        example=20991
    )
    username: str = Field(
        ...,
        description="Username for the user",
        example="U536"
    )
    department: str = Field(
        default="",
        description="User's department (optional)",
        example="IT"
    )
    role: str = Field(
        default="User",
        description="User's role (optional)",
        example="User"
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "user_id": 20991,
                    "username": "U536",
                    "department": "IT",
                    "role": "User"
                },
                {
                    "user_id": 1,
                    "username": "admin",
                    "department": "Admin",
                    "role": "Admin"
                },
                {
                    "user_id": 123,
                    "username": "testuser",
                    "department": "",
                    "role": "User"
                }
            ]
        }


class TokenGenerateResponse(BaseModel):
    """Response with generated JWT token"""
    token: str = Field(
        ...,
        description="JWT token that can be used for SSO authentication"
    )
    user_id: int = Field(
        ...,
        description="User ID encoded in the token"
    )
    username: str = Field(
        ...,
        description="Username encoded in the token"
    )
    department: str = Field(
        ...,
        description="Department encoded in the token"
    )
    role: str = Field(
        ...,
        description="Role encoded in the token"
    )
    sso_url: str = Field(
        ...,
        description="Complete SSO URL - paste this in your browser to login as this user"
    )
    expires_in_minutes: int = Field(
        ...,
        description="Token expiration time in minutes"
    )


@router.post(
    "/generate-token",
    response_model=TokenGenerateResponse,
    summary="🔑 Generate JWT Token for SSO Testing",
    description="""
    Generate a JWT token for testing SSO authentication and user isolation.
    
    ⚠️ **DEV ONLY** - This endpoint is automatically disabled in production!
    
    ## How to Use:
    
    1. **Fill in user details** (user_id, username, etc.)
    2. **Click Execute** to generate the token
    3. **Copy the `sso_url`** from the response
    4. **Paste the URL in your browser** to login as that user
    5. **Check workflows** - you should only see workflows owned by that user ID
    
    ## Test Scenarios:
    
    ### Test User Isolation:
    - Generate token for user ID 1 → login → create workflows
    - Generate token for user ID 20991 → login → should see NO workflows from user 1
    - Create workflows as user 20991 → should have author_id=20991
    
    ### Test SSO Flow:
    - Token validation
    - Session creation
    - Cookie setting
    - Redirect to frontend
    
    ## Notes:
    - User does NOT need to exist in TAV database
    - User info comes from JWT token claims (SSO provider is source of truth)
    - Token expires after 120 minutes by default
    """,
    response_description="JWT token and SSO URL for testing"
)
def generate_test_token(request: TokenGenerateRequest):
    """Generate a JWT token for SSO testing"""
    # Only allow in development mode
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev tools are disabled in production"
        )
    
    try:
        # Generate token using JwtTokenManager
        token = JwtTokenManager.generate_token(
            username=request.username,
            user_id=request.user_id,
            department=request.department,
            role=request.role
        )
        
        # Build SSO URL
        base_url = settings.BASE_URL or f"http://localhost:{settings.FRONTEND_PORT}"
        sso_url = f"http://localhost:{settings.BACKEND_PORT}/api/v1/sso/?token={token}"
        
        logger.info(f"🔑 Generated test token for user {request.user_id} ({request.username})")
        
        return TokenGenerateResponse(
            token=token,
            user_id=request.user_id,
            username=request.username,
            department=request.department,
            role=request.role,
            sso_url=sso_url,
            expires_in_minutes=settings.JWT_EXPIRY_MINUTES
        )
        
    except Exception as e:
        logger.error(f"❌ Error generating token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate token: {str(e)}"
        )


@router.get(
    "/validate-token",
    summary="✅ Validate & Decode JWT Token",
    description="""
    Validate and decode a JWT token to see its contents.
    
    ⚠️ **DEV ONLY** - This endpoint is automatically disabled in production!
    
    ## How to Use:
    
    1. **Paste a JWT token** in the token parameter
    2. **Click Execute**
    3. **View the decoded claims** and user info
    
    ## What You'll See:
    - Token validity status
    - All JWT claims (sub, userId, username, department, role, exp, iat, etc.)
    - Extracted user ID and username
    
    ## Use Cases:
    - Debug why a token isn't working
    - Check token expiration
    - Verify user info in token
    - Test token generation
    """,
    response_description="Token validation result with decoded claims"
)
def validate_token(
    token: str = Query(
        ...,
        description="JWT token to validate (paste the full token string)",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
):
    """Validate and decode a JWT token"""
    # Only allow in development mode
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev tools are disabled in production"
        )
    
    claims = JwtTokenManager.validate_token(token)
    
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )
    
    return {
        "valid": True,
        "claims": claims,
        "user_id": JwtTokenManager.get_user_id_from_token(token),
        "username": JwtTokenManager.get_username_from_token(token)
    }
