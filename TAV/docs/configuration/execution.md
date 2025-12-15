# Execution Config Reference

## Overview

This document lists ALL configuration fields that affect workflow execution. These are read from the database `settings` table and must be properly handled by the Par

allelExecutor.

---

## 1. EXECUTION SETTINGS (26 fields)

### Concurrency & Performance
| Field | Default | Range | Used In | Description |
|-------|---------|-------|---------|-------------|
| `max_concurrent_nodes` | 5 | 1-50 | **ParallelExecutor semaphore** | Max nodes executing in parallel per workflow |
| `ai_concurrent_limit` | 1 | 1-10 | **LLM/AI pool semaphore** | Max concurrent AI calls (expensive) |
| `max_concurrent_runs_global` | 8 | 1-200 | **Orchestrator global check** | Max total workflow runs system-wide |
| `max_concurrent_runs_per_workflow` | 20 | 1-50 | **TriggerManager callback** | Max concurrent runs of same workflow |
| `max_queue_depth_per_workflow` | 200 | 1-10000 | **Future: Queue system** | Max queued executions per workflow |

### Timeouts & Limits
| Field | Default | Range | Used In | Description |
|-------|---------|-------|---------|-------------|
| `default_timeout` | 300s | 10-7200s | **ParallelExecutor node execution** | Default node timeout |
| `http_timeout` | 60s | 5-600s | **HTTPRequestNode** | HTTP request timeout |
| `workflow_timeout` | 1800s | 60-86400s | **ParallelExecutor overall** | Max workflow execution time |

### Retry & Error Handling
| Field | Default | Range | Used In | Description |
|-------|---------|-------|---------|-------------|
| `error_handling` | "stop_on_error" | stop/continue | **ParallelExecutor error handling** | Stop on first error vs continue |
| `max_retries` | 3 | 0-20 | **ParallelExecutor retry logic** | Max retry attempts on failure |
| `retry_delay` | 5.0s | 0.1-300s | **ParallelExecutor retry logic** | Initial delay between retries |
| `backoff_multiplier` | 1.5 | 1.0-5.0 | **ParallelExecutor retry logic** | Exponential backoff multiplier |
| `max_retry_delay` | 60s | 1-3600s | **ParallelExecutor retry logic** | Max delay between retries |

### Triggers & Monitoring
| Field | Default | Range | Used In | Description |
|-------|---------|-------|---------|-------------|
| `trigger_max_executions` | 0 | 0+ | **TriggerManager** | Max trigger executions (0=unlimited) |
| `auto_restart_triggers` | False | bool | **TriggerManager** | Auto-restart triggers after failure |
| `monitoring_interval` | 30s | 5-3600s | **Trigger nodes** | Trigger check interval |

### Queue Management (Future)
| Field | Default | Range | Used In | Description |
|-------|---------|-------|---------|-------------|
| `use_priority_queue` | True | bool | **Future: Priority queue** | Enable priority-based queue |
| `max_priority_events` | 10 | 1-1000 | **Future: Priority queue** | Max high-priority events |
| `queue_timeout` | 60s | 10-3600s | **Future: Queue operations** | Queue operation timeout |

### Resource Management
| Field | Default | Range | Used In | Description |
|-------|---------|-------|---------|-------------|
| `memory_limit_mb` | 512 | 64-16384 | **Future: Sandbox** | Memory limit per execution |
| `max_execution_history` | 100 | 10-10000 | **Orchestrator cleanup** | Max stored execution logs |
| `validate_workflows` | True | bool | **Orchestrator pre-check** | Validate workflow before execution |
| `sandbox_mode` | False | bool | **Future: Sandboxing** | Run nodes in sandbox (restricted) |
| `allow_external_requests` | True | bool | **HTTPRequestNode** | Allow nodes to make HTTP requests |

### Payload Management
| Field | Default | Range | Used In | Description |
|-------|---------|-------|---------|-------------|
| `payload_max_chars` | 4000 | 100-1000000 | **Future: Payload projection** | Max chars in payload projection |
| `payload_max_items` | 100 | 10-10000 | **Future: Array projection** | Max items in array projection |
| `payload_inline_max_bytes` | 256KB | 16KB-50MB | **Future: Inline data** | Max inline payload size |

---

## 2. AI SETTINGS (17 fields)

### Global AI Settings
| Field | Default | Used In | Description |
|-------|---------|---------|-------------|
| `enabled` | True | **LangChainManager** | Enable AI features globally |
| `default_provider` | "openai" | **LangChainManager** | Default AI provider name |
| `fallback_provider` | "local_server" | **LangChainManager** | Fallback if default fails |
| `default_temperature` | 0.7 | **LLMCapability** | Default sampling temperature |
| `default_max_tokens` | 1000 | **LLMCapability** | Default max tokens |
| `request_timeout` | 30s | **LangChainManager** | AI request timeout |
| `max_retries` | 3 | **LangChainManager** | Max AI request retries |
| `retry_delay` | 1.0s | **LangChainManager** | Delay between AI retries |

### Per-Provider Config (nested dict)
- `name`, `provider_type`, `enabled`, `api_key`, `base_url`, `default_model`
- `auth_type`, `available_models`, `max_tokens_limit`
- `supports_streaming`, `supports_function_calling`
- `rate_limit_per_minute`, `custom_headers`, `default_temperature`

---

## 3. WORKFLOW-LEVEL CONFIG (Per-Workflow Override)

These are stored in `Workflow.execution_config` JSONB field and override global settings:

```python
class WorkflowExecutionConfig(BaseModel):
    """Per-workflow execution overrides."""
    
    # Concurrency (overrides global)
    workflow_concurrency: int = 5          # Max parallel workflow instances (for triggers)
    max_concurrent_nodes: int = 10         # Worker pool size for this workflow
    
    # Error handling (overrides global)
    stop_on_error: bool = True             # Stop on first error
    retry_enabled: bool = False            # Enable retries
    max_retries: int = 3                   # Retry attempts
    retry_backoff: float = 2.0             # Exponential backoff
    
    # Timeouts (overrides global)
    node_timeout_seconds: Optional[int] = 300   # Per-node timeout
    workflow_timeout_seconds: Optional[int] = 1800  # Workflow timeout
    
    # Pause/Resume
    pausable: bool = True                  # Allow workflow pause/resume
```

---

## Implementation Requirements for ParallelExecutor

### ✅ MUST IMPLEMENT (Phase 2)

1. **Concurrency Control**:
   - Read `max_concurrent_nodes` from config → create semaphore
   - Read `ai_concurrent_limit` → create LLM pool semaphore
   - Standard pool semaphore (from `max_concurrent_nodes`)

2. **Timeouts**:
   - Read `default_timeout` → apply to each node execution
   - Read `workflow_timeout` → apply to overall workflow
   - Use `asyncio.wait_for()` with timeout values

3. **Error Handling**:
   - Read `error_handling` ("stop_on_error" vs "continue_on_error")
   - If stop_on_error: raise exception immediately
   - If continue_on_error: log error, mark node as failed, continue

4. **Retry Logic**:
   - Read `max_retries`, `retry_delay`, `backoff_multiplier`, `max_retry_delay`
   - Implement exponential backoff:
     ```python
     delay = min(retry_delay * (backoff_multiplier ** attempt), max_retry_delay)
     await asyncio.sleep(delay)
     ```

5. **Workflow-Level Overrides**:
   - Load `Workflow.execution_config` from DB
   - Parse as `WorkflowExecutionConfig`
   - Prefer workflow config over global settings

---

### ⏳ DEFER TO FUTURE (Phase 3+)

- `memory_limit_mb` - Sandboxing
- `sandbox_mode` - Node isolation
- `payload_max_*` - Payload projection
- `use_priority_queue` - Priority queue system
- `validate_workflows` - Pre-execution validation
- `allow_external_requests` - Request filtering

---

## Config Loading Pattern

```python
# In Orchestrator
async def load_execution_config(workflow_id: str, db: Session) -> Dict[str, Any]:
    """Load merged execution config (workflow overrides + global defaults)."""
    
    # 1. Load global settings from DB
    global_settings = await settings_repo.get_namespace("execution")
    execution_settings = ExecutionSettings(**global_settings)
    
    # 2. Load workflow from DB
    workflow = await db.get(Workflow, workflow_id)
    
    # 3. Parse workflow-level overrides (if present)
    workflow_config = {}
    if workflow.execution_config:
        workflow_config = WorkflowExecutionConfig(**workflow.execution_config)
    
    # 4. Merge: workflow overrides global
    merged_config = {
        "max_concurrent_nodes": workflow_config.get("max_concurrent_nodes") or execution_settings.max_concurrent_nodes,
        "ai_concurrent_limit": execution_settings.ai_concurrent_limit,
        "default_timeout": workflow_config.get("node_timeout_seconds") or execution_settings.default_timeout,
        "workflow_timeout": workflow_config.get("workflow_timeout_seconds") or execution_settings.workflow_timeout,
        "stop_on_error": workflow_config.get("stop_on_error", execution_settings.error_handling == "stop_on_error"),
        "max_retries": workflow_config.get("max_retries") or execution_settings.max_retries,
        "retry_delay": execution_settings.retry_delay,
        "backoff_multiplier": execution_settings.backoff_multiplier,
        "max_retry_delay": execution_settings.max_retry_delay,
    }
    
    return merged_config
```

---

## Summary

**Total Fields**: 69 config fields across 8 namespaces

**Phase 2 Implementation**:
- ✅ 15 critical fields (concurrency, timeouts, error handling, retries)
- ⏳ 54 deferred fields (queues, sandboxing, payloads, cleanup, integrations)

**Config Sources**:
1. **Global** (DB settings table) - Default for all workflows
2. **Per-Workflow** (Workflow.execution_config) - Overrides for specific workflow
3. **Per-Provider** (AI settings) - AI provider-specific settings

**Priority**: Workflow > Global > Hardcoded defaults

