"""
Custom Node Generation API Endpoints - Conversational AI Approach

Multi-turn conversational interface for custom node building with AI.
Users chat with AI to clarify requirements, then generate code.
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from app.api.deps import get_db, get_current_user_smart
from app.database.models.user import User
from app.database.models.conversation import Conversation, ConversationMessage, CustomNode

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================

# ==============================================================================
# TOOLING HELPERS
# ==============================================================================

ALLOWED_SCOPES = {
    "builtin": Path("app/core/nodes/builtin"),
    "base": Path("app/core/nodes/base.py"),
    "registry": Path("app/core/nodes/registry.py"),
    "loader": Path("app/core/nodes/loader.py"),
    "docs": Path("docs/reference/built-in-nodes.md"),
}


def _safe_read(path: Path, max_bytes: int = 8000) -> str:
    """Read file content safely, bounded by max_bytes."""
    if not path.exists() or not path.is_file():
        return ""
    data = path.read_bytes()[:max_bytes]
    return data.decode(errors="ignore")


def _search_in_dir(root: Path, query: str, max_results: int) -> List["ToolLookupResult"]:
    results: List["ToolLookupResult"] = []
    query_lower = query.lower()
    for file in sorted(root.rglob("*.py")):
        if len(results) >= max_results:
            break
        try:
            text = file.read_text(errors="ignore")
            if query_lower in text.lower():
                idx = text.lower().find(query_lower)
                start = max(0, idx - 200)
                end = min(len(text), idx + 200)
                snippet = text[start:end]
                results.append(ToolLookupResult(path=str(file), snippet=snippet))
        except Exception:
            continue
    return results

class StartConversationRequest(BaseModel):
    """Request to start a new conversation"""
    provider: str = Field(..., description="AI provider (openai, anthropic, deepseek, etc.)")
    model: str = Field(..., description="Model name (gpt-4o, claude-3-5-sonnet, etc.)")
    temperature: Optional[float] = Field(default=0.3, ge=0.0, le=2.0, description="Generation temperature")
    initial_message: Optional[str] = Field(None, description="Optional initial user message")


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


class MessageResponse(BaseModel):
    """Single message in conversation"""
    id: int
    role: str
    content: str
    created_at: datetime
    provider: Optional[str] = None
    model: Optional[str] = None


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


# Reuse from original API
class NodeValidationRequest(BaseModel):
    """Request model for code validation"""
    code: str = Field(..., description="Python node code to validate")


class ValidationError(BaseModel):
    """Single validation error"""
    line: Optional[int] = None
    column: Optional[int] = None
    message: str
    severity: str = Field(default="error", description="error, warning, or info")


class NodeValidationResponse(BaseModel):
    """Response model for validation"""
    valid: bool
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []
    node_type: Optional[str] = None
    class_name: Optional[str] = None
    message: Optional[str] = None


class SaveNodeRequest(BaseModel):
    """Request model for saving node"""
    conversation_id: str = Field(..., description="Conversation ID")
    code: Optional[str] = Field(None, description="Code to save (uses conversation code if not provided)")
    overwrite: bool = Field(default=False, description="Allow overwriting existing node file")


class SaveNodeResponse(BaseModel):
    """Response model for save operation"""
    success: bool
    node_type: str
    file_path: str
    message: str
    registered: bool = Field(default=False, description="Whether node was successfully registered")


# ==============================================================================
# TOOLING MODELS (Phase 1 - lookup & examples)
# ==============================================================================

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


# ==============================================================================
# TOOLING ENDPOINTS (Phase 1 - read-only lookup & curated examples)
# ==============================================================================

@router.post("/tools/lookup", response_model=ToolLookupResponse)
async def tool_lookup(
    request: ToolLookupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Read-only lookup across bounded scopes:
    - builtin : app/core/nodes/builtin/**
    - base    : app/core/nodes/base.py
    - registry: app/core/nodes/registry.py
    - loader  : app/core/nodes/loader.py
    - docs    : docs/reference/built-in-nodes.md
    """
    scope = request.scope.lower()
    if scope not in ALLOWED_SCOPES:
        raise HTTPException(status_code=400, detail="Invalid scope")

    root = ALLOWED_SCOPES[scope]
    results: List[ToolLookupResult] = []

    if root.is_file():
        content = _safe_read(root)
        if not content:
            return ToolLookupResponse(success=False, results=[])
        if request.query.strip():
            q = request.query.lower()
            if q in content.lower():
                idx = content.lower().find(q)
                start = max(0, idx - 200)
                end = min(len(content), idx + 200)
                snippet = content[start:end]
            else:
                snippet = content[: min(len(content), 800)]
        else:
            snippet = content[: min(len(content), 800)]
        results.append(ToolLookupResult(path=str(root), snippet=snippet))
    else:
        results = _search_in_dir(root, request.query, request.max_results)

    return ToolLookupResponse(success=True, results=results)


EXAMPLES: Dict[str, str] = {
    "llm": """```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
from app.services.langchain_manager import LangChainManager

@register_node(
    node_type="llm_prompt",
    category=NodeCategory.AI,
    name="LLM Prompt",
    description="Call an LLM with a prompt",
    icon="fa-solid fa-robot",
)
class LLMPromptNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [{
            "name": "prompt",
            "type": PortType.TEXT,
            "display_name": "Prompt",
            "description": "Prompt to send",
            "required": True,
        }]

    @classmethod
    def get_output_ports(cls):
        return [{
            "name": "response",
            "type": PortType.TEXT,
            "display_name": "Response",
            "description": "LLM response",
            "required": True,
        }]

    @classmethod
    def get_config_schema(cls):
        return {
            "provider": {"type": "text", "label": "Provider", "default": "anthropic"},
            "model": {"type": "text", "label": "Model", "default": "claude-3-5-sonnet-20241022"},
            "temperature": {"type": "number", "label": "Temperature", "default": 0.2},
        }

    async def execute(self, input_data: NodeExecutionInput):
        manager = LangChainManager(self.db)  # assumes db available on self
        prompt = input_data.inputs.get("prompt", "")
        result = await manager.call_llm(
            prompt=prompt,
            provider=self.config.get("provider", "anthropic"),
            model=self.config.get("model", "claude-3-5-sonnet-20241022"),
            temperature=float(self.config.get("temperature", 0.2)),
        )
        return {"response": result}
```""",
    "http": """```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
import requests

@register_node(
    node_type="http_get",
    category=NodeCategory.ACTIONS,
    name="HTTP GET",
    description="Fetch JSON from a URL",
    icon="fa-solid fa-globe",
)
class HttpGetNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [{
            "name": "trigger",
            "type": PortType.SIGNAL,
            "display_name": "Trigger",
            "description": "Trigger request",
            "required": False,
        }]

    @classmethod
    def get_output_ports(cls):
        return [{
            "name": "data",
            "type": PortType.UNIVERSAL,
            "display_name": "Data",
            "description": "Response JSON",
            "required": True,
        }]

    @classmethod
    def get_config_schema(cls):
        return {
            "url": {"type": "text", "label": "URL", "required": True, "default": "https://api.example.com/data"},
            "timeout": {"type": "number", "label": "Timeout (s)", "default": 10},
        }

    async def execute(self, input_data: NodeExecutionInput):
        url = self.config.get("url")
        timeout = float(self.config.get("timeout", 10))
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return {"data": resp.json()}
```""",
    "processing": """```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

@register_node(
    node_type="text_uppercase",
    category=NodeCategory.PROCESSING,
    name="Text Uppercase",
    description="Convert text to uppercase",
    icon="fa-solid fa-arrows-up-to-line",
)
class TextUppercaseNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [{
            "name": "text",
            "type": PortType.TEXT,
            "display_name": "Text",
            "description": "Input text",
            "required": True,
        }]

    @classmethod
    def get_output_ports(cls):
        return [{
            "name": "result",
            "type": PortType.TEXT,
            "display_name": "Uppercase Text",
            "description": "Uppercased text",
            "required": True,
        }]

    @classmethod
    def get_config_schema(cls):
        return {}

    async def execute(self, input_data: NodeExecutionInput):
        text = input_data.inputs.get("text", "")
        return {"result": text.upper()}
```""",
    "export": """```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
import json

@register_node(
    node_type="json_export",
    category=NodeCategory.EXPORT,
    name="JSON Export",
    description="Serialize data to JSON string",
    icon="fa-solid fa-file-export",
)
class JsonExportNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [{
            "name": "data",
            "type": PortType.UNIVERSAL,
            "display_name": "Data",
            "description": "Data to export",
            "required": True,
        }]

    @classmethod
    def get_output_ports(cls):
        return [{
            "name": "json",
            "type": PortType.TEXT,
            "display_name": "JSON",
            "description": "Serialized JSON",
            "required": True,
        }]

    @classmethod
    def get_config_schema(cls):
        return {}

    async def execute(self, input_data: NodeExecutionInput):
        data = input_data.inputs.get("data")
        return {"json": json.dumps(data)}
```""",
    "weather": """```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
import requests

@register_node(
    node_type="weather_fetch",
    category=NodeCategory.ACTIONS,
    name="Weather Fetch",
    description="Fetch current weather for cities",
    icon="fa-solid fa-cloud-sun",
)
class WeatherFetchNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [{
            "name": "trigger",
            "type": PortType.SIGNAL,
            "display_name": "Trigger",
            "description": "Trigger fetch",
            "required": False,
        }]

    @classmethod
    def get_output_ports(cls):
        return [
            {"name": "weather_json", "type": PortType.UNIVERSAL, "display_name": "Weather JSON", "description": "Raw weather data", "required": True},
            {"name": "summary", "type": PortType.TEXT, "display_name": "Summary", "description": "Summary text", "required": True},
        ]

    @classmethod
    def get_config_schema(cls):
        return {
            "api_key": {"type": "text", "label": "API Key", "required": True, "secret": True},
            "cities": {"type": "text", "label": "Cities (comma-separated)", "default": "Singapore, Bangkok", "required": True},
            "units": {"type": "select", "label": "Units", "default": "metric",
                      "options": [{"label": "Metric", "value": "metric"}, {"label": "Imperial", "value": "imperial"}, {"label": "Standard", "value": "standard"}]},
        }

    async def execute(self, input_data: NodeExecutionInput):
        api_key = self.config.get("api_key")
        units = self.config.get("units", "metric")
        cities_str = self.config.get("cities", "")
        cities = [c.strip() for c in cities_str.split(",") if c.strip()]
        if not api_key or not cities:
            raise ValueError("API key and at least one city are required")

        base_url = "https://api.openweathermap.org/data/2.5/weather"
        results = []
        for city in cities:
            try:
                params = {"q": city, "appid": api_key, "units": units}
                resp = requests.get(base_url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                results.append(data)
            except Exception as e:
                results.append({"city": city, "error": str(e)})

        summaries = []
        unit_symbol = "°C" if units == "metric" else ("°F" if units == "imperial" else "K")
        for r in results:
            if "error" in r:
                summaries.append(f"{r.get('city','?')}: {r['error']}")
            else:
                summaries.append(f"{r.get('name','?')}: {r.get('main',{}).get('temp','?')}{unit_symbol}, {r.get('weather',[{}])[0].get('description','')}")

        return {
            "weather_json": results,
            "summary": "\\n".join(summaries),
        }
```""",
}


@router.post("/tools/example", response_model=ExampleResponse)
async def tool_example(
    request: ExampleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Return a curated example snippet by kind."""
    kind = request.kind.lower()
    if kind not in EXAMPLES:
        raise HTTPException(status_code=400, detail="Invalid example kind")
    return ExampleResponse(success=True, example=EXAMPLES[kind])
# ==============================================================================
# TOOLING MODELS (Phase 1 - lookup & examples)
# ==============================================================================

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


# ==============================================================================
# CONVERSATION ENDPOINTS
# ==============================================================================

@router.post("/conversations/start", response_model=StartConversationResponse)
async def start_conversation(
    request: StartConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Start a new custom node building conversation.
    
    The AI assistant will guide the user through defining:
    - Node functionality
    - Input/output ports
    - Configuration fields
    - External dependencies
    - Error handling needs
    
    Returns initial greeting and sets up conversation session.
    """
    logger.info(f"🆕 Starting conversation: user={current_user.id}, provider={request.provider}, model={request.model}")
    
    try:
        # Generate conversation ID
        conversation_id = str(uuid.uuid4())
        
        # Generate title (will be updated from first message)
        title = "New Custom Node"
        
        # Create conversation record
        conversation = Conversation(
            id=conversation_id,
            user_id=current_user.id,
            title=title,
            status="active",
            provider=request.provider,
            model=request.model,
            temperature=str(request.temperature) if request.temperature else "0.3",
            requirements=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(conversation)
        
        # Import conversation manager
        from app.services.conversation_manager import ConversationManager
        
        manager = ConversationManager(db)
        
        assistant_message = ""

        # If user provided initial message, process it
        if request.initial_message:
            # Save user message
            user_msg = ConversationMessage(
                conversation_id=conversation_id,
                role="user",
                content=request.initial_message,
                created_at=datetime.utcnow()
            )
            db.add(user_msg)
            
            # Generate AI response
            response = await manager.process_message(
                conversation=conversation,
                user_message=request.initial_message
            )
            
            # Update title from first message
            conversation.title = manager.generate_title(request.initial_message)
            
            assistant_message = response["assistant_message"]
            
            # Save assistant response
            msg = ConversationMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_message,
                provider=request.provider,
                model=request.model,
                created_at=datetime.utcnow()
            )
            db.add(msg)
        else:
            # Generate initial AI greeting
            assistant_message = await manager.get_initial_message()
            
            # Save assistant message
            msg = ConversationMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_message,
                provider=request.provider,
                model=request.model,
                created_at=datetime.utcnow()
            )
            db.add(msg)
        
        db.commit()
        
        logger.info(f"✅ Conversation started: {conversation_id}")
        
        return StartConversationResponse(
            success=True,
            conversation_id=conversation_id,
            title=conversation.title,
            assistant_message=assistant_message,
            provider=request.provider,
            model=request.model
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to start conversation: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start conversation: {str(e)}"
        )



@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: str,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Send a message and stream the AI response in real-time (SSE).
    
    Returns Server-Sent Events with:
    - data: {type: "token", content: "..."} for each token
    - data: {type: "done", ready_to_generate: true/false}
    """
    logger.info(f"💬 Streaming message in conversation {conversation_id}")
    
    async def generate_stream():
        try:
            # Get conversation
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id
            ).first()
            
            if not conversation:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Conversation not found'})}\n\n"
                return
            
            if conversation.status not in ['active', 'refining', 'failed', 'generating']:
                # Allow most statuses so users can continue/retry
                yield f"data: {json.dumps({'type': 'error', 'message': f'Conversation is {conversation.status}'})}\n\n"
                return
            
            # Reset status if it was failed or stuck in generating
            if conversation.status in ['failed', 'generating']:
                conversation.status = 'active'
                db.commit()
            
            # Save user message
            user_msg = ConversationMessage(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                created_at=datetime.utcnow()
            )
            db.add(user_msg)
            db.commit()
            
            # Check if user is confirming generation
            from app.services.conversation_manager import ConversationManager
            manager = ConversationManager(db)
            
            # Process message with AI - code generation happens in-chat now
            manager_stream = manager.process_message_stream(
                conversation=conversation,
                user_message=request.message
            )
            
            full_message = ""
            ready_to_generate = False
            requirements = None
            generated_code = None
            
            async for chunk in manager_stream:
                if chunk["type"] == "token":
                    full_message += chunk["content"]
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']})}\n\n"
                elif chunk["type"] == "done":
                    full_message = chunk["assistant_message"]
                    ready_to_generate = chunk["ready_to_generate"]
                    requirements = chunk.get("requirements")
                    generated_code = chunk.get("generated_code")
            
            # Save assistant response
            assistant_msg = ConversationMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=full_message,
                provider=conversation.provider,
                model=conversation.model,
                created_at=datetime.utcnow()
            )
            db.add(assistant_msg)
            
            # Update conversation
            conversation.updated_at = datetime.utcnow()
            if requirements:
                conversation.requirements = requirements
            
            # If code was generated in the chat, validate and save it
            if generated_code:
                try:
                    from app.services.code_validator import NodeCodeValidator
                    
                    logger.info("✨ Code found in response, validating...")
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Validating generated code...'})}\n\n"
                    
                    validator = NodeCodeValidator()
                    validation = validator.validate(generated_code)
                    
                    # Extract node type and class name from code if possible
                    # (Simple regex for now, validator might do better)
                    node_type_match = re.search(r'@register_node\(\s*["\']([^"\']+)["\']', generated_code)
                    node_type = node_type_match.group(1) if node_type_match else "custom_node"
                    
                    class_name_match = re.search(r'class\s+(\w+)\s*\(', generated_code)
                    class_name = class_name_match.group(1) if class_name_match else "CustomNode"
                    
                    conversation.generated_code = generated_code
                    conversation.node_type = node_type
                    conversation.class_name = class_name
                    conversation.validation_status = "valid" if validation["valid"] else "invalid"
                    conversation.validation_errors = validation.get("errors")
                    conversation.status = "refining" if validation["valid"] else "failed"
                    
                    db.commit()
                    
                    yield f"data: {json.dumps({'type': 'generation_complete', 'success': True, 'node_type': node_type})}\n\n"
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process generated code: {e}", exc_info=True)
                    yield f"data: {json.dumps({'type': 'generation_complete', 'success': False, 'error': str(e)})}\n\n"
            
            db.commit()
            
            # Signal done
            yield f"data: {json.dumps({'type': 'done', 'ready_to_generate': ready_to_generate, 'requirements': requirements})}\n\n"
        
        except Exception as e:
            logger.error(f"❌ Stream failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """List conversations (optionally by status: active/generating/refining/completed/failed/abandoned)."""
    logger.info(f"📋 Listing conversations for user {current_user.id}")
    
    try:
        query = db.query(Conversation).filter(Conversation.user_id == current_user.id)
        
        if status:
            query = query.filter(Conversation.status == status)
        
        conversations = query.order_by(Conversation.updated_at.desc()).limit(limit).all()
        
        conversation_list = [
            ConversationDetail(
                id=conv.id,
                title=conv.title,
                status=conv.status,
                provider=conv.provider,
                model=conv.model,
                temperature=conv.temperature,
                requirements=conv.requirements,
                generated_code=conv.generated_code,
                node_type=conv.node_type,
                message_count=conv.message_count,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                completed_at=conv.completed_at
            )
            for conv in conversations
        ]
        
        return ConversationListResponse(
            success=True,
            conversations=conversation_list,
            total=len(conversation_list)
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to list conversations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list conversations: {str(e)}"
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Get full conversation details including all messages.
    
    Used to resume a conversation or review history.
    """
    logger.info(f"📖 Getting conversation {conversation_id}")
    
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages
        messages = [
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                provider=msg.provider,
                model=msg.model
            )
            for msg in conversation.messages
        ]
        
        conversation_detail = ConversationDetail(
            id=conversation.id,
            title=conversation.title,
            status=conversation.status,
            provider=conversation.provider,
            model=conversation.model,
            temperature=conversation.temperature,
            requirements=conversation.requirements,
            generated_code=conversation.generated_code,
            node_type=conversation.node_type,
            message_count=conversation.message_count,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            completed_at=conversation.completed_at
        )
        
        return ConversationDetailResponse(
            success=True,
            conversation=conversation_detail,
            messages=messages
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation: {str(e)}"
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Delete a conversation and all its messages."""
    logger.info(f"🗑️ Deleting conversation {conversation_id}")
    
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        db.delete(conversation)
        db.commit()
        
        return {"success": True, "message": "Conversation deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete conversation: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )


# ==============================================================================
# CODE GENERATION ENDPOINTS  
# ==============================================================================

@router.post("/conversations/{conversation_id}/generate", response_model=GenerateCodeResponse)
async def generate_code(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Generate node code from conversation requirements.
    
    This endpoint:
    1. Extracts all requirements from conversation history
    2. Generates complete Python node class using AI
    3. Validates the generated code
    4. Stores code in conversation
    5. Returns code for review
    
    Note: This does NOT save to filesystem yet - that's a separate step.
    """
    logger.info(f"✨ Generating code for conversation {conversation_id}")
    
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Update status
        conversation.status = "generating"
        db.commit()
        
        # Generate code
        from app.services.node_generator import NodeGenerator
        
        generator = NodeGenerator(db)
        result = await generator.generate_from_conversation(conversation)
        
        # Validate code
        from app.services.code_validator import NodeCodeValidator
        
        validator = NodeCodeValidator()
        validation = validator.validate(result["code"])
        
        # Update conversation with generated code
        conversation.generated_code = result["code"]
        conversation.node_type = result.get("node_type")
        conversation.class_name = result.get("class_name")
        conversation.validation_status = "valid" if validation["valid"] else "invalid"
        conversation.validation_errors = validation.get("errors")
        conversation.status = "refining" if validation["valid"] else "failed"
        conversation.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"✅ Code generated: {result.get('node_type')}, valid={validation['valid']}")
        
        return GenerateCodeResponse(
            success=True,
            code=result["code"],
            node_type=result["node_type"],
            class_name=result["class_name"],
            validation_status="valid" if validation["valid"] else "invalid",
            validation_errors=validation.get("errors")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Code generation failed: {e}", exc_info=True)
        db.rollback()
        
        # Update conversation status to failed
        try:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                conversation.status = "failed"
                db.commit()
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate code: {str(e)}"
        )


@router.post("/conversations/{conversation_id}/refine", response_model=GenerateCodeResponse)
async def refine_code(
    conversation_id: str,
    request: RefineCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Refine generated code based on user feedback.
    
    User can request changes like:
    - "Add error handling for API timeouts"
    - "Change the temperature config to use a slider"
    - "Add a retry mechanism"
    
    AI will modify the code and return updated version.
    """
    logger.info(f"🔄 Refining code for conversation {conversation_id}")
    
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if not conversation.generated_code:
            raise HTTPException(status_code=400, detail="No code generated yet")
        
        # Save user refinement request as message
        user_msg = ConversationMessage(
            conversation_id=conversation_id,
            role="user",
            content=f"[Refinement Request] {request.refinement_request}",
            created_at=datetime.utcnow()
        )
        db.add(user_msg)
        
        # Refine code with AI
        from app.services.node_generator import NodeGenerator
        
        generator = NodeGenerator(db)
        result = await generator.refine_code(
            conversation=conversation,
            refinement_request=request.refinement_request
        )
        
        # Validate refined code
        from app.services.code_validator import NodeCodeValidator
        
        validator = NodeCodeValidator()
        validation = validator.validate(result["code"])
        
        # Update conversation
        conversation.generated_code = result["code"]
        conversation.validation_status = "valid" if validation["valid"] else "invalid"
        conversation.validation_errors = validation.get("errors")
        conversation.updated_at = datetime.utcnow()
        
        # Save AI response
        assistant_msg = ConversationMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=f"[Refinement] {result.get('explanation', 'Code updated')}",
            provider=conversation.provider,
            model=conversation.model,
            created_at=datetime.utcnow()
        )
        db.add(assistant_msg)
        
        db.commit()
        
        logger.info(f"✅ Code refined successfully")
        
        return GenerateCodeResponse(
            success=True,
            code=result["code"],
            node_type=conversation.node_type or "",
            class_name=conversation.class_name or "",
            validation_status="valid" if validation["valid"] else "invalid",
            validation_errors=validation.get("errors")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Code refinement failed: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refine code: {str(e)}"
        )


# ==============================================================================
# VALIDATION & SAVE ENDPOINTS (Reuse from original API)
# ==============================================================================

@router.post("/validate", response_model=NodeValidationResponse)
async def validate_node_code(
    request: NodeValidationRequest,
    current_user: User = Depends(get_current_user_smart)
):
    """Validate custom node code for security and correctness."""
    logger.info(f"🔍 Validating node code")
    
    try:
        from app.services.code_validator import NodeCodeValidator
        
        validator = NodeCodeValidator()
        result = validator.validate(request.code)
        
        errors = [ValidationError(message=err, severity="error") for err in result.get("errors", [])]
        warnings = [ValidationError(message=warn, severity="warning") for warn in result.get("warnings", [])]
        
        return NodeValidationResponse(
            valid=result["valid"],
            errors=errors,
            warnings=warnings,
            node_type=result.get("node_type"),
            class_name=result.get("class_name"),
            message="Validation complete" if result["valid"] else "Validation failed"
        )
    
    except Exception as e:
        logger.error(f"❌ Validation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate node code: {str(e)}"
        )


@router.post("/save", response_model=SaveNodeResponse)
async def save_custom_node(
    request: SaveNodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Save validated custom node to filesystem and database.
    
    This is the final step after code generation and review.
    """
    logger.info(f"💾 Saving custom node from conversation {request.conversation_id}")
    
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Use provided code or conversation code
        code = request.code or conversation.generated_code
        
        if not code:
            raise HTTPException(status_code=400, detail="No code to save")
        
        # Validate one more time
        from app.services.code_validator import NodeCodeValidator
        from app.services.node_saver import NodeSaver
        
        validator = NodeCodeValidator()
        validation = validator.validate(code)
        
        if not validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Code validation failed: {validation['errors']}"
            )
        
        # Save to filesystem
        saver = NodeSaver()
        save_result = saver.save_node(
            code=code,
            node_type=validation["node_type"],
            overwrite=request.overwrite
        )
        
        # Create CustomNode record
        custom_node = CustomNode(
            user_id=current_user.id,
            conversation_id=conversation.id,
            node_type=validation["node_type"],
            display_name=conversation.title,
            description=conversation.requirements.get("functionality") if conversation.requirements else None,
            category=conversation.requirements.get("category", "processing") if conversation.requirements else "processing",
            icon=conversation.requirements.get("icon") if conversation.requirements else None,
            code=code,
            file_path=save_result["file_path"],
            is_active=True,
            is_registered=False,
            version="1.0.0",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(custom_node)
        
        # Update conversation
        conversation.status = "completed"
        conversation.completed_at = datetime.utcnow()
        conversation.custom_node_id = custom_node.id
        
        db.commit()
        
        # Hot-reload
        try:
            from app.services.node_reloader import NodeReloader
            reloader = NodeReloader()
            await reloader.reload_custom_nodes()
            custom_node.is_registered = True
            db.commit()
            registered = True
        except Exception as reload_error:
            logger.warning(f"⚠️ Hot-reload failed: {reload_error}")
            registered = False
        
        logger.info(f"✅ Node saved: {save_result['file_path']}")
        
        return SaveNodeResponse(
            success=True,
            node_type=validation["node_type"],
            file_path=save_result["file_path"],
            message=save_result["message"],
            registered=registered
        )
    
    except HTTPException:
        raise
    except FileExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Failed to save node: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save node: {str(e)}"
        )
