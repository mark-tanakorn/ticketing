"""
Authentication Schemas

Pydantic models for authentication-related operations.
"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Schema for login request."""
    
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    """Schema for login response."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    user_id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    
    refresh_token: str = Field(..., description="Refresh token")


class RefreshTokenResponse(BaseModel):
    """Schema for refresh token response."""
    
    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class LogoutResponse(BaseModel):
    """Schema for logout response."""
    
    message: str = Field(..., description="Logout confirmation message")
