"""
Settings Models

Stores application behavior settings in the database with audit trail support.

Tables:
    - settings: Current settings (key-value store with namespaces)
    - setting_history: Audit log of all changes

Design Principles:
    - All application behavior settings stored in DB
    - Secrets/credentials remain in environment variables
    - JSON for complex values (validated by Pydantic schemas)
    - Audit trail tracks who changed what and when
    - Namespace support for logical grouping (execution, ai, ui, storage, etc.)
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, Integer, Index

from app.database.base import Base, get_current_timestamp


class Setting(Base):
    """
    Application settings stored as key-value pairs with namespaces.
    
    Examples:
        namespace='execution', key='max_concurrent_nodes', value='5'
        namespace='ai', key='default_provider', value='"openai"'
        namespace='ai.providers.openai', key='api_key', value='<encrypted>'
    """
    __tablename__ = "settings"

    # Composite primary key (namespace + key)
    namespace = Column(String(255), primary_key=True, nullable=False, index=True)
    key = Column(String(255), primary_key=True, nullable=False, index=True)
    
    # Value stored as JSON string (allows complex objects)
    value = Column(Text, nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_current_timestamp, onupdate=get_current_timestamp, nullable=False)
    updated_by = Column(String(255), default="system", nullable=False)
    
    # Description/documentation
    description = Column(Text, nullable=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_settings_namespace', 'namespace'),
        Index('idx_settings_updated_at', 'updated_at'),
    )
    
    def __repr__(self) -> str:
        return f"<Setting(namespace='{self.namespace}', key='{self.key}')>"


class SettingHistory(Base):
    """
    Audit log of all setting changes.
    
    Tracks who changed what, when, and from what value.
    """
    __tablename__ = "setting_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # What was changed
    namespace = Column(String(255), nullable=False, index=True)
    key = Column(String(255), nullable=False, index=True)
    
    # Change details
    old_value = Column(Text, nullable=True)  # NULL for new settings
    new_value = Column(Text, nullable=True)  # NULL for deleted settings
    
    # Change metadata
    changed_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    changed_by = Column(String(255), default="system", nullable=False)
    
    # Optional: change reason/comment
    change_reason = Column(Text, nullable=True)
    
    # Indexes for audit queries
    __table_args__ = (
        Index('idx_history_namespace_key', 'namespace', 'key'),
        Index('idx_history_changed_at', 'changed_at'),
        Index('idx_history_changed_by', 'changed_by'),
    )
    
    def __repr__(self) -> str:
        return f"<SettingHistory(namespace='{self.namespace}', key='{self.key}', changed_at='{self.changed_at}')>"
