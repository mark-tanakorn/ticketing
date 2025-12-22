"""
Schemas for Custom Nodes API (chat, tools, and library).

This module exists to keep endpoint modules small and focused.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== Conversations (Chat) ====================

class AttachmentRef(BaseModel):
    """
    Reference to an uploaded file (stored via /api/v1/files/upload).
    We pass lightweight metadata so the UI can render chips and the backend can
    validate ownership + load content for prompting.
    """
    file_id: str = Field(..., min_length=1, description="File ID from /api/v1/files/upload")
    filename: Optional[str] = Field(default=None, description="Original filename")
    mime_type: Optional[str] = Field(default=None, description="MIME type")
    file_category: Optional[str] = Field(default=None, description="document|image|audio|video|archive|other")
    file_size_bytes: Optional[int] = Field(default=None, ge=0, description="File size in bytes")

class StartConversationRequest(BaseModel):
    """Request to start a new conversation"""
    provider: str = Field(..., description="AI provider (openai, anthropic, deepseek, etc.)")
    model: str = Field(..., description="Model name (gpt-4o, claude-3-5-sonnet, etc.)")
    temperature: Optional[float] = Field(default=0.3, ge=0.0, le=2.0, description="Generation temperature")
    initial_message: Optional[str] = Field(None, description="Optional initial user message")
    attachments: Optional[List[AttachmentRef]] = Field(default=None, description="Optional attachments for the initial message")

class StartConversationStreamRequest(BaseModel):
    """
    Start a new conversation and stream the first assistant response.
    This is used by the frontend welcome flow so the first message has the same
    Activity / tool_start/tool_end traces as normal streaming messages.
    """
    provider: str = Field(..., description="AI provider (openai, anthropic, deepseek, etc.)")
    model: str = Field(..., description="Model name (gpt-4o, claude-3-5-sonnet, etc.)")
    temperature: Optional[float] = Field(default=0.3, ge=0.0, le=2.0, description="Generation temperature")
    message: str = Field(..., min_length=1, max_length=5000, description="Initial user message")
    attachments: Optional[List[AttachmentRef]] = Field(default=None, description="Optional attachments for the initial message")


class StartConversationResponse(BaseModel):
    """Response with new conversation details"""
    success: bool
    conversation_id: str
    title: str
    assistant_message: str
    provider: str
    model: str


class SendMessageRequest(BaseModel):
    """Request to send a message in conversation"""
    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    attachments: Optional[List[AttachmentRef]] = Field(default=None, description="Optional attachments for this message")
    provider: Optional[str] = Field(default=None, description="Optional override provider for this message (updates conversation)")
    model: Optional[str] = Field(default=None, description="Optional override model for this message (updates conversation)")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="Optional override temperature for this message (updates conversation)")


class MessageResponse(BaseModel):
    """Single message in conversation"""
    id: int
    role: str
    content: str
    created_at: datetime
    provider: Optional[str] = None
    model: Optional[str] = None
    activity: Optional[Any] = None


class ConversationDetail(BaseModel):
    """Full conversation details"""
    id: str
    title: str
    status: str
    provider: str
    model: str
    temperature: Optional[str]
    requirements: Optional[Dict[str, Any]]
    generated_code: Optional[str]
    node_type: Optional[str]
    class_name: Optional[str] = None
    validation_status: Optional[str] = None
    validation_errors: Optional[List[str]] = None
    message_count: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


class ConversationListResponse(BaseModel):
    """List of conversations"""
    success: bool
    conversations: List[ConversationDetail]
    total: int


class ConversationDetailResponse(BaseModel):
    """Full conversation with messages"""
    success: bool
    conversation: ConversationDetail
    messages: List[MessageResponse]


class GenerateCodeRequest(BaseModel):
    """Request to generate code from conversation"""
    pass  # No parameters needed, uses conversation context


class GenerateCodeResponse(BaseModel):
    """Response with generated code"""
    success: bool
    code: str
    node_type: str
    class_name: str
    validation_status: str
    validation_errors: Optional[List[str]] = None


class RefineCodeRequest(BaseModel):
    """Request to refine generated code"""
    refinement_request: str = Field(..., description="What to change/improve")


class NodeValidationRequest(BaseModel):
    """Validate node code"""
    code: str = Field(..., min_length=1, max_length=250000)


class ValidationError(BaseModel):
    message: str
    severity: str = Field("error", description="error|warning|info")


class NodeValidationResponse(BaseModel):
    """Response model for validation"""
    valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    node_type: Optional[str] = None
    class_name: Optional[str] = None
    message: Optional[str] = None


class SaveNodeRequest(BaseModel):
    """Save node request"""
    conversation_id: str
    code: Optional[str] = None
    overwrite: bool = False


class SaveNodeResponse(BaseModel):
    """Response model for save operation"""
    success: bool
    node_type: str
    file_path: str
    message: str
    registered: bool


class UpdateConversationCodeRequest(BaseModel):
    code: str


class UpdateConversationCodeResponse(BaseModel):
    """Response model for saving edited code to conversation."""
    success: bool
    conversation: ConversationDetail


# ==================== Tools (read-only) ====================

class ToolLookupRequest(BaseModel):
    """Lookup request in scoped code/doc locations"""
    query: str
    scope: str = Field(..., description="One of: builtin, base, registry, loader, docs")
    max_results: int = Field(3, ge=1, le=10)


class ToolLookupResult(BaseModel):
    path: str
    snippet: str


class ToolLookupResponse(BaseModel):
    success: bool
    results: List[ToolLookupResult]


class ExampleRequest(BaseModel):
    """Example snippet request"""
    kind: str = Field(..., description="One of: llm, http, processing, export, weather")


class ExampleResponse(BaseModel):
    success: bool
    example: str


# ==================== Library (My Nodes) ====================

class CustomNodeSummary(BaseModel):
    id: int
    node_type: str
    display_name: str
    description: Optional[str] = None
    category: str
    icon: Optional[str] = None
    version: Optional[str] = None
    is_active: bool
    is_registered: bool
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CustomNodeDetail(CustomNodeSummary):
    code: str


class CustomNodeListResponse(BaseModel):
    success: bool
    nodes: List[CustomNodeSummary]
    total: int


class UpdateCustomNodeCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=250000, description="Updated node code")


class UpdateCustomNodeCodeResponse(BaseModel):
    success: bool
    node: CustomNodeDetail


class RegisterCustomNodeResponse(BaseModel):
    success: bool
    node: CustomNodeSummary
    message: str


class DeleteCustomNodeResponse(BaseModel):
    success: bool
    deleted_id: int
    deleted_node_type: str
    deleted_file_path: Optional[str] = None
    message: str


