"""
Credential Model

Store encrypted API keys, OAuth tokens, and other authentication credentials.
Used by nodes to securely access external services.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, Integer, Index, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
import enum

from app.database.base import Base, get_current_timestamp


class AuthType(str, enum.Enum):
    """Types of authentication methods."""
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"
    SMTP = "smtp"
    DATABASE = "database"
    TWILIO = "twilio"
    CUSTOM = "custom"


class Credential(Base):
    """
    Store encrypted API keys and OAuth tokens.
    
    Security:
        - encrypted_data field contains sensitive credentials (encrypted at rest)
        - metadata field contains non-sensitive info (not encrypted)
        - Encryption handled by CredentialManager service
    
    Examples:
        Slack credential:
            name: "My Slack Workspace"
            service_type: "slack"
            auth_type: "bearer_token"
            encrypted_data: {"token": "xoxb-..."}  # Encrypted
            metadata: {"workspace": "myteam", "scopes": ["chat:write"]}
            
        SMTP credential:
            name: "Gmail SMTP"
            service_type: "smtp"
            auth_type: "smtp"
            encrypted_data: {"password": "..."}  # Encrypted
            metadata: {"host": "smtp.gmail.com", "port": 587, "username": "user@gmail.com"}
    """
    __tablename__ = "credentials"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    
    # User ownership
    user_id = Column(Integer, nullable=False, index=True)
    
    # Credential identification
    name = Column(String(255), nullable=False)
    service_type = Column(String(100), nullable=False, index=True)
    auth_type = Column(SQLEnum(AuthType), nullable=False)
    
    # Encrypted sensitive data (JSON)
    # This stores the actual credentials (API keys, tokens, passwords)
    # Format depends on auth_type:
    #   api_key: {"api_key": "..."}
    #   bearer_token: {"token": "..."}
    #   basic_auth: {"username": "...", "password": "..."}
    #   oauth2: {"access_token": "...", "refresh_token": "...", "expires_at": "..."}
    #   smtp: {"password": "..."}
    #   database: {"password": "..."}
    encrypted_data = Column(Text, nullable=False)  # JSON string, encrypted
    
    # Non-sensitive metadata (JSON, not encrypted)
    # This stores configuration that's not secret:
    #   - SMTP: host, port, username, use_tls
    #   - OAuth: scopes, token_type, workspace/org info
    #   - Database: host, port, database name, username
    # Note: Using config_metadata because 'metadata' is reserved by SQLAlchemy
    config_metadata = Column(Text, nullable=True)  # JSON string, not encrypted
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_current_timestamp, onupdate=get_current_timestamp, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Optional: Description/notes
    description = Column(Text, nullable=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_credentials_user_id', 'user_id'),
        Index('idx_credentials_service_type', 'service_type'),
        Index('idx_credentials_is_active', 'is_active'),
        Index('idx_credentials_user_service', 'user_id', 'service_type'),
    )
    
    def __repr__(self) -> str:
        return f"<Credential(id={self.id}, name='{self.name}', service_type='{self.service_type}', auth_type='{self.auth_type.value}')>"

