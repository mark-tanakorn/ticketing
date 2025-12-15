# Nodes API

Complete reference for discovering and working with workflow nodes.

---

## Overview

The Nodes API provides information about all available node types in TAV Engine. Use this API to:
- Discover what nodes are available
- Get node schemas and configuration options
- Build dynamic UI for node selection
- Validate node configurations

**Base Path:** `/api/v1/nodes`

---

## Table of Contents

- [Get Node Definitions](#get-node-definitions)
- [Get Registry Status](#get-registry-status)
- [Get Categories](#get-categories)
- [Reload Registry](#reload-registry)
- [Node Structure](#node-structure)
- [Node Categories](#node-categories)

---

## Get Node Definitions

Get all available node definitions with complete metadata.

### Endpoint

```
GET /api/v1/nodes/definitions
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | string | Filter by category (e.g., "ai", "actions", "triggers") |
| `search` | string | Search in node name or description |

### Response

**Status Code:** `200 OK`

```json
{
  "success": true,
  "total_nodes": 42,
  "nodes": [
    {
      "node_type": "text_input",
      "display_name": "Text Input",
      "description": "Input text manually or from variables",
      "category": "input",
      "icon": "fa-solid fa-keyboard",
      "class_name": "TextInputNode",
      "input_ports": [],
      "output_ports": [
        {
          "name": "output",
          "type": "text",
          "display_name": "Text Output",
          "description": "The input text",
          "required": false
        }
      ],
      "config_schema": {
        "default_text": {
          "type": "string",
          "label": "Default Text",
          "description": "Text to output",
          "required": false,
          "widget": "textarea",
          "default": ""
        }
      }
    },
    {
      "node_type": "llm_chat",
      "display_name": "LLM Chat",
      "description": "Send messages to AI models",
      "category": "ai",
      "icon": "fa-solid fa-brain",
      "class_name": "LLMChatNode",
      "input_ports": [
        {
          "name": "input",
          "type": "text",
          "display_name": "Message",
          "description": "User message to send to AI",
          "required": true
        }
      ],
      "output_ports": [
        {
          "name": "response",
          "type": "text",
          "display_name": "AI Response",
          "description": "Response from AI model"
        }
      ],
      "config_schema": {
        "llm_provider": {
          "type": "string",
          "label": "LLM Provider",
          "description": "AI provider (uses default from settings if not specified)",
          "required": false,
          "widget": "provider_select",
          "api_endpoint": "/api/v1/ai/providers/available"
        },
        "llm_model": {
          "type": "string",
          "label": "Model",
          "description": "Model to use",
          "required": false,
          "widget": "model_select",
          "depends_on": "llm_provider",
          "api_endpoint": "/api/v1/ai/providers/{llm_provider}/models"
        },
        "llm_temperature": {
          "type": "float",
          "label": "Temperature",
          "description": "Controls randomness (0.0 = deterministic, 1.0 = creative)",
          "required": false,
          "widget": "slider",
          "min": 0.0,
          "max": 2.0,
          "step": 0.1,
          "default": 0.7
        },
        "system_prompt": {
          "type": "string",
          "label": "System Prompt",
          "description": "Instructions for the AI",
          "required": false,
          "widget": "textarea",
          "default": "You are a helpful assistant"
        }
      }
    }
  ],
  "categories": {
    "input": [
      { "node_type": "text_input", ...},
      { "node_type": "image_upload", ...}
    ],
    "ai": [
      { "node_type": "llm_chat", ...},
      { "node_type": "vision_llm", ...}
    ],
    "output": [...],
    "processing": [...],
    "control": [...],
    "data": [...],
    "actions": [...],
    "triggers": [...]
  },
  "registry_info": {
    "total_nodes": 42,
    "nodes_by_category": {
      "input": 5,
      "ai": 4,
      "output": 3,
      "processing": 8,
      "control": 4,
      "data": 6,
      "actions": 7,
      "triggers": 5
    }
  }
}
```

### Examples

**Get all nodes:**
```bash
curl http://localhost:5000/api/v1/nodes/definitions
```

**Filter by category:**
```bash
curl "http://localhost:5000/api/v1/nodes/definitions?category=ai"
```

**Search nodes:**
```bash
curl "http://localhost:5000/api/v1/nodes/definitions?search=email"
```

**Combine filters:**
```bash
curl "http://localhost:5000/api/v1/nodes/definitions?category=actions&search=http"
```

---

## Get Registry Status

Get node registry statistics.

### Endpoint

```
GET /api/v1/nodes/registry/status
```

### Response

**Status Code:** `200 OK`

```json
{
  "success": true,
  "total_nodes": 42,
  "nodes_by_category": {
    "input": 5,
    "ai": 4,
    "output": 3,
    "processing": 8,
    "control": 4,
    "data": 6,
    "actions": 7,
    "triggers": 5
  },
  "node_types": [
    "text_input",
    "image_upload",
    "llm_chat",
    "vision_llm",
    "http_request",
    ...
  ]
}
```

### Example

```bash
curl http://localhost:5000/api/v1/nodes/registry/status
```

---

## Get Categories

Get list of all node categories.

### Endpoint

```
GET /api/v1/nodes/categories
```

### Response

**Status Code:** `200 OK`

```json
{
  "success": true,
  "categories": [
    {
      "id": "input",
      "label": "Input",
      "description": "Input nodes for receiving data",
      "icon": "fa-solid fa-arrow-right-to-bracket",
      "node_count": 5
    },
    {
      "id": "ai",
      "label": "AI",
      "description": "AI and machine learning nodes",
      "icon": "fa-solid fa-brain",
      "node_count": 4
    },
    {
      "id": "output",
      "label": "Output",
      "description": "Output nodes for displaying/exporting data",
      "icon": "fa-solid fa-arrow-right-from-bracket",
      "node_count": 3
    },
    {
      "id": "processing",
      "label": "Processing",
      "description": "Data processing and transformation",
      "icon": "fa-solid fa-gears",
      "node_count": 8
    },
    {
      "id": "control",
      "label": "Control Flow",
      "description": "Conditional logic and loops",
      "icon": "fa-solid fa-code-branch",
      "node_count": 4
    },
    {
      "id": "data",
      "label": "Data",
      "description": "Data parsing and manipulation",
      "icon": "fa-solid fa-database",
      "node_count": 6
    },
    {
      "id": "actions",
      "label": "Actions",
      "description": "External actions and integrations",
      "icon": "fa-solid fa-bolt",
      "node_count": 7
    },
    {
      "id": "triggers",
      "label": "Triggers",
      "description": "Automatic workflow triggers",
      "icon": "fa-solid fa-clock",
      "node_count": 5
    }
  ]
}
```

### Example

```bash
curl http://localhost:5000/api/v1/nodes/categories
```

---

## Reload Registry

Reload the node registry (scans for new nodes).

### Endpoint

```
POST /api/v1/nodes/registry/reload
```

### Response

**Status Code:** `200 OK`

```json
{
  "success": true,
  "message": "Node registry reloaded successfully",
  "stats": {
    "modules_scanned": 45,
    "nodes_found": 42,
    "nodes_registered": 42,
    "errors": []
  }
}
```

### Example

```bash
curl -X POST http://localhost:5000/api/v1/nodes/registry/reload
```

### Use Cases

- After adding custom nodes
- After system updates
- During development
- Troubleshooting missing nodes

---

## Node Structure

### Node Definition

Each node has the following structure:

```json
{
  "node_type": "unique_type_identifier",
  "display_name": "Human Readable Name",
  "description": "What this node does",
  "category": "ai",
  "icon": "fa-solid fa-brain",
  "class_name": "PythonClassName",
  "input_ports": [...],
  "output_ports": [...],
  "config_schema": {...}
}
```

### Port Definition

Input and output ports:

```json
{
  "name": "port_name",
  "type": "text",
  "display_name": "Human Readable Port Name",
  "description": "What data this port handles",
  "required": true,
  "default_value": null
}
```

**Port Types:**
- `universal`: Accepts any data type
- `text`: Text/string data
- `number`: Numeric data
- `boolean`: True/false
- `object`: JSON object
- `array`: List/array
- `image`: Image data
- `audio`: Audio data
- `video`: Video data
- `file`: File reference
- `signal`: Trigger signal (no data)

### Config Schema

Configuration fields:

```json
{
  "field_name": {
    "type": "string",
    "label": "Field Label",
    "description": "Help text",
    "required": false,
    "widget": "text",
    "default": "",
    "placeholder": "Example value",
    "options": [],
    "min": 0,
    "max": 100,
    "step": 1,
    "show_if": {"other_field": "value"},
    "depends_on": "provider_field",
    "api_endpoint": "/api/v1/...",
    "group": "Advanced Settings"
  }
}
```

**Widget Types:**
- `text`: Single line text input
- `textarea`: Multi-line text input
- `password`: Password input (encrypted)
- `number`: Number input
- `slider`: Numeric slider
- `select`: Dropdown selection
- `checkbox`: Boolean checkbox
- `provider_select`: AI provider selector
- `model_select`: AI model selector (dynamic)
- `credential`: Credential picker
- `file_picker`: File selector
- `folder_picker`: Folder selector

**Field Types:**
- `string`: Text value
- `number`: Numeric value
- `float`: Floating point number
- `boolean`: True/false
- `select`: One of options
- `multiselect`: Multiple from options
- `json`: JSON object
- `array`: Array of values

---

## Node Categories

### Input (5 nodes)

**Purpose:** Receive data into workflows

**Nodes:**
- `text_input` - Manual text input
- `image_upload` - Upload images
- `document_upload` - Upload documents
- `audio_upload` - Upload audio files
- `video_upload` - Upload video files

### AI (4 nodes)

**Purpose:** AI and machine learning operations

**Nodes:**
- `llm_chat` - LLM conversation
- `vision_llm` - Vision AI (image understanding)
- `huggingface` - HuggingFace models
- `agent` - Multi-step AI agents

### Output (3 nodes)

**Purpose:** Display or export results

**Nodes:**
- `text_display` - Display text output
- `media_output` - Display media (images, video)
- `file_export` - Export files

### Processing (8 nodes)

**Purpose:** Transform and process data

**Nodes:**
- `csv_reader` - Read CSV files
- `document_loader` - Load documents
- `image_loader` - Load images
- `audio_transcriber` - Transcribe audio
- `document_merger` - Merge documents
- `file_converter` - Convert file formats
- `csv_value_extractor` - Extract CSV values
- `file_listener` - Watch for file changes

### Control Flow (4 nodes)

**Purpose:** Conditional logic and loops

**Nodes:**
- `decision` - If/else branching
- `loop_orchestrator` - Iterate over data
- `ornode` - OR gate (first successful)
- `virtual_time` - Time control for loops

### Data (6 nodes)

**Purpose:** Parse and manipulate data

**Nodes:**
- `json_parser` - Parse JSON
- `csv_export` - Export to CSV
- `pdf_export` - Export to PDF
- `state_get` - Get workflow state
- `state_set` - Set workflow state
- `state_update` - Update workflow state

### Actions (7 nodes)

**Purpose:** External integrations and actions

**Nodes:**
- `http_request` - Make HTTP requests
- `email_composer` - Send emails
- `email_approval` - Email approval flows
- `whatsapp_send` - Send WhatsApp messages
- `whatsapp_listener` - Receive WhatsApp messages
- `search` - Web search
- `weather` - Get weather data

### Triggers (5 nodes)

**Purpose:** Automatic workflow activation

**Nodes:**
- `schedule_trigger` - Time-based scheduling
- `file_polling_trigger` - Watch for files
- `email_polling_trigger` - Watch for emails
- (More triggers can be added)

---

## Use Cases

### Building a Node Selector UI

```javascript
// Fetch all nodes
const response = await fetch('http://localhost:5000/api/v1/nodes/definitions');
const data = await response.json();

// Group by category
const nodesByCategory = data.categories;

// Render sidebar
Object.entries(nodesByCategory).forEach(([category, nodes]) => {
  const categoryEl = createCategory(category);
  
  nodes.forEach(node => {
    const nodeEl = createNodeButton(
      node.display_name,
      node.icon,
      node.description
    );
    
    nodeEl.onclick = () => addNodeToCanvas(node);
    categoryEl.appendChild(nodeEl);
  });
  
  sidebar.appendChild(categoryEl);
});
```

### Building a Node Configuration Form

```javascript
// Get node definition
const node = data.nodes.find(n => n.node_type === 'llm_chat');

// Build form from config_schema
Object.entries(node.config_schema).forEach(([fieldName, schema]) => {
  const field = createFormField(
    fieldName,
    schema.label,
    schema.widget,
    schema.default
  );
  
  // Handle conditional visibility
  if (schema.show_if) {
    field.style.display = checkCondition(schema.show_if) ? 'block' : 'none';
  }
  
  // Handle dynamic options
  if (schema.api_endpoint) {
    loadOptions(schema.api_endpoint).then(options => {
      field.setOptions(options);
    });
  }
  
  form.appendChild(field);
});
```

### Validating Node Configuration

```javascript
// Validate required fields
function validateNodeConfig(nodeType, config) {
  const nodeDef = getNodeDefinition(nodeType);
  const errors = [];
  
  Object.entries(nodeDef.config_schema).forEach(([field, schema]) => {
    if (schema.required && !config[field]) {
      errors.push(`${schema.label} is required`);
    }
    
    // Type validation
    if (config[field]) {
      if (schema.type === 'number' && isNaN(config[field])) {
        errors.push(`${schema.label} must be a number`);
      }
      
      // Range validation
      if (schema.min !== undefined && config[field] < schema.min) {
        errors.push(`${schema.label} must be at least ${schema.min}`);
      }
      if (schema.max !== undefined && config[field] > schema.max) {
        errors.push(`${schema.label} must be at most ${schema.max}`);
      }
    }
  });
  
  return errors;
}
```

---

## Best Practices

### For UI Developers

1. **Cache node definitions** - They rarely change, cache locally
2. **Use icons** - Render icons from `icon` field for better UX
3. **Show descriptions** - Display on hover for discoverability
4. **Group by category** - Makes finding nodes easier
5. **Implement search** - Use the `search` parameter
6. **Validate configurations** - Check required fields before saving

### For API Integration

1. **Get definitions once** - At application startup
2. **Cache metadata** - No need to fetch on every workflow load
3. **Reload on updates** - Use reload endpoint after system updates
4. **Handle errors gracefully** - Fall back to defaults if schemas missing

### For Custom Nodes

1. **Follow naming conventions** - Clear, descriptive `node_type`
2. **Provide good descriptions** - Users rely on these
3. **Use appropriate categories** - Helps with discovery
4. **Define clear schemas** - Include all config options
5. **Add icons** - Makes nodes recognizable

---

## Related Documentation

- [Workflow API](rest.md) - Creating workflows with nodes
- [Node Architecture](../architecture/nodes.md) - How nodes work internally
- [Creating Custom Nodes](../development/custom-nodes.md) - Build your own nodes

---

## Support

- 📖 [Full Documentation](../README.md)
- 🐛 [Report Issues](https://github.com/Markepattsu/tav_opensource/issues)
- 💬 [Community Discussions](https://github.com/Markepattsu/tav_opensource/discussions)

