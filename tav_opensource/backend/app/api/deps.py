"""
API Dependencies

Provides common dependencies for API endpoints including authentication,
database sessions, trigger manager, and current user access.
"""

from collections.abc import Generator
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models.user import User
from app.database.repositories.users import UserRepository
from app.database.session import SessionLocal


# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Security scheme - auto_error=False allows us to handle missing auth with 401 instead of 403
security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """
    Get database session.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Data to encode in token
        expires_delta: Optional expiration time
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create JWT refresh token.
    
    Args:
        data: Data to encode in token
    
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and validate JWT token.
    
    Args:
        token: JWT token to decode
    
    Returns:
        Decoded token data
    
    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials (Bearer token)
        db: Database session
    
    Returns:
        Current user object
    
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Decode token
    payload = decode_token(token)
    
    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user ID from token
    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(int(user_id))
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user_repo.is_active(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled or deleted"
        )
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (not disabled or deleted).
    
    Args:
        current_user: Current user from token
    
    Returns:
        Active user object
    
    Raises:
        HTTPException: If user is not active
    """
    # Additional check (already done in get_current_user, but explicit)
    if current_user.user_is_disabled is True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    if current_user.user_is_deleted is True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deleted"
        )
    
    return current_user


def get_current_user_dev(
    db: Session = Depends(get_db)
) -> User:
    """
    Development mode: Get first active user (bypasses authentication).
    
    ⚠️ WARNING: Only use in development! Do not use in production!
    
    Args:
        db: Database session
    
    Returns:
        First active user in database
    
    Raises:
        HTTPException: If no active user found
    """
    from app.database.repositories.users import UserRepository
    
    user_repo = UserRepository(db)
    
    # Get first active user (not deleted, not disabled)
    user = db.query(User).filter(
        User.user_is_deleted == False,
        User.user_is_disabled == False
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active user found in database. Please create an admin user first."
        )
    
    return user


def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current admin user (for endpoints requiring admin privileges).
    
    TODO: Implement proper role-based access control (RBAC).
    For now, this is a placeholder that just checks if user is active.
    
    Args:
        current_user: Current active user
    
    Returns:
        Admin user object
    
    Raises:
        HTTPException: If user is not an admin
    """
    # TODO: Check if user has admin role
    # For now, just return the current user
    # In production, you would check a role field or permission system
    
    return current_user


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """
    Get user repository instance.
    
    Args:
        db: Database session
    
    Returns:
        UserRepository instance
    """
    return UserRepository(db)


def get_trigger_manager(request: Request):
    """
    Get TriggerManager singleton from app state.
    
    This is initialized at app startup and used for managing
    trigger nodes across persistent workflows.
    
    Args:
        request: FastAPI request object (provides access to app.state)
    
    Returns:
        TriggerManager instance
    
    Raises:
        HTTPException: If TriggerManager not initialized
    """
    from app.core.execution.trigger_manager import TriggerManager
    
    if not hasattr(request.app.state, 'trigger_manager'):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TriggerManager not initialized. Server may still be starting up."
        )
    
    trigger_manager = request.app.state.trigger_manager
    
    if trigger_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TriggerManager failed to initialize at startup. Check server logs."
        )
    
    return trigger_manager


def get_user_identifier(user: User) -> str:
    """
    Get a safe user identifier for logging/tracking purposes.
    
    Works in both dev mode (where email might not be set) and production.
    Falls back gracefully through multiple fields.
    
    Args:
        user: User object
    
    Returns:
        User identifier string (email > username > user_id > "system")
    """
    if hasattr(user, 'user_email') and user.user_email:
        return user.user_email
    if hasattr(user, 'email') and user.email:
        return user.email
    if hasattr(user, 'user_name') and user.user_name:
        return user.user_name
    if hasattr(user, 'user_id') and user.user_id:
        return f"user_{user.user_id}"
    return "system"


def get_current_user_smart(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> User:
    """
    Smart user dependency that switches between dev and production mode.
    
    - **Dev Mode (enable_dev_mode=True in DB)**: Bypasses authentication, returns first active user
    - **Production Mode (enable_dev_mode=False in DB)**: Requires JWT token authentication
    
    Controlled by database setting: developer.enable_dev_mode
    
    Args:
        db: Database session
        credentials: Optional HTTP authorization credentials
    
    Returns:
        User object
    
    Raises:
        HTTPException: If authentication fails (production mode) or no user found (dev mode)
    """
    # Check if dev mode is enabled in database
    try:
        from app.core.config.manager import SettingsManager
        manager = SettingsManager(db)
        dev_settings = manager.get_developer_settings()
        enable_dev_mode = dev_settings.enable_dev_mode
    except Exception as e:
        # Fallback to env variable if database read fails
        logger.warning(f"Failed to read dev mode from database, falling back to env: {e}")
        enable_dev_mode = settings.ENABLE_DEV_MODE
    
    if enable_dev_mode:
        # DEV MODE: Bypass authentication
        return get_current_user_dev(db)
    else:
        # PRODUCTION MODE: Require authentication
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return get_current_user(credentials, db)


def get_current_user_always_dev(
    db: Session = Depends(get_db)
) -> User:
    """
    Special dependency that ALWAYS bypasses authentication.
    
    Used exclusively for the developer settings endpoint to prevent lockouts.
    
    This ensures that users can always toggle dev mode back on, even if they
    accidentally disabled it and don't have valid credentials.
    
    Args:
        db: Database session
    
    Returns:
        User object (first active user)
    
    Raises:
        HTTPException: If no active user found in database
    """
    return get_current_user_dev(db)

