"""
Settings Manager

High-level API for managing application settings with type safety and validation.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.database.repositories.settings import SettingsRepository
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
from app.security.encryption import encrypt_value, decrypt_value

logger = logging.getLogger(__name__)


class SettingsManager:
    """
    High-level settings manager with type safety and validation.
    
    Provides validated access to all application settings stored in database.
    """
    
    # Fields that should be encrypted in database
    ENCRYPTED_FIELDS = {
        "ai.providers.*.api_key",
        "integrations.search_serper_api_key",
        "integrations.search_bing_api_key",
        "integrations.search_google_pse_api_key",
        "integrations.huggingface_api_token",
    }
    
    def __init__(self, db: Session):
        """
        Initialize settings manager.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.repo = SettingsRepository(db)
    
    # ==========================================================================
    # EXECUTION SETTINGS
    # ==========================================================================
    
    def get_execution_settings(self) -> ExecutionSettings:
        """
        Get execution settings with validation.
        
        Returns:
            ExecutionSettings: Validated execution settings
        """
        data = self.repo.get_namespace("execution")
        return ExecutionSettings(**data) if data else ExecutionSettings()
    
    def update_execution_settings(
        self, 
        settings: ExecutionSettings, 
        updated_by: str = "system"
    ) -> ExecutionSettings:
        """
        Update execution settings.
        
        Args:
            settings: New execution settings
            updated_by: Who is making the update
            
        Returns:
            ExecutionSettings: Updated settings
        """
        settings_dict = settings.model_dump()
        
        for key, value in settings_dict.items():
            self.repo.set("execution", key, value, updated_by)
        
        logger.info(f"Updated execution settings (by: {updated_by})")
        return self.get_execution_settings()
    
    # ==========================================================================
    # AI SETTINGS
    # ==========================================================================
    
    def get_ai_settings(self) -> AISettings:
        """
        Get AI settings with validation and decryption.
        
        Returns:
            AISettings: Validated AI settings with decrypted keys
        """
        data = self.repo.get_namespace("ai")
        
        if not data:
            return AISettings()
        
        # Decrypt provider API keys
        if "providers" in data and isinstance(data["providers"], dict):
            for provider_name, provider_data in data["providers"].items():
                if "api_key" in provider_data and provider_data["api_key"]:
                    try:
                        provider_data["api_key"] = decrypt_value(provider_data["api_key"])
                    except Exception as e:
                        logger.warning(f"Failed to decrypt API key for {provider_name}: {e}")
                        provider_data["api_key"] = ""
        
        return AISettings(**data)
    
    def update_ai_settings(
        self, 
        settings: AISettings, 
        updated_by: str = "system"
    ) -> AISettings:
        """
        Update AI settings with encryption of sensitive fields.
        
        Args:
            settings: New AI settings
            updated_by: Who is making the update
            
        Returns:
            AISettings: Updated settings
        """
        settings_dict = settings.model_dump()
        
        # Encrypt provider API keys
        if "providers" in settings_dict and isinstance(settings_dict["providers"], dict):
            for provider_name, provider_data in settings_dict["providers"].items():
                if "api_key" in provider_data and provider_data["api_key"]:
                    try:
                        provider_data["api_key"] = encrypt_value(provider_data["api_key"])
                    except Exception as e:
                        logger.error(f"Failed to encrypt API key for {provider_name}: {e}")
        
        # Save each field
        for key, value in settings_dict.items():
            self.repo.set("ai", key, value, updated_by)
        
        logger.info(f"Updated AI settings (by: {updated_by})")
        return self.get_ai_settings()
    
    def get_ai_provider(self, provider_name: str) -> Optional[AIProviderConfig]:
        """
        Get a specific AI provider configuration.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            AIProviderConfig or None if not found
        """
        ai_settings = self.get_ai_settings()
        return ai_settings.providers.get(provider_name)
    
    def add_ai_provider(
        self, 
        provider_name: str, 
        provider_config: AIProviderConfig,
        updated_by: str = "system"
    ) -> AISettings:
        """
        Add or update an AI provider.
        
        Args:
            provider_name: Name of the provider
            provider_config: Provider configuration
            updated_by: Who is making the update
            
        Returns:
            AISettings: Updated AI settings
        """
        ai_settings = self.get_ai_settings()
        ai_settings.providers[provider_name] = provider_config
        return self.update_ai_settings(ai_settings, updated_by)
    
    def remove_ai_provider(
        self, 
        provider_name: str,
        updated_by: str = "system"
    ) -> AISettings:
        """
        Remove an AI provider.
        
        Args:
            provider_name: Name of the provider to remove
            updated_by: Who is making the update
            
        Returns:
            AISettings: Updated AI settings
        """
        ai_settings = self.get_ai_settings()
        if provider_name in ai_settings.providers:
            del ai_settings.providers[provider_name]
        return self.update_ai_settings(ai_settings, updated_by)
    
    # ==========================================================================
    # UI SETTINGS
    # ==========================================================================
    
    def get_ui_settings(self) -> UISettings:
        """
        Get UI settings with validation.
        
        Returns:
            UISettings: Validated UI settings
        """
        data = self.repo.get_namespace("ui")
        return UISettings(**data) if data else UISettings()
    
    def update_ui_settings(
        self, 
        settings: UISettings, 
        updated_by: str = "system"
    ) -> UISettings:
        """
        Update UI settings.
        
        Args:
            settings: New UI settings
            updated_by: Who is making the update
            
        Returns:
            UISettings: Updated settings
        """
        settings_dict = settings.model_dump()
        
        for key, value in settings_dict.items():
            self.repo.set("ui", key, value, updated_by)
        
        logger.info(f"Updated UI settings (by: {updated_by})")
        return self.get_ui_settings()
    
    # ==========================================================================
    # STORAGE SETTINGS
    # ==========================================================================
    
    def get_storage_settings(self) -> StorageSettings:
        """
        Get storage settings with validation.
        
        Returns:
            StorageSettings: Validated storage settings
        """
        data = self.repo.get_namespace("storage")
        return StorageSettings(**data) if data else StorageSettings()
    
    def update_storage_settings(
        self, 
        settings: StorageSettings, 
        updated_by: str = "system"
    ) -> StorageSettings:
        """
        Update storage settings.
        
        Args:
            settings: New storage settings
            updated_by: Who is making the update
            
        Returns:
            StorageSettings: Updated settings
        """
        settings_dict = settings.model_dump()
        
        for key, value in settings_dict.items():
            self.repo.set("storage", key, value, updated_by)
        
        logger.info(f"Updated storage settings (by: {updated_by})")
        return self.get_storage_settings()
    
    # ==========================================================================
    # SECURITY SETTINGS
    # ==========================================================================
    
    def get_security_settings(self) -> SecuritySettings:
        """
        Get security settings with validation.
        
        Returns:
            SecuritySettings: Validated security settings
        """
        data = self.repo.get_namespace("security")
        return SecuritySettings(**data) if data else SecuritySettings()
    
    def update_security_settings(
        self, 
        settings: SecuritySettings, 
        updated_by: str = "system"
    ) -> SecuritySettings:
        """
        Update security settings.
        
        Args:
            settings: New security settings
            updated_by: Who is making the update
            
        Returns:
            SecuritySettings: Updated settings
        """
        settings_dict = settings.model_dump()
        
        for key, value in settings_dict.items():
            self.repo.set("security", key, value, updated_by)
        
        logger.info(f"Updated security settings (by: {updated_by})")
        return self.get_security_settings()
    
    # ==========================================================================
    # NETWORK SETTINGS
    # ==========================================================================
    
    def get_network_settings(self) -> NetworkSettings:
        """
        Get network settings with validation.
        
        Returns:
            NetworkSettings: Validated network settings
        """
        data = self.repo.get_namespace("network")
        return NetworkSettings(**data) if data else NetworkSettings()
    
    def update_network_settings(
        self, 
        settings: NetworkSettings, 
        updated_by: str = "system"
    ) -> NetworkSettings:
        """
        Update network settings.
        
        Args:
            settings: New network settings
            updated_by: Who is making the update
            
        Returns:
            NetworkSettings: Updated settings
        """
        settings_dict = settings.model_dump()
        
        for key, value in settings_dict.items():
            self.repo.set("network", key, value, updated_by)
        
        logger.info(f"Updated network settings (by: {updated_by})")
        return self.get_network_settings()
    
    # ==========================================================================
    # INTEGRATIONS SETTINGS
    # ==========================================================================
    
    def get_integrations_settings(self) -> IntegrationsSettings:
        """
        Get integrations settings with validation and decryption.
        
        Returns:
            IntegrationsSettings: Validated integrations settings
        """
        data = self.repo.get_namespace("integrations")
        
        if not data:
            return IntegrationsSettings()
        
        # Decrypt API keys
        encrypted_keys = [
            "search_serper_api_key",
            "search_bing_api_key", 
            "search_google_pse_api_key",
            "huggingface_api_token"
        ]
        
        for key in encrypted_keys:
            if key in data and data[key]:
                try:
                    data[key] = decrypt_value(data[key])
                except Exception as e:
                    logger.warning(f"Failed to decrypt {key}: {e}")
                    data[key] = ""
        
        return IntegrationsSettings(**data)
    
    def update_integrations_settings(
        self, 
        settings: IntegrationsSettings, 
        updated_by: str = "system"
    ) -> IntegrationsSettings:
        """
        Update integrations settings with encryption of sensitive fields.
        
        Args:
            settings: New integrations settings
            updated_by: Who is making the update
            
        Returns:
            IntegrationsSettings: Updated settings
        """
        settings_dict = settings.model_dump()
        
        # Encrypt API keys
        encrypted_keys = [
            "search_serper_api_key",
            "search_bing_api_key",
            "search_google_pse_api_key",
            "huggingface_api_token"
        ]
        
        for key in encrypted_keys:
            if key in settings_dict and settings_dict[key]:
                try:
                    settings_dict[key] = encrypt_value(settings_dict[key])
                except Exception as e:
                    logger.error(f"Failed to encrypt {key}: {e}")
        
        # Save each field
        for key, value in settings_dict.items():
            self.repo.set("integrations", key, value, updated_by)
        
        logger.info(f"Updated integrations settings (by: {updated_by})")
        return self.get_integrations_settings()
    
    # ==========================================================================
    # DEVELOPER SETTINGS
    # ==========================================================================
    
    def get_developer_settings(self) -> DeveloperSettings:
        """
        Get developer settings with validation.
        
        Returns:
            DeveloperSettings: Validated developer settings
        """
        data = self.repo.get_namespace("developer")
        return DeveloperSettings(**data) if data else DeveloperSettings()
    
    def update_developer_settings(
        self, 
        settings: DeveloperSettings, 
        updated_by: str = "system"
    ) -> DeveloperSettings:
        """
        Update developer settings.
        
        Args:
            settings: New developer settings
            updated_by: Who is making the update
            
        Returns:
            DeveloperSettings: Updated settings
        """
        settings_dict = settings.model_dump()
        
        for key, value in settings_dict.items():
            self.repo.set("developer", key, value, updated_by)
        
        logger.info(f"Updated developer settings (by: {updated_by})")
        return self.get_developer_settings()
    
    # ==========================================================================
    # ALL SETTINGS
    # ==========================================================================
    
    def get_all_settings(self) -> AllSettings:
        """
        Get all settings with validation.
        
        Returns:
            AllSettings: All application settings
        """
        return AllSettings(
            execution=self.get_execution_settings(),
            ai=self.get_ai_settings(),
            ui=self.get_ui_settings(),
            storage=self.get_storage_settings(),
            security=self.get_security_settings(),
            network=self.get_network_settings(),
            integrations=self.get_integrations_settings(),
            developer=self.get_developer_settings(),
        )
    
    def initialize_defaults(self, updated_by: str = "system") -> AllSettings:
        """
        Initialize all settings with default values if not already set.
        
        Args:
            updated_by: Who is initializing
            
        Returns:
            AllSettings: Initialized settings
        """
        logger.info("Initializing default settings...")
        
        # Check if any settings exist
        all_settings_data = self.repo.get_all()
        
        if not all_settings_data:
            # No settings exist, create defaults
            defaults = AllSettings()
            
            # Save each namespace
            self.update_execution_settings(defaults.execution, updated_by)
            self.update_ai_settings(defaults.ai, updated_by)
            self.update_ui_settings(defaults.ui, updated_by)
            self.update_storage_settings(defaults.storage, updated_by)
            self.update_security_settings(defaults.security, updated_by)
            self.update_network_settings(defaults.network, updated_by)
            self.update_integrations_settings(defaults.integrations, updated_by)
            self.update_developer_settings(defaults.developer, updated_by)
            
            logger.info("✅ Default settings initialized")
        else:
            logger.info("ℹ️  Settings already exist, skipping initialization")
        
        return self.get_all_settings()


# ==============================================================================
# GLOBAL INSTANCE
# ==============================================================================

_settings_manager: Optional[SettingsManager] = None


def get_settings_manager(db: Session) -> SettingsManager:
    """
    Get settings manager instance.
    
    Args:
        db: Database session
        
    Returns:
        SettingsManager: Settings manager instance
    """
    return SettingsManager(db)


def init_settings_manager(db: Session) -> SettingsManager:
    """
    Initialize settings manager with default values.
    
    Args:
        db: Database session
        
    Returns:
        SettingsManager: Initialized settings manager
    """
    manager = SettingsManager(db)
    manager.initialize_defaults()
    return manager


