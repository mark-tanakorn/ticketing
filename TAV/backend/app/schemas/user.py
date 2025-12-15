"""
User Schemas

Pydantic models for user data, including JWT-based user representation
that doesn't require database lookups.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema"""
    user_name: str
    user_email: Optional[str] = None
    user_firstname: Optional[str] = None
    user_lastname: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema"""
    user_password: str


class UserUpdate(BaseModel):
    """User update schema"""
    user_email: Optional[str] = None
    user_firstname: Optional[str] = None
    user_lastname: Optional[str] = None
    user_password: Optional[str] = None


class UserResponse(UserBase):
    """User response schema"""
    id: int
    user_id: str
    user_is_deleted: bool = False
    user_is_disabled: bool = False
    
    class Config:
        from_attributes = True


class JWTUser(BaseModel):
    """
    JWT-based user representation (no database required).
    
    This model represents a user authenticated via SSO JWT token.
    User data comes from JWT claims, not from TAV database.
    
    This allows TAV to work without storing user records locally,
    relying instead on BizProj (or other SSO provider) as the source of truth.
    """
    id: int = Field(..., description="User ID from JWT token")
    user_name: str = Field(..., description="Username from JWT token")
    user_email: Optional[str] = Field(None, description="Email (if provided in JWT)")
    user_firstname: Optional[str] = Field(None, description="First name (if provided)")
    user_lastname: Optional[str] = Field(None, description="Last name (if provided)")
    department: Optional[str] = Field(None, description="Department from JWT")
    role: Optional[str] = Field(None, description="Role from JWT")
    
    # Make it compatible with existing code that expects User model
    @property
    def user_is_deleted(self) -> bool:
        """JWT users are never deleted (they wouldn't have valid tokens)"""
        return False
    
    @property
    def user_is_disabled(self) -> bool:
        """JWT users are never disabled (they wouldn't have valid tokens)"""
        return False
    
    @classmethod
    def from_jwt_claims(cls, claims: dict) -> "JWTUser":
        """
        Create JWTUser from JWT token claims.
        
        Args:
            claims: Decoded JWT payload
            
        Returns:
            JWTUser instance
            
        Example JWT claims:
            {
                "sub": "mark.tanakorn",
                "userId": "123",
                "username": "mark.tanakorn",
                "department": "IT",
                "role": "User",
                "iss": "BizProj",
                "aud": "TAV",
                ...
            }
        """
        return cls(
            id=int(claims.get("userId", 0)),
            user_name=claims.get("username", claims.get("sub", "unknown")),
            user_email=claims.get("email"),
            user_firstname=claims.get("firstname") or claims.get("firstName"),
            user_lastname=claims.get("lastname") or claims.get("lastName"),
            department=claims.get("department"),
            role=claims.get("role", "User")
        )
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Token payload schema"""
    sub: int  # User ID
    exp: Optional[int] = None
    type: str = "access"  # access or refresh


class UserListResponse(BaseModel):
    """User list response schema"""
    users: list[UserResponse]
    total: int
    page: int = 1
    page_size: int = 50


class PasswordChange(BaseModel):
    """Password change schema"""
    old_password: str
    new_password: str = Field(..., min_length=6)


class PasswordReset(BaseModel):
    """Password reset schema"""
    new_password: str = Field(..., min_length=6)
