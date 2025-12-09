"""
AI Provider Management API Endpoints

Handles AI provider configuration, validation, and model listing.
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user_smart, get_user_identifier
from app.database.models.user import User
from app.core.config.manager import SettingsManager
from app.schemas.settings import AISettings, AIProviderConfig
from app.core.ai.registry import get_provider_registry

# Import for validation
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# PROVIDER METADATA (Single source of truth)
# ==============================================================================

PROVIDER_METADATA = {
    "openai": {
        "name": "openai",
        "display_name": "OpenAI",
        "description": "GPT-4, GPT-3.5, and other OpenAI models",
        "default_base_url": "https://api.openai.com/v1",
        "auth_type": "bearer_token",
        "requires_api_key": True,
        "supports_streaming": True,
        "supports_function_calling": True,
        "default_models": [
            {"id": "gpt-5", "name": "GPT-5 (Latest 2025)", "recommended": True},
            {"id": "gpt-5-mini", "name": "GPT-5 Mini (Fast & Cheap)", "recommended": True},
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
            {"id": "gpt-4", "name": "GPT-4"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
        ],
        "default_model": "gpt-5",
        "max_tokens": 4096,
        "icon": "🤖",
        "category": "popular",
        "documentation_url": "https://platform.openai.com/docs",
    },
    "anthropic": {
        "name": "anthropic",
        "display_name": "Anthropic",
        "description": "Claude 3.5 Sonnet, Opus, and Haiku models",
        "default_base_url": "https://api.anthropic.com/v1",
        "auth_type": "x-api-key",
        "requires_api_key": True,
        "supports_streaming": True,
        "supports_function_calling": False,
        "default_models": [
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet (Latest)", "recommended": True},
            {"id": "claude-3-5-sonnet-20240620", "name": "Claude 3.5 Sonnet (June)"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus (Powerful)"},
            {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet"},
            {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku (Fast)"},
        ],
        "default_model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4096,
        "icon": "🧠",
        "category": "popular",
        "documentation_url": "https://docs.anthropic.com/",
    },
    "deepseek": {
        "name": "deepseek",
        "display_name": "DeepSeek",
        "description": "DeepSeek Chat and Coder models (Very cheap!)",
        "default_base_url": "https://api.deepseek.com/v1",
        "auth_type": "bearer_token",
        "requires_api_key": True,
        "supports_streaming": True,
        "supports_function_calling": True,
        "default_models": [
            {"id": "deepseek-chat", "name": "DeepSeek Chat", "recommended": True},
            {"id": "deepseek-coder", "name": "DeepSeek Coder"},
        ],
        "default_model": "deepseek-chat",
        "max_tokens": 4096,
        "icon": "🔍",
        "category": "popular",
        "documentation_url": "https://platform.deepseek.com/",
    },
    "local": {
        "name": "local",
        "display_name": "Local (Ollama)",
        "description": "Self-hosted Ollama models (Llama, Mistral, etc.) - 100% FREE!",
        "default_base_url": "http://localhost:11434",
        "auth_type": "none",
        "requires_api_key": False,
        "supports_streaming": True,
        "supports_function_calling": False,
        "default_models": [
            {"id": "llama3", "name": "Llama 3", "recommended": True},
            {"id": "mistral", "name": "Mistral"},
            {"id": "codellama", "name": "Code Llama"},
            {"id": "phi", "name": "Phi"},
        ],
        "default_model": "llama3",
        "max_tokens": 2048,
        "icon": "🏠",
        "category": "popular",
        "documentation_url": "https://ollama.ai/",
    },
    "google": {
        "name": "google",
        "display_name": "Google AI",
        "description": "Gemini Pro, Flash, and other Google models",
        "default_base_url": "https://generativelanguage.googleapis.com/v1",
        "auth_type": "bearer_token",
        "requires_api_key": True,
        "supports_streaming": True,
        "supports_function_calling": True,
        "default_models": [
            {"id": "gemini-3-flash", "name": "Gemini 3 Flash (Latest 2025)", "recommended": True},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "recommended": True},
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
            {"id": "gemini-pro", "name": "Gemini Pro"},
        ],
        "default_model": "gemini-3-flash",
        "max_tokens": 8192,
        "icon": "🔷",
        "category": "cloud",
        "documentation_url": "https://ai.google.dev/",
    },
    "cohere": {
        "name": "cohere",
        "display_name": "Cohere",
        "description": "Command and Command-R models",
        "default_base_url": "https://api.cohere.ai/v1",
        "auth_type": "bearer_token",
        "requires_api_key": True,
        "supports_streaming": True,
        "supports_function_calling": True,
        "default_models": [
            {"id": "command-r-plus", "name": "Command R+ (Latest)", "recommended": True},
            {"id": "command-r", "name": "Command R"},
            {"id": "command", "name": "Command"},
        ],
        "default_model": "command-r-plus",
        "max_tokens": 4096,
        "icon": "🟣",
        "category": "cloud",
        "documentation_url": "https://docs.cohere.com/",
    },
    "mistral": {
        "name": "mistral",
        "display_name": "Mistral AI",
        "description": "Mistral Large, Medium, and Small models",
        "default_base_url": "https://api.mistral.ai/v1",
        "auth_type": "bearer_token",
        "requires_api_key": True,
        "supports_streaming": True,
        "supports_function_calling": True,
        "default_models": [
            {"id": "mistral-large-latest", "name": "Mistral Large (Latest)", "recommended": True},
            {"id": "mistral-medium-latest", "name": "Mistral Medium"},
            {"id": "mistral-small-latest", "name": "Mistral Small"},
        ],
        "default_model": "mistral-large-latest",
        "max_tokens": 8192,
        "icon": "🌊",
        "category": "cloud",
        "documentation_url": "https://docs.mistral.ai/",
    },
    "together": {
        "name": "together",
        "display_name": "Together AI",
        "description": "Wide selection of open-source models",
        "default_base_url": "https://api.together.xyz/v1",
        "auth_type": "bearer_token",
        "requires_api_key": True,
        "supports_streaming": True,
        "supports_function_calling": True,
        "default_models": [
            {"id": "meta-llama/Llama-3-70b-chat-hf", "name": "Llama 3 70B", "recommended": True},
            {"id": "mistralai/Mixtral-8x7B-Instruct-v0.1", "name": "Mixtral 8x7B"},
            {"id": "NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO", "name": "Nous Hermes 2"},
        ],
        "default_model": "meta-llama/Llama-3-70b-chat-hf",
        "max_tokens": 4096,
        "icon": "🤝",
        "category": "cloud",
        "documentation_url": "https://docs.together.ai/",
    },
    "replicate": {
        "name": "replicate",
        "display_name": "Replicate",
        "description": "Run models from Replicate's collection",
        "default_base_url": "https://api.replicate.com/v1",
        "auth_type": "bearer_token",
        "requires_api_key": True,
        "supports_streaming": False,
        "supports_function_calling": False,
        "default_models": [
            {"id": "meta/llama-2-70b-chat", "name": "Llama 2 70B Chat", "recommended": True},
            {"id": "mistralai/mixtral-8x7b-instruct-v0.1", "name": "Mixtral 8x7B"},
        ],
        "default_model": "meta/llama-2-70b-chat",
        "max_tokens": 2048,
        "icon": "🔄",
        "category": "cloud",
        "documentation_url": "https://replicate.com/docs",
    },
    "huggingface": {
        "name": "huggingface",
        "display_name": "HuggingFace",
        "description": "Access models from HuggingFace Hub",
        "default_base_url": "https://api-inference.huggingface.co/models",
        "auth_type": "bearer_token",
        "requires_api_key": True,
        "supports_streaming": False,
        "supports_function_calling": False,
        "default_models": [
            {"id": "meta-llama/Meta-Llama-3-8B-Instruct", "name": "Llama 3 8B", "recommended": True},
            {"id": "mistralai/Mistral-7B-Instruct-v0.2", "name": "Mistral 7B"},
            {"id": "microsoft/phi-2", "name": "Phi-2"},
        ],
        "default_model": "meta-llama/Meta-Llama-3-8B-Instruct",
        "max_tokens": 2048,
        "icon": "🤗",
        "category": "cloud",
        "documentation_url": "https://huggingface.co/docs/api-inference",
    },
    "groq": {
        "name": "groq",
        "display_name": "Groq",
        "description": "Ultra-fast inference (500+ tokens/sec!)",
        "default_base_url": "https://api.groq.com/openai/v1",
        "auth_type": "bearer_token",
        "requires_api_key": True,
        "supports_streaming": True,
        "supports_function_calling": True,
        "default_models": [
            {"id": "llama-3.1-70b-versatile", "name": "Llama 3.1 70B", "recommended": True},
            {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B (Instant)"},
            {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B"},
        ],
        "default_model": "llama-3.1-70b-versatile",
        "max_tokens": 8192,
        "icon": "⚡",
        "category": "cloud",
        "documentation_url": "https://groq.com/docs",
    },
    "perplexity": {
        "name": "perplexity",
        "display_name": "Perplexity AI",
        "description": "Powerful models with built-in web search",
        "default_base_url": "https://api.perplexity.ai",
        "auth_type": "bearer_token",
        "requires_api_key": True,
        "supports_streaming": True,
        "supports_function_calling": False,
        "default_models": [
            {"id": "llama-3.1-sonar-large-128k-online", "name": "Sonar Large (Online)", "recommended": True},
            {"id": "llama-3.1-sonar-small-128k-online", "name": "Sonar Small (Online)"},
            {"id": "llama-3.1-70b-instruct", "name": "Llama 3.1 70B"},
        ],
        "default_model": "llama-3.1-sonar-large-128k-online",
        "max_tokens": 4096,
        "icon": "🔎",
        "category": "cloud",
        "documentation_url": "https://docs.perplexity.ai/",
    },
}


# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================

class ValidateProviderRequest(BaseModel):
    """Request model for provider validation."""
    provider_type: str = Field(..., description="Provider type (openai, anthropic, deepseek, local)")
    api_key: str = Field(default="", description="API key to validate")
    base_url: Optional[str] = Field(None, description="Custom base URL")


class ModelInfo(BaseModel):
    """Model information."""
    id: str
    name: str
    created: Optional[int] = None
    size: Optional[int] = None


class ValidateProviderResponse(BaseModel):
    """Response model for provider validation."""
    valid: bool
    models: List[ModelInfo] = []
    provider_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


# ==============================================================================
# AI PROVIDER ENDPOINTS
# ==============================================================================

@router.get("/providers")
@router.get("/providers/available")
async def get_available_providers(
    current_user: User = Depends(get_current_user_smart),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get list of configured AI providers from database settings.
    Only returns providers that are actually configured and enabled.
    
    Available at both:
    - /api/v1/ai/providers (short form)
    - /api/v1/ai/providers/available (explicit form)
    """
    try:
        # Load configured providers from database
        manager = SettingsManager(db)
        ai_settings = manager.get_ai_settings()
        
        # Build response with only configured providers
        configured_providers = {}
        
        for provider_key, provider_config in ai_settings.providers.items():
            # Only include enabled providers
            if provider_config.enabled:
                # Use provider_type as the actual identifier (normalized to lowercase)
                provider_type_normalized = provider_config.provider_type.lower()
                
                # Get metadata from PROVIDER_METADATA if available
                provider_meta = PROVIDER_METADATA.get(provider_type_normalized, {})
                
                configured_providers[provider_type_normalized] = {
                    "name": provider_type_normalized,  # Use provider_type as identifier (like "openai")
                    "provider_type": provider_type_normalized,  # Explicit provider type field
                    "display_name": provider_config.name,  # Display name from DB (like "ChatGPT" or "OpenAI")
                    "description": provider_meta.get("description", ""),
                    "icon": provider_meta.get("icon", "🤖"),
                    "enabled": True,
                    "role": provider_config.role,
                    "default_model": provider_config.default_model,
                    "base_url": provider_config.base_url,
                }
        
        logger.info(f"Configured providers (by type): {list(configured_providers.keys())}")
        
        return {
            "providers": configured_providers,
            "count": len(configured_providers)
        }
        
    except Exception as e:
        logger.error(f"Failed to get configured providers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configured providers: {str(e)}"
        )


@router.get("/providers/{provider_name}/models")
async def get_provider_models(
    provider_name: str,
    current_user: User = Depends(get_current_user_smart),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get available models for a specific provider by fetching from the provider's API.
    
    This endpoint:
    1. Loads provider configuration from database (API key, base URL)
    2. Calls the provider's API to fetch actual available models
    3. Falls back to default models from PROVIDER_METADATA if API call fails
    
    Args:
        provider_name: Provider identifier (openai, anthropic, deepseek, etc.) - case insensitive
    
    Returns:
        Dict with models list and provider information
        
    Used by frontend to populate model dropdown when user selects a provider.
    """
    try:
        # Normalize provider name to lowercase for case-insensitive matching
        provider_name = provider_name.lower()
        
        # Check if provider exists in metadata
        if provider_name not in PROVIDER_METADATA:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider '{provider_name}' not found"
            )
        
        # Get provider metadata
        provider_meta = PROVIDER_METADATA[provider_name]
        
        # Try to get provider configuration from database
        manager = SettingsManager(db)
        ai_settings = manager.get_ai_settings()
        
        # Debug logging
        logger.info(f"🔍 Loaded AI settings from DB. Providers in DB: {list(ai_settings.providers.keys())}")
        logger.info(f"🔍 Looking for provider: '{provider_name}'")
        
        # Build lookup by provider_type instead of dict key (dict keys are custom names)
        # This allows looking up by standardized provider type (openai, anthropic, local, etc.)
        providers_by_type = {}
        for key, config in ai_settings.providers.items():
            provider_type = config.provider_type.lower()
            providers_by_type[provider_type] = config
            logger.info(f"  - Found provider in DB: key='{key}', type='{provider_type}', name='{config.name}'")
        
        # Check if this provider is configured
        if provider_name not in providers_by_type:
            logger.error(f"Provider '{provider_name}' not configured in database")
            logger.error(f"Available provider types: {list(providers_by_type.keys())}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider '{provider_name}' is not configured. Please configure it in settings first."
            )
        
        provider_config = providers_by_type[provider_name]
        
        # Fetch models from provider's API
        logger.info(f"Fetching models from {provider_name} API using stored credentials...")
        
        # OpenAI
        if provider_name == "openai":
            if not OPENAI_AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="OpenAI library not installed"
                )
            
            try:
                client = AsyncOpenAI(
                    api_key=provider_config.api_key,
                    base_url=provider_config.base_url or "https://api.openai.com/v1"
                )
                
                # Fetch models
                logger.info(f"Calling OpenAI API at {provider_config.base_url or 'https://api.openai.com/v1'}...")
                models_response = await client.models.list()
                
                # Show ALL models (no filtering)
                chat_models = [
                    {
                        "id": model.id,
                        "name": model.id,
                        "recommended": model.id in ["gpt-5", "gpt-4o", "gpt-4o-mini"]
                    }
                    for model in models_response.data
                ]
                
                logger.info(f"✅ Fetched {len(chat_models)} models from OpenAI API")
                
                return {
                    "provider": provider_name,
                    "provider_display_name": provider_meta.get("display_name", provider_name),
                    "models": chat_models,
                    "count": len(chat_models),
                    "source": "api"
                }
            
            except Exception as e:
                logger.error(f"❌ Failed to fetch OpenAI models from API: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to fetch models from OpenAI: {str(e)}"
                )
            
        # Anthropic
        elif provider_name == "anthropic":
            if not HTTPX_AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="httpx library not installed"
                )
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{provider_config.base_url or 'https://api.anthropic.com/v1'}/models",
                        headers={
                            "x-api-key": provider_config.api_key,
                            "anthropic-version": "2023-06-01"
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if "data" in data and isinstance(data["data"], list):
                            models = [
                                {
                                    "id": model["id"],
                                    "name": model.get("display_name", model["id"]),
                                    "recommended": "sonnet" in model["id"].lower() and "3-5" in model["id"]
                                }
                                for model in data["data"]
                            ]
                            
                            logger.info(f"✅ Fetched {len(models)} models from Anthropic API")
                            
                            return {
                                "provider": provider_name,
                                "provider_display_name": provider_meta.get("display_name", provider_name),
                                "models": models,
                                "count": len(models),
                                "source": "api"
                            }
                    
                    raise ValueError(f"HTTP {response.status_code}")
            
            except Exception as e:
                logger.error(f"❌ Failed to fetch Anthropic models from API: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to fetch models from Anthropic: {str(e)}"
                )
            
        # DeepSeek (OpenAI-compatible)
        elif provider_name == "deepseek":
            if not OPENAI_AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="OpenAI library not installed"
                )
            
            try:
                client = AsyncOpenAI(
                    api_key=provider_config.api_key,
                    base_url=provider_config.base_url or "https://api.deepseek.com/v1"
                )
                
                # Fetch models
                logger.info(f"Calling DeepSeek API at {provider_config.base_url or 'https://api.deepseek.com/v1'}...")
                models_response = await client.models.list()
                
                models = [
                    {
                        "id": model.id,
                        "name": model.id,
                        "recommended": "chat" in model.id.lower()
                    }
                    for model in models_response.data
                ]
                
                logger.info(f"✅ Fetched {len(models)} models from DeepSeek API")
                
                return {
                    "provider": provider_name,
                    "provider_display_name": provider_meta.get("display_name", provider_name),
                    "models": models,
                    "count": len(models),
                    "source": "api"
                }
            
            except Exception as e:
                logger.error(f"❌ Failed to fetch DeepSeek models from API: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to fetch models from DeepSeek: {str(e)}"
                )
            
        # Local (Ollama)
        elif provider_name == "local":
            if not HTTPX_AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="httpx library not installed"
                )
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{provider_config.base_url or 'http://localhost:11434'}/api/tags",
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        models = [
                            {
                                "id": model["name"],
                                "name": model["name"],
                                "recommended": "llama3" in model["name"].lower()
                            }
                            for model in data.get("models", [])
                        ]
                        
                        logger.info(f"✅ Fetched {len(models)} models from Ollama API")
                        
                        return {
                            "provider": provider_name,
                            "provider_display_name": provider_meta.get("display_name", provider_name),
                            "models": models,
                            "count": len(models),
                            "source": "api"
                        }
                    
                    raise ValueError(f"HTTP {response.status_code}")
            
            except Exception as e:
                logger.error(f"❌ Failed to fetch Ollama models from API: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to fetch models from Ollama: {str(e)}"
                )
        
        # Google (Gemini)
        elif provider_name == "google":
            if not HTTPX_AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="httpx library not installed"
                )
            
            try:
                # Try both v1 (stable) and v1beta (preview) endpoints
                base_urls_to_try = [
                    provider_config.base_url or "https://generativelanguage.googleapis.com/v1",
                    "https://generativelanguage.googleapis.com/v1beta"
                ]
                
                all_models = []
                success = False
                
                async with httpx.AsyncClient() as client:
                    for api_url in base_urls_to_try:
                        try:
                            logger.info(f"🔍 Trying Google API endpoint: {api_url}")
                            response = await client.get(
                                f"{api_url}/models",
                                params={"key": provider_config.api_key},
                                timeout=10
                            )
                            
                            if response.status_code == 200:
                                data = response.json()
                                
                                # Google returns { "models": [{ "name": "models/gemini-pro", ... }], ... }
                                if "models" in data and isinstance(data["models"], list):
                                    logger.info(f"📋 Found {len(data['models'])} total models from {api_url}")
                                    
                                    # Filter for generative models, but be more lenient
                                    for model in data["models"]:
                                        model_name = model["name"].replace("models/", "")
                                        supported_methods = model.get("supportedGenerationMethods", [])
                                        
                                        # Include if it supports generateContent OR if it's a gemini model
                                        if ("generateContent" in supported_methods or 
                                            "gemini" in model_name.lower()):
                                            # Mark latest Gemini models as recommended
                                            is_recommended = any(x in model_name.lower() for x in ["gemini-3", "gemini-2.5", "gemini-1.5-pro"])
                                            
                                            all_models.append({
                                                "id": model_name,
                                                "name": model.get("displayName", model_name),
                                                "recommended": is_recommended
                                            })
                                            logger.debug(f"✓ Added model: {model_name} (methods: {supported_methods})")
                                        else:
                                            logger.debug(f"✗ Skipped model: {model_name} (methods: {supported_methods})")
                                    
                                    success = True
                                    break
                        except Exception as endpoint_error:
                            logger.warning(f"Failed to fetch from {api_url}: {endpoint_error}")
                            continue
                
                if success and all_models:
                    # Remove duplicates
                    seen = set()
                    unique_models = []
                    for model in all_models:
                        if model["id"] not in seen:
                            seen.add(model["id"])
                            unique_models.append(model)
                    
                    logger.info(f"✅ Fetched {len(unique_models)} unique models from Google AI API")
                    
                    return {
                        "provider": provider_name,
                        "provider_display_name": provider_meta.get("display_name", provider_name),
                        "models": unique_models,
                        "count": len(unique_models),
                        "source": "api"
                    }
                
                raise ValueError("No valid models found from Google AI API")
            
            except Exception as e:
                logger.error(f"❌ Failed to fetch Google AI models from API: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to fetch models from Google AI: {str(e)}"
                )
        
        # OpenAI-compatible providers (Cohere, Mistral, Groq, Perplexity, Together)
        elif provider_name in ["cohere", "mistral", "groq", "perplexity", "together"]:
            if not OPENAI_AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="OpenAI library not installed"
                )
            
            try:
                client = AsyncOpenAI(
                    api_key=provider_config.api_key,
                    base_url=provider_config.base_url
                )
                
                # Fetch models
                logger.info(f"Calling {provider_name} API at {provider_config.base_url}...")
                models_response = await client.models.list()
                
                models = [
                    {
                        "id": model.id,
                        "name": model.id,
                        "recommended": False
                    }
                    for model in models_response.data
                ]
                
                logger.info(f"✅ Fetched {len(models)} models from {provider_name} API")
                
                return {
                    "provider": provider_name,
                    "provider_display_name": provider_meta.get("display_name", provider_name),
                    "models": models,
                    "count": len(models),
                    "source": "api"
                }
            
            except Exception as e:
                logger.error(f"❌ Failed to fetch {provider_name} models from API: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to fetch models from {provider_name}: {str(e)}"
                )
        
        else:
            # For other providers, API fetching not supported
            logger.error(f"Provider '{provider_name}' doesn't support API model fetching")
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Model fetching not implemented for provider: {provider_name}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get models for provider '{provider_name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get models for provider: {str(e)}"
        )


@router.get(
    "/settings",
    response_model=AISettings,
    summary="Get AI settings",
    description="Retrieve AI provider settings"
)
async def get_ai_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Get AI settings."""
    try:
        manager = SettingsManager(db)
        return manager.get_ai_settings()
    except Exception as e:
        logger.error(f"Failed to get AI settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve AI settings: {str(e)}"
        )


@router.put(
    "/settings",
    response_model=AISettings,
    summary="Update AI settings",
    description="Update AI provider settings"
)
async def update_ai_settings(
    settings: AISettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Update AI settings."""
    try:
        manager = SettingsManager(db)
        updated_settings = manager.update_ai_settings(
            settings,
            updated_by=get_user_identifier(current_user)
        )
        logger.info(f"AI settings updated by {get_user_identifier(current_user)}")
        return updated_settings
    except Exception as e:
        logger.error(f"Failed to update AI settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update AI settings: {str(e)}"
        )


@router.post(
    "/providers/validate",
    response_model=ValidateProviderResponse,
    summary="Validate AI provider",
    description="Validate API key and fetch available models from provider"
)
async def validate_provider(
    request: ValidateProviderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Validate AI provider credentials and fetch available models.
    
    This endpoint:
    1. Tests the API key by making a connection to the provider
    2. Fetches the list of available models
    3. Returns validation status and models
    
    Args:
        request: Validation request with provider type, API key, and base URL
        
    Returns:
        Validation response with models if successful
    """
    provider_type = request.provider_type.lower()
    api_key = request.api_key
    base_url = request.base_url
    
    logger.info(f"Validating {provider_type} provider for user {get_user_identifier(current_user)}")
    
    try:
        # OpenAI
        if provider_type == "openai":
            if not OPENAI_AVAILABLE:
                return ValidateProviderResponse(
                    valid=False,
                    error="OpenAI library not installed",
                    error_type="DependencyError"
                )
            
            try:
                client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url or "https://api.openai.com/v1"
                )
                
                # Fetch models
                models_response = await client.models.list()
                
                # Show ALL models (no filtering)
                chat_models = [
                    ModelInfo(
                        id=model.id,
                        name=model.id,
                        created=model.created if hasattr(model, 'created') else None
                    )
                    for model in models_response.data
                ]
                
                # Sort by most recent first
                chat_models.sort(key=lambda x: x.created or 0, reverse=True)
                
                logger.info(f"✅ OpenAI validation successful: {len(chat_models)} models found")
                
                return ValidateProviderResponse(
                    valid=True,
                    models=chat_models,
                    provider_info={
                        "name": "OpenAI",
                        "connection": "success",
                        "models_count": len(chat_models)
                    }
                )
            
            except Exception as e:
                logger.error(f"❌ OpenAI validation failed: {e}")
                return ValidateProviderResponse(
                    valid=False,
                    error=str(e),
                    error_type=type(e).__name__
                )
        
        # Anthropic
        elif provider_type == "anthropic":
            if not HTTPX_AVAILABLE:
                return ValidateProviderResponse(
                    valid=False,
                    error="httpx library not installed",
                    error_type="DependencyError"
                )
            
            try:
                # Fetch models from Anthropic's /v1/models endpoint
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{base_url or 'https://api.anthropic.com/v1'}/models",
                        headers={
                            "x-api-key": api_key,
                            "anthropic-version": "2023-06-01"
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Anthropic returns { "data": [{ "id": "...", "display_name": "...", ... }], ... }
                        if "data" in data and isinstance(data["data"], list):
                            models = [
                                ModelInfo(
                                    id=model["id"], 
                                    name=model.get("display_name", model["id"])
                                )
                                for model in data["data"]
                            ]
                            
                            logger.info(f"✅ Anthropic validation successful, fetched {len(models)} models")
                            
                            return ValidateProviderResponse(
                                valid=True,
                                models=models,
                                provider_info={
                                    "name": "Anthropic",
                                    "connection": "success",
                                    "models_count": len(models)
                                }
                            )
                        else:
                            raise Exception("Invalid response format from Anthropic API")
                    else:
                        raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            except Exception as e:
                logger.error(f"❌ Anthropic validation failed: {e}")
                return ValidateProviderResponse(
                    valid=False,
                    error=str(e),
                    error_type=type(e).__name__
                )
        
        # DeepSeek
        elif provider_type == "deepseek":
            if not OPENAI_AVAILABLE:
                return ValidateProviderResponse(
                    valid=False,
                    error="OpenAI library not installed (DeepSeek uses OpenAI-compatible API)",
                    error_type="DependencyError"
                )
            
            try:
                client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url or "https://api.deepseek.com/v1"
                )
                
                # Fetch models
                models_response = await client.models.list()
                
                models = [
                    ModelInfo(id=model.id, name=model.id)
                    for model in models_response.data
                ]
                
                logger.info(f"✅ DeepSeek validation successful: {len(models)} models found")
                
                return ValidateProviderResponse(
                    valid=True,
                    models=models,
                    provider_info={
                        "name": "DeepSeek",
                        "connection": "success",
                        "models_count": len(models)
                    }
                )
            
            except Exception as e:
                logger.error(f"❌ DeepSeek validation failed: {e}")
                return ValidateProviderResponse(
                    valid=False,
                    error=str(e),
                    error_type=type(e).__name__
                )
        
        # Local (Ollama)
        elif provider_type == "local":
            if not HTTPX_AVAILABLE:
                return ValidateProviderResponse(
                    valid=False,
                    error="httpx library not installed",
                    error_type="DependencyError"
                )
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{base_url or 'http://localhost:11434'}/api/tags",
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        models = [
                            ModelInfo(
                                id=model["name"],
                                name=model["name"],
                                size=model.get("size", 0)
                            )
                            for model in data.get("models", [])
                        ]
                        
                        logger.info(f"✅ Local (Ollama) validation successful: {len(models)} models found")
                        
                        return ValidateProviderResponse(
                            valid=True,
                            models=models,
                            provider_info={
                                "name": "Local (Ollama)",
                                "connection": "success",
                                "models_count": len(models)
                            }
                        )
                    else:
                        raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            except Exception as e:
                logger.error(f"❌ Local (Ollama) validation failed: {e}")
                return ValidateProviderResponse(
                    valid=False,
                    error=str(e),
                    error_type=type(e).__name__
                )
        
        # Google (Gemini)
        elif provider_type == "google":
            if not HTTPX_AVAILABLE:
                return ValidateProviderResponse(
                    valid=False,
                    error="httpx library not installed",
                    error_type="DependencyError"
                )
            
            try:
                # Test API key by listing models
                # Try both v1 (stable) and v1beta (preview) endpoints
                base_urls_to_try = [
                    base_url or "https://generativelanguage.googleapis.com/v1",
                    "https://generativelanguage.googleapis.com/v1beta"
                ]
                
                all_models = []
                success = False
                
                async with httpx.AsyncClient() as client:
                    for api_url in base_urls_to_try:
                        try:
                            logger.info(f"🔍 Trying Google API endpoint: {api_url}")
                            response = await client.get(
                                f"{api_url}/models",
                                params={"key": api_key},
                                timeout=10
                            )
                            
                            if response.status_code == 200:
                                data = response.json()
                                
                                # Google returns { "models": [{ "name": "models/gemini-pro", ... }], ... }
                                if "models" in data and isinstance(data["models"], list):
                                    logger.info(f"📋 Found {len(data['models'])} total models from {api_url}")
                                    
                                    # Filter for generative models, but be more lenient
                                    for model in data["models"]:
                                        model_name = model["name"].replace("models/", "")
                                        supported_methods = model.get("supportedGenerationMethods", [])
                                        
                                        # Include if it supports generateContent OR if it's a gemini model
                                        # (Some newer models might have different method names)
                                        if ("generateContent" in supported_methods or 
                                            "gemini" in model_name.lower()):
                                            all_models.append(ModelInfo(
                                                id=model_name,
                                                name=model.get("displayName", model_name)
                                            ))
                                            logger.debug(f"✓ Added model: {model_name} (methods: {supported_methods})")
                                        else:
                                            logger.debug(f"✗ Skipped model: {model_name} (methods: {supported_methods})")
                                    
                                    success = True
                                    break
                        except Exception as endpoint_error:
                            logger.warning(f"Failed to fetch from {api_url}: {endpoint_error}")
                            continue
                
                if success and all_models:
                    # Remove duplicates (in case model appears in both v1 and v1beta)
                    seen = set()
                    unique_models = []
                    for model in all_models:
                        if model.id not in seen:
                            seen.add(model.id)
                            unique_models.append(model)
                    
                    logger.info(f"✅ Google (Gemini) validation successful: {len(unique_models)} unique models found")
                    
                    return ValidateProviderResponse(
                        valid=True,
                        models=unique_models,
                        provider_info={
                            "name": "Google AI (Gemini)",
                            "connection": "success",
                            "models_count": len(unique_models)
                        }
                    )
                else:
                    raise Exception("No valid models found or invalid response format from Google AI API")
            
            except Exception as e:
                logger.error(f"❌ Google (Gemini) validation failed: {e}")
                return ValidateProviderResponse(
                    valid=False,
                    error=str(e),
                    error_type=type(e).__name__
                )
        
        # Cohere (OpenAI-compatible)
        elif provider_type == "cohere":
            if not OPENAI_AVAILABLE:
                return ValidateProviderResponse(
                    valid=False,
                    error="OpenAI library not installed (Cohere uses OpenAI-compatible API)",
                    error_type="DependencyError"
                )
            
            try:
                client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url or "https://api.cohere.ai/v1"
                )
                
                # Fetch models
                models_response = await client.models.list()
                
                models = [
                    ModelInfo(id=model.id, name=model.id)
                    for model in models_response.data
                ]
                
                logger.info(f"✅ Cohere validation successful: {len(models)} models found")
                
                return ValidateProviderResponse(
                    valid=True,
                    models=models,
                    provider_info={
                        "name": "Cohere",
                        "connection": "success",
                        "models_count": len(models)
                    }
                )
            
            except Exception as e:
                logger.error(f"❌ Cohere validation failed: {e}")
                return ValidateProviderResponse(
                    valid=False,
                    error=str(e),
                    error_type=type(e).__name__
                )
        
        # Mistral (OpenAI-compatible)
        elif provider_type == "mistral":
            if not OPENAI_AVAILABLE:
                return ValidateProviderResponse(
                    valid=False,
                    error="OpenAI library not installed (Mistral uses OpenAI-compatible API)",
                    error_type="DependencyError"
                )
            
            try:
                client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url or "https://api.mistral.ai/v1"
                )
                
                # Fetch models
                models_response = await client.models.list()
                
                models = [
                    ModelInfo(id=model.id, name=model.id)
                    for model in models_response.data
                ]
                
                logger.info(f"✅ Mistral validation successful: {len(models)} models found")
                
                return ValidateProviderResponse(
                    valid=True,
                    models=models,
                    provider_info={
                        "name": "Mistral AI",
                        "connection": "success",
                        "models_count": len(models)
                    }
                )
            
            except Exception as e:
                logger.error(f"❌ Mistral validation failed: {e}")
                return ValidateProviderResponse(
                    valid=False,
                    error=str(e),
                    error_type=type(e).__name__
                )
        
        # Groq (OpenAI-compatible, ultra-fast!)
        elif provider_type == "groq":
            if not OPENAI_AVAILABLE:
                return ValidateProviderResponse(
                    valid=False,
                    error="OpenAI library not installed (Groq uses OpenAI-compatible API)",
                    error_type="DependencyError"
                )
            
            try:
                client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url or "https://api.groq.com/openai/v1"
                )
                
                # Fetch models
                models_response = await client.models.list()
                
                models = [
                    ModelInfo(id=model.id, name=model.id)
                    for model in models_response.data
                ]
                
                logger.info(f"✅ Groq validation successful: {len(models)} models found")
                
                return ValidateProviderResponse(
                    valid=True,
                    models=models,
                    provider_info={
                        "name": "Groq",
                        "connection": "success",
                        "models_count": len(models)
                    }
                )
            
            except Exception as e:
                logger.error(f"❌ Groq validation failed: {e}")
                return ValidateProviderResponse(
                    valid=False,
                    error=str(e),
                    error_type=type(e).__name__
                )
        
        # Perplexity (OpenAI-compatible)
        elif provider_type == "perplexity":
            if not OPENAI_AVAILABLE:
                return ValidateProviderResponse(
                    valid=False,
                    error="OpenAI library not installed (Perplexity uses OpenAI-compatible API)",
                    error_type="DependencyError"
                )
            
            try:
                client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url or "https://api.perplexity.ai"
                )
                
                # Fetch models
                models_response = await client.models.list()
                
                models = [
                    ModelInfo(id=model.id, name=model.id)
                    for model in models_response.data
                ]
                
                logger.info(f"✅ Perplexity validation successful: {len(models)} models found")
                
                return ValidateProviderResponse(
                    valid=True,
                    models=models,
                    provider_info={
                        "name": "Perplexity AI",
                        "connection": "success",
                        "models_count": len(models)
                    }
                )
            
            except Exception as e:
                logger.error(f"❌ Perplexity validation failed: {e}")
                return ValidateProviderResponse(
                    valid=False,
                    error=str(e),
                    error_type=type(e).__name__
                )
        
        # Together AI (OpenAI-compatible)
        elif provider_type == "together":
            if not OPENAI_AVAILABLE:
                return ValidateProviderResponse(
                    valid=False,
                    error="OpenAI library not installed (Together AI uses OpenAI-compatible API)",
                    error_type="DependencyError"
                )
            
            try:
                client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url or "https://api.together.xyz/v1"
                )
                
                # Fetch models
                models_response = await client.models.list()
                
                models = [
                    ModelInfo(id=model.id, name=model.id)
                    for model in models_response.data
                ]
                
                logger.info(f"✅ Together AI validation successful: {len(models)} models found")
                
                return ValidateProviderResponse(
                    valid=True,
                    models=models,
                    provider_info={
                        "name": "Together AI",
                        "connection": "success",
                        "models_count": len(models)
                    }
                )
            
            except Exception as e:
                logger.error(f"❌ Together AI validation failed: {e}")
                return ValidateProviderResponse(
                    valid=False,
                    error=str(e),
                    error_type=type(e).__name__
                )
        
        # Replicate (OpenAI-compatible)
        elif provider_type == "replicate":
            if not HTTPX_AVAILABLE:
                return ValidateProviderResponse(
                    valid=False,
                    error="httpx library not installed",
                    error_type="DependencyError"
                )
            
            try:
                # Replicate uses a different auth format
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{base_url or 'https://api.replicate.com/v1'}/models",
                        headers={"Authorization": f"Token {api_key}"},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        # Use default models from metadata for now
                        models = [
                            ModelInfo(id=m["id"], name=m["name"])
                            for m in PROVIDER_METADATA["replicate"]["default_models"]
                        ]
                        
                        logger.info(f"✅ Replicate validation successful")
                        
                        return ValidateProviderResponse(
                            valid=True,
                            models=models,
                            provider_info={
                                "name": "Replicate",
                                "connection": "success",
                                "models_count": len(models)
                            }
                        )
                    else:
                        raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            except Exception as e:
                logger.error(f"❌ Replicate validation failed: {e}")
                return ValidateProviderResponse(
                    valid=False,
                    error=str(e),
                    error_type=type(e).__name__
                )
        
        # Unknown provider
        else:
            return ValidateProviderResponse(
                valid=False,
                error=f"Unknown provider type: {provider_type}",
                error_type="InvalidProviderType"
            )
    
    except Exception as e:
        logger.error(f"❌ Unexpected error during validation: {e}", exc_info=True)
        return ValidateProviderResponse(
            valid=False,
            error=f"Unexpected error: {str(e)}",
            error_type=type(e).__name__
        )

