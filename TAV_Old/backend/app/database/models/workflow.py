"""
Workflow Model

Stores workflow definitions including nodes, connections, and metadata.
"""

from datetime import datetime
import uuid
from sqlalchemy import Column, String, BigInteger, Integer, Float, Text, Boolean, DateTime, Index, JSON, ForeignKey

from app.database.base import Base, get_current_timestamp


class Workflow(Base):
    """
    Workflow definition model.
    
    Stores the complete workflow structure including nodes, connections,
    and configuration.
    """
    __tablename__ = "workflows"

    id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        nullable=False
    )
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    version = Column(String(50), default="1.0", nullable=False)
    
    # Complete workflow definition stored as JSON
    # Includes: nodes[], connections[], settings, etc.
    workflow_data = Column(JSON, nullable=False)
    
    # Metadata
    tags = Column(JSON, nullable=True)  # Array of tags for categorization
    author_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Execution configuration (overrides global settings)
    # See EXECUTION_CONFIG_REFERENCE.md for field definitions
    execution_config = Column(JSON, nullable=True)
    
    # Status (unified workflow status)
    status = Column(String(50), default="na", nullable=False, index=True)
    last_execution_id = Column(String(36), ForeignKey('executions.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Status flags
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_template = Column(Boolean, default=False, nullable=False)
    
    # Template Management (NEW)
    template_category = Column(String(100), nullable=True, index=True)  # Category for templates
    template_subcategory = Column(String(100), nullable=True)  # Subcategory
    template_usage_count = Column(Integer, nullable=False, default=0)  # Times template was used
    template_rating = Column(Float, nullable=True)  # Average user rating
    template_validation_schema = Column(JSON, nullable=True)  # Validation rules
    template_instructions = Column(Text, nullable=True)  # Setup instructions
    parent_template_id = Column(String(36), ForeignKey('workflows.id', ondelete='SET NULL'), nullable=True)  # Template inheritance
    
    # Execution recommendations (hint for API consumers)
    # Suggests whether this workflow is suitable for synchronous execution
    # Values: "false" (default), "true", "timeout=30", etc.
    recommended_await_completion = Column(String(50), nullable=False, default="false")
    
    # Monitoring timestamps (for persistent/trigger workflows)
    monitoring_started_at = Column(DateTime(timezone=True), nullable=True)
    monitoring_stopped_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=get_current_timestamp, onupdate=get_current_timestamp, nullable=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_workflows_name', 'name'),
        Index('idx_workflows_status', 'status'),
        Index('idx_workflows_last_execution_id', 'last_execution_id'),
        Index('idx_workflows_is_active', 'is_active'),
        Index('idx_workflows_last_run_at', 'last_run_at'),
        Index('idx_workflows_author_id', 'author_id'),
        Index('idx_workflows_created_at', 'created_at'),
        Index('idx_workflows_template_category', 'template_category'),
        Index('idx_workflows_is_template_category', 'is_template', 'template_category'),
    )
    
    def __repr__(self) -> str:
        return f"<Workflow(id='{self.id}', name='{self.name}', version='{self.version}')>"
