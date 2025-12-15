# Node Capabilities Reference

This document provides the complete API reference for all node capability mixins. Capabilities are composable mixins that add functionality to nodes.

> **Architecture Overview**: See [Node Architecture](../architecture/nodes.md) for conceptual understanding of how capabilities fit into the node system.

---

## Overview

Capabilities follow the **composition over inheritance** pattern. Nodes can mix in multiple capabilities:

```python
class MyNode(Node, LLMCapability, ExportCapability):
    """A node that uses LLM and exports files"""
    pass
```

### Available Capabilities

| Capability | Purpose | Resource Pool | Auto-Injected Config |
|------------|---------|---------------|---------------------|
| `LLMCapability` | LLM API calls | `llm` | provider, model, temperature |
| `AICapability` | Embeddings, RAG, ML | `ai` | - |
| `ComputeCapability` | Heavy computation | `ai` | - |
| `TriggerCapability` | Workflow triggers | `standard` | - |
| `ExportCapability` | File export/download | `standard` | export_mode, output_folder, filename |
| `PasswordProtectedFileCapability` | Encrypted file handling | - | file_password |

---

## LLMCapability

Mixin for nodes that call LLM APIs via LangChain.

### Features
- Auto-injected LLM config fields (provider, model, temperature, max_tokens)
- Helper methods for LLM calls via LangChainManager
- Automatic resource pool assignment (`llm`)
- Config cascade: node config → workflow variables → global defaults

### Usage

```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import LLMCapability

class TextSummarizerNode(Node, LLMCapability):
    async def execute(self, input_data: NodeExecutionInput):
        text = input_data.ports.get("text")
        
        # Simple LLM call
        summary = await self.call_llm(
            user_prompt=f"Summarize this text: {text}",
            system_prompt="You are a professional summarizer."
        )
        
        return {"summary": summary}
```

### Auto-Injected Config Fields

When a node has `LLMCapability`, these config fields are automatically added:

| Field | Type | Widget | Description |
|-------|------|--------|-------------|
| `llm_provider` | string | `provider_select` | AI provider (openai, anthropic, etc.) |
| `llm_model` | string | `model_select` | Model name (dynamic based on provider) |
| `llm_temperature` | float | `slider` | Sampling temperature (0.0-2.0) |

### Methods

#### `call_llm()`

Simple LLM call with auto-injected config.

```python
async def call_llm(
    self,
    user_prompt: str,
    system_prompt: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    **kwargs  # Override config: provider, model, temperature, max_tokens
) -> str:
```

**Parameters:**
- `user_prompt`: The user message to send
- `system_prompt`: Optional system context
- `context`: Optional additional context data (will be extracted via `extract_content`)
- `**kwargs`: Override LLM config for this specific call

**Returns:** LLM response content as string

**Example:**
```python
# Basic call
response = await self.call_llm("Generate a greeting")

# With system prompt
response = await self.call_llm(
    user_prompt="Translate to French: Hello",
    system_prompt="You are a translator."
)

# Override config for this call
response = await self.call_llm(
    user_prompt="Be creative!",
    temperature=1.5,
    model="gpt-4"
)
```

#### `call_llm_with_messages()`

Multi-turn conversation with optional function calling.

```python
async def call_llm_with_messages(
    self,
    messages: List[Dict[str, str]],
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
```

**Parameters:**
- `messages`: List of messages in OpenAI format `[{"role": "user", "content": "..."}]`
- `tools`: Optional list of tool definitions for function calling
- `tool_choice`: Optional tool choice preference

**Returns:** Dict with `content` and optionally `tool_calls`

**Example:**
```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What's the weather?"}
]

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            }
        }
    }
}]

response = await self.call_llm_with_messages(
    messages=messages,
    tools=tools,
    tool_choice="auto"
)
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `llm_provider` | `Optional[str]` | Configured LLM provider |
| `llm_model` | `Optional[str]` | Configured model name |
| `llm_temperature` | `Optional[float]` | Configured temperature |
| `llm_max_tokens` | `Optional[int]` | Configured max tokens |

### Config Cascade

LLM config is resolved with priority (highest to lowest):

1. **Node-level config** - Set in workflow node definition
2. **Workflow variables** - Set in execution context
3. **Global AIGovernor defaults** - From app settings/environment

```python
# Example: Node config (highest priority)
{
    "node_id": "summarizer",
    "config": {
        "llm_provider": "anthropic",  # Will be used
        "llm_model": "claude-3-sonnet-20240229"
    }
}

# Workflow variables (middle priority)
variables = {
    "llm_provider": "openai",  # Ignored (node config wins)
    "llm_max_tokens": 500      # Used (not in node config)
}

# Global defaults (lowest priority)
# From AIConfig in app settings
```

### Cleanup

LLMCapability creates a database session for LangChain operations. Call `cleanup()` when done:

```python
node.cleanup()  # Closes database session
```

---

## AICapability

Mixin for compute-intensive AI nodes (embeddings, RAG, vision, etc.).

### Features
- Marks node for AI resource pool (`ai`)
- Helper methods for embeddings via LangChain
- Vector search support

### Use Cases
- Image processing
- Embeddings generation
- Local ML inference
- Video/audio processing
- RAG operations

### Usage

```python
from app.core.nodes.base import Node
from app.core.nodes.capabilities import AICapability

class DocumentEmbedderNode(Node, AICapability):
    async def execute(self, input_data):
        text = input_data.ports.get("text")
        
        # Generate embeddings
        embedding = await self.embed_text(text)
        
        return {"embedding": embedding}
```

### Methods

#### `get_embeddings()`

Get LangChain Embeddings instance.

```python
def get_embeddings(
    self,
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> Embeddings:
```

**Returns:** LangChain Embeddings instance (defaults to HuggingFace local - FREE!)

#### `embed_text()`

Embed a single text string.

```python
async def embed_text(
    self,
    text: str,
    provider: Optional[str] = None
) -> List[float]:
```

**Returns:** Embedding vector (list of floats)

#### `embed_documents()`

Embed multiple documents.

```python
async def embed_documents(
    self,
    texts: List[str],
    provider: Optional[str] = None
) -> List[List[float]]:
```

**Returns:** List of embedding vectors

---

## ComputeCapability

Marker mixin for heavy computation nodes (non-AI).

### Features
- Marks node for compute resource pool (`ai`)
- No additional methods - purely a resource marker

### Use Cases
- Video encoding
- Large file processing
- Data transformation
- Complex calculations

### Usage

```python
from app.core.nodes.base import Node
from app.core.nodes.capabilities import ComputeCapability

class VideoEncoderNode(Node, ComputeCapability):
    async def execute(self, input_data):
        # Heavy computation runs with resource limiting
        result = await encode_video(input_data.ports["video"])
        return {"output": result}
```

---

## ExportCapability

Mixin for nodes that generate downloadable files (CSV, PDF, Excel, etc.).

### Features
- Auto-injected export config fields
- Two export modes: download (browser) or save to path
- Network share support with authentication
- Standardized MediaFormat output
- Temporary file management

### Usage

```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import ExportCapability

class CSVExportNode(Node, ExportCapability):
    @classmethod
    def get_config_schema(cls):
        # Export fields are auto-injected, just define your custom fields
        return {
            "delimiter": {
                "type": "string",
                "label": "Delimiter",
                "default": ","
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput):
        # Generate your file content
        csv_content = b"name,value\nfoo,123"
        
        # Use ExportCapability to handle download/save
        return await self.handle_export(
            input_data=input_data,
            file_content=csv_content,
            filename="export.csv",
            mime_type="text/csv"
        )
```

### Auto-Injected Config Fields

| Field | Type | Widget | Description |
|-------|------|--------|-------------|
| `export_mode` | select | `select` | "download" or "path" |
| `output_folder` | string | `folder_picker` | Folder path (for "path" mode) |
| `network_credential` | string | `credential` | Credential for network shares |
| `filename` | string | `text` | Output filename (supports templates) |

### Methods

#### `handle_export()`

Handle export based on configured mode.

```python
async def handle_export(
    self,
    input_data: NodeExecutionInput,
    file_content: bytes,
    filename: str,
    mime_type: str = "application/octet-stream"
) -> Dict[str, Any]:
```

**Parameters:**
- `input_data`: Node execution input (for config resolution)
- `file_content`: File content as bytes
- `filename`: Filename with extension
- `mime_type`: MIME type for download

**Returns:** Result dict with:
- `result`: Success/error info, file path, size
- `file`: MediaFormat output (can be connected to other nodes)
- `_download`: Download marker (for browser download mode)

### Export Modes

#### Download Mode (default)
- Saves file to `data/temp/`
- Returns download marker for frontend
- Browser triggers download to user's Downloads folder

#### Path Mode
- Saves directly to specified `output_folder`
- Supports local paths: `C:\Users\Name\exports`
- Supports UNC network shares: `\\server\share\folder`
- Optional credential for authenticated network shares

### Filename Templates

Supported placeholders:
- `{timestamp}` - YYYYMMDD_HHMMSS
- `{date}` - YYYYMMDD
- `{time}` - HHMMSS
- `{datetime}` - YYYYMMDD_HHMMSS
- `{year}`, `{month}`, `{day}`

**Example:** `report_{date}.csv` → `report_20241204.csv`

### Network Share Authentication

For UNC paths requiring authentication:

1. Create a Basic Auth credential in the system
2. Select it in `network_credential` config
3. ExportCapability handles authentication automatically

```python
# Path like: \\192.168.1.100\shared\exports
# Credential provides: username, password
```

---

## TriggerCapability

Mixin for trigger nodes that initiate workflow execution.

### Features
- No input ports (source nodes)
- Background monitoring via `start_monitoring()` / `stop_monitoring()`
- Direct workflow execution via `fire_trigger()`
- Concurrency-controlled execution spawning

### Usage

```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import TriggerCapability
from app.core.nodes.registry import register_node
import asyncio

@register_node("schedule_trigger", category="triggers")
class ScheduleTriggerNode(Node, TriggerCapability):
    trigger_type = "schedule"  # For execution_source
    
    async def execute(self, input_data: NodeExecutionInput):
        # Only called for manual testing
        return {"output": "triggered manually"}
    
    async def start_monitoring(self, workflow_id: str, executor_callback):
        self._workflow_id = workflow_id
        self._executor_callback = executor_callback
        self._is_monitoring = True
        
        interval = self.config.get("interval_seconds", 300)
        self._monitoring_task = asyncio.create_task(self._monitor_loop(interval))
    
    async def stop_monitoring(self):
        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
    
    async def _monitor_loop(self, interval: int):
        while self._is_monitoring:
            await asyncio.sleep(interval)
            await self.fire_trigger({
                "trigger_time": datetime.now().isoformat(),
                "trigger_type": "schedule"
            })
```

### Abstract Methods (Must Implement)

#### `start_monitoring()`

Start monitoring for trigger events.

```python
async def start_monitoring(
    self,
    workflow_id: str,
    executor_callback: Callable[[str, Dict[str, Any], str], Awaitable[None]]
):
```

**Parameters:**
- `workflow_id`: Workflow to trigger
- `executor_callback`: Function to call when triggered (signature: `(workflow_id, trigger_data, execution_source)`)

#### `stop_monitoring()`

Stop monitoring for trigger events.

```python
async def stop_monitoring(self):
```

Should:
- Set `self._is_monitoring = False`
- Cancel `self._monitoring_task`
- Clean up resources

### Methods

#### `fire_trigger()`

Fire the trigger (spawn workflow execution).

```python
async def fire_trigger(self, trigger_data: Dict[str, Any]):
```

**Parameters:**
- `trigger_data`: Data to pass to workflow execution (becomes initial payload)

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_monitoring` | `bool` | Whether trigger is currently monitoring |
| `trigger_type` | `str` | Execution source identifier (set as class attribute) |

---

## PasswordProtectedFileCapability

Mixin for nodes that process password-protected files.

### Features
- Auto-injected `file_password` config field
- PDF password support via PyMuPDF
- Office document (DOCX, XLSX, PPTX) support via msoffcrypto-tool
- Consistent password handling across all file processing nodes

### Supported File Types

| Type | Library | Formats |
|------|---------|---------|
| PDF | PyMuPDF (fitz) | .pdf |
| Office | msoffcrypto-tool | .docx, .xlsx, .pptx |
| ZIP | zipfile (stdlib) | .zip |

### Usage

```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import PasswordProtectedFileCapability

class DocumentLoaderNode(Node, PasswordProtectedFileCapability):
    # file_password field automatically added to config schema!
    
    async def execute(self, input_data: NodeExecutionInput):
        file_path = input_data.ports.get("file")
        password = self.resolve_config(input_data, "file_password")
        
        # Open PDF with password support
        doc = self.open_pdf_with_password(file_path, password)
        
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        return {"text": text}
```

### Auto-Injected Config Field

| Field | Type | Widget | Description |
|-------|------|--------|-------------|
| `file_password` | string | `password` | Password for encrypted files |

### Methods

#### `open_pdf_with_password()`

Open PDF with optional password support.

```python
def open_pdf_with_password(
    self,
    pdf_path: str,
    password: Optional[str] = None
) -> fitz.Document:
```

**Parameters:**
- `pdf_path`: Path to PDF file
- `password`: Optional password

**Returns:** PyMuPDF document object

**Raises:**
- `ImportError`: If PyMuPDF not installed
- `ValueError`: If PDF is encrypted but no password, or password incorrect

#### `open_office_doc_with_password()`

Decrypt password-protected Office document.

```python
def open_office_doc_with_password(
    self,
    file_path: str,
    password: Optional[str] = None,
    output_path: Optional[str] = None
) -> str:
```

**Parameters:**
- `file_path`: Path to encrypted Office document
- `password`: Password for decryption
- `output_path`: Optional path for decrypted file (creates temp file if None)

**Returns:** Path to decrypted file

#### `check_pdf_encrypted()`

Check if a PDF is password-protected.

```python
def check_pdf_encrypted(self, pdf_path: str) -> bool:
```

---

## Helper Functions

### Resource Detection

```python
from app.core.nodes.capabilities import (
    get_resource_classes,
    has_llm_capability,
    has_ai_capability,
    has_trigger_capability,
    has_password_capability
)

# Get resource pools for a node
resources = get_resource_classes(node)  # ["llm"], ["ai"], ["standard"], or ["llm", "ai"]

# Check specific capabilities
if has_llm_capability(node):
    # Node uses LLM
    pass
```

### Resource Classes

| Capability | Resource Class |
|------------|---------------|
| None | `["standard"]` |
| LLMCapability | `["llm"]` |
| AICapability | `["ai"]` |
| ComputeCapability | `["ai"]` |
| LLMCapability + AICapability | `["llm", "ai"]` |

---

## Combining Capabilities

Nodes can mix multiple capabilities:

```python
@register_node("ai_report_generator", category="ai")
class AIReportGeneratorNode(Node, LLMCapability, ExportCapability):
    """
    Generates reports using AI and exports to PDF.
    
    Resource classes: ["llm"] (from LLMCapability)
    Auto-injected config: LLM fields + Export fields
    """
    
    async def execute(self, input_data: NodeExecutionInput):
        # Use LLM to generate content
        report = await self.call_llm(
            user_prompt="Generate a report from this data",
            context=input_data.ports.get("data")
        )
        
        # Use ExportCapability to save as PDF
        return await self.handle_export(
            input_data=input_data,
            file_content=report.encode(),
            filename="report.pdf",
            mime_type="application/pdf"
        )
```

```python
@register_node("document_analyzer", category="ai")
class DocumentAnalyzerNode(Node, LLMCapability, AICapability, PasswordProtectedFileCapability):
    """
    Analyzes documents with embeddings and LLM.
    
    Resource classes: ["llm", "ai"]
    Supports password-protected files.
    """
    pass
```

