
"""
Configuration Management using Pydantic Settings


This file handles ONLY infrastructure settings and secrets from environment variables.
Application behavior settings (timeouts, UI preferences, etc.) are stored in the database.


Environment Variables (All Optional - Have Defaults):
    - SECRET_KEY: Application signing key (default provided for dev)
    - ENCRYPTION_KEY: Database encryption key (default provided for dev)
    - DATABASE_URL: Database connection (defaults to SQLite)
   
Recommended for Production:
    - Set SECRET_KEY and ENCRYPTION_KEY in .env file
    - Store AI API keys in database (encrypted)
    - Store OAuth credentials in database (encrypted)
   
Note: AI provider keys and OAuth credentials should be stored in the database
      for better security and runtime configurability. They are kept here as
      optional fallbacks for simple deployments.
"""


from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


def get_default_cors_origins(backend_port: int = 5000, frontend_port: int = 3000) -> List[str]:
    """Generate default CORS origins based on configured ports."""
    return [
        f"http://localhost:{frontend_port}",
        f"http://localhost:{frontend_port + 1}",  # For potential dev server
        f"http://localhost:{backend_port}",
        f"http://127.0.0.1:{frontend_port}",
        f"http://127.0.0.1:{backend_port}",
    ]



class Settings(BaseSettings):
    """
    Infrastructure and secrets configuration.
   
    Loaded from environment variables only. Application behavior settings
    are stored in the database via the settings manager.
    """


    # Project Info
    PROJECT_NAME: str = "TAV Engine"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # Port Configuration
    BACKEND_PORT: int = Field(
        default=5000,
        env="BACKEND_PORT",
        description="Port for the backend API server"
    )
    FRONTEND_PORT: int = Field(
        default=3000,
        env="FRONTEND_PORT",
        description="Port for the frontend server"
    )
   
    # Frontend URL (for review links, webhooks, etc.)
    BASE_URL: str = Field(
        default="",  # Empty = auto-detect from FRONTEND_PORT
        env="BASE_URL",
        description="Frontend base URL for generating review links and callbacks"
    )
    
    @field_validator("BASE_URL", mode="after")
    @classmethod
    def set_default_base_url(cls, v, info):
        """Set default BASE_URL based on FRONTEND_PORT if not provided."""
        if not v:
            # Get frontend port from values or default
            frontend_port = info.data.get("FRONTEND_PORT", 3000)
            return f"http://localhost:{frontend_port}"
        return v
   
    # Development Mode (bypasses authentication)
    # ⚠️ WARNING: Set to False in production!
    ENABLE_DEV_MODE: bool = Field(
        default=True,
        env="ENABLE_DEV_MODE",
        description="Enable development mode (bypasses authentication). Set to False in production."
    )


    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production-min-32-chars",
        env="SECRET_KEY"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")


    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=[],  # Empty = auto-generate from ports
        env="CORS_ORIGINS",
    )
   
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON string or list."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If not valid JSON, treat as comma-separated string
                return [origin.strip() for origin in v.split(',')]
        return v
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins with dynamic port defaults if not explicitly set."""
        if self.CORS_ORIGINS:
            return self.CORS_ORIGINS
        # Generate defaults based on configured ports
        return [
            f"http://localhost:{self.FRONTEND_PORT}",
            f"http://localhost:{self.FRONTEND_PORT + 1}",
            f"http://localhost:{self.BACKEND_PORT}",
            f"http://127.0.0.1:{self.FRONTEND_PORT}",
            f"http://127.0.0.1:{self.BACKEND_PORT}",
        ]


    # Database - Support both SQLite and PostgreSQL
    DATABASE_URL: str = Field(
        default="sqlite:///./data/tav_engine.db",
        env="DATABASE_URL"
    )
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=40, env="DB_MAX_OVERFLOW")
   
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL is valid."""
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")
        # Support SQLite and PostgreSQL (including async variants)
        if not (v.startswith("sqlite:///") or 
                v.startswith("postgresql://") or 
                v.startswith("postgresql+asyncpg://")):
            raise ValueError(
                "DATABASE_URL must start with 'sqlite:///', 'postgresql://', or 'postgresql+asyncpg://'"
            )
        return v


    # Redis (Optional - for caching and Celery)
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    REDIS_POOL_SIZE: int = Field(default=10, env="REDIS_POOL_SIZE")


    # Celery (Optional - for background tasks)
    CELERY_BROKER_URL: Optional[str] = Field(default=None, env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(default=None, env="CELERY_RESULT_BACKEND")


    # Security & Encryption
    ENCRYPTION_KEY: str = Field(
        default="dev-encryption-key-change-prod-32b",
        env="ENCRYPTION_KEY"
    )
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")


    # AI Provider Keys (Optional - can be stored encrypted in DB)
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    DEEPSEEK_API_KEY: Optional[str] = Field(default=None, env="DEEPSEEK_API_KEY")
    GOOGLE_API_KEY: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")


    # OAuth Credentials (Optional - can be stored encrypted in DB)
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_SECRET")
    MICROSOFT_CLIENT_ID: Optional[str] = Field(default=None, env="MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET: Optional[str] = Field(default=None, env="MICROSOFT_CLIENT_SECRET")
    MICROSOFT_TENANT_ID: Optional[str] = Field(default="common", env="MICROSOFT_TENANT_ID")


    # Storage (Optional - defaults to local filesystem)
    STORAGE_BACKEND: str = Field(default="local", env="STORAGE_BACKEND")
    S3_BUCKET: Optional[str] = Field(default=None, env="S3_BUCKET")
    S3_REGION: Optional[str] = Field(default=None, env="S3_REGION")
    S3_ACCESS_KEY: Optional[str] = Field(default=None, env="S3_ACCESS_KEY")
    S3_SECRET_KEY: Optional[str] = Field(default=None, env="S3_SECRET_KEY")


    # Observability
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    ENABLE_TRACING: bool = Field(default=False, env="ENABLE_TRACING")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True




# Global settings instance
settings = Settings()


