"""
File Model

Tracks uploaded files with metadata, deduplication, and lifecycle management.
"""

from datetime import datetime
import uuid
from sqlalchemy import Column, String, BigInteger, Integer, DateTime, Index, JSON, ForeignKey, Enum as SQLEnum
import enum

from app.database.base import Base, get_current_timestamp


class FileType(str, enum.Enum):
    """File category for lifecycle management."""
    UPLOAD = "upload"        # User uploaded files (30-day TTL)
    ARTIFACT = "artifact"    # Generated outputs (7-day TTL)
    TEMPORARY = "temporary"  # Processing internals (1-hour TTL)
    PERMANENT = "permanent"  # Never auto-deleted


class FileCategory(str, enum.Enum):
    """File content category."""
    DOCUMENT = "document"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    ARCHIVE = "archive"
    OTHER = "other"


class File(Base):
    """
    Uploaded file metadata and tracking.
    
    Stores file information, enables deduplication via hash,
    and supports lifecycle management.
    """
    __tablename__ = "files"

    id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        nullable=False
    )
    
    # File identification
    filename = Column(String(500), nullable=False)
    storage_path = Column(String(1000), nullable=False, unique=True)  # Actual storage path/key
    
    # File properties
    file_size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA256 for deduplication
    
    # File categorization
    file_type = Column(
        SQLEnum(FileType),
        nullable=False,
        default=FileType.UPLOAD,
        index=True
    )
    file_category = Column(
        SQLEnum(FileCategory),
        nullable=False,
        default=FileCategory.OTHER,
        index=True
    )
    
    # Ownership
    uploaded_by_id = Column(
        Integer, 
        ForeignKey('users.id', ondelete='SET NULL'), 
        nullable=True, 
        index=True
    )
    
    # Workflow association (optional)
    workflow_id = Column(String(36), nullable=True, index=True)
    execution_id = Column(String(36), nullable=True, index=True)
    
    # Access tracking
    access_count = Column(Integer, default=0, nullable=False)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Lifecycle
    uploaded_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)  # For cleanup
    
    # Additional metadata (renamed to avoid SQLAlchemy reserved word)
    file_metadata = Column(JSON, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_files_file_hash', 'file_hash'),
        Index('idx_files_uploaded_at', 'uploaded_at'),
        Index('idx_files_expires_at', 'expires_at'),
        Index('idx_files_uploaded_by_id', 'uploaded_by_id'),
        Index('idx_files_file_type', 'file_type'),
        Index('idx_files_file_category', 'file_category'),
        Index('idx_files_workflow_id', 'workflow_id'),
    )
    
    def __repr__(self) -> str:
        return f"<File(id='{self.id}', filename='{self.filename}', type={self.file_type}, size={self.file_size_bytes})>"
