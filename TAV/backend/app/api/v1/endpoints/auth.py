"""
Authentication Endpoints

Handles user authentication, login, logout, and token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db,
    get_current_user,
    get_current_active_user,
    get_user_repository,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.database.models.user import User
from app.database.repositories.users import UserRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    LogoutResponse,
)
from app.schemas.user import UserResponse


router = APIRouter(prefix="/auth", tags=["🔑 Authentication"])


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(
    login_data: LoginRequest,
    user_repo: UserRepository = Depends(get_user_repository)
) -> LoginResponse:
    """
    Login with username and password.
    
    Args:
        login_data: Login credentials (username & password)
        user_repo: User repository
    
    Returns:
        Access token, refresh token, and user info
    
    Raises:
        HTTPException: If authentication fails
    """
    # Authenticate user
    user = user_repo.authenticate(login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.id,
        username=user.user_name
    )


@router.post("/refresh", response_model=RefreshTokenResponse, status_code=status.HTTP_200_OK)
def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> RefreshTokenResponse:
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_data: Refresh token
        db: Database session
    
    Returns:
        New access token
    
    Raises:
        HTTPException: If refresh token is invalid
    """
    # Decode refresh token
    try:
        payload = decode_token(refresh_data.refresh_token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user ID
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user still exists and is active
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(int(user_id))
    
    if not user or not user_repo.is_active(user.id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new access token
    access_token = create_access_token(data={"sub": user_id})
    
    return RefreshTokenResponse(
        access_token=access_token,
        token_type="bearer"
    )


@router.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
def logout(
    current_user: User = Depends(get_current_active_user)
) -> LogoutResponse:
    """
    Logout current user.
    
    Note: Since we're using JWT, logout is primarily client-side.
    The client should discard the tokens. This endpoint mainly serves
    as a confirmation and could be used for logging/audit purposes.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Logout confirmation message
    """
    # TODO: Add to token blacklist if implementing token revocation
    # For now, just return success message
    
    return LogoutResponse(
        message=f"User {current_user.user_name} logged out successfully"
    )


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        User information (without sensitive fields)
    """
    return UserResponse.model_validate(current_user)
