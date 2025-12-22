"""
JWT Token Manager for SSO between BizProj and TAV

Generates and validates JWT tokens for cross-application authentication.
Equivalent to BizProj's JwtTokenManager.cs
"""

import base64
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from jose import JWTError, jwt

from app.config import settings


class JwtTokenManager:
    """JWT Token Manager for SSO"""

    @staticmethod
    def _get_secret_key() -> bytes:
        """Get JWT secret key from config, decoded from base64"""
        secret_b64 = settings.JWT_SECRET_KEY
        return base64.b64decode(secret_b64)

    @staticmethod
    def _get_issuer() -> str:
        """Get JWT issuer from config"""
        return settings.JWT_ISSUER

    @staticmethod
    def _get_audience() -> str:
        """Get JWT audience from config"""
        return settings.JWT_AUDIENCE

    @staticmethod
    def _get_expiry_minutes() -> int:
        """Get JWT expiry minutes from config"""
        return settings.JWT_EXPIRY_MINUTES

    @staticmethod
    def generate_token(username: str, user_id: int, department: str = "", role: str = "") -> str:
        """
        Generate JWT token for authenticated user

        Args:
            username: User's username
            user_id: User's ID
            department: User's department (optional)
            role: User's role (optional)

        Returns:
            JWT token string

        Raises:
            ValueError: If secret key is not configured
        """
        secret_key = JwtTokenManager._get_secret_key()
        if not secret_key:
            raise ValueError("JWT_SECRET_KEY not configured")

        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=JwtTokenManager._get_expiry_minutes())

        claims = {
            "sub": username,
            "userId": str(user_id),
            "username": username,
            "department": department or "",
            "role": role or "User",
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "iss": JwtTokenManager._get_issuer(),
            "aud": JwtTokenManager._get_audience(),
        }

        token = jwt.encode(claims, secret_key, algorithm="HS256")
        return token

    @staticmethod
    def validate_token(token: str) -> Optional[Dict]:
        """
        Validate JWT token and extract claims

        Args:
            token: JWT token string

        Returns:
            Dict with claims if valid, None if invalid
        """
        if not token:
            return None

        secret_key = JwtTokenManager._get_secret_key()
        if not secret_key:
            raise ValueError("JWT_SECRET_KEY not configured")

        try:
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=["HS256"],
                issuer=JwtTokenManager._get_issuer(),
                audience=JwtTokenManager._get_audience(),
                options={"verify_exp": True}
            )
            return payload
        except JWTError:
            return None

    @staticmethod
    def get_user_id_from_token(token: str) -> int:
        """
        Extract user ID from JWT token

        Args:
            token: JWT token string

        Returns:
            User ID or 0 if not found/invalid
        """
        claims = JwtTokenManager.validate_token(token)
        if claims and "userId" in claims:
            try:
                return int(claims["userId"])
            except ValueError:
                pass
        return 0

    @staticmethod
    def get_username_from_token(token: str) -> str:
        """
        Extract username from JWT token

        Args:
            token: JWT token string

        Returns:
            Username or empty string if not found/invalid
        """
        claims = JwtTokenManager.validate_token(token)
        if claims and "username" in claims:
            return claims["username"]
        return ""