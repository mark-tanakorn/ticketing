"""
Settings Schemas

Pydantic models for validating application settings stored in database.
"""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, validator


# ==============================================================================
# EXECUTION SETTINGS
# ==============================================================================

class ExecutionSettings(BaseModel):
    """Workflow execution behavior settings."""
    
    # Concurrency & Performance
    max_concurrent_nodes: int = Field(
        default=5, 
        ge=1, 
        le=50,
        description="Max nodes executing in parallel per workflow"
    )
    ai_concurrent_limit: int = Field(
        default=1, 
        ge=1, 
        le=10,
        description="Max concurrent AI calls (expensive)"
    )
    max_concurrent_runs_global: int = Field(
        default=8, 
        ge=1, 
        le=200,
        description="Max total workflow runs system-wide"
    )
    max_concurrent_runs_per_workflow: int = Field(
        default=20, 
        ge=1, 
        le=50,
        description="Max concurrent runs of same workflow"
    )
    max_queue_depth_per_workflow: int = Field(
        default=200, 
        ge=1, 
        le=10000,
        description="Max queued executions per workflow"
    )
    
    # Timeouts & Limits (seconds)
    default_timeout: int = Field(
        default=300, 
        ge=10, 
        le=7200,
        description="Default node timeout (seconds)"
    )
    http_timeout: int = Field(
        default=60, 
        ge=5, 
        le=600,
        description="HTTP request timeout (seconds)"
    )
    workflow_timeout: int = Field(
        default=1800, 
        ge=60, 
        le=86400,
        description="Max workflow execution time (seconds)"
    )
    
    # Retry & Error Handling
    error_handling: Literal["stop_on_error", "continue_on_error"] = Field(
        default="stop_on_error",
        description="Error handling strategy"
    )
    max_retries: int = Field(
        default=3, 
        ge=0, 
        le=20,
        description="Max retry attempts on failure"
    )
    retry_delay: float = Field(
        default=5.0, 
        ge=0.1, 
        le=300.0,
        description="Initial delay between retries (seconds)"
    )
    backoff_multiplier: float = Field(
        default=1.5, 
        ge=1.0, 
        le=5.0,
        description="Exponential backoff multiplier"
    )
    max_retry_delay: int = Field(
        default=60, 
        ge=1, 
        le=3600,
        description="Max delay between retries (seconds)"
    )
    
    # Triggers & Monitoring
    trigger_max_executions: int = Field(
        default=0, 
        ge=0,
        description="Max trigger executions (0=unlimited)"
    )
    auto_restart_triggers: bool = Field(
        default=False,
        description="Auto-restart triggers after failure"
    )
    monitoring_interval: int = Field(
        default=30, 
        ge=5, 
        le=3600,
        description="Trigger check interval (seconds)"
    )
    
    # Queue Management
    use_priority_queue: bool = Field(
        default=True,
        description="Enable priority-based queue"
    )
    max_priority_events: int = Field(
        default=10, 
        ge=1, 
        le=1000,
        description="Max high-priority events"
    )
    queue_timeout: int = Field(
        default=60, 
        ge=10, 
        le=3600,
        description="Queue operation timeout (seconds)"
    )
    
    # Resource Management
    memory_limit_mb: int = Field(
        default=512, 
        ge=64, 
        le=16384,
        description="Memory limit per execution (MB)"
    )
    max_execution_history: int = Field(
        default=100, 
        ge=10, 
        le=10000,
        description="Max stored execution logs"
    )
    validate_workflows: bool = Field(
        default=True,
        description="Validate workflow before execution"
    )
    sandbox_mode: bool = Field(
        default=False,
        description="Run nodes in sandbox (restricted)"
    )
    allow_external_requests: bool = Field(
        default=True,
        description="Allow nodes to make HTTP requests"
    )
    
    # Payload Management
    payload_max_chars: int = Field(
        default=4000, 
        ge=100, 
        le=1000000,
        description="Max chars in payload projection"
    )
    payload_max_items: int = Field(
        default=100, 
        ge=10, 
        le=10000,
        description="Max items in array projection"
    )
    payload_inline_max_bytes: int = Field(
        default=262144,  # 256KB
        ge=16384,  # 16KB
        le=52428800,  # 50MB
        description="Max inline payload size (bytes)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "max_concurrent_nodes": 5,
                "default_timeout": 300,
                "error_handling": "stop_on_error"
            }
        }


# ==============================================================================
# AI SETTINGS
# ==============================================================================

class AIProviderConfig(BaseModel):
    """Configuration for a specific AI provider."""
    
    name: str = Field(..., description="Display name")
    provider_type: str = Field(..., description="Provider type (openai, anthropic, etc.)")
    enabled: bool = Field(default=False, description="Whether provider is active")
    role: Literal["primary", "fallback", "inactive"] = Field(
        default="inactive",
        description="Provider role in fallback chain"
    )
    fallback_priority: Optional[int] = Field(
        default=None,
        description="Priority order for fallback providers (1, 2, 3...)"
    )
    api_key: str = Field(default="", description="API key (encrypted in DB)")
    base_url: str = Field(..., description="Provider API endpoint")
    default_model: str = Field(..., description="Default model to use")
    auth_type: Literal["bearer_token", "api_key", "x-api-key", "none"] = Field(
        default="bearer_token",
        description="Authentication type"
    )
    available_models: List[str] = Field(
        default_factory=list,
        description="List of available models"
    )
    max_tokens_limit: int = Field(
        default=4096, 
        gt=0,
        description="Max tokens supported"
    )
    supports_streaming: bool = Field(
        default=True,
        description="Streaming support"
    )
    supports_function_calling: bool = Field(
        default=False,
        description="Function calling support"
    )
    rate_limit_per_minute: int = Field(
        default=60, 
        gt=0,
        description="Rate limit"
    )
    custom_headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom HTTP headers"
    )
    default_temperature: float = Field(
        default=0.7, 
        ge=0.0, 
        le=2.0,
        description="Provider-specific temperature"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "OpenAI",
                "provider_type": "openai",
                "enabled": True,
                "base_url": "https://api.openai.com/v1",
                "default_model": "gpt-4"
            }
        }


class AISettings(BaseModel):
    """AI provider configuration and behavior."""
    
    # Global AI Settings
    enabled: bool = Field(
        default=True,
        description="Enable AI features globally"
    )
    default_provider: str = Field(
        default="openai",
        description="Default AI provider (determined from provider with role='primary')"
    )
    fallback_provider: str = Field(
        default="",  # Empty by default - determined from providers with role='fallback'
        description="Fallback provider if default fails (determined from provider roles)"
    )
    default_temperature: float = Field(
        default=0.7, 
        ge=0.0, 
        le=2.0,
        description="Default sampling temperature"
    )
    default_max_tokens: int = Field(
        default=16384, 
        gt=0,
        description="Default max tokens"
    )
    request_timeout: int = Field(
        default=120,  # 2 minutes - sufficient for vision models with large images
        gt=0,
        description="AI request timeout (seconds)"
    )
    max_retries: int = Field(
        default=3, 
        ge=0,
        description="Max AI request retries"
    )
    retry_delay: float = Field(
        default=1.0, 
        gt=0,
        description="Delay between AI retries (seconds)"
    )
    
    # Providers (nested)
    providers: Dict[str, AIProviderConfig] = Field(
        default_factory=dict,
        description="AI provider configurations"
    )
    
    @validator('default_provider')
    def validate_default_provider(cls, v, values):
        """Ensure default provider exists in providers."""
        # Skip validation during initialization (providers may not be set yet)
        return v
    
    @validator('fallback_provider')
    def validate_fallback_provider(cls, v, values):
        """Ensure fallback provider exists in providers."""
        # Skip validation during initialization
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "default_provider": "openai",
                "default_temperature": 0.7,
                "providers": {
                    "openai": {
                        "name": "OpenAI",
                        "provider_type": "openai",
                        "enabled": True
                    }
                }
            }
        }


# ==============================================================================
# UI SETTINGS
# ==============================================================================

class UISettings(BaseModel):
    """User interface defaults."""
    
    default_theme_mode: Literal["light", "dark", "default"] = Field(
        default="default",
        description="Default theme mode"
    )
    default_grid_size: int = Field(
        default=20, 
        ge=10, 
        le=50,
        description="Canvas grid size (pixels)"
    )
    enable_grid: bool = Field(
        default=True,
        description="Show grid on workflow canvas"
    )
    grid_opacity: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Canvas grid opacity (0.0-1.0)"
    )
    auto_save_enabled: bool = Field(
        default=True,
        description="Enable auto-save for workflows"
    )
    auto_save_delay: int = Field(
        default=1000,
        ge=500,
        le=10000,
        description="Auto-save delay in milliseconds"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "default_theme_mode": "dark",
                "default_grid_size": 20,
                "enable_grid": True,
                "grid_opacity": 0.3,
                "auto_save_enabled": True,
                "auto_save_delay": 1000
            }
        }


# ==============================================================================
# STORAGE SETTINGS
# ==============================================================================

class StorageSettings(BaseModel):
    """Data retention and cleanup policies."""
    
    # Retention
    result_storage_days: int = Field(
        default=30, 
        ge=1, 
        le=365,
        description="Days to keep execution results"
    )
    max_execution_history: int = Field(
        default=100, 
        ge=10, 
        le=10000,
        description="Max execution logs to keep"
    )
    
    # Cleanup Master Switches
    auto_cleanup: bool = Field(
        default=True,
        description="Automatically cleanup old data"
    )
    temp_file_cleanup: bool = Field(
        default=True,
        description="Cleanup temporary files"
    )
    cleanup_on_startup: bool = Field(
        default=False,
        description="Delete all uploads/artifacts/temp files on server restart (dev only, data loss risk!)"
    )
    
    # Uploads (User input files)
    upload_dir: str = Field(
        default="uploads",
        description="Upload storage directory"
    )
    upload_storage_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Days to keep uploaded files"
    )
    uploads_cleanup_interval_hours: int = Field(
        default=24,
        ge=1,
        le=168,  # Max 1 week
        description="Upload cleanup frequency (hours)"
    )
    
    # Artifacts (Generated outputs)
    artifact_dir: str = Field(
        default="artifacts",
        description="Artifact storage directory"
    )
    artifact_ttl_days: int = Field(
        default=7, 
        ge=1, 
        le=365,
        description="Artifact retention (days)"
    )
    artifact_max_bytes: int = Field(
        default=1073741824,  # 1GB
        ge=10485760,  # 10MB
        description="Max artifacts size (bytes)"
    )
    artifact_backend: Literal["fs", "s3", "gcs"] = Field(
        default="fs",
        description="Artifact storage backend"
    )
    artifact_cleanup_interval_hours: int = Field(
        default=6,
        ge=1,
        le=168,  # Max 1 week
        description="Artifact cleanup frequency (hours)"
    )
    
    # Temp Files (Processing internals)
    temp_dir: str = Field(
        default="temp",
        description="Temporary file storage directory"
    )
    temp_cleanup_interval_hours: int = Field(
        default=1,
        ge=1,
        le=24,
        description="Temp file cleanup frequency (hours)"
    )
    temp_file_max_age_hours: int = Field(
        default=1,
        ge=1,
        le=24,
        description="Max age of temp files before deletion (hours)"
    )
    
    # Legacy fields (kept for backward compatibility)
    delayed_cleanup_minutes: int = Field(
        default=60, 
        ge=1, 
        le=1440,
        description="Delayed cleanup window (minutes) - DEPRECATED"
    )
    uploads_cleanup_interval_minutes: int = Field(
        default=60, 
        ge=1, 
        le=1440,
        description="Upload cleanup frequency (minutes) - DEPRECATED, use uploads_cleanup_interval_hours"
    )
    artifact_cleanup_interval_minutes: int = Field(
        default=360, 
        ge=10, 
        le=10080,
        description="Artifact cleanup frequency (minutes) - DEPRECATED, use artifact_cleanup_interval_hours"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "result_storage_days": 30,
                "auto_cleanup": True,
                "artifact_backend": "fs"
            }
        }


# ==============================================================================
# SECURITY SETTINGS
# ==============================================================================

class SecuritySettings(BaseModel):
    """Security and rate limiting settings."""
    
    max_content_length: int = Field(
        default=104857600,  # 100MB
        ge=1048576,  # 1MB minimum
        le=2147483648,  # 2GB maximum
        description="Maximum request body size in bytes. Protects server from large uploads. 1MB = 1048576 bytes, 100MB = 104857600 bytes."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "max_content_length": 104857600
            }
        }


# ==============================================================================
# NETWORK SETTINGS
# ==============================================================================

class NetworkSettings(BaseModel):
    """Network configuration settings."""
    
    cors_origins: List[str] = Field(
        default=["http://localhost:*"],
        description="Allowed CORS origins"
    )
    
    @validator('cors_origins')
    def validate_cors_origins(cls, v):
        """Validate CORS origins format."""
        for origin in v:
            if not origin.startswith(('http://', 'https://', 'ws://', 'wss://')):
                raise ValueError(f"Invalid CORS origin: {origin}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "cors_origins": ["http://localhost:3000", "https://yourdomain.com"]
            }
        }


# ==============================================================================
# INTEGRATIONS SETTINGS
# ==============================================================================

class IntegrationsSettings(BaseModel):
    """Optional third-party integrations."""
    
    # Search APIs (all encrypted)
    search_serper_api_key: str = Field(
        default="",
        description="Serper.dev API key (encrypted)"
    )
    search_bing_api_key: str = Field(
        default="",
        description="Bing Web Search API key (encrypted)"
    )
    search_google_pse_api_key: str = Field(
        default="",
        description="Google Programmable Search API key (encrypted)"
    )
    search_google_pse_cx: str = Field(
        default="",
        description="Google PSE Search Engine ID"
    )
    search_duckduckgo_enabled: bool = Field(
        default=True,
        description="Enable DuckDuckGo search (no key needed)"
    )
    
    # AI Platforms
    huggingface_api_token: str = Field(
        default="",
        description="HuggingFace API token (encrypted)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "search_duckduckgo_enabled": True,
                "search_serper_api_key": ""
            }
        }


# ==============================================================================
# DEVELOPER SETTINGS
# ==============================================================================

class DeveloperSettings(BaseModel):
    """Development and debugging settings."""
    
    enable_dev_mode: bool = Field(
        default=True,
        description="Enable development mode (bypasses authentication). Disable in production."
    )
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode (verbose logging)"
    )
    console_logging: bool = Field(
        default=True,
        description="Log to console"
    )
    error_details: bool = Field(
        default=True,
        description="Include full error details in responses"
    )
    api_timing: bool = Field(
        default=False,
        description="Log API endpoint timing"
    )
    memory_monitoring: bool = Field(
        default=False,
        description="Monitor memory usage"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "debug_mode": False,
                "console_logging": True
            }
        }


# ==============================================================================
# ALL SETTINGS
# ==============================================================================

class AllSettings(BaseModel):
    """Complete application settings."""
    
    execution: ExecutionSettings = Field(default_factory=ExecutionSettings)
    ai: AISettings = Field(default_factory=AISettings)
    ui: UISettings = Field(default_factory=UISettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    network: NetworkSettings = Field(default_factory=NetworkSettings)
    integrations: IntegrationsSettings = Field(default_factory=IntegrationsSettings)
    developer: DeveloperSettings = Field(default_factory=DeveloperSettings)

    class Config:
        json_schema_extra = {
            "example": {
                "execution": {
                    "max_concurrent_nodes": 5
                },
                "ai": {
                    "enabled": True
                }
            }
        }

