# Variable Resolution Reference

This document covers the variable resolution system used in TAV workflows for dynamic configuration values.

> **Architecture Overview**: See [Node Architecture](../architecture/nodes.md) for how variables integrate with node execution.

---

## Overview

The variable system supports three modes for configuration values:

1. **Literal values** - Direct, static values
2. **Variable references** - Read from shared space (`{{node_id.field}}`)
3. **Template strings** - Mix text and variables (`Hello {{node1.name}}`)
4. **System variables** - Built-in values (`{current_date}`)

---

## Variable Syntax

### Node Variables (Double Braces)

Reference data from other nodes using `{{node_id.field}}`:

```
{{trigger.name}}              → Value of 'name' field from 'trigger' node
{{http_request.response}}     → Response from 'http_request' node
{{llm_chat.output.summary}}   → Nested field access
```

### System Variables (Single Braces)

Access built-in system values using `{variable_name}`:

```
{current_date}      → 2024-12-04
{current_time}      → 14:30:45
{current_datetime}  → 2024-12-04 14:30:45
{timestamp}         → 1733320245
{year}              → 2024
{month}             → 12
{day}               → 4
{hour}              → 14
{minute}            → 30
{second}            → 45
```

---

## Available System Variables

| Variable | Format | Example |
|----------|--------|---------|
| `current_date` | YYYY-MM-DD | 2024-12-04 |
| `current_time` | HH:MM:SS | 14:30:45 |
| `current_datetime` | YYYY-MM-DD HH:MM:SS | 2024-12-04 14:30:45 |
| `timestamp` | Unix timestamp | 1733320245 |
| `year` | YYYY | 2024 |
| `month` | M (1-12) | 12 |
| `day` | D (1-31) | 4 |
| `hour` | H (0-23) | 14 |
| `minute` | M (0-59) | 30 |
| `second` | S (0-59) | 45 |

---

## Shared Space Structure

Variables are stored in a shared space during workflow execution:

```python
variables = {
    "_nodes": {
        "trigger": {
            "name": "John Doe",
            "email": "john@example.com",
            "data": {"order_id": "12345"}
        },
        "http_request": {
            "response": {
                "status": 200,
                "body": {"result": "success"}
            }
        },
        "llm_chat": {
            "output": "Generated text...",
            "tokens_used": 150
        }
    }
}
```

Each node's output is stored under `_nodes.{node_id}`.

---

## API Reference

### resolve_variable()

Resolve a variable path to its value from the shared space.

```python
from app.core.nodes.variables import resolve_variable

variables = {
    "_nodes": {
        "node1": {"phone": "+1234567890"},
        "http_request": {
            "response": {"full_name": "John Doe"}
        }
    }
}

# Simple field access
value = resolve_variable("node1.phone", variables)
# "+1234567890"

# Nested field access
value = resolve_variable("http_request.response.full_name", variables)
# "John Doe"

# Non-existent field returns None
value = resolve_variable("node1.invalid", variables)
# None
```

**Signature:**
```python
def resolve_variable(
    variable_path: str,     # e.g., "node1.phone" or "node1.response.field"
    variables: Dict[str, Any]
) -> Optional[Any]
```

**Variable Path Format:**
- First segment: node ID (`node1`, `trigger`, `http_request`)
- Remaining segments: field path (`phone`, `response.body.result`)
- Minimum 2 segments required (`node_id.field`)

---

### resolve_template()

Resolve a template string with both node and system variables.

```python
from app.core.nodes.variables import resolve_template

variables = {
    "_nodes": {
        "trigger": {"name": "John", "order_id": "12345"}
    }
}

# Node variables (double braces)
result = resolve_template(
    "Hello {{trigger.name}}, your order #{{trigger.order_id}} is confirmed",
    variables
)
# "Hello John, your order #12345 is confirmed"

# System variables (single braces)
result = resolve_template(
    "Report generated on {current_date} at {current_time}",
    variables
)
# "Report generated on 2024-12-04 at 14:30:45"

# Mixed
result = resolve_template(
    "Hi {{trigger.name}}, today is {current_date}",
    variables
)
# "Hi John, today is 2024-12-04"

# Unresolved variables are kept as-is
result = resolve_template(
    "Hello {{trigger.invalid}}",
    variables
)
# "Hello {{trigger.invalid}}"
```

**Signature:**
```python
def resolve_template(
    template: str,
    variables: Dict[str, Any]
) -> str
```

---

### resolve_config_value()

Universal config value resolver. Handles all input formats.

```python
from app.core.nodes.variables import resolve_config_value

variables = {
    "_nodes": {
        "node1": {"phone": "+1234", "name": "John"}
    }
}

# Structured format - literal
value = resolve_config_value(
    {"source": "literal", "value": "Hello"},
    variables
)
# "Hello"

# Structured format - variable
value = resolve_config_value(
    {"source": "variable", "variable_path": "node1.phone"},
    variables
)
# "+1234"

# Structured format - template
value = resolve_config_value(
    {"source": "template", "template": "Hi {{node1.name}}"},
    variables
)
# "Hi John"

# Plain string with templates (backward compatible)
value = resolve_config_value(
    "Hi {{node1.name}}, date: {current_date}",
    variables
)
# "Hi John, date: 2024-12-04"

# Plain value (pass-through)
value = resolve_config_value("literal string", variables)
# "literal string"

value = resolve_config_value(123, variables)
# 123
```

**Signature:**
```python
def resolve_config_value(
    config_value: Any,
    variables: Dict[str, Any]
) -> Any
```

**Supported Formats:**

| Format | Example | Description |
|--------|---------|-------------|
| Structured literal | `{"source": "literal", "value": "Hello"}` | Direct value |
| Structured variable | `{"source": "variable", "variable_path": "node1.field"}` | Single variable |
| Structured template | `{"source": "template", "template": "{{node1.name}}"}` | Template string |
| Plain template | `"Hello {{node1.name}}"` | Backward compatible |
| Plain value | `"text"`, `123`, `true` | Pass-through |

**Encryption Support:**
Encrypted values (from credential storage) are automatically decrypted before resolution.

---

### get_system_variable()

Get a single system variable value.

```python
from app.core.nodes.variables import get_system_variable

date = get_system_variable("current_date")
# "2024-12-04"

time = get_system_variable("current_time")
# "14:30:45"

# Unknown variable returns None
value = get_system_variable("unknown")
# None
```

**Signature:**
```python
def get_system_variable(var_name: str) -> Optional[str]
```

---

### get_available_variables()

Get all available variables in shared space (for UI/debugging).

```python
from app.core.nodes.variables import get_available_variables

variables = {
    "_nodes": {
        "node1": {"phone": "+1234", "message": "Hello"},
        "node2": {"status": "ok"}
    }
}

available = get_available_variables(variables)
# {
#     "node1": {"phone": "+1234", "message": "Hello"},
#     "node2": {"status": "ok"}
# }
```

**Signature:**
```python
def get_available_variables(variables: Dict[str, Any]) -> Dict[str, Dict[str, Any]]
```

---

### get_variable_paths()

Get all available variable paths (for autocomplete).

```python
from app.core.nodes.variables import get_variable_paths

variables = {
    "_nodes": {
        "node1": {"phone": "+1234", "message": "Hello"},
        "node2": {"status": "ok"}
    }
}

paths = get_variable_paths(variables)
# ["node1.message", "node1.phone", "node2.status"]
```

**Signature:**
```python
def get_variable_paths(variables: Dict[str, Any]) -> list[str]
```

---

## Usage in Nodes

### Using resolve_config()

The `Node` base class provides `resolve_config()` which automatically handles variable resolution:

```python
class MyNode(Node):
    async def execute(self, input_data: NodeExecutionInput):
        # Automatically resolves variables in config values
        recipient = self.resolve_config(input_data, "recipient")
        
        # With default value
        timeout = self.resolve_config(input_data, "timeout", 30)
        
        # Template in config
        message = self.resolve_config(input_data, "message")
        # If config is "Hello {{trigger.name}}", resolves to "Hello John"
```

### Manual Resolution

For custom variable handling:

```python
from app.core.nodes.variables import resolve_template, resolve_config_value

class MyNode(Node):
    async def execute(self, input_data: NodeExecutionInput):
        variables = input_data.variables
        
        # Resolve a template
        greeting = resolve_template(
            "Welcome, {{trigger.user.name}}!",
            variables
        )
        
        # Resolve any config format
        value = resolve_config_value(
            self.config.get("some_field"),
            variables
        )
```

---

## Config Schema with Variables

Enable variable support in node config schema:

```python
@classmethod
def get_config_schema(cls):
    return {
        "recipient": {
            "type": "string",
            "label": "Recipient",
            "allow_template": True,  # Enable variable picker in UI
            "placeholder": "{{trigger.email}}"
        },
        "message": {
            "type": "string",
            "widget": "textarea",
            "label": "Message",
            "allow_template": True,
            "help": "Use {{node.field}} for variables, {current_date} for system vars"
        }
    }
```

The `allow_template: true` flag tells the frontend to show a variable picker UI.

---

## Structured Config Format

For explicit control, use structured format:

```json
{
    "node_id": "email_sender",
    "config": {
        "recipient": {
            "source": "variable",
            "variable_path": "trigger.email"
        },
        "subject": {
            "source": "template",
            "template": "Order {{trigger.order_id}} - {current_date}"
        },
        "body": {
            "source": "literal",
            "value": "Thank you for your order!"
        }
    }
}
```

---

## Best Practices

### 1. Use Default Values

```python
# ✅ Good - provides fallback
value = self.resolve_config(input_data, "field", "default")

# ❌ Risky - may be None
value = self.resolve_config(input_data, "field")
```

### 2. Handle Missing Variables

```python
# Variables that don't exist return None (for resolve_variable)
# or keep placeholder (for resolve_template)

value = resolve_variable("nonexistent.field", variables)
if value is None:
    # Handle missing data
    pass

result = resolve_template("Hello {{missing.name}}", variables)
# "Hello {{missing.name}}" - placeholder preserved
```

### 3. Document Expected Variables

```python
class MyNode(Node):
    """
    My Node - processes trigger data.
    
    Expected Variables:
    - {{trigger.user.name}} - User's name
    - {{trigger.user.email}} - User's email
    """
```

### 4. Nested Access for Complex Data

```python
# Access deeply nested data
value = resolve_variable("api_response.data.users.0.name", variables)

# The path traverses:
# _nodes → api_response → data → users → [0] → name
```

### 5. Combine with System Variables

```python
# Create meaningful dynamic content
template = """
Report for {{trigger.customer_name}}
Generated: {current_datetime}
Period: {year}-{month}
"""

result = resolve_template(template, variables)
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Variable path too short (`"node1"`) | Returns `None`, logs warning |
| Node not found in shared space | Returns `None`, logs debug |
| Field not found in node data | Returns `None`, logs debug |
| Invalid system variable | Returns `None` (kept in template) |
| Non-string template | Converted to string |

All resolution functions are designed to be safe - they return `None` or preserve placeholders rather than throwing errors.

