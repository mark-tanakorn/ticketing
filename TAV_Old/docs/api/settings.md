# Settings API

Complete reference for system configuration and settings management.

---

## Overview

The Settings API allows you to configure TAV Engine behavior, including:
- Execution settings (timeouts, concurrency, error handling)
- AI provider configuration (OpenAI, Anthropic, Google, etc.)
- UI preferences (theme, grid, canvas)
- Storage and cleanup policies
- Security settings
- Network configuration
- Integrations (search APIs, etc.)
- Developer settings

**Base Path:** `/api/v1/settings`

---

## Table of Contents

- [Get All Settings](#get-all-settings)
- [Execution Settings](#execution-settings)
- [AI Settings](#ai-settings)
- [UI Settings](#ui-settings)
- [Storage Settings](#storage-settings)
- [Security Settings](#security-settings)
- [Network Settings](#network-settings)
- [Integrations Settings](#integrations-settings)
- [Developer Settings](#developer-settings)
- [Settings Structure](#settings-structure)

---

## Get All Settings

Get all application settings in one call.

### Endpoint

```
GET /api/v1/settings
```

### Response

**Status Code:** `200 OK`

```json
{
  "execution": {
    "max_concurrent_nodes": 5,
    "ai_concurrent_limit": 1,
    "default_timeout": 300,
    ...
  },
  "ai": {
    "enabled": true,
    "default_provider": "openai",
    "providers": {...},
    ...
  },
  "ui": {
    "default_theme_mode": "default",
    "default_grid_size": 20,
    ...
  },
  "storage": {
    "result_storage_days": 30,
    "auto_cleanup": true,
    ...
  },
  "security": {
    "max_content_length": 104857600
  },
  "network": {
    "cors_origins": ["http://localhost:*"]
  },
  "integrations": {
    "search_duckduckgo_enabled": true,
    ...
  },
  "developer": {
    "enable_dev_mode": true,
    "debug_mode": false,
    ...
  }
}
```

### Example

```bash
curl http://localhost:5000/api/v1/settings
```

---

## Execution Settings

Configure workflow execution behavior.

### Get Execution Settings

```
GET /api/v1/settings/execution
```

### Update Execution Settings

```
PUT /api/v1/settings/execution
```

### Request Body

```json
{
  "max_concurrent_nodes": 10,
  "ai_concurrent_limit": 2,
  "max_concurrent_runs_global": 8,
  "max_concurrent_runs_per_workflow": 20,
  "max_queue_depth_per_workflow": 200,
  "default_timeout": 600,
  "http_timeout": 60,
  "workflow_timeout": 1800,
  "error_handling": "stop_on_error",
  "max_retries": 3,
  "retry_delay": 5.0,
  "backoff_multiplier": 1.5,
  "max_retry_delay": 60,
  "trigger_max_executions": 0,
  "auto_restart_triggers": false,
  "monitoring_interval": 30,
  "use_priority_queue": true,
  "max_priority_events": 10,
  "queue_timeout": 60,
  "memory_limit_mb": 512,
  "max_execution_history": 100,
  "validate_workflows": true,
  "sandbox_mode": false,
  "allow_external_requests": true,
  "payload_max_chars": 4000,
  "payload_max_items": 100,
  "payload_inline_max_bytes": 262144
}
```

### Field Descriptions

**Concurrency & Performance:**
- `max_concurrent_nodes` (1-50, default: 5): Max nodes executing in parallel per workflow
- `ai_concurrent_limit` (1-10, default: 1): Max concurrent AI calls (expensive)
- `max_concurrent_runs_global` (1-200, default: 8): Max total running workflows
- `max_concurrent_runs_per_workflow` (1-50, default: 20): Max concurrent runs of same workflow

**Timeouts:**
- `default_timeout` (10-7200s, default: 300): Default node timeout
- `http_timeout` (5-600s, default: 60): HTTP request timeout
- `workflow_timeout` (60-86400s, default: 1800): Max workflow execution time

**Error Handling:**
- `error_handling` ("stop_on_error" | "continue_on_error", default: "stop_on_error"): Error strategy
- `max_retries` (0-20, default: 3): Max retry attempts on failure
- `retry_delay` (0.1-300s, default: 5.0): Initial delay between retries
- `backoff_multiplier` (1.0-5.0, default: 1.5): Exponential backoff multiplier
- `max_retry_delay` (1-3600s, default: 60): Max delay between retries

**Triggers & Monitoring:**
- `trigger_max_executions` (0+, default: 0): Max trigger executions (0=unlimited)
- `auto_restart_triggers` (boolean, default: false): Auto-restart triggers after failure
- `monitoring_interval` (5-3600s, default: 30): Trigger check interval

**Queue Management:**
- `use_priority_queue` (boolean, default: true): Enable priority-based queue
- `max_priority_events` (1-1000, default: 10): Max high-priority events
- `queue_timeout` (10-3600s, default: 60): Queue operation timeout

**Resource Management:**
- `memory_limit_mb` (64-16384, default: 512): Memory limit per execution
- `max_execution_history` (10-10000, default: 100): Max stored execution logs
- `validate_workflows` (boolean, default: true): Validate workflow before execution
- `sandbox_mode` (boolean, default: false): Run nodes in sandbox (restricted)
- `allow_external_requests` (boolean, default: true): Allow nodes to make HTTP requests

**Payload Management:**
- `payload_max_chars` (100-1000000, default: 4000): Max chars in payload projection
- `payload_max_items` (10-10000, default: 100): Max items in array projection
- `payload_inline_max_bytes` (16384-52428800, default: 262144): Max inline payload size

### Example

```bash
# Get
curl http://localhost:5000/api/v1/settings/execution

# Update
curl -X PUT http://localhost:5000/api/v1/settings/execution \
  -H "Content-Type: application/json" \
  -d '{
    "max_concurrent_nodes": 10,
    "default_timeout": 600,
    "stop_on_error": false
  }'
```

---

## AI Settings

Configure AI providers and models.

### Get AI Settings

```
GET /api/v1/settings/ai
```

### Update AI Settings

```
PUT /api/v1/settings/ai
```

### Request Body

```json
{
  "enabled": true,
  "default_provider": "openai",
  "fallback_provider": "anthropic",
  "default_temperature": 0.7,
  "default_max_tokens": 16384,
  "request_timeout": 120,
  "max_retries": 3,
  "retry_delay": 1.0,
  "providers": {
    "openai": {
      "name": "OpenAI",
      "provider_type": "openai",
      "enabled": true,
      "role": "primary",
      "api_key": "sk-...",
      "base_url": "https://api.openai.com/v1",
      "default_model": "gpt-5",
      "auth_type": "bearer_token",
      "available_models": ["gpt-5", "gpt-4o", ...],
      "max_tokens_limit": 4096,
      "supports_streaming": true,
      "supports_function_calling": true,
      "rate_limit_per_minute": 60,
      "default_temperature": 0.7
    },
    "anthropic": {
      "name": "Anthropic",
      "provider_type": "anthropic",
      "enabled": true,
      "role": "fallback",
      "fallback_priority": 1,
      "api_key": "sk-ant-...",
      "base_url": "https://api.anthropic.com/v1",
      "default_model": "claude-3-5-sonnet-20241022",
      ...
    }
  }
}
```

### Field Descriptions

**Global Settings:**
- `enabled` (boolean, default: true): Enable AI features globally
- `default_provider` (string, default: "openai"): Default AI provider
- `fallback_provider` (string): Fallback provider if default fails
- `default_temperature` (0.0-2.0, default: 0.7): Default sampling temperature
- `default_max_tokens` (int, default: 16384): Default max tokens
- `request_timeout` (int, default: 120): AI request timeout (seconds)
- `max_retries` (0+, default: 3): Max AI request retries
- `retry_delay` (float, default: 1.0): Delay between AI retries

**Provider Configuration:**
- `name`: Display name
- `provider_type`: Provider identifier (openai, anthropic, google, etc.)
- `enabled`: Whether provider is active
- `role`: "primary", "fallback", or "inactive"
- `fallback_priority`: Priority order for fallback (1, 2, 3...)
- `api_key`: API key (encrypted in database)
- `base_url`: Provider API endpoint
- `default_model`: Default model to use
- `auth_type`: Authentication type
- `available_models`: List of available models
- `max_tokens_limit`: Max tokens supported
- `supports_streaming`: Streaming support
- `supports_function_calling`: Function calling support
- `rate_limit_per_minute`: Rate limit
- `custom_headers`: Custom HTTP headers
- `default_temperature`: Provider-specific temperature

### Example

```bash
# Get
curl http://localhost:5000/api/v1/settings/ai

# Update (add OpenAI provider)
curl -X PUT http://localhost:5000/api/v1/settings/ai \
  -H "Content-Type: application/json" \
  -d '{
    "default_provider": "openai",
    "providers": {
      "openai": {
        "name": "OpenAI",
        "provider_type": "openai",
        "enabled": true,
        "role": "primary",
        "api_key": "sk-...",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4"
      }
    }
  }'
```

**See also:** [AI Provider API](../api/ai-providers.md) for provider-specific endpoints.

---

## UI Settings

Configure user interface defaults.

### Get UI Settings

```
GET /api/v1/settings/ui
```

### Update UI Settings

```
PUT /api/v1/settings/ui
```

### Request Body

```json
{
  "default_theme_mode": "dark",
  "default_grid_size": 20,
  "enable_grid": true,
  "grid_opacity": 0.3
}
```

### Field Descriptions

- `default_theme_mode` ("light" | "dark" | "default", default: "default"): Default theme mode
- `default_grid_size` (10-50, default: 20): Canvas grid size (pixels)
- `enable_grid` (boolean, default: true): Show grid on workflow canvas
- `grid_opacity` (0.0-1.0, default: 0.3): Canvas grid opacity

### Example

```bash
curl -X PUT http://localhost:5000/api/v1/settings/ui \
  -H "Content-Type: application/json" \
  -d '{
    "default_theme_mode": "dark",
    "default_grid_size": 20,
    "enable_grid": true,
    "grid_opacity": 0.4
  }'
```

---

## Storage Settings

Configure data retention and cleanup policies.

### Get Storage Settings

```
GET /api/v1/settings/storage
```

### Update Storage Settings

```
PUT /api/v1/settings/storage
```

### Request Body

```json
{
  "result_storage_days": 30,
  "max_execution_history": 100,
  "auto_cleanup": true,
  "temp_file_cleanup": true,
  "cleanup_on_startup": false,
  "upload_dir": "uploads",
  "upload_storage_days": 30,
  "uploads_cleanup_interval_hours": 24,
  "artifact_dir": "artifacts",
  "artifact_ttl_days": 7,
  "artifact_max_bytes": 1073741824,
  "artifact_backend": "fs",
  "artifact_cleanup_interval_hours": 6,
  "temp_dir": "temp",
  "temp_cleanup_interval_hours": 1,
  "temp_file_max_age_hours": 1
}
```

### Field Descriptions

**Retention:**
- `result_storage_days` (1-365, default: 30): Days to keep execution results
- `max_execution_history` (10-10000, default: 100): Max execution logs to keep

**Cleanup Master Switches:**
- `auto_cleanup` (boolean, default: true): Automatically cleanup old data
- `temp_file_cleanup` (boolean, default: true): Cleanup temporary files
- `cleanup_on_startup` (boolean, default: false): ⚠️ Delete all files on restart (dev only, data loss risk!)

**Uploads:**
- `upload_dir` (string, default: "uploads"): Upload storage directory
- `upload_storage_days` (1-365, default: 30): Days to keep uploaded files
- `uploads_cleanup_interval_hours` (1-168, default: 24): Upload cleanup frequency

**Artifacts:**
- `artifact_dir` (string, default: "artifacts"): Artifact storage directory
- `artifact_ttl_days` (1-365, default: 7): Artifact retention (days)
- `artifact_max_bytes` (10485760+, default: 1073741824): Max artifacts size (bytes)
- `artifact_backend` ("fs" | "s3" | "gcs", default: "fs"): Artifact storage backend
- `artifact_cleanup_interval_hours` (1-168, default: 6): Artifact cleanup frequency

**Temp Files:**
- `temp_dir` (string, default: "temp"): Temporary file storage directory
- `temp_cleanup_interval_hours` (1-24, default: 1): Temp file cleanup frequency
- `temp_file_max_age_hours` (1-24, default: 1): Max age of temp files before deletion

### Example

```bash
curl -X PUT http://localhost:5000/api/v1/settings/storage \
  -H "Content-Type: application/json" \
  -d '{
    "auto_cleanup": true,
    "result_storage_days": 60,
    "upload_storage_days": 90
  }'
```

---

## Security Settings

Configure security and rate limiting.

### Get Security Settings

```
GET /api/v1/settings/security
```

### Update Security Settings

```
PUT /api/v1/settings/security
```

### Request Body

```json
{
  "max_content_length": 104857600
}
```

### Field Descriptions

- `max_content_length` (1048576-2147483648, default: 104857600): Maximum request body size in bytes (100MB default)

### Example

```bash
curl -X PUT http://localhost:5000/api/v1/settings/security \
  -H "Content-Type: application/json" \
  -d '{
    "max_content_length": 209715200
  }'
```

---

## Network Settings

Configure network and CORS settings.

### Get Network Settings

```
GET /api/v1/settings/network
```

### Update Network Settings

```
PUT /api/v1/settings/network
```

### Request Body

```json
{
  "cors_origins": [
    "http://localhost:3000",
    "http://localhost:5000",
    "https://yourdomain.com"
  ]
}
```

### Field Descriptions

- `cors_origins` (array of strings): Allowed CORS origins (must start with http:// or https://)

### Example

```bash
curl -X PUT http://localhost:5000/api/v1/settings/network \
  -H "Content-Type: application/json" \
  -d '{
    "cors_origins": [
      "http://localhost:3000",
      "http://192.168.1.100:3000",
      "https://myapp.com"
    ]
  }'
```

---

## Integrations Settings

Configure third-party integrations.

### Get Integrations Settings

```
GET /api/v1/settings/integrations
```

### Update Integrations Settings

```
PUT /api/v1/settings/integrations
```

### Request Body

```json
{
  "search_serper_api_key": "",
  "search_bing_api_key": "",
  "search_google_pse_api_key": "",
  "search_google_pse_cx": "",
  "search_duckduckgo_enabled": true,
  "huggingface_api_token": ""
}
```

### Field Descriptions

**Search APIs:**
- `search_serper_api_key` (string): Serper.dev API key (encrypted)
- `search_bing_api_key` (string): Bing Web Search API key (encrypted)
- `search_google_pse_api_key` (string): Google Programmable Search API key (encrypted)
- `search_google_pse_cx` (string): Google PSE Search Engine ID
- `search_duckduckgo_enabled` (boolean, default: true): Enable DuckDuckGo search (no key needed)

**AI Platforms:**
- `huggingface_api_token` (string): HuggingFace API token (encrypted)

### Example

```bash
curl -X PUT http://localhost:5000/api/v1/settings/integrations \
  -H "Content-Type: application/json" \
  -d '{
    "search_duckduckgo_enabled": true,
    "huggingface_api_token": "hf_..."
  }'
```

---

## Developer Settings

Configure development and debugging options.

### Get Developer Settings

```
GET /api/v1/settings/developer
```

### Update Developer Settings

```
PUT /api/v1/settings/developer
```

### Request Body

```json
{
  "enable_dev_mode": false,
  "debug_mode": false,
  "console_logging": true,
  "error_details": true,
  "api_timing": false,
  "memory_monitoring": false
}
```

### Field Descriptions

- `enable_dev_mode` (boolean, default: true): ⚠️ Enable development mode (bypasses authentication). **Disable in production!**
- `debug_mode` (boolean, default: false): Enable debug mode (verbose logging)
- `console_logging` (boolean, default: true): Log to console
- `error_details` (boolean, default: true): Include full error details in responses
- `api_timing` (boolean, default: false): Log API endpoint timing
- `memory_monitoring` (boolean, default: false): Monitor memory usage

### Example

```bash
# Production settings
curl -X PUT http://localhost:5000/api/v1/settings/developer \
  -H "Content-Type: application/json" \
  -d '{
    "enable_dev_mode": false,
    "debug_mode": false,
    "error_details": false
  }'
```

---

## Settings Structure

### Response Format

All GET endpoints return settings in this format:

```json
{
  "field_name": value,
  "another_field": value
}
```

### Update Format

PUT endpoints accept partial updates - only include fields you want to change:

```json
{
  "field_name": new_value
}
```

Fields not included remain unchanged.

### Validation

- Settings are validated against schemas
- Invalid values return `400 Bad Request`
- Out-of-range values are clamped to valid ranges
- Required fields cannot be null

---

## Best Practices

### For Production Deployments

1. **Disable dev mode:**
   ```json
   {"enable_dev_mode": false}
   ```

2. **Increase timeouts** for long workflows:
   ```json
   {"default_timeout": 600, "workflow_timeout": 3600}
   ```

3. **Configure AI providers** with API keys

4. **Set appropriate concurrency limits** based on resources

5. **Enable cleanup** to prevent storage growth:
   ```json
   {"auto_cleanup": true, "result_storage_days": 30}
   ```

### For Development

1. **Enable dev mode** for easier testing:
   ```json
   {"enable_dev_mode": true}
   ```

2. **Enable debug logging:**
   ```json
   {"debug_mode": true, "api_timing": true}
   ```

3. **Disable cleanup** to inspect results:
   ```json
   {"auto_cleanup": false}
   ```

### For Performance

1. **Increase parallel execution:**
   ```json
   {"max_concurrent_nodes": 10, "ai_concurrent_limit": 3}
   ```

2. **Adjust timeouts** for your workflows

3. **Enable priority queue:**
   ```json
   {"use_priority_queue": true}
   ```

---

## Error Handling

### Common Errors

| Code | Description | Resolution |
|------|-------------|------------|
| `400` | Validation error (invalid value) | Check field constraints |
| `500` | Failed to update settings | Check logs |

### Error Response

```json
{
  "detail": "Validation error message",
  "field": "field_name",
  "value": "invalid_value",
  "constraint": "Valid range: 1-100"
}
```

---

## Related Documentation

- [Configuration Reference](../configuration/settings.md) - Detailed field documentation
- [Execution Config Reference](../configuration/execution.md) - All execution settings
- [Environment Config Guide](../configuration/environment.md) - Environment variables

---

## Support

- 📖 [Full Documentation](../README.md)
- 🐛 [Report Issues](https://github.com/Markepattsu/tav_opensource/issues)
- 💬 [Community Discussions](https://github.com/Markepattsu/tav_opensource/discussions)







