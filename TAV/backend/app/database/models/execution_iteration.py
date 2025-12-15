"""
Execution Iteration Model

Tracks iterations within a single workflow execution.
Enables loop-based workflows with detailed iteration tracking.
"""

from datetime import datetime
import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, Index, JSON, ForeignKey, Text

from app.database.base import Base, get_current_timestamp


class ExecutionIteration(Base):
    """
    Iteration tracking for loop-based workflows.
    
    Stores data for each iteration within a single execution.
    Use cases:
    - Business operations: Daily operation cycles
    - Data processing: Batch processing iterations
    - Simulations: Virtual days, simulation steps
    - ML training: Training epochs
    - Testing: Test scenario iterations
    """
    __tablename__ = "execution_iterations"

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
    
    # Iteration identification
    iteration_number = Column(Integer, nullable=False)
    iteration_label = Column(String(255), nullable=True)  # Human-readable: "day_5", "batch_42", "epoch_10"
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False, default=get_current_timestamp)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Virtual vs Real Time (for time-accelerated workflows)
    virtual_timestamp = Column(DateTime(timezone=True), nullable=True)  # Simulated time
    real_timestamp = Column(DateTime(timezone=True), nullable=False, default=get_current_timestamp)
    time_scale = Column(Float, nullable=False, default=1.0)  # Acceleration factor
    
    # Iteration Data
    input_data = Column(JSON, nullable=True)  # Inputs for this iteration
    output_data = Column(JSON, nullable=True)  # Outputs from this iteration
    iteration_metadata = Column(JSON, nullable=True)  # Additional context
    
    # Status
    status = Column(String(50), nullable=False, default='running')  # running, completed, failed, skipped
    error_message = Column(Text, nullable=True)
    
    # Performance Metrics
    nodes_executed = Column(Integer, nullable=False, default=0)
    tokens_used = Column(Integer, nullable=True)  # For LLM workflows
    
    # Indexes
    __table_args__ = (
        Index('idx_exec_iter_execution', 'execution_id', 'iteration_number'),
        Index('idx_exec_iter_status', 'execution_id', 'status'),
        Index('idx_exec_iter_virtual_time', 'execution_id', 'virtual_timestamp'),
    )
    
    def __repr__(self) -> str:
        return f"<ExecutionIteration(execution_id='{self.execution_id}', iteration={self.iteration_number}, status='{self.status}')>"

