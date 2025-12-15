"""
Execution Result Model

Stores final results and artifacts from workflow executions.
"""

from datetime import datetime
import uuid
from sqlalchemy import Column, String, BigInteger, Integer, Float, Boolean, DateTime, Index, JSON, ForeignKey

from app.database.base import Base, get_current_timestamp


class ExecutionResult(Base):
    """
    Final execution result and artifacts.
    
    Stores the output data, files, and metadata from completed executions.
    """
    __tablename__ = "execution_results"

    id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        nullable=False
    )
    execution_id = Column(
        String(36), 
        ForeignKey('executions.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    
    # Result type: success, error, partial, output
    result_type = Column(String(100), nullable=False, index=True)
    
    # Result data (JSON)
    result_data = Column(JSON, nullable=True)
    
    # File storage (if result is a file)
    file_path = Column(String(500), nullable=True)  # Path to result file
    file_size_bytes = Column(BigInteger, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    # Artifact Management (NEW)
    artifact_key = Column(String(255), nullable=True, index=True)  # Artifact identifier
    artifact_category = Column(String(100), nullable=True, index=True)  # Category for grouping
    tags = Column(JSON, nullable=True)  # Searchable tags
    version = Column(Integer, nullable=False, default=1)  # Artifact version
    replaces_artifact_id = Column(String(36), ForeignKey('execution_results.id', ondelete='SET NULL'), nullable=True)
    referenced_by_executions = Column(JSON, nullable=True)  # Track which executions used this
    access_count = Column(Integer, nullable=False, default=0)  # Usage tracking
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    workflow_id = Column(String(36), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=True, index=True)
    description = Column(String, nullable=True)  # Artifact description
    
    # Lifecycle
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)  # For cleanup
    
    # Indexes
    __table_args__ = (
        Index('idx_execution_results_execution_id', 'execution_id'),
        Index('idx_execution_results_result_type', 'result_type'),
        Index('idx_execution_results_expires_at', 'expires_at'),
        Index('idx_exec_results_artifact_key', 'artifact_key'),
        Index('idx_exec_results_artifact_category', 'artifact_category'),
        Index('idx_exec_results_workflow', 'workflow_id'),
    )
    
    def __repr__(self) -> str:
        return f"<ExecutionResult(id='{self.id}', execution_id='{self.execution_id}', result_type='{self.result_type}')>"
