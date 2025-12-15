"""
API Key Model

API key management for programmatic access.
"""

from datetime import datetime
import uuid
from sqlalchemy import Column, String, BigInteger, Integer, Boolean, DateTime, Index, JSON, ForeignKey

from app.database.base import Base, get_current_timestamp


class APIKey(Base):
    """
    API key for programmatic access.
    
    Stores hashed API keys with scopes and lifecycle management.
    Note: Authentication not fully implemented in v1, but schema is ready.
    """
    __tablename__ = "api_keys"

    id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        nullable=False
    )
    
    # Key identification (never store the actual key, only hash)
    key_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA256 hash
    key_prefix = Column(String(20), nullable=False)  # First 8 chars for display (e.g., "sk-abc...")
    name = Column(String(255), nullable=False)  # Human-readable name
    
    # Ownership
    user_id = Column(
        Integer, 
        ForeignKey('users.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    
    # Permissions
    scopes = Column(JSON, nullable=False)  # Array of permission scopes
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Lifecycle
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_api_keys_key_hash', 'key_hash'),
        Index('idx_api_keys_user_id', 'user_id'),
        Index('idx_api_keys_is_active', 'is_active'),
        Index('idx_api_keys_expires_at', 'expires_at'),
    )
    
    def __repr__(self) -> str:
        return f"<APIKey(id='{self.id}', name='{self.name}', key_prefix='{self.key_prefix}')>"
