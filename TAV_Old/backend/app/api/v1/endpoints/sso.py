"""
SSO Endpoint

Handles Single Sign-On from BizProj using JWT tokens.
"""

import logging
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.core.jwt_manager import JwtTokenManager
from app.config import settings
from app.api.deps import create_access_token
from datetime import timedelta

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/sso",
    tags=["SSO"],
    responses={
        401: {"description": "Unauthorized - Invalid or expired token"},
        400: {"description": "Bad Request - Missing user data in token"},
    }
)


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="🚪 SSO Login",
    description="""
    Single Sign-On login endpoint for BizProj → TAV authentication.
    
    ## How It Works:
    
    1. **User clicks "Access TAV"** in BizProj
    2. **BizProj generates JWT token** with user info (userId, username, department, role)
    3. **BizProj redirects to this endpoint** with token in URL query parameter
    4. **TAV validates the JWT token** (checks signature, expiration, issuer, audience)
    5. **TAV creates session** for the user (generates TAV session token)
    6. **TAV sets session cookie** (HTTP-only for security)
    7. **TAV redirects to frontend** with session token in URL
    8. **User is logged in** and can access TAV with their own workflows/files
    
    ## Flow Diagram:
    ```
    BizProj → JWT Token → This Endpoint → Validate → Create Session → Redirect → Frontend
    ```
    
    ## Security:
    - JWT token must be signed with shared secret key
    - Token must not be expired
    - Token must have correct issuer (BizProj) and audience (TAV)
    - Session cookie is HTTP-only (XSS protection)
    - Session cookie is Secure in production (HTTPS only)
    
    ## Testing:
    Use the **Dev Tools → Generate Token** endpoint to create test tokens!
    
    ## Token Requirements:
    - Must contain: `userId`, `username`
    - Optional: `department`, `role`
    - Must have valid `iss` (issuer), `aud` (audience), `exp` (expiration)
    
    ## What Happens After:
    - User is redirected to: `{BASE_URL}?token={tav_session_token}`
    - Frontend receives TAV session token
    - Frontend stores token (localStorage or uses cookie)
    - Subsequent API calls include token in Authorization header
    - User sees only their own workflows/files (isolation by user_id)
    """,
    response_class=RedirectResponse,
    response_description="Redirects to TAV frontend with session cookie set"
)
def sso_login(
    token: str = Query(
        ...,
        description="JWT token from BizProj containing user authentication info (userId, username, etc.)",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
) -> RedirectResponse:
    """
    SSO login endpoint.

    Validates JWT token from BizProj, creates TAV session, and redirects to dashboard.

    Flow:
    1. Validate incoming SSO JWT from BizProj
    2. Extract user info (userId, username, etc.)
    3. Create TAV session token (separate from SSO token)
    4. Set session cookie
    5. Redirect to TAV frontend

    Args:
        token: JWT token from BizProj containing user authentication info

    Returns:
        Redirect to TAV dashboard with session cookie set

    Raises:
        HTTPException: If token is invalid or user data is missing
    """
    # Validate the SSO JWT token from BizProj
    claims = JwtTokenManager.validate_token(token)
    if not claims:
        logger.warning("❌ SSO: Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired SSO token"
        )

    # Log all claims from the JWT (for debugging)
    logger.info(f"✅ SSO: Token validated successfully")
    logger.info(f"📦 SSO Claims: {claims}")
    logger.info(f"   - sub: {claims.get('sub')}")
    logger.info(f"   - userId: {claims.get('userId')}")
    logger.info(f"   - username: {claims.get('username')}")
    logger.info(f"   - department: {claims.get('department')}")
    logger.info(f"   - role: {claims.get('role')}")

    # Extract user info from token
    user_id = JwtTokenManager.get_user_id_from_token(token)
    username = JwtTokenManager.get_username_from_token(token)

    logger.info(f"👤 SSO: User ID={user_id}, Username={username}")
    
    # Validate user data
    if user_id == 0 or not username:
        logger.error("❌ SSO: Missing or invalid user data in token")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user data in SSO token"
        )

    # Create TAV session token (different from SSO token)
    # This token will be used for subsequent API calls within TAV
    # It contains the user_id which will be used for authorization
    tav_token = create_access_token(
        data={
            "sub": str(user_id),  # User ID as string (JWT spec requirement)
            "username": username,
            "department": claims.get("department", ""),
            "role": claims.get("role", "User"),
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    logger.info(f"🔑 SSO: Created TAV session token for user {user_id}")

    # Build redirect URL to frontend
    # Frontend will receive the token and store it (localStorage/cookie)
    dashboard_url = f"{settings.BASE_URL}?token={tav_token}"
    
    # Create redirect response with cookie
    response = RedirectResponse(
        url=dashboard_url,
        status_code=status.HTTP_302_FOUND
    )
    
    # Set HTTP-only cookie for additional security
    # Frontend can use either the URL token or this cookie
    response.set_cookie(
        key="tav_session",
        value=tav_token,
        httponly=True,  # Prevents JavaScript access (XSS protection)
        secure=settings.ENVIRONMENT == "production",  # HTTPS only in production
        samesite="lax",  # CSRF protection
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert minutes to seconds
    )
    
    logger.info(f"✅ SSO: User {username} (ID={user_id}) logged in successfully")
    
    return response