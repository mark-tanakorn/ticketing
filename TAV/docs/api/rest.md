# Workflow API

Complete reference for creating and managing workflows.

---

## Overview

The Workflow API allows you to create, read, update, and delete workflow definitions programmatically. Workflows define the structure of your automation (nodes, connections, configuration).

**Base Path:** `/api/v1/workflows`

---

## Table of Contents

- [Create Workflow](#create-workflow)
- [List Workflows](#list-workflows)
- [Get Workflow](#get-workflow)
- [Update Workflow](#update-workflow)
- [Delete Workflow](#delete-workflow)
- [Duplicate Workflow](#duplicate-workflow)
- [Rename Workflow](#rename-workflow)
- [Workflow Structure](#workflow-structure)
- [Validation](#validation)
- [Security](#security)

---

## Create Workflow

Create a new workflow definition.

### Endpoint

```
POST /api/v1/workflows
```

### Request Body

```json
{
  "name": "My Workflow",
  "description": "Workflow description",
  "version": "1.0",
  "nodes": [
    {
      "node_id": "node_1",
      "node_type": "text_input",
      "name": "Input",
      "category": "input",
      "config": {
        "default_text": "Hello"
      },
      "position": {"x": 100, "y": 100}
    },
    {
      "node_id": "node_2",
      "node_type": "llm_chat",
      "name": "AI Chat",
      "category": "ai",
      "config": {
        "system_prompt": "You are helpful",
        "llm_provider": "openai",
        "llm_model": "gpt-4"
      },
      "position": {"x": 300, "y": 100}
    }
  ],
  "connections": [
    {
      "source_node_id": "node_1",
      "source_port": "output",
      "target_node_id": "node_2",
      "target_port": "input"
    }
  ],
  "canvas_objects": [],
  "tags": ["ai", "demo"],
  "execution_config": {
    "max_concurrent_nodes": 5,
    "default_timeout": 300,
    "stop_on_error": true
  },
  "metadata": {
    "author": "John Doe",
    "category": "AI Automation"
  },
  "recommended_await_completion": "false"
}
```

**Fields:**

- `name` (required, string, 1-255 chars): Workflow name
- `description` (optional, string): Workflow description
- `version` (optional, string, default: "1.0"): Version number
- `nodes` (required, array): List of node configurations (see [Node Structure](#node-structure))
- `connections` (required, array): List of connections between nodes
- `canvas_objects` (optional, array): UI elements (groups, text annotations)
- `tags` (optional, array of strings): Tags for categorization
- `execution_config` (optional, object): Execution settings override
- `metadata` (optional, object): Custom metadata
- `recommended_await_completion` (optional, string): Hint for API consumers ("true", "false", "timeout=30")

### Response

**Status Code:** `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Workflow",
  "description": "Workflow description",
  "version": "1.0",
  "nodes": [...],
  "connections": [...],
  "canvas_objects": [],
  "tags": ["ai", "demo"],
  "execution_config": {...},
  "metadata": {...},
  "status": "na",
  "is_active": true,
  "is_template": false,
  "author_id": 1,
  "created_at": "2025-12-02T10:30:00Z",
  "updated_at": "2025-12-02T10:30:00Z",
  "last_run_at": null,
  "recommended_await_completion": "false"
}
```

### Example

```bash
curl -X POST http://localhost:5000/api/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Simple AI Workflow",
    "description": "Text to AI processing",
    "nodes": [
      {
        "node_id": "input_1",
        "node_type": "text_input",
        "name": "User Input",
        "category": "input",
        "config": {"default_text": "Hello AI"},
        "position": {"x": 100, "y": 100}
      },
      {
        "node_id": "llm_1",
        "node_type": "llm_chat",
        "name": "ChatGPT",
        "category": "ai",
        "config": {
          "system_prompt": "You are helpful",
          "llm_provider": "openai"
        },
        "position": {"x": 300, "y": 100}
      }
    ],
    "connections": [
      {
        "source_node_id": "input_1",
        "source_port": "output",
        "target_node_id": "llm_1",
        "target_port": "input"
      }
    ]
  }'
```

### Security

**Sensitive fields are automatically encrypted:**
- Passwords in node configs (`password`, `api_key`, etc.)
- Credentials
- API keys

They are stored encrypted in the database and decrypted when retrieved.

---

## List Workflows

Get all workflows with summary information.

### Endpoint

```
GET /api/v1/workflows
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | 0 | Number of records to skip (pagination) |
| `limit` | integer | 100 | Maximum records to return (max: 100) |
| `include_templates` | boolean | false | Include template workflows |
| `include_inactive` | boolean | false | Include inactive workflows |

### Response

**Status Code:** `200 OK`

```json
[
  {
    "id": "uuid",
    "name": "Workflow 1",
    "description": "Description",
    "version": "1.0",
    "status": "completed",
    "is_active": true,
    "is_template": false,
    "author_id": 1,
    "created_at": "2025-12-02T10:00:00Z",
    "updated_at": "2025-12-02T10:30:00Z",
    "last_run_at": "2025-12-02T10:25:00Z",
    "monitoring_started_at": null,
    "monitoring_stopped_at": null,
    "tags": ["ai", "automation"],
    "recommended_await_completion": "false"
  },
  {
    "id": "uuid",
    "name": "Workflow 2",
    "description": "Another workflow",
    "version": "1.0",
    "status": "pending",
    "is_active": true,
    "is_template": false,
    "author_id": 1,
    "created_at": "2025-12-02T09:00:00Z",
    "updated_at": "2025-12-02T09:30:00Z",
    "last_run_at": null,
    "monitoring_started_at": "2025-12-02T09:30:00Z",
    "monitoring_stopped_at": null,
    "tags": ["monitoring"],
    "recommended_await_completion": "false"
  }
]
```

**Workflow Status Values:**
- `na`: Never run
- `pending`: Monitoring for triggers
- `running`: Currently executing
- `completed`: Last run succeeded
- `failed`: Last run failed
- `stopped`: User stopped
- `paused`: Paused for resume

### Examples

**Get all workflows:**
```bash
curl http://localhost:5000/api/v1/workflows
```

**Pagination:**
```bash
curl "http://localhost:5000/api/v1/workflows?skip=20&limit=10"
```

**Include templates:**
```bash
curl "http://localhost:5000/api/v1/workflows?include_templates=true"
```

**Include inactive:**
```bash
curl "http://localhost:5000/api/v1/workflows?include_inactive=true"
```

---

## Get Workflow

Get complete workflow data by ID.

### Endpoint

```
GET /api/v1/workflows/{workflow_id}
```

### Path Parameters

- `workflow_id` (required): Workflow UUID

### Response

**Status Code:** `200 OK`

```json
{
  "id": "uuid",
  "name": "My Workflow",
  "description": "Description",
  "version": "1.0",
  "nodes": [
    {
      "node_id": "node_1",
      "node_type": "text_input",
      "name": "Input",
      "category": "input",
      "config": {...},
      "position": {"x": 100, "y": 100}
    }
  ],
  "connections": [
    {
      "source_node_id": "node_1",
      "source_port": "output",
      "target_node_id": "node_2",
      "target_port": "input"
    }
  ],
  "canvas_objects": [],
  "tags": ["ai"],
  "execution_config": {
    "max_concurrent_nodes": 5,
    "default_timeout": 300
  },
  "metadata": {},
  "status": "completed",
  "is_active": true,
  "is_template": false,
  "author_id": 1,
  "created_at": "2025-12-02T10:00:00Z",
  "updated_at": "2025-12-02T10:30:00Z",
  "last_run_at": "2025-12-02T10:25:00Z",
  "recommended_await_completion": "false"
}
```

**Note:** Sensitive fields (passwords, API keys) are decrypted in the response for authorized users.

### Example

```bash
curl http://localhost:5000/api/v1/workflows/550e8400-e29b-41d4-a716-446655440000
```

### Error

**Status Code:** `404 Not Found`

```json
{
  "detail": "Workflow 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

---

## Update Workflow

Update an existing workflow definition.

### Endpoint

```
PUT /api/v1/workflows/{workflow_id}
```

### Path Parameters

- `workflow_id` (required): Workflow UUID

### Request Body

**Partial updates are supported** - only include fields you want to change:

```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "version": "1.1",
  "nodes": [...],
  "connections": [...],
  "canvas_objects": [...],
  "tags": ["ai", "updated"],
  "execution_config": {...},
  "metadata": {...},
  "recommended_await_completion": "timeout=30"
}
```

**All fields are optional** - any field not included will remain unchanged.

### Response

**Status Code:** `200 OK`

Returns the complete updated workflow (same format as [Get Workflow](#get-workflow)).

### Examples

**Update name and description:**
```bash
curl -X PUT http://localhost:5000/api/v1/workflows/{workflow_id} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Workflow Name",
    "description": "New description"
  }'
```

**Update nodes and connections:**
```bash
curl -X PUT http://localhost:5000/api/v1/workflows/{workflow_id} \
  -H "Content-Type: application/json" \
  -d '{
    "nodes": [...],
    "connections": [...]
  }'
```

**Update execution config:**
```bash
curl -X PUT http://localhost:5000/api/v1/workflows/{workflow_id} \
  -H "Content-Type: application/json" \
  -d '{
    "execution_config": {
      "max_concurrent_nodes": 10,
      "default_timeout": 600
    }
  }'
```

**Update tags:**
```bash
curl -X PUT http://localhost:5000/api/v1/workflows/{workflow_id} \
  -H "Content-Type: application/json" \
  -d '{
    "tags": ["production", "ai", "important"]
  }'
```

---

## Delete Workflow

Delete a workflow and all its execution history.

### Endpoint

```
DELETE /api/v1/workflows/{workflow_id}
```

### Path Parameters

- `workflow_id` (required): Workflow UUID

### Response

**Status Code:** `200 OK`

```json
{
  "message": "Workflow deleted successfully",
  "workflow_id": "uuid",
  "workflow_name": "My Workflow"
}
```

### Example

```bash
curl -X DELETE http://localhost:5000/api/v1/workflows/{workflow_id}
```

### Error

**Status Code:** `404 Not Found`

```json
{
  "detail": "Workflow {workflow_id} not found"
}
```

### Warning

⚠️ **This action is permanent!**
- Deletes the workflow definition
- Deletes all execution history
- Deletes all execution logs
- Cannot be undone

Consider using "inactive" status instead:
```bash
curl -X PUT http://localhost:5000/api/v1/workflows/{workflow_id} \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

---

## Duplicate Workflow

Create a copy of an existing workflow.

### Endpoint

```
POST /api/v1/workflows/{workflow_id}/duplicate
```

### Path Parameters

- `workflow_id` (required): Workflow UUID to duplicate

### Response

**Status Code:** `201 Created`

Returns the new workflow with:
- New UUID
- Name appended with " (Copy)"
- Status reset to "na"
- Execution history cleared
- All nodes and connections copied

```json
{
  "id": "new-uuid",
  "name": "My Workflow (Copy)",
  "description": "Description",
  "version": "1.0",
  "nodes": [...],
  "connections": [...],
  "status": "na",
  "created_at": "2025-12-02T11:00:00Z",
  ...
}
```

### Example

```bash
curl -X POST http://localhost:5000/api/v1/workflows/{workflow_id}/duplicate
```

---

## Rename Workflow

Quick rename endpoint (faster than full update).

### Endpoint

```
PATCH /api/v1/workflows/{workflow_id}/name
```

### Path Parameters

- `workflow_id` (required): Workflow UUID

### Request Body

```json
{
  "name": "New Workflow Name"
}
```

### Response

**Status Code:** `200 OK`

```json
{
  "message": "Workflow renamed successfully",
  "workflow_id": "uuid",
  "old_name": "Old Name",
  "new_name": "New Workflow Name"
}
```

### Example

```bash
curl -X PATCH http://localhost:5000/api/v1/workflows/{workflow_id}/name \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Workflow v2"
  }'
```

---

## Workflow Structure

### Node Structure

Each node in the `nodes` array:

```json
{
  "node_id": "unique_id",
  "node_type": "text_input",
  "name": "Display Name",
  "description": "Optional description",
  "category": "input",
  "config": {
    "param1": "value1",
    "param2": "value2"
  },
  "position": {
    "x": 100,
    "y": 200
  }
}
```

**Required fields:**
- `node_id`: Unique identifier within workflow
- `node_type`: Node type (must exist in node registry)
- `name`: Display name
- `category`: Node category
- `config`: Node configuration object
- `position`: Canvas position

**Node Categories:**
- `input`: Input nodes (Text Input, File Upload, etc.)
- `output`: Output nodes (Text Display, File Export, etc.)
- `processing`: Processing nodes (Transform, Filter, etc.)
- `ai`: AI nodes (LLM Chat, Vision, etc.)
- `control`: Control flow (Decision, Loop, etc.)
- `data`: Data operations (JSON Parser, CSV, etc.)
- `actions`: Actions (HTTP Request, Email, etc.)
- `triggers`: Trigger nodes (Schedule, File Polling, etc.)

### Connection Structure

Each connection in the `connections` array:

```json
{
  "source_node_id": "node_1",
  "source_port": "output",
  "target_node_id": "node_2",
  "target_port": "input"
}
```

**Required fields:**
- `source_node_id`: Source node ID
- `source_port`: Source output port name
- `target_node_id`: Target node ID
- `target_port`: Target input port name

### Canvas Objects Structure

UI elements like groups and text annotations:

```json
{
  "canvas_objects": [
    {
      "id": "group_1",
      "type": "group",
      "name": "My Group",
      "position": {"x": 50, "y": 50},
      "size": {"width": 400, "height": 300},
      "color": "#3b82f6",
      "contains": ["node_1", "node_2"]
    },
    {
      "id": "text_1",
      "type": "text",
      "content": "This is a note",
      "position": {"x": 500, "y": 100},
      "fontSize": 14,
      "color": "#6b7280"
    }
  ]
}
```

---

## Validation

### Automatic Validation

The API automatically validates:

1. **Node IDs are unique** within the workflow
2. **Connections reference valid nodes** (both source and target exist)
3. **Required fields are present** in nodes and connections
4. **Workflow structure is valid** (no circular dependencies for synchronous nodes)

### Validation Errors

**Status Code:** `400 Bad Request`

```json
{
  "detail": "Validation error: Duplicate node IDs found"
}
```

**Common validation errors:**
- `"Workflow must have at least one node"`
- `"Duplicate node IDs found"`
- `"Connection references non-existent source node: {node_id}"`
- `"Connection references non-existent target node: {node_id}"`

---

## Security

### Authentication

All endpoints require authentication (except in dev mode).

**Header:**
```
Authorization: Bearer <jwt_token>
```

### Encryption

Sensitive fields are automatically encrypted:
- `password` fields in node configs
- `api_key` fields
- Credential references
- Any field matching sensitive patterns

**Encrypted in database:**
```json
{
  "config": {
    "password": "encrypted:AES256:..."
  }
}
```

**Decrypted in API responses:**
```json
{
  "config": {
    "password": "actual_password"
  }
}
```

### Permissions

- Users can only access their own workflows (or shared workflows in future)
- System admin can access all workflows
- Templates can be accessed by all users

---

## Error Handling

### Common Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `400` | Bad Request (validation error) | Check request body structure |
| `404` | Workflow not found | Verify workflow ID exists |
| `409` | Conflict (duplicate name, etc.) | Use different name or update existing |
| `500` | Internal server error | Check logs, contact support |

### Error Response Format

```json
{
  "detail": "Error message",
  "error_type": "ValidationError",
  "timestamp": "2025-12-02T10:30:00Z"
}
```

---

## Best Practices

### Naming

- **Use descriptive names:** "Customer Email Automation" not "Workflow 1"
- **Include version in name:** "Report Generator v2"
- **Use tags for categorization:** `["production", "email", "daily"]`

### Structure

- **Keep workflows focused:** One clear purpose per workflow
- **Use descriptive node names:** "Fetch Customer Data" not "HTTP 1"
- **Group related nodes:** Use canvas groups for organization
- **Add comments:** Use text annotations to explain complex logic

### Configuration

- **Set execution config appropriately:**
  - Short workflows: Lower timeout
  - Long workflows: Higher timeout
  - Parallel processing: Increase `max_concurrent_nodes`
  - AI-heavy: Increase `ai_concurrent_limit`

- **Use metadata for tracking:**
  ```json
  {
    "metadata": {
      "owner": "team-name",
      "environment": "production",
      "cost_center": "engineering",
      "last_reviewed": "2025-12-01"
    }
  }
  ```

### Version Control

- **Increment version on major changes:** "1.0" → "1.1" → "2.0"
- **Use tags for releases:** `["v1.0", "stable"]`
- **Duplicate before major changes:** Test changes on duplicate first
- **Keep descriptions updated:** Document what changed

---

## Related Documentation

- [Execution API](execution.md) - Running workflows
- [Nodes API](nodes.md) - Available nodes and their schemas
- [Settings API](settings.md) - System configuration
- [Architecture](../architecture/nodes.md) - How nodes work internally

---

## Support

- 📖 [Full Documentation](../README.md)
- 🐛 [Report Issues](https://github.com/Markepattsu/tav_opensource/issues)
- 💬 [Community Discussions](https://github.com/Markepattsu/tav_opensource/discussions)
