"""
AI Provider Registry

Central registry for AI provider clients.
"""

from typing import Type, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for AI provider client classes"""

    def __init__(self):
        self.providers: Dict[str, Type] = {}
        logger.info("🤖 Provider Registry initialized")

    def register_provider(self, name: str, client_class: Type) -> None:
        """
        Register a provider client class.
        
        Args:
            name: Provider name (e.g., 'openai', 'anthropic')
            client_class: Provider client class
        """
        self.providers[name] = client_class
        logger.debug(f"📝 Registered provider: {name}")

    def get_client_class(self, name: str) -> Optional[Type]:
        """
        Get a provider client class by name.
        
        Args:
            name: Provider name
            
        Returns:
            Provider client class or None if not found
        """
        return self.providers.get(name)

    def list_providers(self) -> list:
        """Get list of registered provider names"""
        return list(self.providers.keys())

    def is_registered(self, name: str) -> bool:
        """Check if a provider is registered"""
        return name in self.providers


# Global registry instance
_provider_registry: Optional[ProviderRegistry] = None


def get_provider_registry() -> ProviderRegistry:
    """Get the global provider registry instance"""
    global _provider_registry
    if _provider_registry is None:
        _provider_registry = ProviderRegistry()
    return _provider_registry
