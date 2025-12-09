"""
Audit Log Model

System-wide audit trail for all important actions.
"""

from datetime import datetime
import uuid
from sqlalchemy import Column, String, BigInteger, Integer, DateTime, Index, JSON, ForeignKey, Text

from app.database.base import Base, get_current_timestamp


class AuditLog(Base):
    """
    System-wide audit log.
    
    Tracks all important actions across the system for security
    and compliance purposes.
    """
    __tablename__ = "audit_logs"

    id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        nullable=False
    )
    
    # Who performed the action
    user_id = Column(
        Integer, 
        ForeignKey('users.id', ondelete='SET NULL'), 
        nullable=True, 
        index=True
    )
    
    # What action was performed
    action = Column(String(100), nullable=False, index=True)  # create, update, delete, execute, etc.
    resource_type = Column(String(100), nullable=False, index=True)  # workflow, execution, setting, etc.
    resource_id = Column(String(255), nullable=False, index=True)  # ID of the resource
    
    # Change details
    changes = Column(JSON, nullable=True)  # Before/after values
    
    # Request metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)  # Browser/client info
    
    # Result
    timestamp = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False, index=True)
    status = Column(String(50), nullable=False)  # success, failure
    error_message = Column(Text, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_resource_type', 'resource_type'),
        Index('idx_audit_logs_resource_id', 'resource_id'),
        Index('idx_audit_logs_timestamp', 'timestamp'),
    )
    
    def __repr__(self) -> str:
        return f"<AuditLog(id='{self.id}', action='{self.action}', resource_type='{self.resource_type}')>"
