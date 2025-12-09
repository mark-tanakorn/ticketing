"""
Execution Log Model

Detailed step-by-step logs for each node in a workflow execution.
"""

from datetime import datetime
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Index, JSON, ForeignKey, Text

from app.database.base import Base, get_current_timestamp


class ExecutionLog(Base):
    """
    Step-by-step execution log for workflow nodes.
    
    Captures input, output, errors, and timing for each node execution.
    """
    __tablename__ = "execution_logs"

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
    
    # Node identification
    node_id = Column(String(255), nullable=False, index=True)
    node_name = Column(String(255), nullable=False)
    
    # Status: pending, running, completed, failed, skipped
    status = Column(String(50), nullable=False)
    
    # Log level: INFO, WARNING, ERROR, DEBUG
    log_level = Column(String(20), nullable=False)
    
    # Log message
    message = Column(Text, nullable=False)
    
    # Node data
    input_data = Column(JSON, nullable=True)  # Node input
    output_data = Column(JSON, nullable=True)  # Node output
    error_details = Column(JSON, nullable=True)  # Error stack trace/details
    
    # Event & Anomaly Tracking (NEW)
    event_type = Column(String(100), nullable=True, index=True)  # anomaly, failure, alert, milestone
    event_category = Column(String(100), nullable=True, index=True)  # performance, data_quality, business_logic
    severity = Column(String(20), nullable=True, index=True)  # low, medium, high, critical
    impact_score = Column(Float, nullable=True)  # 0-10 scale
    affected_metrics = Column(JSON, nullable=True)  # Metrics affected by this event
    resolved = Column(Boolean, nullable=False, default=False)  # Issue resolution status
    resolution_notes = Column(Text, nullable=True)  # Resolution details
    detection_method = Column(String(100), nullable=True)  # rule, ml, threshold, pattern
    iteration_number = Column(Integer, nullable=True)  # For loop-based workflows
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)  # Node execution duration
    
    # Indexes
    __table_args__ = (
        Index('idx_execution_logs_execution_id', 'execution_id'),
        Index('idx_execution_logs_node_id', 'node_id'),
        Index('idx_execution_logs_status', 'status'),
        Index('idx_execution_logs_started_at', 'started_at'),
        Index('idx_exec_logs_event_type', 'event_type'),
        Index('idx_exec_logs_event_category', 'event_category'),
        Index('idx_exec_logs_severity', 'severity'),
        Index('idx_exec_logs_unresolved', 'resolved', 'severity'),
    )
    
    def __repr__(self) -> str:
        return f"<ExecutionLog(id='{self.id}', node_id='{self.node_id}', status='{self.status}')>"
