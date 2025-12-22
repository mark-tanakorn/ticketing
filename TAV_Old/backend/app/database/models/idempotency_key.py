"""
Idempotency Key Model

Webhook and API request deduplication.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Index, JSON

from app.database.base import Base, get_current_timestamp


class IdempotencyKey(Base):
    """
    Idempotency key for webhook/API deduplication.
    
    Prevents duplicate processing of webhooks and API requests.
    Keys expire after a configurable TTL.
    """
    __tablename__ = "idempotency_keys"

    key = Column(String(255), primary_key=True, nullable=False)
    request_hash = Column(String(64), nullable=False, index=True)  # Hash of request body
    
    # Cached response (optional, for returning same response)
    response_data = Column(JSON, nullable=True)
    
    # Lifecycle
    processed_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_idempotency_keys_request_hash', 'request_hash'),
        Index('idx_idempotency_keys_expires_at', 'expires_at'),
    )
    
    def __repr__(self) -> str:
        return f"<IdempotencyKey(key='{self.key}', processed_at='{self.processed_at}')>"

