# Node System Architecture

## Overview

The node system is the foundation for all workflow operations. It provides a simple yet powerful interface for building custom workflow nodes with automatic LLM integration, resource management, and execution tracking.

> **Reference Documentation:**
> - [Capabilities Reference](../reference/capabilities.md) - LLM, AI, Export, Trigger capabilities
> - [Multimodal Format Reference](../reference/multimodal.md) - MediaFormat and formatters
> - [Variables Reference](../reference/variables.md) - Variable resolution and templates
> - [Built-in Nodes Reference](../reference/built-in-nodes.md) - All available nodes

---

## Core Concepts

### Node Base Class

All nodes inherit from the `Node` base class in `backend/app/core/nodes/base.py`.

**Key Features:**
- Simple `execute()` interface - one method to implement
- Declarative port definitions via class methods
- Declarative config schema via class methods
- Type-safe configuration with auto-validation
- Resource class auto-detection for concurrency management

```python
class Node(ABC):
    def __init__(self, config: NodeConfiguration)
    
    # Define node interface (class methods)
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]
    
    # Execute the node
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]
```

### NodeExecutionInput

Data passed to `execute()`:

| Field | Type | Description |
|-------|------|-------------|
| `ports` | Dict | Input port data from connected nodes |
| `workflow_id` | str | Current workflow ID |
| `execution_id` | str | Current execution ID |
| `node_id` | str | This node's ID |
| `variables` | Dict | Workflow variables (shared space) |
| `config` | Dict | Node configuration |

---

## Port System

Nodes declare their inputs and outputs via class methods:

```python
@classmethod
def get_input_ports(cls) -> List[Dict[str, Any]]:
    return [
        {
            "name": "text",
            "type": PortType.TEXT,
            "display_name": "Text Input",
            "description": "Input text to process",
            "required": True
        }
    ]

@classmethod
def get_output_ports(cls) -> List[Dict[str, Any]]:
    return [
        {
            "name": "result",
            "type": PortType.TEXT,
            "display_name": "Result",
            "description": "Processed text"
        }
    ]
```

**Benefits:**
- ✅ No instantiation needed to query schema
- ✅ Declarative and self-documenting
- ✅ Full IDE support and type hints
- ✅ API can return definitions without executing nodes

### PortType Enum

```python
class PortType(str, Enum):
    # Core types
    SIGNAL = "signal"       # Control flow
    UNIVERSAL = "universal" # General data
    
    # Multimodal types
    TEXT = "text"           # Plain text, markdown, code
    IMAGE = "image"         # Images
    AUDIO = "audio"         # Audio files
    VIDEO = "video"         # Video files
    DOCUMENT = "document"   # Documents (PDF, DOCX)
    
    # Special ports
    TOOLS = "tools"         # Tool definitions
    MEMORY = "memory"       # Memory/retrieval context
    UI = "ui"               # Human-in-the-loop UI
```

---

## Configuration Schema

Nodes declare their configuration via `get_config_schema()`:

```python
@classmethod
def get_config_schema(cls) -> Dict[str, Any]:
    return {
        "max_length": {
            "type": "integer",
            "label": "Max Length",
            "description": "Maximum character length",
            "required": False,
            "default": 1000,
            "widget": "number",
            "min": 0,
            "max": 10000
        }
    }
```

### Supported Types & Widgets

| Type | Widgets | Description |
|------|---------|-------------|
| `string` | `text`, `textarea`, `password` | Text input |
| `integer` | `number` | Whole numbers |
| `float` | `number`, `slider` | Decimal numbers |
| `boolean` | `checkbox` | True/false |
| `select` | `select` | Dropdown selection |
| `array` | `tags` | List of values |

### Config Resolution

Use `resolve_config()` to get values with variable support:

```python
async def execute(self, input_data: NodeExecutionInput):
    # Resolves variables, applies defaults
    max_length = self.resolve_config(input_data, "max_length", 1000)
```

See [Variables Reference](../reference/variables.md) for template syntax.

---

## Capability System

Capabilities are composable mixins that add functionality:

```python
class MyNode(Node, LLMCapability, ExportCapability):
    """Node with LLM and export capabilities"""
    pass
```

### Available Capabilities

| Capability | Purpose | Resource Pool |
|------------|---------|---------------|
| `LLMCapability` | LLM API calls | `llm` |
| `AICapability` | Embeddings, ML | `ai` |
| `ComputeCapability` | Heavy computation | `ai` |
| `TriggerCapability` | Workflow triggers | `standard` |
| `ExportCapability` | File export | `standard` |
| `PasswordProtectedFileCapability` | Encrypted files | - |

See [Capabilities Reference](../reference/capabilities.md) for full API.

### Resource Management

Nodes are automatically assigned to resource pools based on capabilities:

| Capabilities | Resource Classes |
|--------------|------------------|
| None | `["standard"]` |
| LLMCapability | `["llm"]` |
| AICapability | `["ai"]` |
| Both | `["llm", "ai"]` |

The executor uses these to manage concurrency (semaphores per pool).

---

## Node Registry

Nodes are registered using the `@register_node` decorator:

```python
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory

@register_node(
    node_type="my_node",
    category=NodeCategory.PROCESSING,
    name="My Node",
    description="Does something useful",
    icon="fa-solid fa-gear",
    version="1.0.0"
)
class MyNode(Node):
    pass
```

### Auto-Discovery

The loader in `backend/app/core/nodes/loader.py` automatically discovers nodes:
- Scans `builtin/` and `custom/` directories
- Registers classes inheriting from `Node`
- No manual imports needed

### Registry API

```python
from app.core.nodes.registry import NodeRegistry

# Get node class
node_class = NodeRegistry.get("my_node")

# List all nodes
all_nodes = NodeRegistry.list_all()

# Check registration
if NodeRegistry.is_registered("my_node"):
    pass
```

---

## Node Categories

Categories organize nodes in the UI:

```python
class NodeCategory(Enum):
    TRIGGERS = "triggers"           # Webhook, Schedule, Manual
    COMMUNICATION = "communication" # HTTP, Email, Slack
    DATA = "data"                   # Database, Files, Transform
    LOGIC = "logic"                 # If/Else, Loop, Switch
    AI = "ai"                       # LLM, ML, RAG
    WORKFLOW = "workflow"           # Start, End, Subworkflow
    INTEGRATION = "integration"     # External services
    UTILITY = "utility"             # Delay, Math, String
    PROCESSING = "processing"       # Document processing
    INPUT = "input"                 # User input
    OUTPUT = "output"               # Display output
    EXPORT = "export"               # File export
```

**Important:** Category ≠ Capability. A node in `NodeCategory.AI` doesn't automatically use LLM - it needs `LLMCapability` for that.

---

## Example: Complete Node

```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import LLMCapability
from app.core.nodes.registry import register_node
from app.core.nodes.multimodal import TextFormatter
from app.schemas.workflow import NodeCategory, PortType

@register_node(
    node_type="text_summarizer",
    category=NodeCategory.AI,
    name="Text Summarizer",
    description="Summarize text using AI",
    icon="fa-solid fa-compress",
    version="1.0.0"
)
class TextSummarizerNode(Node, LLMCapability):
    """Summarizes text using LLM."""
    
    @classmethod
    def get_input_ports(cls):
        return [
            {
                "name": "text",
                "type": PortType.TEXT,
                "display_name": "Input Text",
                "required": True
            }
        ]
    
    @classmethod
    def get_output_ports(cls):
        return [
            {
                "name": "summary",
                "type": PortType.TEXT,
                "display_name": "Summary"
            }
        ]
    
    @classmethod
    def get_config_schema(cls):
        # LLM fields (provider, model, temperature) are auto-injected
        return {
            "max_words": {
                "type": "integer",
                "label": "Max Words",
                "default": 100,
                "min": 10,
                "max": 500
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput):
        # Get input
        text = input_data.ports.get("text", "")
        max_words = self.resolve_config(input_data, "max_words", 100)
        
        # Call LLM (from LLMCapability)
        summary = await self.call_llm(
            user_prompt=f"Summarize in {max_words} words:\n\n{text}",
            system_prompt="You are a professional summarizer."
        )
        
        # Return in MediaFormat
        return {
            "summary": TextFormatter.format(summary)
        }
```

---

## Trigger Nodes

Trigger nodes are special nodes that **initiate** workflow execution. They:
- Have no input ports (they're source nodes)
- Implement `TriggerCapability`
- Run in background monitoring mode
- Fire workflows via callback when events occur

```python
@register_node("schedule_trigger", category="triggers")
class ScheduleTriggerNode(Node, TriggerCapability):
    trigger_type = "schedule"
    
    async def start_monitoring(self, workflow_id, executor_callback):
        # Start background task
        self._monitoring_task = asyncio.create_task(self._loop())
    
    async def stop_monitoring(self):
        # Stop background task
        self._monitoring_task.cancel()
    
    async def _loop(self):
        while self._is_monitoring:
            await asyncio.sleep(300)
            await self.fire_trigger({"time": datetime.now()})
```

See [Capabilities Reference](../reference/capabilities.md#triggercapability) for details.

---

## Integration with Executor

### Node Instantiation

```python
# Executor loads node
node_config = workflow.get_node(node_id)
node_class = NodeRegistry.get(node_config.node_type)
node_instance = node_class(node_config)
```

### Node Execution

```python
# Build input
input_data = NodeExecutionInput(
    ports={"text": "Hello"},
    workflow_id=context.workflow_id,
    execution_id=context.execution_id,
    node_id=node_id,
    variables=context.variables,
    config=node_config.config
)

# Execute with resource constraints
resource_classes = node_instance.resource_classes
async with acquire_resources(resource_classes):
    outputs = await node_instance.execute(input_data)

# Store outputs
context.node_outputs[node_id] = outputs
```

See [Executor Architecture](./executor.md) for full execution flow.

---

## Key Design Principles

### 1. Composition Over Inheritance
- Capabilities as mixins, not base class inheritance
- Easy to combine: `Node, LLMCapability, ExportCapability`
- No inheritance hierarchy complexity

### 2. Declarative Definitions
- Ports and config defined via class methods
- No instance state needed for schema queries
- Self-documenting node definitions

### 3. Automatic Detection
- Resource classes detected from capabilities
- Config fields injected based on capabilities
- No manual capability declarations

### 4. Standardized Data Flow
- MediaFormat for all multimodal data
- Variable resolution for dynamic values
- Consistent patterns across all nodes

---

## File Structure

```
backend/app/core/nodes/
├── __init__.py          # Public exports
├── base.py              # Node base class, NodeExecutionInput
├── capabilities.py      # All capability mixins
├── registry.py          # NodeRegistry, @register_node
├── loader.py            # Auto-discovery and registration
├── multimodal.py        # MediaFormat, formatters
├── variables.py         # Variable resolution
├── builtin/             # Built-in nodes by category
│   ├── actions/
│   ├── ai/
│   ├── analytics/
│   ├── business/
│   ├── communication/
│   ├── control/
│   ├── data/
│   ├── input/
│   ├── output/
│   ├── processing/
│   └── triggers/
└── custom/              # Custom/business-specific nodes
```

---

## Summary

The node system provides:

✅ Simple base class with single `execute()` method  
✅ Composable capability mixins for LLM, AI, Export, etc.  
✅ Declarative port and config definitions  
✅ Automatic resource management  
✅ Standardized multimodal data format  
✅ Variable resolution for dynamic values  
✅ Auto-discovery and registration  

See the [Reference Documentation](#overview) for detailed API specifications.
