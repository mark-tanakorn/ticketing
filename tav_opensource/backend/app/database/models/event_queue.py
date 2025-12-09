"""
Event Queue Model

Background event processing queue for async operations.
"""

from datetime import datetime
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Index, JSON, ForeignKey, Text

from app.database.base import Base, get_current_timestamp


class EventQueue(Base):
    """
    Background event queue.
    
    Stores events for asynchronous processing (e.g., workflow triggers,
    file processing, notifications).
    """
    __tablename__ = "event_queue"

    id = Column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        nullable=False
    )
    
    # Event type (e.g., workflow.trigger, file.process, email.send)
    event_type = Column(String(100), nullable=False, index=True)
    
    # Related workflow (if applicable)
    workflow_id = Column(
        String(36), 
        ForeignKey('workflows.id', ondelete='CASCADE'), 
        nullable=True, 
        index=True
    )
    
    # Priority (1=highest, 10=lowest)
    priority = Column(Integer, default=5, nullable=False, index=True)
    
    # Event payload
    event_data = Column(JSON, nullable=False)
    
    # Status: pending, processing, completed, failed
    status = Column(String(50), default='pending', nullable=False, index=True)
    
    # Retry logic
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Timing
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False, index=True)
    scheduled_for = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False, index=True)  # When to process
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Composite index for efficient queue polling
    __table_args__ = (
        Index('idx_event_queue_status_priority', 'status', 'priority'),
        Index('idx_event_queue_workflow_id', 'workflow_id'),
        Index('idx_event_queue_event_type', 'event_type'),
        Index('idx_event_queue_scheduled_for', 'scheduled_for'),
    )
    
    def __repr__(self) -> str:
        return f"<EventQueue(id='{self.id}', event_type='{self.event_type}', status='{self.status}')>"

