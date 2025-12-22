# Execution API

Complete reference for workflow execution endpoints.

---

## Overview

TAV Engine's execution system supports two modes:

- **Oneshot Mode**: Execute workflow once and return results
- **Persistent Mode**: Monitor for triggers and execute automatically

The API automatically detects which mode to use based on the workflow structure (presence of trigger nodes).

---

## Table of Contents

- [Execute Workflow](#execute-workflow)
- [Stop Workflow](#stop-workflow)
- [Get Workflow Status](#get-workflow-status)
- [Stream Execution Events (SSE)](#stream-execution-events-sse)
- [Execution Modes](#execution-modes)
- [Sync vs Async Execution](#sync-vs-async-execution)
- [Error Handling](#error-handling)

---

## Execute Workflow

**Smart "Run" button** - Automatically detects oneshot vs persistent mode and executes accordingly.

### Endpoint

```
POST /api/v1/workflows/{workflow_id}/execute
```

### Behavior

The API automatically detects the workflow type:

- **Has trigger nodes** (Schedule, File Polling, Email Polling, etc.) → Activates **persistent monitoring**
- **No trigger nodes** → Executes **oneshot** (runs once)

### Headers

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `X-Await-Completion` | string | No | Controls sync/async execution (see [Sync vs Async](#sync-vs-async-execution)) |
| `Authorization` | string | Yes* | Bearer token (*optional in dev mode) |

### Request Body

```json
{
  "trigger_data": {
    "param1": "value1",
    "param2": "value2"
  },
  "execution_config": {
    "max_concurrent_nodes": 5,
    "default_timeout": 300,
    "stop_on_error": true
  }
}
```

**Fields:**

- `trigger_data` (optional): Data to inject into trigger nodes or available as workflow variables
- `execution_config` (optional): Override workflow execution settings for this run only

### Response (Async - Default)

**Status Code:** `202 Accepted`

**Oneshot Mode:**
```json
{
  "workflow_id": "uuid",
  "execution_id": "uuid",
  "mode": "oneshot",
  "status": "running",
  "message": "Workflow execution started",
  "sse_url": "/api/v1/executions/{execution_id}/stream"
}
```

**Persistent Mode:**
```json
{
  "workflow_id": "uuid",
  "mode": "persistent",
  "status": "monitoring",
  "message": "Workflow monitoring activated",
  "trigger_count": 3,
  "triggers": [
    {
      "node_id": "schedule_1",
      "node_type": "schedule_trigger",
      "config": {
        "interval": "1h"
      }
    }
  ],
  "monitoring_started_at": "2025-12-02T10:30:00Z"
}
```

### Response (Sync - With X-Await-Completion)

**Status Code:** `200 OK` (if completed), `408 Request Timeout` (if timeout exceeded)

```json
{
  "workflow_id": "uuid",
  "execution_id": "uuid",
  "mode": "oneshot",
  "status": "completed",
  "completed": true,
  "started_at": "2025-12-02T10:30:00Z",
  "completed_at": "2025-12-02T10:30:45Z",
  "duration_seconds": 45,
  "final_outputs": {
    "output_node_1": {
      "result": "Success"
    }
  },
  "node_results": {
    "node_1": {
      "status": "completed",
      "outputs": {...}
    }
  }
}
```

### Examples

**Async Execution (Default):**

```bash
curl -X POST http://localhost:5000/api/v1/workflows/{workflow_id}/execute \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_data": {
      "user_input": "Hello AI"
    }
  }'
```

**Sync Execution (Wait for completion):**

```bash
curl -X POST http://localhost:5000/api/v1/workflows/{workflow_id}/execute \
  -H "Content-Type: application/json" \
  -H "X-Await-Completion: true" \
  -d '{}'
```

**Sync with Custom Timeout:**

```bash
curl -X POST http://localhost:5000/api/v1/workflows/{workflow_id}/execute \
  -H "Content-Type: application/json" \
  -H "X-Await-Completion: timeout=30" \
  -d '{}'
```

**With Execution Config Override:**

```bash
curl -X POST http://localhost:5000/api/v1/workflows/{workflow_id}/execute \
  -H "Content-Type: application/json" \
  -d '{
    "execution_config": {
      "max_concurrent_nodes": 10,
      "default_timeout": 600,
      "stop_on_error": false,
      "max_retries": 5
    }
  }'
```

---

## Stop Workflow

**Universal "Stop" button** - Works for both oneshot executions and persistent monitoring.

### Endpoint

```
POST /api/v1/workflows/{workflow_id}/stop
```

### Behavior

- **Persistent (monitoring)** → Deactivates triggers, cancels in-flight executions
- **Oneshot (running)** → Cancels current execution
- **Idle** → No-op (returns success)

This is a **hard stop** that immediately terminates all activity.

### Request

No request body required.

### Response

**Status Code:** `200 OK`

```json
{
  "workflow_id": "uuid",
  "mode": "persistent",
  "status": "stopped",
  "message": "Stopped persistent workflow (cancelled 2 executions)"
}
```

**Fields:**

- `mode`: Type of workflow stopped (`persistent`, `oneshot`, or `idle`)
- `status`: Always `"stopped"`
- `message`: Human-readable description of what was stopped

### Example

```bash
curl -X POST http://localhost:5000/api/v1/workflows/{workflow_id}/stop
```

---

## Get Workflow Status

Get current workflow state (monitoring, running, idle, etc.).

### Endpoint

```
GET /api/v1/workflows/{workflow_id}/status
```

### Response

**Status Code:** `200 OK`

```json
{
  "workflow_id": "uuid",
  "mode": "persistent",
  "status": "pending",
  "monitoring_state": "active",
  "trigger_count": 3,
  "active_triggers": [
    {
      "node_id": "schedule_1",
      "node_type": "schedule_trigger",
      "status": "running"
    }
  ],
  "running_executions": [
    {
      "execution_id": "uuid",
      "started_at": "2025-12-02T10:30:00Z",
      "status": "running"
    }
  ],
  "last_execution_id": "uuid",
  "last_run_at": "2025-12-02T10:25:00Z",
  "last_execution_status": "completed"
}
```

**Fields:**

- `mode`: `persistent`, `oneshot`, or `idle`
- `status`: Current workflow status (`na`, `pending`, `running`, `completed`, `failed`, `stopped`)
- `monitoring_state`: For persistent workflows (`active`, `inactive`)
- `trigger_count`: Number of active triggers
- `active_triggers`: List of trigger nodes currently monitoring
- `running_executions`: Currently executing runs
- `last_execution_id`: Most recent execution UUID
- `last_run_at`: Timestamp of last execution
- `last_execution_status`: Result of last execution

### Example

```bash
curl http://localhost:5000/api/v1/workflows/{workflow_id}/status
```

---

## Stream Execution Events (SSE)

Real-time Server-Sent Events (SSE) stream for execution updates.

### Endpoint

```
GET /api/v1/executions/{execution_id}/stream
```

### Event Types

| Event | Description |
|-------|-------------|
| `execution_start` | Workflow execution started |
| `node_start` | Node execution started |
| `node_complete` | Node execution completed |
| `node_failed` | Node execution failed |
| `execution_complete` | Workflow execution completed |
| `execution_failed` | Workflow execution failed |
| `execution_cancelled` | Workflow execution cancelled |
| `heartbeat` | Keep-alive ping (every 30s) |

### Event Format

Each event is sent as:

```
event: execution_event
data: {"type": "node_start", "node_id": "uuid", "status": "running", ...}
```

### Event Data Examples

**execution_start:**
```json
{
  "type": "execution_start",
  "execution_id": "uuid",
  "workflow_id": "uuid",
  "status": "running",
  "message": "Workflow execution started",
  "timestamp": "2025-12-02T10:30:00Z"
}
```

**node_start:**
```json
{
  "type": "node_start",
  "execution_id": "uuid",
  "node_id": "uuid",
  "node_type": "llm_chat",
  "node_name": "AI Assistant",
  "status": "running",
  "message": "Node execution started",
  "timestamp": "2025-12-02T10:30:05Z"
}
```

**node_complete:**
```json
{
  "type": "node_complete",
  "execution_id": "uuid",
  "node_id": "uuid",
  "node_type": "llm_chat",
  "node_name": "AI Assistant",
  "status": "completed",
  "outputs": {
    "response": "Hello! How can I help you?"
  },
  "duration_seconds": 2.5,
  "timestamp": "2025-12-02T10:30:07Z"
}
```

**node_failed:**
```json
{
  "type": "node_failed",
  "execution_id": "uuid",
  "node_id": "uuid",
  "node_type": "http_request",
  "node_name": "API Call",
  "status": "failed",
  "error": "Connection timeout",
  "error_type": "TimeoutError",
  "timestamp": "2025-12-02T10:30:10Z"
}
```

**execution_complete:**
```json
{
  "type": "execution_complete",
  "execution_id": "uuid",
  "workflow_id": "uuid",
  "status": "completed",
  "duration_seconds": 45,
  "final_outputs": {
    "output_node_1": {
      "result": "Success"
    }
  },
  "timestamp": "2025-12-02T10:30:45Z"
}
```

**execution_failed:**
```json
{
  "type": "execution_failed",
  "execution_id": "uuid",
  "workflow_id": "uuid",
  "status": "failed",
  "error": "Node execution failed",
  "failed_node_id": "uuid",
  "timestamp": "2025-12-02T10:30:20Z"
}
```

### JavaScript Example

```javascript
const eventSource = new EventSource(
  `http://localhost:5000/api/v1/executions/${executionId}/stream`
);

eventSource.addEventListener('execution_event', (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'node_start':
      console.log(`Node ${data.node_name} started`);
      break;
    case 'node_complete':
      console.log(`Node ${data.node_name} completed:`, data.outputs);
      break;
    case 'execution_complete':
      console.log('Workflow completed!', data.final_outputs);
      eventSource.close();
      break;
    case 'execution_failed':
      console.error('Workflow failed:', data.error);
      eventSource.close();
      break;
  }
});

eventSource.onerror = (error) => {
  console.error('SSE connection error:', error);
  eventSource.close();
};
```

### Python Example

```python
import requests
import json

response = requests.get(
    f'http://localhost:5000/api/v1/executions/{execution_id}/stream',
    stream=True
)

for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data:'):
            event_data = json.loads(line_str[5:])
            print(f"Event: {event_data['type']}")
            print(f"Data: {event_data}")
```

---

## Execution Modes

### Oneshot Mode

**When:** Workflow has NO trigger nodes

**Behavior:**
- Executes once when "Run" is clicked
- Returns execution result
- Workflow status returns to previous state after completion

**Use Cases:**
- Data processing pipelines
- API integrations
- One-time automations
- Manual workflows

**Example Workflow:**
```
[Text Input] → [LLM Chat] → [Text Display]
```

### Persistent Mode

**When:** Workflow has trigger nodes (Schedule, File Polling, Email Polling, etc.)

**Behavior:**
- Activates trigger monitoring when "Run" is clicked
- Runs automatically when triggers fire
- Continues monitoring until "Stop" is clicked
- Can execute multiple times concurrently (based on settings)

**Use Cases:**
- Scheduled reports
- File watchers
- Email automation
- Webhook listeners
- Continuous monitoring

**Example Workflow:**
```
[Schedule Trigger] → [Fetch Data] → [Process] → [Send Email]
```

---

## Sync vs Async Execution

### Async Execution (Default)

**Header:** None or `X-Await-Completion: false`

**Behavior:**
- Returns immediately with execution ID
- Client uses SSE to track progress
- Best for long-running workflows
- Non-blocking

**When to use:**
- UI applications (with real-time updates)
- Long workflows (>30 seconds)
- When you need progress updates
- Default for most cases

**Response Time:** ~50ms (just starts execution)

### Sync Execution

**Header:** `X-Await-Completion: true` or `X-Await-Completion: timeout=30`

**Behavior:**
- Waits for workflow to complete
- Returns final result in response
- Blocks until done or timeout
- No SSE needed

**When to use:**
- API integrations
- Webhooks
- Short workflows (<30 seconds)
- When you just need the final result

**Response Time:** Actual workflow duration (up to timeout)

**Timeout Behavior:**

| Header Value | Timeout | Description |
|--------------|---------|-------------|
| `true` | Workflow timeout from settings (default: 1800s) | Wait until completion |
| `timeout=30` | 30 seconds | Custom timeout (capped at workflow timeout) |
| Not set | N/A | Async mode |

**Timeout Response:**

If workflow doesn't complete within timeout:

```json
{
  "workflow_id": "uuid",
  "execution_id": "uuid",
  "mode": "oneshot",
  "status": "running",
  "completed": false,
  "message": "Execution still running after timeout",
  "sse_url": "/api/v1/executions/{execution_id}/stream"
}
```

**Status Code:** `408 Request Timeout`

The execution continues running. Client can:
1. Poll status endpoint
2. Connect to SSE stream
3. Call stop if no longer needed

---

## Error Handling

### Common Error Codes

| Code | Scenario | Resolution |
|------|----------|------------|
| `400` | Invalid request (bad workflow definition, config) | Check request body |
| `404` | Workflow not found | Verify workflow ID exists |
| `408` | Sync execution timeout | Use async mode or increase timeout |
| `409` | Workflow already running (if limits exceeded) | Wait or increase concurrency limits |
| `500` | Execution engine error | Check logs, retry |

### Error Response Format

```json
{
  "detail": "Error message",
  "workflow_id": "uuid",
  "execution_id": "uuid",
  "error_type": "ValidationError",
  "timestamp": "2025-12-02T10:30:00Z"
}
```

### Error Recovery

**Node Failure:**
- Controlled by `stop_on_error` setting
- `true`: Workflow stops immediately
- `false`: Failed nodes marked, other branches continue

**Retry Logic:**
- Automatic retries based on `max_retries` setting
- Exponential backoff
- Per-node retry tracking

**Workflow Failure:**
- Status set to `failed`
- Execution record preserved
- Error details in `execution_log`

---

## Rate Limiting

### Concurrency Limits

Configured in Settings → Execution:

| Setting | Default | Description |
|---------|---------|-------------|
| `max_concurrent_runs_global` | 8 | Max total running workflows system-wide |
| `max_concurrent_runs_per_workflow` | 20 | Max concurrent runs of same workflow |
| `max_queue_depth_per_workflow` | 200 | Max queued executions per workflow |

### Behavior When Limits Reached

- **Oneshot:** Returns `409 Conflict` (try again later)
- **Persistent:** Queues trigger events, processes when capacity available

---

## Best Practices

### For UI Applications

1. Use **async execution** (default)
2. Connect to **SSE stream** for real-time updates
3. Show **progress indicators** based on node events
4. Handle **reconnection** if SSE drops

### For API Integrations

1. Use **sync execution** with reasonable timeout
2. Handle **408 timeout** by falling back to polling
3. Implement **exponential backoff** for retries
4. Monitor execution status if timeout occurs

### For Webhooks

1. Use **sync execution** for immediate response
2. Set **short timeout** (30s) appropriate for HTTP
3. Return **execution ID** if timeout occurs
4. Provide **callback URL** for completion notification (if supported)

### Performance Tips

1. **Parallel execution:** Use independent branches for concurrent processing
2. **Resource pools:** AI nodes share `ai_concurrent_limit` pool
3. **Timeouts:** Set appropriate `default_timeout` per node
4. **Batch processing:** Use loop nodes for bulk operations

---

## Related Documentation

- [Workflow API](rest.md) - Create and manage workflows
- [Execution Engine Architecture](../architecture/executor.md) - How execution works internally
- [Configuration Reference](../configuration/execution.md) - All execution settings
- [Node System](../architecture/nodes.md) - Understanding nodes

---

## Support

- 📖 [Full Documentation](../README.md)
- 🐛 [Report Issues](https://github.com/Markepattsu/tav_opensource/issues)
- 💬 [Community Discussions](https://github.com/Markepattsu/tav_opensource/discussions)

