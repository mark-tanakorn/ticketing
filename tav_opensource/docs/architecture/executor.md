# Execution Engine Architecture

Complete reference for TAV Engine's parallel workflow execution system.

---

## Overview

The **Execution Engine** (also called Executor) is the core component that runs workflows. It takes workflow definitions (nodes + connections) and executes them intelligently:

- ⚡ **Parallel execution** - Independent nodes run simultaneously
- 🔄 **Reactive scheduling** - Nodes execute as soon as dependencies complete
- 🎯 **Smart concurrency** - Worker pool prevents resource exhaustion
- 📊 **Real-time updates** - Live progress streaming via SSE (Server-Sent Events)
- 🛡️ **Configurable error handling** - Retry, timeout, stop-on-error policies

---

## Table of Contents

- [Execution Modes](#execution-modes)
- [Parallel Execution Architecture](#parallel-execution-architecture)
- [Data Flow System](#data-flow-system)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Monitoring & Triggers](#monitoring--triggers)
- [Real-Time Updates](#real-time-updates)
- [Performance](#performance)

---

## Execution Modes

TAV Engine supports **two execution modes** based on workflow content:

### 1. One-Shot Mode

**When:** Workflow has NO trigger nodes (manual workflows)

**Behavior:**
- User clicks "Run" → Executes once → Completes → Done
- Synchronous or asynchronous (based on `await_completion` config)
- No background processes
- `execution_source = "manual"`

**Use Cases:**
- Data processing pipelines
- Report generation
- API integrations
- Any workflow triggered manually

**API Example:**

```bash
# Execute workflow (one-shot)
curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/execute" \
  -H "Content-Type: application/json" \
  -d '{"trigger_data": {}, "await_completion": false}'
```

---

### 2. Monitoring Mode (Persistent)

**When:** Workflow has trigger nodes (webhook, schedule, email, file detection)

**Behavior:**
- User clicks "Start Monitoring" → Spawns background listener
- **Server-side execution** - Independent of browser
- **State persistence** - Survives server restarts
- Multiple concurrent executions (configurable limit)
- `execution_source = "webhook"` / `"schedule"` / `"polling_*"` / etc.

**Use Cases:**
- Webhook receivers
- Scheduled jobs (cron-like)
- Email automation
- File watchers
- Event-driven workflows

**Workflow State:**

```python
workflow.monitoring_started_at   # When monitoring began
workflow.monitoring_stopped_at   # When monitoring stopped
workflow.is_active               # Currently monitoring?
```

**API Example:**

```bash
# Start monitoring (for workflows with triggers)
curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/monitoring/start"

# Stop monitoring
curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/monitoring/stop"
```

---

## Parallel Execution Architecture

### Core Principles

**Reactive Scheduling:**
- Nodes execute as soon as ALL dependencies complete
- No predetermined order - fully dynamic
- Push-based: Completed nodes trigger dependent nodes

**Worker Pool:**
- Bounded concurrency (max N nodes executing simultaneously)
- Prevents resource exhaustion
- Configurable per workflow

**Dependency Graph:**
- Built from connections at runtime
- Tracks "remaining dependencies" counter per node
- Nodes with 0 remaining dependencies are "ready"

---

### How It Works

#### 1. Graph Building (Pre-Execution)

```python
# Input: Workflow with nodes and connections
workflow = {
    "nodes": [
        {"node_id": "A", "node_type": "trigger"},
        {"node_id": "B", "node_type": "http_request"},
        {"node_id": "C", "node_type": "http_request"},
        {"node_id": "D", "node_type": "response"}
    ],
    "connections": [
        {"source_node": "A", "target_node": "B"},
        {"source_node": "A", "target_node": "C"},
        {"source_node": "B", "target_node": "D"},
        {"source_node": "C", "target_node": "D"}
    ]
}

# Output: Dependency graph
graph = {
    "A": {"dependencies": [], "dependents": ["B", "C"]},
    "B": {"dependencies": ["A"], "dependents": ["D"]},
    "C": {"dependencies": ["A"], "dependents": ["D"]},
    "D": {"dependencies": ["B", "C"], "dependents": []}
}
```

**Visual:**

```
    A (trigger)
   / \
  B   C  (parallel)
   \ /
    D (response)
```

#### 2. Reactive Execution Loop

```python
# Pseudo-code
async def execute_workflow():
    # Step 1: Find source nodes (no dependencies)
    ready_nodes = ["A"]  # Only A has no dependencies
executing_tasks = {}

    # Step 2: Execute until complete
while ready_nodes or executing_tasks:
        # Start ready nodes (respecting worker pool limit)
    for node_id in ready_nodes:
            if len(executing_tasks) < max_concurrent_nodes:
                task = execute_node(node_id)
        executing_tasks[node_id] = task
    
    ready_nodes = []
    
        # Wait for any node to complete
    done, pending = await asyncio.wait(
        executing_tasks.values(),
            return_when=FIRST_COMPLETED
        )
        
        # Process completed nodes
        for completed_task in done:
            node_id = get_node_id(completed_task)
            result = await completed_task
            
            # Store result
            context.node_outputs[node_id] = result
            
            # Update dependency counters
            newly_ready = graph.mark_completed(node_id)
        ready_nodes.extend(newly_ready)

            # Remove from executing
            del executing_tasks[node_id]
```

#### 3. Execution Timeline

**Example workflow:** `A → [B, C] → D`

```
Time 0: ready=[A], executing=[]
  → Start A

Time 1: ready=[], executing=[A]
  → A completes
  → B and C become ready

Time 2: ready=[B, C], executing=[]
  → Start B and C (parallel)

Time 3: ready=[], executing=[B, C]
  → B completes
  → D still has C as dependency (not ready yet)

Time 4: ready=[], executing=[C]
  → C completes
  → D becomes ready (all dependencies done)

Time 5: ready=[D], executing=[]
  → Start D

Time 6: ready=[], executing=[D]
  → D completes
  → Workflow complete
```

**Key Insight:** B and C run **truly in parallel** (not sequential like n8n/Zapier).

---

### Worker Pool Management

**Purpose:** Prevent spawning unlimited threads (would crash with large workflows)

**Implementation:**

```python
class ParallelExecutor:
    def __init__(self, max_workers: int = 10):
        self.semaphore = asyncio.Semaphore(max_workers)
    
    async def execute_node(self, node_id: str):
        async with self.semaphore:  # Blocks if pool full
            # Execute node
            result = await node.execute(inputs)
            return result
```

**Configuration:**

```python
# Per workflow
workflow.execution_config.max_concurrent_nodes = 10  # Max 10 nodes at once

# Per node (via capabilities)
node.resource_classes = ["standard"]  # Uses standard pool
node.resource_classes = ["llm"]       # Uses LLM pool (separate limits)
```

---

## Data Flow System

TAV Engine uses a **hybrid data flow model**:

1. **Connection-based flow** (primary, automatic)
2. **Shared variables** (optional, opt-in)

---

### 1. Connection-Based Flow (Primary)

**Default behavior:** Data flows ONLY through explicit connections.

**How it works:**

```
Node A outputs: {output: "Hello"}
  ↓ (connection: A.output → B.input)
Node B receives: {input: "Hello"}
  ↓ (connection: B.output → C.input)
Node C receives: {input: "World"}  ← Only sees Node B, NOT Node A
```

**Assembly (automatic):**

```python
# System assembles inputs for each node
def assemble_inputs(node_id, context, graph):
    inputs = {}
    
    # Get all connections TO this node
    for conn in graph.get_input_connections(node_id):
        # Get source node's output
        source_outputs = context.node_outputs[conn.source_node]
        
        # Map: source port → target port
        inputs[conn.target_port] = source_outputs[conn.source_port]
    
    return inputs
```

**Node receives assembled inputs:**

```python
class MyNode(Node):
    async def execute(self, input_data: NodeExecutionInput):
        # input_data.ports contains assembled data
        value = input_data.ports["input"]  # From connected node
        
        result = process(value)
        
        return {"output": result}
```

---

### 2. Shared Variables (Optional)

**Problem:** LLM nodes need context from earlier nodes, but connection flow doesn't accumulate data.

**Solution:** Opt-in shared state via workflow variables.

#### Configuration

**In workflow definition:**

```json
{
  "node_id": "extract1",
  "name": "Extract Question",
  "node_type": "text_processing",
  "config": {...},
  "share_output_to_variables": true,      // ← Enable sharing
  "variable_name": "question_context"     // ← Custom name (optional)
}
```

**Effect:**
- Node outputs are shared to `context.variables`
- Accessible by ALL downstream nodes
- Stored by both **name** (readable) and **ID** (unique)

#### Variable Structure

```python
context.variables = {
    # System namespace: Auto-shared node outputs
    "_nodes": {
        "by_name": {
            "Extract Question": {"output": "What is quantum?"}
        },
        "by_id": {
            "node_abc123": {"output": "What is quantum?"}
        }
    },
    
    # Workflow namespace: Workflow-level data
    "_workflow": {
        "total_processed": 42,
        "start_time": "2025-01-01T00:00:00Z"
    },
    
    # Custom: User-defined variables (set by nodes)
    "conversation_history": [...],
    "accumulated_data": [...]
}
```

#### Accessing Shared Variables

```python
class MyLLMNode(Node):
    async def execute(self, input_data: NodeExecutionInput):
        # Access by name (readable)
        nodes_by_name = input_data.variables.get("_nodes", {}).get("by_name", {})
        extract_data = nodes_by_name.get("Extract Question", {})
        question = extract_data.get("output", "")
        
        # Access by ID (guaranteed unique)
        nodes_by_id = input_data.variables.get("_nodes", {}).get("by_id", {})
        specific_node = nodes_by_id.get("node_abc123", {})
        
        # Access custom variables
        conversation = input_data.variables.get("conversation_history", [])
        
        # Build LLM context
        context_text = f"Earlier question: {question}"
        
        response = await self.call_llm(
            prompt=input_data.ports["input"],
            system_context=context_text
        )
        
        return {"output": response}
```

#### Writing Custom Variables

```python
class AccumulatorNode(Node):
    async def execute(self, input_data: NodeExecutionInput):
        # Read custom variable
        accumulated = input_data.variables.get("accumulated_data", [])
        
        # Modify
        accumulated.append(input_data.ports["input"])
        
        # Write back (mutations persist)
        input_data.variables["accumulated_data"] = accumulated
        
        return {"output": len(accumulated)}
```

---

### Data Flow Comparison

| Method | Scope | When to Use | Auto/Manual |
|--------|-------|-------------|-------------|
| **Connections** | Point-to-point | Always (primary) | Auto |
| **Shared Variables (by name)** | Workflow-wide | LLM context, readable | Opt-in |
| **Shared Variables (by ID)** | Workflow-wide | Unique access | Opt-in |
| **Custom Variables** | Workflow-wide | Conversation history, counters | Manual (code) |

**Visual:**

```
CONNECTION-BASED:
┌──────────┐
│  Node A  │──┐
└──────────┘  │
              ├──→ ┌──────────┐
┌──────────┐  │    │  Node C  │  receives: {in1: A, in2: B}
│  Node B  │──┘    └──────────┘
└──────────┘

SHARED VARIABLES:
┌─────────────────────────────────┐
│  WORKFLOW VARIABLES             │
│  _nodes.by_name.Node A: {...}  │ ← Accessible by all
└────────────┬────────────────────┘
             │
             ▼
      ┌──────────┐
      │  Node C  │  can read: variables["_nodes"]["by_name"]["Node A"]
      └──────────┘
```

---

## Configuration

Workflow execution behavior is controlled via `execution_config` (stored in workflow definition).

### Execution Config Schema

```python
class WorkflowExecutionConfig(BaseModel):
    # Error handling
    stop_on_error: bool = True              # Stop workflow on first error
    retry_enabled: bool = False             # Enable automatic retries
    max_retries: int = 3                    # Max retry attempts per node
    retry_backoff: float = 2.0              # Exponential backoff (2^n seconds)
    
    # Timeouts
    node_timeout_seconds: int = 300         # Per-node timeout (5 min)
    workflow_timeout_seconds: int = 3600    # Workflow timeout (1 hour)
    
    # Concurrency
    workflow_concurrency: int = 5           # Max parallel workflow instances (monitoring mode)
    max_concurrent_nodes: int = 10          # Max nodes executing simultaneously
    
    # Mode
    execution_mode: str = "auto"            # auto, sequential, parallel
    recommended_await_completion: bool = False  # Hint for sync/async execution
```

### Setting Config

**Via API:**

```bash
curl -X PUT "http://localhost:8000/api/v1/workflows/{workflow_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "execution_config": {
      "stop_on_error": false,
      "retry_enabled": true,
      "max_retries": 5,
      "max_concurrent_nodes": 20
    }
  }'
```

**Via UI:**
- Workflow Settings → Execution Tab
- Configure all options visually

---

## Error Handling

### Strategies

#### 1. Stop on Error (Default)

```python
stop_on_error: true
```

**Behavior:**
- First node failure → Entire workflow stops immediately
- All executing nodes are cancelled
- Workflow status: `failed`

**Use Cases:**
- Critical pipelines (payment processing)
- Data integrity requirements
- Fail-fast development

#### 2. Continue on Error

```python
stop_on_error: false
```

**Behavior:**
- Failed nodes are marked as failed
- Workflow continues with other branches
- Dependent nodes of failed node are skipped
- Workflow status: `completed_with_errors`

**Use Cases:**
- Best-effort processing
- Parallel data pipelines
- Notification workflows (some channels may fail)

#### 3. Retry Strategy

```python
retry_enabled: true
max_retries: 3
retry_backoff: 2.0  # 2^n seconds
```

**Behavior:**
- Failed node retries automatically
- Wait: 2s, 4s, 8s between retries (exponential backoff)
- After max retries → Treat as failed (apply stop_on_error logic)

**Use Cases:**
- Network requests (transient failures)
- Rate-limited APIs
- Flaky external services

#### 4. Timeout Handling

```python
node_timeout_seconds: 300        # 5 min per node
workflow_timeout_seconds: 3600   # 1 hour total
```

**Behavior:**
- Node exceeds timeout → Cancelled + marked as failed
- Workflow exceeds timeout → All nodes cancelled, workflow failed

**Use Cases:**
- Prevent infinite loops
- Resource management
- SLA enforcement

---

### Error Handling Flow

```python
# Pseudo-code
async def execute_node_with_retry(node_id):
    attempts = 0
    max_attempts = config.max_retries + 1 if config.retry_enabled else 1
    
    while attempts < max_attempts:
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                execute_node(node_id),
                timeout=config.node_timeout_seconds
            )
            return result  # Success
            
        except asyncio.TimeoutError:
            logger.error(f"Node {node_id} timed out")
            if config.stop_on_error:
                raise  # Stop workflow
            else:
                return None  # Continue workflow
        
        except Exception as e:
            attempts += 1
            if attempts < max_attempts:
                # Retry with backoff
                wait_time = config.retry_backoff ** attempts
                await asyncio.sleep(wait_time)
                logger.info(f"Retrying node {node_id} (attempt {attempts})")
            else:
                # Max retries exceeded
                logger.error(f"Node {node_id} failed after {attempts} attempts")
                if config.stop_on_error:
                    raise  # Stop workflow
                else:
                    return None  # Continue workflow
```

---

## Monitoring & Triggers

### Trigger Manager

**Purpose:** Manages persistent workflows with trigger nodes.

**Responsibilities:**
1. Start/stop monitoring workflows
2. Listen for trigger events (webhook, schedule, file, email)
3. Spawn execution instances when triggers fire
4. Enforce concurrency limits
5. Persist monitoring state (survives server restarts)

### Trigger Types

| Trigger Type | Description | Example |
|-------------|-------------|---------|
| **Webhook** | HTTP endpoint listener | `POST /webhooks/{workflow_id}` |
| **Schedule** | Cron-like scheduling | Every day at 9 AM |
| **File Detection** | File watcher | New file in `uploads/` |
| **Email** | Email inbox polling | New email from client |
| **Database Polling** | Query database | New rows in `orders` table |

### Trigger Handling

**When trigger fires:**

```python
async def handle_trigger(workflow_id, trigger_data):
    workflow = get_workflow(workflow_id)
    
    # Check monitoring state
    if not workflow.is_active:
        logger.warning(f"Trigger for inactive workflow {workflow_id}")
        return
    
    # Check concurrency limit
    active_executions = count_active_executions(workflow_id)
    
    if active_executions >= workflow.execution_config.workflow_concurrency:
        logger.warning(f"Workflow {workflow_id} at max concurrency ({active_executions})")
        return  # Ignore trigger (NOT queued)
    
    # Spawn new execution instance
    execution_id = await spawn_execution(
        workflow_id=workflow_id,
        execution_source=trigger_type,  # "webhook", "schedule", etc.
        trigger_data=trigger_data
    )
    
    logger.info(f"Spawned execution {execution_id} for workflow {workflow_id}")
```

### Concurrency Example

**Workflow config:**
```python
workflow_concurrency: 3  # Max 3 parallel instances
```

**Scenario:** Webhook receives 10 simultaneous requests

**Result:**
- First 3 requests → Spawn execution instances (run in parallel)
- Remaining 7 requests → Ignored (logged)
- When an instance completes → Next trigger can spawn new instance

**Note:** Triggers are NOT queued in v1.0 (ignored if at limit).

---

## Real-Time Updates

TAV Engine streams execution progress in real-time using **Server-Sent Events (SSE)**.

### SSE Endpoint

```bash
GET /api/v1/executions/{execution_id}/stream
```

**Response:** Stream of events in SSE format

### Event Types

```typescript
// Node started
{
  "type": "node_started",
  "execution_id": "exec_123",
  "node_id": "node_abc",
  "timestamp": "2025-12-02T10:00:00Z"
}

// Node completed
{
  "type": "node_completed",
  "execution_id": "exec_123",
  "node_id": "node_abc",
  "outputs": {"output": "Hello"},
  "duration_ms": 1234,
  "timestamp": "2025-12-02T10:00:01Z"
}

// Node failed
{
  "type": "node_failed",
  "execution_id": "exec_123",
  "node_id": "node_abc",
  "error": "Connection timeout",
  "timestamp": "2025-12-02T10:00:01Z"
}

// Workflow completed
{
  "type": "workflow_completed",
  "execution_id": "exec_123",
  "status": "completed",
  "final_outputs": {...},
  "duration_ms": 5678,
  "timestamp": "2025-12-02T10:00:05Z"
}
```

### Frontend Integration

**JavaScript Example:**

```javascript
const eventSource = new EventSource(
  `http://localhost:8000/api/v1/executions/${executionId}/stream`
);

eventSource.addEventListener('node_started', (e) => {
  const data = JSON.parse(e.data);
  console.log(`Node ${data.node_id} started`);
  // Update UI: highlight node as "running"
});

eventSource.addEventListener('node_completed', (e) => {
  const data = JSON.parse(e.data);
  console.log(`Node ${data.node_id} completed in ${data.duration_ms}ms`);
  // Update UI: show success checkmark
});

eventSource.addEventListener('workflow_completed', (e) => {
  const data = JSON.parse(e.data);
  console.log(`Workflow completed with status: ${data.status}`);
  eventSource.close();  // Stop listening
});
```

**React Hook Example:**

```typescript
function useExecutionStream(executionId: string) {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  
  useEffect(() => {
    const eventSource = new EventSource(
      `/api/v1/executions/${executionId}/stream`
    );
    
    const handleEvent = (e: MessageEvent) => {
      const event = JSON.parse(e.data);
      setEvents(prev => [...prev, event]);
    };
    
    eventSource.addEventListener('node_started', handleEvent);
    eventSource.addEventListener('node_completed', handleEvent);
    eventSource.addEventListener('node_failed', handleEvent);
    eventSource.addEventListener('workflow_completed', handleEvent);
    
    return () => eventSource.close();
  }, [executionId]);
  
  return events;
}
```

---

## Performance

### Optimization Strategies

#### 1. Worker Pool Sizing

**Default:** 10 concurrent nodes per workflow

**Tuning:**
- **CPU-bound workflows** (data processing): Match CPU core count
- **I/O-bound workflows** (HTTP requests, DB queries): Higher (20-50)
- **LLM-heavy workflows** (AI agents): Lower (5-10)

**Configuration:**

```python
# High I/O workflow
execution_config.max_concurrent_nodes = 30

# High CPU workflow
execution_config.max_concurrent_nodes = 8  # Match CPU cores
```

#### 2. Resource Pooling

**Standard Pool:**
- Most nodes (HTTP, data processing, triggers)
- Limit: `max_concurrent_nodes`

**LLM Pool:**
- AI nodes (OpenAI, Anthropic, Google AI)
- Separate limit (prevents rate limit exhaustion)
- Default: 50 requests/minute

**AI Agent Pool:**
- Complex AI agents with tool use
- Lower limit (resource-intensive)
- Default: 5 concurrent

#### 3. Execution Mode Tuning

**Sequential Mode:**
```python
execution_mode: "sequential"
```
- Nodes execute one-by-one
- Useful for debugging, strict ordering
- Lower resource usage

**Parallel Mode (Default):**
```python
execution_mode: "parallel"
```
- Maximum parallelism
- Best performance
- Higher resource usage

**Auto Mode:**
```python
execution_mode: "auto"
```
- System decides based on workflow structure
- Balances performance and resources

---

### Performance Monitoring

**Metrics tracked:**
- Nodes executing (current count)
- Nodes pending (waiting for dependencies)
- Nodes completed
- Worker pool utilization (%)
- Execution duration (total, per-node)
- Bottleneck nodes (slowest nodes)

**API Endpoint:**

```bash
GET /api/v1/workflows/{workflow_id}/status
```

**Response:**

```json
{
  "workflow_id": "wf_123",
  "status": "running",
  "nodes_completed": 5,
  "nodes_executing": 3,
  "nodes_pending": 2,
  "worker_pool_utilization": 0.3,
  "duration_ms": 12345,
  "bottleneck_nodes": [
    {"node_id": "llm1", "duration_ms": 8000}
  ]
}
```

---

### Scalability

**Current limits (SQLite):**
- ✅ 100 nodes per workflow
- ✅ 1,000 concurrent executions
- ✅ 10,000 total executions (with cleanup)

**For larger scale:**
- Consider Enterprise Edition (PostgreSQL support)
- Better concurrency handling
- Distributed execution
- Advanced monitoring

---

## Troubleshooting

### Workflow Stuck

**Symptoms:** Workflow status "running" but no progress

**Diagnosis:**

```bash
python backend/scripts/check_stuck_executions.py
```

**Solutions:**
1. Check logs for node errors
2. Verify network connectivity (for HTTP nodes)
3. Check resource limits (CPU, memory)
4. Stop workflow and restart

### Node Timeout

**Symptoms:** Node fails with "TimeoutError"

**Solutions:**
1. Increase `node_timeout_seconds`
2. Optimize node logic (if custom node)
3. Check external service responsiveness
4. Enable retry (if transient)

### Concurrency Issues

**Symptoms:** "Max concurrency reached" warnings

**Solutions:**
1. Increase `max_concurrent_nodes`
2. Reduce parallelism (bottleneck detection)
3. Optimize slow nodes
4. Consider sequential mode for debugging

### Memory Growth

**Symptoms:** Backend memory usage grows during execution

**Solutions:**
1. Enable `auto_cleanup` in storage settings
2. Reduce `max_execution_history`
3. Clear old executions manually
4. Avoid storing large data in node outputs

---

## Related Documentation

- [Node System](nodes.md) - Node architecture and capabilities
- [Database](database.md) - Execution data storage
- [Execution API](../api/execution.md) - API endpoints for execution
- [Settings](../api/settings.md) - Configuration options

---

## Support

- 📖 [Full Documentation](../README.md)
- 🐛 [Report Issues](https://github.com/Markepattsu/tav_opensource/issues)
- 💬 [Community Discussions](https://github.com/Markepattsu/tav_opensource/discussions)
