# TAV Engine Configuration Structure

Complete settings layout for database-backed configuration.

---

## 🔐 ENVIRONMENT VARIABLES (Infrastructure - NOT in DB)

These stay in `.env` file and are loaded via Pydantic BaseSettings.
See `deployment/configs/env.unified.example` for the full template.

```bash
# Core Infrastructure
SECRET_KEY=<required-32-chars-minimum>
ENCRYPTION_KEY=<required-32-chars-minimum>
DATABASE_URL=sqlite:///./data/tav_engine.db
BASE_URL=http://localhost:5000

# Port Configuration
BACKEND_PORT=5000
FRONTEND_PORT=3000

# Development Mode
ENABLE_DEV_MODE=true
ENVIRONMENT=development

# Optional: AI Provider Keys (can also be encrypted in DB)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...

# Observability
LOG_LEVEL=INFO
```

---

## 🗄️ DATABASE SETTINGS (Application Behavior)

Settings stored in database with namespace organization:

---

### **1. EXECUTION NAMESPACE** (22 fields)

Core workflow execution behavior.

#### **Concurrency & Performance**
| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `max_concurrent_nodes` | int | 5 | 1-50 | Max nodes executing in parallel per workflow |
| `ai_concurrent_limit` | int | 1 | 1-10 | Max concurrent AI calls (expensive) |
| `max_concurrent_runs_global` | int | 8 | 1-200 | Max total workflow runs system-wide |
| `max_concurrent_runs_per_workflow` | int | 20 | 1-50 | Max concurrent runs of same workflow |
| `max_queue_depth_per_workflow` | int | 200 | 1-10000 | Max queued executions per workflow |

#### **Timeouts & Limits**
| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `default_timeout` | int | 300 | 10-7200 | Default node timeout (seconds) |
| `http_timeout` | int | 60 | 5-600 | HTTP request timeout (seconds) |
| `workflow_timeout` | int | 1800 | 60-86400 | Max workflow execution time (seconds) |

#### **Retry & Error Handling**
| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `error_handling` | str | "stop_on_error" | enum | "stop_on_error" or "continue_on_error" |
| `max_retries` | int | 3 | 0-20 | Max retry attempts on failure |
| `retry_delay` | float | 5.0 | 0.1-300.0 | Initial delay between retries (seconds) |
| `backoff_multiplier` | float | 1.5 | 1.0-5.0 | Exponential backoff multiplier |
| `max_retry_delay` | int | 60 | 1-3600 | Max delay between retries (seconds) |

#### **Triggers & Monitoring**
| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `trigger_max_executions` | int | 0 | ≥0 | Max trigger executions (0=unlimited) |
| `auto_restart_triggers` | bool | False | - | Auto-restart triggers after failure |
| `monitoring_interval` | int | 30 | 5-3600 | Trigger check interval (seconds) |

#### **Queue Management**
| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `use_priority_queue` | bool | True | - | Enable priority-based queue |
| `max_priority_events` | int | 10 | 1-1000 | Max high-priority events |
| `queue_timeout` | int | 60 | 10-3600 | Queue operation timeout (seconds) |

#### **Resource Management**
| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `memory_limit_mb` | int | 512 | 64-16384 | Memory limit per execution (MB) |
| `max_execution_history` | int | 100 | 10-10000 | Max stored execution logs |
| `validate_workflows` | bool | True | - | Validate workflow before execution |
| `sandbox_mode` | bool | False | - | Run nodes in sandbox (restricted) |
| `allow_external_requests` | bool | True | - | Allow nodes to make HTTP requests |

#### **Payload Management**
| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `payload_max_chars` | int | 4000 | 100-1000000 | Max chars in payload projection |
| `payload_max_items` | int | 100 | 10-10000 | Max items in array projection |
| `payload_inline_max_bytes` | int | 262144 | 16384-52428800 | Max inline payload size (bytes, 256KB) |

---

### **2. AI NAMESPACE** (8 global + providers)

AI provider configuration and behavior.

#### **Global AI Settings**
| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `enabled` | bool | True | - | Enable AI features globally |
| `default_provider` | str | "openai" | must exist in providers | Default AI provider name |
| `fallback_provider` | str | "local_server" | must exist in providers | Fallback if default fails |
| `default_temperature` | float | 0.7 | 0.0-2.0 | Default sampling temperature |
| `default_max_tokens` | int | 1000 | >0 | Default max tokens |
| `request_timeout` | int | 30 | >0 | AI request timeout (seconds) |
| `max_retries` | int | 3 | ≥0 | Max AI request retries |
| `retry_delay` | float | 1.0 | >0 | Delay between AI retries (seconds) |

#### **Providers** (nested dict: `ai.providers.{provider_name}`)

Each provider has these fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | str | - | Display name (e.g., "OpenAI") |
| `provider_type` | str | - | Type: openai/anthropic/deepseek/local_server/etc |
| `enabled` | bool | False | Whether provider is active |
| `api_key` | str | "" | API key (encrypted in DB) |
| `base_url` | str | - | Provider API endpoint |
| `default_model` | str | - | Default model to use |
| `auth_type` | str | "bearer_token" | bearer_token/api_key/x-api-key/none |
| `available_models` | List[str] | [] | List of available models |
| `max_tokens_limit` | int | 4096 | Max tokens supported |
| `supports_streaming` | bool | True | Streaming support |
| `supports_function_calling` | bool | False | Function calling support |
| `rate_limit_per_minute` | int | 60 | Rate limit |
| `custom_headers` | Dict[str,str] | {} | Custom HTTP headers |
| `default_temperature` | float | 0.7 | Provider-specific temperature |

**Example Providers:**
- `ai.providers.openai` - OpenAI GPT models
- `ai.providers.anthropic` - Claude models
- `ai.providers.deepseek` - DeepSeek models
- `ai.providers.local_server` - Local/self-hosted

---

### **3. UI NAMESPACE** (4 fields)

User interface defaults (frontend uses these as initial values).

| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `default_theme_mode` | str | "default" | enum | "light", "dark", or "default" |
| `default_grid_size` | int | 20 | 10-50 | Canvas grid size (pixels) |
| `enable_grid` | bool | True | - | Show grid on workflow canvas |
| `grid_opacity` | float | 0.3 | 0.0-1.0 | Canvas grid opacity |

---

### **4. STORAGE NAMESPACE** (18 fields)

Data retention and cleanup policies.

#### **Retention**
| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `result_storage_days` | int | 30 | 1-365 | Days to keep execution results |
| `max_execution_history` | int | 100 | 10-10000 | Max execution logs to keep |

#### **Cleanup Master Switches**
| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `auto_cleanup` | bool | True | - | Automatically cleanup old data |
| `temp_file_cleanup` | bool | True | - | Cleanup temporary files |
| `cleanup_on_startup` | bool | False | - | Delete all temp files on server restart (dev only!) |

#### **Uploads (User input files)**
| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `upload_dir` | str | "uploads" | - | Upload storage directory |
| `upload_storage_days` | int | 30 | 1-365 | Days to keep uploaded files |
| `uploads_cleanup_interval_hours` | int | 24 | 1-168 | Upload cleanup frequency (hours) |

#### **Artifacts (Generated outputs)**
| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `artifact_dir` | str | "artifacts" | - | Artifact storage directory |
| `artifact_ttl_days` | int | 7 | 1-365 | Artifact retention (days) |
| `artifact_max_bytes` | int | 1073741824 | ≥10485760 | Max artifacts size (bytes, 1GB) |
| `artifact_backend` | str | "fs" | enum | "fs", "s3", or "gcs" |
| `artifact_cleanup_interval_hours` | int | 6 | 1-168 | Artifact cleanup frequency (hours) |

#### **Temp Files (Processing internals)**
| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `temp_dir` | str | "temp" | - | Temporary file storage directory |
| `temp_cleanup_interval_hours` | int | 1 | 1-24 | Temp file cleanup frequency (hours) |
| `temp_file_max_age_hours` | int | 1 | 1-24 | Max age of temp files before deletion |

---

### **5. SECURITY NAMESPACE** (1 field)

Security and rate limiting (secret_key in ENV, not here).

| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `max_content_length` | int | 104857600 | 1048576-2147483648 | Max request size (bytes, 100MB) |

---

### **6. NETWORK NAMESPACE** (1 field)

Network configuration (base_url in ENV, not here).

| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `cors_origins` | List[str] | ["http://localhost:*"] | valid URLs | Allowed CORS origins |

**Note:** Wildcards only allowed in development. Production requires explicit origins.

---

### **7. INTEGRATIONS NAMESPACE** (7 fields)

Optional third-party integrations (all encrypted).

#### **Search APIs**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `search_serper_api_key` | str | "" | Serper.dev API key (encrypted) |
| `search_bing_api_key` | str | "" | Bing Web Search API key (encrypted) |
| `search_google_pse_api_key` | str | "" | Google Programmable Search API key (encrypted) |
| `search_google_pse_cx` | str | "" | Google PSE Search Engine ID |
| `search_duckduckgo_enabled` | bool | True | Enable DuckDuckGo search (no key needed) |

#### **AI Platforms**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `huggingface_api_token` | str | "" | HuggingFace API token (encrypted) |

---

### **8. DEVELOPER NAMESPACE** (6 fields)

Development and debugging settings.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enable_dev_mode` | bool | True | Enable dev mode (bypasses auth). **Disable in production!** |
| `debug_mode` | bool | False | Enable debug mode (verbose logging) |
| `console_logging` | bool | True | Log to console |
| `error_details` | bool | True | Include full error details in responses |
| `api_timing` | bool | False | Log API endpoint timing |
| `memory_monitoring` | bool | False | Monitor memory usage |

---

## 📊 Summary

### **Total Fields: ~65**

| Namespace | Fields | Description |
|-----------|--------|-------------|
| execution | 22 | Workflow execution behavior |
| ai | 8 + providers | AI configuration |
| ui | 4 | UI defaults |
| storage | 18 | Data retention & cleanup |
| security | 1 | Request limits |
| network | 1 | CORS settings |
| integrations | 6 | Optional APIs |
| developer | 6 | Debug settings |

### **Encrypted Fields:**
- All `api_key` fields in AI providers
- All integration API keys/tokens
- These are encrypted in DB using ENCRYPTION_KEY from env

### **Environment-Only:**
- `SECRET_KEY` - App signing
- `ENCRYPTION_KEY` - Master encryption
- `DATABASE_URL` - DB connection
- `BASE_URL` - Deployment URL
- `BACKEND_PORT` / `FRONTEND_PORT` - Server ports


