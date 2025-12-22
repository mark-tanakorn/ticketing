"""
Conversation Models - Custom node builder conversational AI sessions

Stores multi-turn conversations between users and AI for custom node generation.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.database.base import Base
from app.utils.timezone import get_local_now


class Conversation(Base):
    """
    Conversation session for custom node building with AI.
    
    Lifecycle:
    1. User starts conversation → status='active'
    2. AI asks clarifying questions
    3. Requirements extracted → stored in requirements JSON
    4. User requests generation → status='generating'
    5. Code generated → status='completed'
    6. User refines → status='refining'
    7. Final save → status='completed', links to CustomNode
    
    Each conversation tracks:
    - Full message history (separate table)
    - Extracted requirements (JSON)
    - Generated code (if completed)
    - AI provider/model used
    """
    
    __tablename__ = "conversations"
    
    # Primary identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # User who owns this conversation
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Conversation metadata
    title = Column(String(255), nullable=False, index=True)
    # Auto-generated from first message or manually set
    # Example: "Weather Fetcher Node" or "Create weather data node..."
    
    status = Column(String(50), nullable=False, default="active", index=True)
    # Status values:
    # - 'active': Currently chatting, gathering requirements
    # - 'generating': AI is generating code
    # - 'refining': Code generated, user making refinements
    # - 'completed': Successfully generated and saved
    # - 'failed': Generation failed
    # - 'abandoned': User left without completing
    
    # AI Configuration
    provider = Column(String(50), nullable=False)
    # AI provider used: 'openai', 'anthropic', 'deepseek', etc.
    
    model = Column(String(100), nullable=False)
    # Model name: 'gpt-4o', 'claude-3-5-sonnet', 'deepseek-chat', etc.
    
    temperature = Column(String(10), nullable=True, default="0.3")
    # Generation temperature (stored as string for flexibility)
    
    # Requirements extraction (updated as conversation progresses)
    requirements = Column(JSON, nullable=True)
    # Structured data extracted from conversation:
    # {
    #     "functionality": "Fetch weather data from OpenWeatherMap",
    #     "category": "actions",
    #     "icon": "fa-solid fa-cloud",
    #     "inputs": [
    #         {"name": "location", "type": "text", "description": "..."}
    #     ],
    #     "outputs": [
    #         {"name": "weather_data", "type": "universal", "description": "..."}
    #     ],
    #     "config": [
    #         {"name": "api_key", "type": "string", "widget": "password", ...}
    #     ],
    #     "capabilities": ["LLMCapability"],
    #     "external_dependencies": ["httpx"],
    #     "error_handling": true
    # }
    
    # Generated code (if completed)
    generated_code = Column(Text, nullable=True)
    # The complete Python node class code
    
    node_type = Column(String(100), nullable=True)
    # Extracted node type identifier (e.g., "weather_fetcher")
    
    class_name = Column(String(100), nullable=True)
    # Generated class name (e.g., "WeatherFetcherNode")
    
    # Validation results
    validation_status = Column(String(50), nullable=True)
    # 'valid', 'invalid', 'not_validated'
    
    validation_errors = Column(JSON, nullable=True)
    # List of validation errors if any
    
    # Link to saved custom node (if successfully saved)
    custom_node_id = Column(Integer, ForeignKey("custom_nodes.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=get_local_now, index=True)
    updated_at = Column(DateTime, nullable=False, default=get_local_now, onupdate=get_local_now)
    completed_at = Column(DateTime, nullable=True)
    # When conversation resulted in successful node generation
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationMessage.created_at")
    custom_node = relationship("CustomNode", foreign_keys=[custom_node_id], uselist=False)
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_conversation_user_status", "user_id", "status"),
        Index("idx_conversation_user_created", "user_id", "created_at"),
        Index("idx_conversation_status_updated", "status", "updated_at"),
    )
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}', status={self.status}, user_id={self.user_id})>"
    
    @property
    def message_count(self) -> int:
        """Get total message count in this conversation"""
        return len(self.messages) if self.messages else 0
    
    @property
    def is_active(self) -> bool:
        """Check if conversation is still active (not completed/failed/abandoned)"""
        return self.status in ['active', 'generating', 'refining']
    
    @property
    def has_code(self) -> bool:
        """Check if code has been generated"""
        return bool(self.generated_code)


class ConversationMessage(Base):
    """
    Individual message in a conversation.
    
    Stores the full chat history between user and AI assistant.
    """
    
    __tablename__ = "conversation_messages"
    
    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Which conversation this belongs to
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Message metadata
    role = Column(String(20), nullable=False, index=True)
    # Role values: 'user', 'assistant', 'system'
    # - 'user': Message from the user
    # - 'assistant': AI response
    # - 'system': System messages (e.g., "Code generation started")
    
    content = Column(Text, nullable=False)
    # The actual message content
    
    # Optional: Track which AI actually responded (for debugging/analytics)
    provider = Column(String(50), nullable=True)
    # Provider used for this specific message (can change mid-conversation)
    
    model = Column(String(100), nullable=True)
    # Model used for this specific message
    
    # Metadata
    tokens_used = Column(Integer, nullable=True)
    # Token count if tracked (for cost analysis)
    
    response_time_ms = Column(Integer, nullable=True)
    # How long AI took to respond (milliseconds)

    # UI trace/activity (status + tool events) for this message (primarily assistant messages)
    activity = Column(JSON, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, nullable=False, default=get_local_now, index=True)
    
    # Relationship
    conversation = relationship("Conversation", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index("idx_conversation_message_conversation_created", "conversation_id", "created_at"),
        Index("idx_conversation_message_role", "role"),
    )
    
    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<ConversationMessage(id={self.id}, role={self.role}, content='{preview}')>"


class CustomNode(Base):
    """
    Successfully generated custom nodes that are saved to filesystem.
    
    Tracks custom nodes created through the conversational AI builder.
    Links back to the conversation that generated it.
    """
    
    __tablename__ = "custom_nodes"
    
    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # User who created this node
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Link to conversation that generated this node
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=True)
    
    # Node identification
    node_type = Column(String(100), nullable=False, unique=True, index=True)
    # Unique identifier for the node (e.g., "weather_fetcher")
    
    display_name = Column(String(255), nullable=False)
    # Human-readable name (e.g., "Weather Fetcher")
    
    description = Column(Text, nullable=True)
    # Node description
    
    category = Column(String(50), nullable=False, index=True)
    # Node category: 'processing', 'actions', 'ai', etc.
    
    icon = Column(String(100), nullable=True)
    # FontAwesome icon class
    
    # Code storage
    code = Column(Text, nullable=False)
    # The complete Python node class code
    
    file_path = Column(String(500), nullable=True)
    # Path where node file is saved (e.g., "backend/app/core/nodes/custom/weather_fetcher.py")
    
    # State tracking
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    # Whether node is currently active/registered
    
    is_registered = Column(Boolean, default=False, nullable=False)
    # Whether node is currently registered in NodeRegistry
    
    # Version tracking (for future: allow node updates)
    version = Column(String(20), nullable=True, default="1.0.0")
    
    # Metadata
    input_ports = Column(JSON, nullable=True)
    # Cached port definitions for quick access
    
    output_ports = Column(JSON, nullable=True)
    # Cached port definitions
    
    config_schema = Column(JSON, nullable=True)
    # Cached config schema
    
    # Statistics
    usage_count = Column(Integer, default=0, nullable=False)
    # How many times this node has been used in workflows (future tracking)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=get_local_now, index=True)
    updated_at = Column(DateTime, nullable=False, default=get_local_now, onupdate=get_local_now)
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    conversation = relationship("Conversation", foreign_keys=[conversation_id])
    
    # Indexes
    __table_args__ = (
        Index("idx_custom_node_user_active", "user_id", "is_active"),
        Index("idx_custom_node_category", "category"),
        Index("idx_custom_node_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<CustomNode(id={self.id}, node_type='{self.node_type}', display_name='{self.display_name}')>"
    
    @property
    def file_name(self) -> str:
        """Get the filename for this node"""
        return f"{self.node_type}.py"

