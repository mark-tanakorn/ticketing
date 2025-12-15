"""
Execution Model

Tracks workflow execution runs with status and metadata.
"""

from datetime import datetime
import uuid
from sqlalchemy import Column, String, BigInteger, Integer, DateTime, Index, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database.base import Base, get_current_timestamp


class Execution(Base):
    """
    Workflow execution run model.
    
    Tracks the execution of a workflow including status, timing,
    and results.
    """
    __tablename__ = "executions"

    id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        nullable=False
    )
    workflow_id = Column(
        String(36), 
        ForeignKey('workflows.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    
    # Status: na, pending, running, completed, failed, stopped, paused
    status = Column(String(50), nullable=False, index=True)
    
    # Execution source (how was this execution initiated)
    # manual, webhook, schedule, api, polling, event, child_workflow, retry, resume, system, test
    execution_source = Column(String(100), nullable=True, index=True)
    trigger_data = Column(JSON, nullable=True)  # Input data that triggered the workflow
    
    # Execution mode: oneshot or persistent
    execution_mode = Column(String(20), default="oneshot", nullable=False)
    
    # User who started the execution (nullable for system/webhook triggers)
    started_by = Column(String(255), nullable=True)  # User ID or "system"
    started_by_id = Column(
        Integer, 
        ForeignKey('users.id', ondelete='SET NULL'), 
        nullable=True, 
        index=True
    )
    
    # Workflow snapshot (for audit trail)
    workflow_snapshot = Column(JSON, nullable=True)  # Complete workflow definition at execution time
    
    # Timing
    started_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)  # Total execution duration in milliseconds
    
    # Results
    final_outputs = Column(JSON, nullable=True)  # Final workflow outputs
    node_results = Column(JSON, nullable=True)  # Individual node results
    execution_log = Column(JSON, nullable=True)  # Detailed execution log
    
    # Error handling
    error_message = Column(Text, nullable=True)  # Error details if failed
    
    # Additional metadata (execution_metadata to avoid SQLAlchemy reserved word)
    execution_metadata = Column(JSON, nullable=True)  # Custom execution metadata
    
    # Relationships
    email_interactions = relationship("EmailInteraction", back_populates="execution", foreign_keys="EmailInteraction.execution_id")
    
    # Indexes
    __table_args__ = (
        Index('idx_executions_workflow_id', 'workflow_id'),
        Index('idx_executions_status', 'status'),
        Index('idx_executions_execution_source', 'execution_source'),
        Index('idx_executions_started_at', 'started_at'),
        Index('idx_executions_started_by_id', 'started_by_id'),
    )
    
    def __repr__(self) -> str:
        return f"<Execution(id='{self.id}', workflow_id='{self.workflow_id}', status='{self.status}')>"
