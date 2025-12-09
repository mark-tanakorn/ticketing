"""
Unit tests for Settings Pydantic Schemas
"""

import pytest
from pydantic import ValidationError

from app.schemas.settings import (
    ExecutionSettings,
    AISettings,
    AIProviderConfig,
    UISettings,
    StorageSettings,
    SecuritySettings,
    NetworkSettings,
    IntegrationsSettings,
    DeveloperSettings,
    AllSettings,
)


class TestExecutionSettings:
    """Test execution settings validation."""
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        settings = ExecutionSettings()
        
        assert settings.max_concurrent_nodes == 5
        assert settings.default_timeout == 300
        assert settings.error_handling == "stop_on_error"
        assert settings.max_retries == 3
    
    def test_valid_values(self):
        """Test setting valid values."""
        settings = ExecutionSettings(
            max_concurrent_nodes=10,
            default_timeout=600,
            error_handling="continue_on_error"
        )
        
        assert settings.max_concurrent_nodes == 10
        assert settings.default_timeout == 600
        assert settings.error_handling == "continue_on_error"
    
    def test_max_concurrent_nodes_validation(self):
        """Test max_concurrent_nodes validation."""
        # Valid range: 1-50
        ExecutionSettings(max_concurrent_nodes=1)  # Min
        ExecutionSettings(max_concurrent_nodes=50)  # Max
        
        # Invalid: too low
        with pytest.raises(ValidationError):
            ExecutionSettings(max_concurrent_nodes=0)
        
        # Invalid: too high
        with pytest.raises(ValidationError):
            ExecutionSettings(max_concurrent_nodes=51)
    
    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid range: 10-7200
        ExecutionSettings(default_timeout=10)  # Min
        ExecutionSettings(default_timeout=7200)  # Max
        
        # Invalid: too low
        with pytest.raises(ValidationError):
            ExecutionSettings(default_timeout=5)
        
        # Invalid: too high
        with pytest.raises(ValidationError):
            ExecutionSettings(default_timeout=7300)
    
    def test_error_handling_validation(self):
        """Test error_handling enum validation."""
        ExecutionSettings(error_handling="stop_on_error")
        ExecutionSettings(error_handling="continue_on_error")
        
        # Invalid value
        with pytest.raises(ValidationError):
            ExecutionSettings(error_handling="invalid_mode")
    
    def test_retry_delay_validation(self):
        """Test retry_delay validation."""
        # Valid range: 0.1-300.0
        ExecutionSettings(retry_delay=0.1)  # Min
        ExecutionSettings(retry_delay=300.0)  # Max
        
        # Invalid: too low
        with pytest.raises(ValidationError):
            ExecutionSettings(retry_delay=0.05)
        
        # Invalid: too high
        with pytest.raises(ValidationError):
            ExecutionSettings(retry_delay=301.0)


class TestAIProviderConfig:
    """Test AI provider configuration validation."""
    
    def test_valid_provider(self):
        """Test creating a valid provider config."""
        provider = AIProviderConfig(
            name="OpenAI",
            provider_type="openai",
            enabled=True,
            api_key="sk-test123",
            base_url="https://api.openai.com/v1",
            default_model="gpt-4"
        )
        
        assert provider.name == "OpenAI"
        assert provider.enabled is True
        assert provider.api_key == "sk-test123"
    
    def test_default_values(self):
        """Test provider default values."""
        provider = AIProviderConfig(
            name="Test",
            provider_type="openai",
            base_url="https://api.test.com",
            default_model="test-model"
        )
        
        assert provider.enabled is False
        assert provider.api_key == ""
        assert provider.auth_type == "bearer_token"
        assert provider.max_tokens_limit == 4096
        assert provider.supports_streaming is True
    
    def test_temperature_validation(self):
        """Test temperature validation."""
        # Valid range: 0.0-2.0
        AIProviderConfig(
            name="Test",
            provider_type="test",
            base_url="https://test.com",
            default_model="test",
            default_temperature=0.0
        )
        
        AIProviderConfig(
            name="Test",
            provider_type="test",
            base_url="https://test.com",
            default_model="test",
            default_temperature=2.0
        )
        
        # Invalid: too high
        with pytest.raises(ValidationError):
            AIProviderConfig(
                name="Test",
                provider_type="test",
                base_url="https://test.com",
                default_model="test",
                default_temperature=2.1
            )


class TestAISettings:
    """Test AI settings validation."""
    
    def test_default_values(self):
        """Test default AI settings."""
        settings = AISettings()
        
        assert settings.enabled is True
        assert settings.default_provider == "openai"
        assert settings.fallback_provider == ""  # Empty by default - determined from provider roles
        assert settings.default_temperature == 0.7
        assert settings.providers == {}
    
    def test_with_providers(self):
        """Test AI settings with providers."""
        openai_provider = AIProviderConfig(
            name="OpenAI",
            provider_type="openai",
            enabled=True,
            base_url="https://api.openai.com/v1",
            default_model="gpt-4"
        )
        
        settings = AISettings(
            providers={"openai": openai_provider}
        )
        
        assert "openai" in settings.providers
        assert settings.providers["openai"].name == "OpenAI"


class TestUISettings:
    """Test UI settings validation."""
    
    def test_default_values(self):
        """Test default UI settings."""
        settings = UISettings()
        
        assert settings.default_theme_mode == "default"
        assert settings.default_grid_size == 20
        assert settings.enable_grid is True  # Actual attribute name
    
    def test_theme_mode_validation(self):
        """Test theme mode enum validation."""
        UISettings(default_theme_mode="light")
        UISettings(default_theme_mode="dark")
        UISettings(default_theme_mode="default")
        
        # Invalid value
        with pytest.raises(ValidationError):
            UISettings(default_theme_mode="invalid")
    
    def test_grid_size_validation(self):
        """Test grid size validation."""
        # Valid range: 10-50
        UISettings(default_grid_size=10)  # Min
        UISettings(default_grid_size=50)  # Max
        
        # Invalid: too low
        with pytest.raises(ValidationError):
            UISettings(default_grid_size=5)
        
        # Invalid: too high
        with pytest.raises(ValidationError):
            UISettings(default_grid_size=60)


class TestStorageSettings:
    """Test storage settings validation."""
    
    def test_default_values(self):
        """Test default storage settings."""
        settings = StorageSettings()
        
        assert settings.result_storage_days == 30
        assert settings.auto_cleanup is True
        assert settings.artifact_backend == "fs"
    
    def test_artifact_backend_validation(self):
        """Test artifact backend enum validation."""
        StorageSettings(artifact_backend="fs")
        StorageSettings(artifact_backend="s3")
        StorageSettings(artifact_backend="gcs")
        
        # Invalid value
        with pytest.raises(ValidationError):
            StorageSettings(artifact_backend="invalid")
    
    def test_retention_validation(self):
        """Test retention days validation."""
        # Valid range: 1-365
        StorageSettings(result_storage_days=1)  # Min
        StorageSettings(result_storage_days=365)  # Max
        
        # Invalid: too low
        with pytest.raises(ValidationError):
            StorageSettings(result_storage_days=0)
        
        # Invalid: too high
        with pytest.raises(ValidationError):
            StorageSettings(result_storage_days=400)


class TestNetworkSettings:
    """Test network settings validation."""
    
    def test_default_values(self):
        """Test default network settings."""
        settings = NetworkSettings()
        
        assert settings.cors_origins == ["http://localhost:*"]
    
    def test_valid_cors_origins(self):
        """Test valid CORS origins."""
        settings = NetworkSettings(
            cors_origins=[
                "http://localhost:3000",
                "https://example.com",
                "ws://websocket.com"
            ]
        )
        
        assert len(settings.cors_origins) == 3
    
    def test_invalid_cors_origins(self):
        """Test invalid CORS origins."""
        # Invalid: missing protocol
        with pytest.raises(ValidationError):
            NetworkSettings(cors_origins=["localhost:3000"])
        
        # Invalid: invalid protocol
        with pytest.raises(ValidationError):
            NetworkSettings(cors_origins=["ftp://example.com"])


class TestSecuritySettings:
    """Test security settings validation."""
    
    def test_default_values(self):
        """Test default security settings."""
        settings = SecuritySettings()
        
        assert settings.max_content_length == 104857600  # 100MB
    
    def test_content_length_validation(self):
        """Test max_content_length validation."""
        # Valid range: 1MB-2GB
        SecuritySettings(max_content_length=1048576)  # Min: 1MB
        SecuritySettings(max_content_length=2147483648)  # Max: 2GB
        
        # Invalid: too low
        with pytest.raises(ValidationError):
            SecuritySettings(max_content_length=1000)
        
        # Invalid: too high
        with pytest.raises(ValidationError):
            SecuritySettings(max_content_length=3000000000)


class TestIntegrationsSettings:
    """Test integrations settings validation."""
    
    def test_default_values(self):
        """Test default integrations settings."""
        settings = IntegrationsSettings()
        
        assert settings.search_serper_api_key == ""
        assert settings.search_duckduckgo_enabled is True
        assert settings.huggingface_api_token == ""


class TestDeveloperSettings:
    """Test developer settings validation."""
    
    def test_default_values(self):
        """Test default developer settings."""
        settings = DeveloperSettings()
        
        assert settings.debug_mode is False
        assert settings.console_logging is True
        assert settings.error_details is True
        assert settings.api_timing is False


class TestAllSettings:
    """Test complete settings model."""
    
    def test_default_values(self):
        """Test that all settings namespaces have defaults."""
        settings = AllSettings()
        
        assert isinstance(settings.execution, ExecutionSettings)
        assert isinstance(settings.ai, AISettings)
        assert isinstance(settings.ui, UISettings)
        assert isinstance(settings.storage, StorageSettings)
        assert isinstance(settings.security, SecuritySettings)
        assert isinstance(settings.network, NetworkSettings)
        assert isinstance(settings.integrations, IntegrationsSettings)
        assert isinstance(settings.developer, DeveloperSettings)
    
    def test_model_dump(self):
        """Test converting to dictionary."""
        settings = AllSettings()
        data = settings.model_dump()
        
        assert "execution" in data
        assert "ai" in data
        assert "ui" in data
        assert "storage" in data
        assert "security" in data
        assert "network" in data
        assert "integrations" in data
        assert "developer" in data
    
    def test_custom_values(self):
        """Test creating settings with custom values."""
        execution = ExecutionSettings(max_concurrent_nodes=10)
        ui = UISettings(default_theme_mode="dark")
        
        settings = AllSettings(
            execution=execution,
            ui=ui
        )
        
        assert settings.execution.max_concurrent_nodes == 10
        assert settings.ui.default_theme_mode == "dark"


