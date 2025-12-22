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
from app.schemas.user import JWTUser
import logging

logger = logging.getLogger(__name__)


# JWT Configuration
ALGORITHM = "HS256"
# Token expiry is now controlled by settings.ACCESS_TOKEN_EXPIRE_MINUTES
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
        expires_delta: Optional expiration time (if not provided, uses settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Use settings value instead of hardcoded constant
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
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
        logger.info(f"🔍 Decoding token: {token[:50]}...")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"✅ Token decoded successfully: sub={payload.get('sub')} (type={type(payload.get('sub')).__name__}), token_type={payload.get('type')}")
        return payload
    except JWTError as e:
        logger.error(f"❌ JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> JWTUser:
    """
    Get current authenticated user from JWT token (JWT-based, no DB lookup required).
    
    IMPORTANT: This function now returns JWTUser (not User model from DB).
    User data comes from JWT token claims, not from TAV database.
    This allows SSO integration without requiring users to exist in TAV DB.
    
    Args:
        credentials: HTTP authorization credentials (Bearer token)
        db: Database session (not used anymore, but kept for backward compatibility)
    
    Returns:
        JWTUser object with user data from token
    
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
    
    # Create JWTUser from token claims (no DB lookup)
    jwt_user = JWTUser(
        id=int(user_id),
        user_name=payload.get("username", f"user_{user_id}"),
        user_email=payload.get("email"),
        user_firstname=payload.get("firstname"),
        user_lastname=payload.get("lastname"),
        department=payload.get("department"),
        role=payload.get("role", "User")
    )
    
    logger.debug(f"Authenticated user from JWT: {jwt_user.user_name} (ID={jwt_user.id})")
    
    return jwt_user


def get_current_active_user(
    current_user: JWTUser = Depends(get_current_user)
) -> JWTUser:
    """
    Get current active user (not disabled or deleted).
    
    Note: JWT-based users are always "active" by definition
    (if they have a valid token, they're not disabled/deleted).
    
    Args:
        current_user: Current user from token
    
    Returns:
        Active user object
    """
    # JWT users are always active (token wouldn't be valid otherwise)
    return current_user


def get_current_user_dev(
    db: Session = Depends(get_db)
) -> User:
    """
    Development mode: Get a fallback DB user (bypasses authentication).
    
    ⚠️ WARNING: Only use in development! Do not use in production!
    
    Args:
        db: Database session
    
    Returns:
        First active user in database
    
    Raises:
        HTTPException: If no active user found
    """
    # Prefer user_id=1 (matches expected dev default), otherwise fall back to first active user.
    user = (
        db.query(User)
        .filter(
            User.id == 1,
            User.user_is_deleted == False,
            User.user_is_disabled == False,
        )
        .first()
    )
    if not user:
        user = (
            db.query(User)
            .filter(
                User.user_is_deleted == False,
                User.user_is_disabled == False,
            )
            .first()
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active user found in database. Please create an admin user first."
        )
    
    return user


def get_current_admin_user(
    current_user: JWTUser = Depends(get_current_active_user)
) -> JWTUser:
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
    # TODO: Check if user has admin role from JWT
    # For now, just return the current user
    # In production, check current_user.role == "Admin"
    
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


def get_user_identifier(user: JWTUser) -> str:
    """
    Get a safe user identifier for logging/tracking purposes.
    
    Works with JWTUser model.
    Falls back gracefully through multiple fields.
    
    Args:
        user: JWTUser object
    
    Returns:
        User identifier string (email > username > user_id > "system")
    """
    if hasattr(user, 'user_email') and user.user_email:
        return user.user_email
    if hasattr(user, 'email') and user.email:
        return user.email
    if hasattr(user, 'user_name') and user.user_name:
        return user.user_name
    if hasattr(user, 'id') and user.id:
        return f"user_{user.id}"
    return "system"


def get_current_user_smart(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> JWTUser:
    """
    Smart user dependency that switches between dev and production mode.
    
    - **Dev Mode**: Authentication is optional. If a JWT is provided and valid, it will be used.
      If a JWT is missing OR invalid, falls back to a DB user (prefers user_id=1).
    - **Production Mode**: Requires a valid JWT token.
    
    Controlled by database setting: developer.enable_dev_mode
    
    Args:
        db: Database session
        credentials: Optional HTTP authorization credentials
    
    Returns:
        JWTUser object
    
    Raises:
        HTTPException: If authentication fails (production mode) or no user found (dev mode)
    """
    # Check dev mode first (from DB setting, with env fallback)
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
        # DEV MODE: Token is optional.
        # Try token auth if provided (for SSO testing), but never hard-fail on invalid tokens.
        if credentials:
            logger.info("📝 JWT token provided - attempting token authentication (dev mode)")
            try:
                return get_current_user(credentials, db)
            except HTTPException as e:
                logger.warning(f"Dev mode enabled but token auth failed ({e.detail}); falling back to dev user")
            except Exception as e:
                logger.warning(f"Dev mode enabled but token auth errored; falling back to dev user: {e}", exc_info=True)

        logger.info("🔓 Dev mode enabled - using DB user fallback (id=1 preferred)")
        db_user = get_current_user_dev(db)
        # Convert DB User to JWTUser
        return JWTUser(
            id=db_user.id,
            user_name=db_user.user_name,
            user_email=db_user.user_email,
            user_firstname=db_user.user_firstname,
            user_lastname=db_user.user_lastname,
            department=None,
            role="User"
        )
    else:
        # PRODUCTION MODE: Require authentication
        if credentials:
            return get_current_user(credentials, db)
        logger.error("🔒 Production mode - JWT token required but not provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )


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

