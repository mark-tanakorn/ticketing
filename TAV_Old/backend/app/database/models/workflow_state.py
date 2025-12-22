"""
Workflow State Model

Persistent state storage for workflows across multiple executions.
Enables workflows to maintain state between runs (inventory, checkpoints, conversation history, etc.)
"""

from datetime import datetime
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Index, JSON, ForeignKey, UniqueConstraint

from app.database.base import Base, get_current_timestamp


class WorkflowState(Base):
    """
    Persistent state for workflows.
    
    Enables workflows to store and retrieve state across multiple executions.
    Use cases:
    - Business operations: Inventory levels, customer data, financial state
    - Chatbots: Conversation history, user preferences
    - Data pipelines: Last processed ID, checkpoint
    - Monitoring: Alert history, baseline metrics
    - Simulations: Business state across virtual days
    """
    __tablename__ = "workflow_state"

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
    
    # State identification
    state_key = Column(String(255), nullable=False, index=True)
    state_namespace = Column(String(100), nullable=True)  # Optional: production, simulation, test
    
    # State data
    state_value = Column(JSON, nullable=False)
    state_version = Column(Integer, nullable=False, default=1)
    
    # Metadata
    last_updated_by_execution = Column(
        String(36),
        ForeignKey('executions.id', ondelete='SET NULL'),
        nullable=True
    )
    last_updated_at = Column(DateTime(timezone=True), nullable=False, default=get_current_timestamp)
    created_at = Column(DateTime(timezone=True), nullable=False, default=get_current_timestamp)
    
    # Lifecycle
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration for cleanup
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('workflow_id', 'state_key', 'state_namespace', name='uq_workflow_state_key_namespace'),
        Index('idx_workflow_state_workflow', 'workflow_id', 'state_namespace'),
        Index('idx_workflow_state_key', 'state_key'),
        Index('idx_workflow_state_expires', 'expires_at'),
    )
    
    def __repr__(self) -> str:
        return f"<WorkflowState(workflow_id='{self.workflow_id}', key='{self.state_key}', namespace='{self.state_namespace}')>"

