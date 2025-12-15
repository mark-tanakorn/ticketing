"""
Email Interaction Model - Human-in-the-loop email approval persistence

Stores pending email approvals for workflow pause/resume functionality.
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.utils.timezone import get_local_now


class EmailInteraction(Base):
    """
    Email Interaction - Pending email approvals waiting for human review
    
    Lifecycle:
    1. Email Approval Node creates interaction with token
    2. User receives review link
    3. User opens link, edits draft, approves/rejects
    4. API validates token, updates status
    5. Workflow resumes with edited draft
    
    Security:
    - Token is cryptographically secure (32 bytes)
    - Single-use (invalidated after submission)
    - Expires after 6 hours
    """
    
    __tablename__ = "email_interactions"
    
    # Primary identification
    id = Column(String, primary_key=True)  # UUID interaction_id
    token = Column(String, nullable=False, unique=True, index=True)  # Secure token for verification
    
    # Execution context
    execution_id = Column(String, ForeignKey("executions.id"), nullable=False, index=True)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False, index=True)
    node_id = Column(String, nullable=False)  # Which approval node created this
    
    # Email draft data
    original_draft = Column(JSON, nullable=False)  # Original draft from composer
    edited_draft = Column(JSON, nullable=True)  # User-edited draft after review
    
    # SMTP configuration (needed for sending after approval)
    smtp_config = Column(JSON, nullable=False)  # Provider, credentials, etc.
    
    # State tracking
    status = Column(String, nullable=False, default="pending", index=True)
    # Status values: pending, approved, rejected, expired, sent
    
    action = Column(String, nullable=True)  # User action: approve, reject
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=get_local_now)
    expires_at = Column(DateTime, nullable=False, index=True)  # Auto-expire after 6 hours
    submitted_at = Column(DateTime, nullable=True)  # When user submitted approval
    sent_at = Column(DateTime, nullable=True)  # When email was actually sent
    
    # Metadata
    user_agent = Column(String, nullable=True)  # Browser user agent from submission
    ip_address = Column(String, nullable=True)  # IP address from submission
    
    # Relationships
    execution = relationship("Execution", back_populates="email_interactions", foreign_keys=[execution_id])
    workflow = relationship("Workflow", foreign_keys=[workflow_id])
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_email_interaction_status_expires", "status", "expires_at"),
        Index("idx_email_interaction_execution", "execution_id", "status"),
    )
    
    def __repr__(self):
        return f"<EmailInteraction(id={self.id}, status={self.status}, expires_at={self.expires_at})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if interaction has expired"""
        now = get_local_now()
        expires = self.expires_at
        
        # Make sure both datetimes are timezone-aware for comparison
        if expires.tzinfo is None:
            # If expires_at is naive, make it aware (assume UTC)
            from datetime import timezone
            expires = expires.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            # If now is naive, make it aware (assume UTC)
            from datetime import timezone
            now = now.replace(tzinfo=timezone.utc)
        
        return now > expires
    
    @property
    def is_pending(self) -> bool:
        """Check if interaction is still pending"""
        return self.status == "pending" and not self.is_expired
    
    @property
    def time_remaining_seconds(self) -> int:
        """Get remaining time before expiration in seconds"""
        if self.is_expired:
            return 0
        
        now = get_local_now()
        expires = self.expires_at
        
        # Make sure both datetimes are timezone-aware for comparison
        if expires.tzinfo is None:
            from datetime import timezone
            expires = expires.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            from datetime import timezone
            now = now.replace(tzinfo=timezone.utc)
        
        delta = expires - now
        return max(0, int(delta.total_seconds()))
    
    @classmethod
    def create_new(
        cls,
        interaction_id: str,
        token: str,
        execution_id: str,
        workflow_id: str,
        node_id: str,
        original_draft: dict,
        smtp_config: dict,
        timeout_hours: int = 6
    ) -> "EmailInteraction":
        """
        Create a new email interaction
        
        Args:
            interaction_id: Unique interaction ID (UUID)
            token: Secure verification token
            execution_id: Workflow execution ID
            workflow_id: Workflow ID
            node_id: Approval node ID
            original_draft: Original email draft
            smtp_config: SMTP configuration for sending
            timeout_hours: Hours until expiration (default: 6)
        
        Returns:
            EmailInteraction instance
        """
        now = get_local_now()
        expires_at = now + timedelta(hours=timeout_hours)
        
        return cls(
            id=interaction_id,
            token=token,
            execution_id=execution_id,
            workflow_id=workflow_id,
            node_id=node_id,
            original_draft=original_draft,
            smtp_config=smtp_config,
            status="pending",
            created_at=now,
            expires_at=expires_at
        )
    
    def mark_approved(self, edited_draft: dict, user_agent: str = None, ip_address: str = None):
        """Mark interaction as approved with edited draft"""
        self.status = "approved"
        self.action = "approve"
        self.edited_draft = edited_draft
        self.submitted_at = get_local_now()
        self.user_agent = user_agent
        self.ip_address = ip_address
    
    def mark_rejected(self, user_agent: str = None, ip_address: str = None):
        """Mark interaction as rejected"""
        self.status = "rejected"
        self.action = "reject"
        self.submitted_at = get_local_now()
        self.user_agent = user_agent
        self.ip_address = ip_address
    
    def mark_sent(self):
        """Mark email as sent"""
        self.status = "sent"
        self.sent_at = get_local_now()
    
    def mark_expired(self):
        """Mark interaction as expired"""
        self.status = "expired"

