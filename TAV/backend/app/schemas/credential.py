"""
Credential Schemas

Pydantic models for credential data validation and serialization.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class AuthType(str, Enum):
    """Types of authentication methods."""
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"
    SMTP = "smtp"
    DATABASE = "database"
    TWILIO = "twilio"
    CUSTOM = "custom"


class CredentialFieldDefinition(BaseModel):
    """Definition of a field for a credential type."""
    name: str = Field(..., description="Field name (e.g., 'api_key', 'username')")
    type: str = Field(..., description="Field type (string, integer, boolean, datetime)")
    encrypted: bool = Field(..., description="Whether this field should be encrypted")
    required: bool = Field(default=True, description="Whether this field is required")
    label: Optional[str] = Field(None, description="Display label for UI")
    description: Optional[str] = Field(None, description="Help text for this field")


class CredentialTypeDefinition(BaseModel):
    """Definition of a credential type with its fields."""
    name: str = Field(..., description="Display name (e.g., 'API Key', 'OAuth 2.0')")
    auth_type: AuthType = Field(..., description="Authentication type")
    fields: List[CredentialFieldDefinition] = Field(..., description="Fields for this credential type")
    description: Optional[str] = Field(None, description="Description of this credential type")
    
    
# Predefined credential type definitions (from roadmap)
CREDENTIAL_TYPE_DEFINITIONS = {
    "api_key": CredentialTypeDefinition(
        name="API Key",
        auth_type=AuthType.API_KEY,
        description="Simple API key authentication",
        fields=[
            CredentialFieldDefinition(
                name="api_key",
                type="string",
                encrypted=True,
                label="API Key",
                description="Your API key"
            )
        ]
    ),
    "bearer_token": CredentialTypeDefinition(
        name="Bearer Token",
        auth_type=AuthType.BEARER_TOKEN,
        description="Bearer token authentication",
        fields=[
            CredentialFieldDefinition(
                name="token",
                type="string",
                encrypted=True,
                label="Bearer Token",
                description="Your bearer token"
            )
        ]
    ),
    "basic_auth": CredentialTypeDefinition(
        name="Basic Authentication",
        auth_type=AuthType.BASIC_AUTH,
        description="Username and password authentication",
        fields=[
            CredentialFieldDefinition(
                name="username",
                type="string",
                encrypted=False,
                label="Username",
                description="Username for authentication"
            ),
            CredentialFieldDefinition(
                name="password",
                type="string",
                encrypted=True,
                label="Password",
                description="Password for authentication"
            )
        ]
    ),
    "oauth2": CredentialTypeDefinition(
        name="OAuth 2.0 (Manual Setup)",
        auth_type=AuthType.OAUTH2,
        description="OAuth 2.0 tokens (manually obtained)",
        fields=[
            CredentialFieldDefinition(
                name="access_token",
                type="string",
                encrypted=True,
                label="Access Token",
                description="OAuth access token"
            ),
            CredentialFieldDefinition(
                name="refresh_token",
                type="string",
                encrypted=True,
                required=False,
                label="Refresh Token",
                description="OAuth refresh token (optional)"
            ),
            CredentialFieldDefinition(
                name="expires_at",
                type="datetime",
                encrypted=False,
                required=False,
                label="Expires At",
                description="Token expiration time"
            ),
            CredentialFieldDefinition(
                name="token_type",
                type="string",
                encrypted=False,
                required=False,
                label="Token Type",
                description="Token type (usually 'Bearer')"
            )
        ]
    ),
    "smtp": CredentialTypeDefinition(
        name="SMTP Server (Email)",
        auth_type=AuthType.SMTP,
        description="Generic SMTP server credentials",
        fields=[
            CredentialFieldDefinition(
                name="host",
                type="string",
                encrypted=False,
                label="SMTP Host",
                description="SMTP server hostname"
            ),
            CredentialFieldDefinition(
                name="port",
                type="integer",
                encrypted=False,
                label="SMTP Port",
                description="SMTP server port (usually 587 or 465)"
            ),
            CredentialFieldDefinition(
                name="username",
                type="string",
                encrypted=False,
                label="Username",
                description="SMTP username (usually email address)"
            ),
            CredentialFieldDefinition(
                name="password",
                type="string",
                encrypted=True,
                label="Password",
                description="SMTP password"
            ),
            CredentialFieldDefinition(
                name="use_tls",
                type="boolean",
                encrypted=False,
                required=False,
                label="Use TLS",
                description="Enable TLS/STARTTLS"
            )
        ]
    ),
    "database": CredentialTypeDefinition(
        name="Database Connection",
        auth_type=AuthType.DATABASE,
        description="Database connection credentials",
        fields=[
            CredentialFieldDefinition(
                name="type",
                type="string",
                encrypted=False,
                label="Database Type",
                description="postgresql, mysql, sqlite, etc."
            ),
            CredentialFieldDefinition(
                name="host",
                type="string",
                encrypted=False,
                label="Host",
                description="Database server hostname"
            ),
            CredentialFieldDefinition(
                name="port",
                type="integer",
                encrypted=False,
                label="Port",
                description="Database server port"
            ),
            CredentialFieldDefinition(
                name="database",
                type="string",
                encrypted=False,
                label="Database Name",
                description="Database name"
            ),
            CredentialFieldDefinition(
                name="username",
                type="string",
                encrypted=False,
                label="Username",
                description="Database username"
            ),
            CredentialFieldDefinition(
                name="password",
                type="string",
                encrypted=True,
                label="Password",
                description="Database password"
            )
        ]
    ),
    "twilio": CredentialTypeDefinition(
        name="Twilio (WhatsApp/SMS)",
        auth_type=AuthType.TWILIO,
        description="Twilio API credentials for WhatsApp Business API and SMS messaging",
        fields=[
            CredentialFieldDefinition(
                name="account_sid",
                type="string",
                encrypted=False,
                label="Account SID",
                description="Your Twilio Account SID (starts with 'AC')"
            ),
            CredentialFieldDefinition(
                name="auth_token",
                type="string",
                encrypted=True,
                label="Auth Token",
                description="Your Twilio Auth Token (keep this secret)"
            ),
            CredentialFieldDefinition(
                name="whatsapp_from",
                type="string",
                encrypted=False,
                required=False,
                label="WhatsApp From Number",
                description="Your Twilio WhatsApp number (e.g., +14155238886 or whatsapp:+14155238886)"
            ),
            CredentialFieldDefinition(
                name="messaging_service_sid",
                type="string",
                encrypted=False,
                required=False,
                label="Messaging Service SID",
                description="Optional: Twilio Messaging Service SID for advanced routing"
            )
        ]
    )
}


class CredentialBase(BaseModel):
    """Base credential schema with common fields."""
    name: str = Field(..., max_length=255, description="User-friendly name (e.g., 'My Slack Workspace')")
    service_type: str = Field(..., max_length=100, description="Service identifier (e.g., 'slack', 'google', 'github')")
    auth_type: AuthType = Field(..., description="Authentication method")
    description: Optional[str] = Field(None, description="Optional description/notes")


class CredentialCreate(CredentialBase):
    """Schema for creating a new credential."""
    credential_data: Dict[str, Any] = Field(..., description="Credential data (will be encrypted)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Non-sensitive metadata (not encrypted)")
    
    @validator('credential_data')
    def validate_credential_data(cls, v):
        """Ensure credential_data is not empty."""
        if not v:
            raise ValueError("credential_data cannot be empty")
        return v


class CredentialUpdate(BaseModel):
    """Schema for updating a credential."""
    name: Optional[str] = Field(None, max_length=255, description="User-friendly name")
    credential_data: Optional[Dict[str, Any]] = Field(None, description="Updated credential data (will be encrypted)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    description: Optional[str] = Field(None, description="Updated description")
    is_active: Optional[bool] = Field(None, description="Whether credential is active")


class CredentialInDB(CredentialBase):
    """Schema for credential as stored in database (with encrypted data)."""
    id: int = Field(..., description="Credential ID")
    user_id: int = Field(..., description="User ID who owns this credential")
    encrypted_data: str = Field(..., description="Encrypted JSON string")
    config_metadata: Optional[str] = Field(None, description="Metadata JSON string (not encrypted)")
    is_active: bool = Field(..., description="Whether credential is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last time credential was used")
    
    class Config:
        from_attributes = True


class CredentialResponse(CredentialBase):
    """Schema for credential response (without sensitive data)."""
    id: int = Field(..., description="Credential ID")
    user_id: int = Field(..., description="User ID who owns this credential")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Non-sensitive metadata")
    is_active: bool = Field(..., description="Whether credential is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last time credential was used")
    
    class Config:
        from_attributes = True


class CredentialWithData(CredentialResponse):
    """Schema for credential response with decrypted data (for authenticated requests)."""
    credential_data: Dict[str, Any] = Field(..., description="Decrypted credential data")


class CredentialListResponse(BaseModel):
    """Schema for list of credentials."""
    credentials: List[CredentialResponse] = Field(..., description="List of credentials")
    total: int = Field(..., description="Total number of credentials")


class CredentialTypeResponse(BaseModel):
    """Schema for credential type information."""
    type_id: str = Field(..., description="Type identifier (e.g., 'api_key', 'oauth2')")
    definition: CredentialTypeDefinition = Field(..., description="Type definition")

