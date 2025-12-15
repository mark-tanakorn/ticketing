"""
Unit tests for Settings Manager
"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.core.config.manager import SettingsManager, get_settings_manager, init_settings_manager
from app.schemas.settings import (
    ExecutionSettings,
    AISettings,
    AIProviderConfig,
    UISettings,
    StorageSettings,
)


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def manager(db_session):
    """Create a settings manager."""
    return SettingsManager(db_session)


class TestSettingsManager:
    """Test settings manager functionality."""
    
    def test_get_execution_settings_default(self, manager):
        """Test getting default execution settings."""
        settings = manager.get_execution_settings()
        
        assert isinstance(settings, ExecutionSettings)
        assert settings.max_concurrent_nodes == 5
        assert settings.default_timeout == 300
    
    def test_update_execution_settings(self, manager):
        """Test updating execution settings."""
        new_settings = ExecutionSettings(
            max_concurrent_nodes=10,
            default_timeout=600
        )
        
        updated = manager.update_execution_settings(new_settings, updated_by="test_user")
        
        assert updated.max_concurrent_nodes == 10
        assert updated.default_timeout == 600
        
        # Verify persistence
        retrieved = manager.get_execution_settings()
        assert retrieved.max_concurrent_nodes == 10
    
    def test_get_ai_settings_default(self, manager):
        """Test getting default AI settings."""
        settings = manager.get_ai_settings()
        
        assert isinstance(settings, AISettings)
        assert settings.enabled is True
        assert settings.default_provider == "openai"
        assert settings.providers == {}
    
    def test_update_ai_settings(self, manager):
        """Test updating AI settings."""
        new_settings = AISettings(
            enabled=True,
            default_provider="anthropic",
            default_temperature=0.8
        )
        
        updated = manager.update_ai_settings(new_settings, updated_by="test_user")
        
        assert updated.default_provider == "anthropic"
        assert updated.default_temperature == 0.8
    
    @patch('app.core.config.manager.encrypt_value')
    @patch('app.core.config.manager.decrypt_value')
    def test_ai_api_key_encryption(self, mock_decrypt, mock_encrypt, manager):
        """Test that AI API keys are encrypted/decrypted."""
        mock_encrypt.return_value = "encrypted_key"
        mock_decrypt.return_value = "decrypted_key"
        
        # Create provider with API key
        provider = AIProviderConfig(
            name="OpenAI",
            provider_type="openai",
            enabled=True,
            api_key="sk-test123",
            base_url="https://api.openai.com/v1",
            default_model="gpt-4"
        )
        
        ai_settings = AISettings(
            providers={"openai": provider}
        )
        
        # Update settings (should encrypt)
        manager.update_ai_settings(ai_settings)
        
        # Verify encrypt was called
        mock_encrypt.assert_called_once_with("sk-test123")
        
        # Get settings (should decrypt)
        retrieved = manager.get_ai_settings()
        
        # Verify decrypt was called
        assert mock_decrypt.called
    
    def test_add_ai_provider(self, manager):
        """Test adding an AI provider."""
        provider = AIProviderConfig(
            name="Test Provider",
            provider_type="openai",
            enabled=True,
            base_url="https://api.test.com",
            default_model="test-model"
        )
        
        updated = manager.add_ai_provider("test", provider, updated_by="admin")
        
        assert "test" in updated.providers
        assert updated.providers["test"].name == "Test Provider"
        
        # Verify persistence
        provider_config = manager.get_ai_provider("test")
        assert provider_config is not None
        assert provider_config.name == "Test Provider"
    
    def test_remove_ai_provider(self, manager):
        """Test removing an AI provider."""
        # Add a provider first
        provider = AIProviderConfig(
            name="Test",
            provider_type="openai",
            base_url="https://test.com",
            default_model="test"
        )
        manager.add_ai_provider("test", provider)
        
        # Remove it
        updated = manager.remove_ai_provider("test", updated_by="admin")
        
        assert "test" not in updated.providers
        
        # Verify it's gone
        provider_config = manager.get_ai_provider("test")
        assert provider_config is None
    
    def test_get_ui_settings_default(self, manager):
        """Test getting default UI settings."""
        settings = manager.get_ui_settings()
        
        assert isinstance(settings, UISettings)
        assert settings.default_theme_mode == "default"
        assert settings.default_grid_size == 20
    
    def test_update_ui_settings(self, manager):
        """Test updating UI settings."""
        new_settings = UISettings(
            default_theme_mode="dark",
            default_grid_size=25
        )
        
        updated = manager.update_ui_settings(new_settings, updated_by="user")
        
        assert updated.default_theme_mode == "dark"
        assert updated.default_grid_size == 25
    
    def test_get_storage_settings_default(self, manager):
        """Test getting default storage settings."""
        settings = manager.get_storage_settings()
        
        assert isinstance(settings, StorageSettings)
        assert settings.result_storage_days == 30
        assert settings.auto_cleanup is True
    
    def test_update_storage_settings(self, manager):
        """Test updating storage settings."""
        new_settings = StorageSettings(
            result_storage_days=60,
            auto_cleanup=False
        )
        
        updated = manager.update_storage_settings(new_settings, updated_by="admin")
        
        assert updated.result_storage_days == 60
        assert updated.auto_cleanup is False
    
    @patch('app.core.config.manager.encrypt_value')
    @patch('app.core.config.manager.decrypt_value')
    def test_integrations_encryption(self, mock_decrypt, mock_encrypt, manager):
        """Test that integration API keys are encrypted/decrypted."""
        mock_encrypt.return_value = "encrypted_key"
        mock_decrypt.return_value = "decrypted_key"
        
        from app.schemas.settings import IntegrationsSettings
        
        integrations = IntegrationsSettings(
            search_serper_api_key="test_key_123"
        )
        
        # Update (should encrypt)
        manager.update_integrations_settings(integrations)
        
        # Verify encrypt was called
        mock_encrypt.assert_called()
        
        # Get (should decrypt)
        retrieved = manager.get_integrations_settings()
        
        # Verify decrypt was called
        assert mock_decrypt.called
    
    def test_get_all_settings(self, manager):
        """Test getting all settings at once."""
        all_settings = manager.get_all_settings()
        
        assert all_settings.execution is not None
        assert all_settings.ai is not None
        assert all_settings.ui is not None
        assert all_settings.storage is not None
        assert all_settings.security is not None
        assert all_settings.network is not None
        assert all_settings.integrations is not None
        assert all_settings.developer is not None
    
    def test_initialize_defaults(self, manager):
        """Test initializing default settings."""
        all_settings = manager.initialize_defaults(updated_by="system")
        
        # Verify all namespaces are initialized
        assert all_settings.execution.max_concurrent_nodes == 5
        assert all_settings.ai.enabled is True
        assert all_settings.ui.default_grid_size == 20
        
        # Verify persistence
        execution = manager.get_execution_settings()
        assert execution.max_concurrent_nodes == 5
    
    def test_initialize_defaults_idempotent(self, manager):
        """Test that initializing defaults twice doesn't duplicate."""
        # Initialize once
        manager.initialize_defaults()
        
        # Update a value
        exec_settings = manager.get_execution_settings()
        exec_settings.max_concurrent_nodes = 10
        manager.update_execution_settings(exec_settings)
        
        # Initialize again (should not overwrite)
        manager.initialize_defaults()
        
        # Value should still be 10, not reset to default
        exec_settings = manager.get_execution_settings()
        assert exec_settings.max_concurrent_nodes == 10


class TestSettingsManagerFactories:
    """Test factory functions for settings manager."""
    
    def test_get_settings_manager(self, db_session):
        """Test getting a settings manager instance."""
        manager = get_settings_manager(db_session)
        
        assert isinstance(manager, SettingsManager)
        assert manager.db == db_session
    
    def test_init_settings_manager(self, db_session):
        """Test initializing settings manager with defaults."""
        manager = init_settings_manager(db_session)
        
        assert isinstance(manager, SettingsManager)
        
        # Verify defaults were initialized
        settings = manager.get_execution_settings()
        assert settings.max_concurrent_nodes == 5


