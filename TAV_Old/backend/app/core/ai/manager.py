"""
LangChain Manager

Central manager for all LangChain operations.
Replaces the old AIGovernor with LangChain's mature framework.

This manager:
- Reads AI settings from database
- Creates LangChain LLM instances
- Handles fallback logic
- Provides embeddings, chains, and tools
"""

import logging
from typing import Optional, Dict, Any, List, Union
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class LangChainManager:
    """
    Central manager for LangChain operations.
    
    This replaces AIGovernor and provides:
    - LLM calls with fallback
    - Embeddings
    - RAG chains
    - Agents
    """
    
    def __init__(self, db: Session):
        """
        Initialize LangChain manager.
        
        Args:
            db: Database session for loading settings
        """
        self.db = db
        self._llm_cache: Dict[str, Any] = {}
        self._embeddings_cache: Dict[str, Any] = {}
        self._settings = None
        logger.info("🦜 LangChainManager initialized")
    
    def _load_settings(self):
        """Load AI settings from database."""
        if self._settings is None:
            from app.core.config.manager import SettingsManager
            manager = SettingsManager(self.db)
            self._settings = manager.get_ai_settings()
            
            # Dynamically determine default_provider and fallback_provider from roles
            primary_provider = None
            fallback_providers = []
            
            for provider_key, provider_config in self._settings.providers.items():
                if not provider_config.enabled:
                    continue
                    
                if provider_config.role == "primary":
                    primary_provider = provider_config.provider_type.lower()
                elif provider_config.role == "fallback":
                    fallback_providers.append((
                        provider_config.provider_type.lower(),
                        provider_config.fallback_priority or 999
                    ))
            
            # Sort fallback providers by priority (lowest number = highest priority)
            fallback_providers.sort(key=lambda x: x[1])
            
            # Update settings with dynamically determined providers
            if primary_provider:
                self._settings.default_provider = primary_provider
                logger.info(f"✅ Primary provider: {primary_provider}")
            
            if fallback_providers:
                self._settings.fallback_provider = fallback_providers[0][0]  # Use highest priority fallback
                logger.info(f"✅ Fallback provider: {self._settings.fallback_provider} (priority: {fallback_providers[0][1]})")
            else:
                self._settings.fallback_provider = ""
                logger.warning("⚠️  No fallback provider configured")
            
            logger.info(f"✅ Loaded AI settings: {len(self._settings.providers)} providers")
        return self._settings
    
    def _get_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get provider configuration from database settings by provider_type."""
        settings = self._load_settings()
        
        # Build lookup by provider_type instead of dict key (dict keys are custom names)
        # This allows looking up by standardized provider type (openai, anthropic, local, etc.)
        provider_name_lower = provider_name.lower()
        
        for key, provider in settings.providers.items():
            if provider.provider_type.lower() == provider_name_lower:
                logger.info(f"✅ Found provider config: key='{key}', type='{provider.provider_type}', name='{provider.name}'")
                return {
                    "provider_type": provider.provider_type,
                    "api_key": provider.api_key,
                    "base_url": provider.base_url,
                    "default_model": provider.default_model,
                    "temperature": provider.default_temperature if provider.default_temperature is not None else settings.default_temperature,
                    "max_tokens": provider.max_tokens_limit if provider.max_tokens_limit is not None else settings.default_max_tokens,
                    "timeout": settings.request_timeout,
                }
        
        logger.warning(f"Provider not found: {provider_name}")
        logger.warning(f"Available provider types: {[p.provider_type.lower() for p in settings.providers.values()]}")
        return None
    
    def get_llm(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        streaming: bool = False,
        timeout: Optional[int] = None,
        **kwargs
    ):
        """
        Get a LangChain LLM instance.
        
        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            model: Model name (overrides default)
            temperature: Sampling temperature (overrides default)
            max_tokens: Max tokens (overrides default)
            streaming: Enable streaming
            **kwargs: Additional provider-specific options
            
        Returns:
            LangChain LLM instance (ChatOpenAI, ChatAnthropic, etc.)
        """
        settings = self._load_settings()
        provider = provider or settings.default_provider
        
        # Get provider config
        config = self._get_provider_config(provider)
        if not config:
            raise ValueError(f"Provider not configured: {provider}")
        
        # Override with provided values
        if model:
            config["default_model"] = model
        if temperature is not None:
            config["temperature"] = temperature
            logger.info(f"🌡️  Temperature override: {temperature}")
        if max_tokens:
            config["max_tokens"] = max_tokens
        if timeout is not None:
            config["timeout"] = timeout
        
        # Cache key
        cache_key = f"{provider}:{config['default_model']}:{config['temperature']}"
        
        if cache_key in self._llm_cache and not streaming:
            logger.debug(f"Using cached LLM: {cache_key}")
            return self._llm_cache[cache_key]
        
        # Create LLM instance
        llm = self._create_llm(config, streaming, **kwargs)
        
        # Cache it (don't cache streaming instances)
        if not streaming:
            self._llm_cache[cache_key] = llm
        
        logger.info(f"✅ Created LLM: {provider}/{config['default_model']}")
        return llm
    
    def _create_llm(self, config: Dict[str, Any], streaming: bool, **kwargs):
        """Create LangChain LLM instance based on provider type."""
        provider_type = config["provider_type"]
        
        if provider_type == "openai":
            return self._create_openai_llm(config, streaming, **kwargs)
        
        elif provider_type == "anthropic":
            return self._create_anthropic_llm(config, streaming, **kwargs)
        
        elif provider_type == "deepseek":
            return self._create_deepseek_llm(config, streaming, **kwargs)
        
        elif provider_type == "local":
            return self._create_local_llm(config, streaming, **kwargs)
        
        elif provider_type == "google":
            return self._create_google_llm(config, streaming, **kwargs)
        
        elif provider_type == "cohere":
            return self._create_cohere_llm(config, streaming, **kwargs)
        
        elif provider_type == "mistral":
            return self._create_mistral_llm(config, streaming, **kwargs)
        
        elif provider_type == "groq":
            return self._create_groq_llm(config, streaming, **kwargs)
        
        elif provider_type == "perplexity":
            return self._create_perplexity_llm(config, streaming, **kwargs)
        
        elif provider_type == "together":
            return self._create_together_llm(config, streaming, **kwargs)
        
        elif provider_type == "replicate":
            return self._create_replicate_llm(config, streaming, **kwargs)
        
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
    
    def _create_openai_llm(self, config: Dict[str, Any], streaming: bool, **kwargs):
        """Create OpenAI LLM with proper timeout handling for vision models."""
        try:
            from langchain_openai import ChatOpenAI
            import httpx
        except ImportError:
            raise ImportError("OpenAI support requires: pip install langchain-openai httpx")
        
        # Get timeout from config (already loaded from DB ai.request_timeout)
        # config["timeout"] is set from settings.request_timeout in _get_provider_config()
        settings = self._load_settings()
        timeout = config.get("timeout", settings.request_timeout)
        
        logger.info(f"🔧 Creating OpenAI LLM: model={config['default_model']}, timeout={timeout}s")
        
        # Create httpx client with explicit timeouts
        # Vision models need longer read timeout but reasonable connect timeout
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                timeout=timeout,  # Total timeout
                connect=10.0,     # Connection timeout (fast)
                read=timeout,     # Read timeout (can be long for vision)
                write=30.0,       # Write timeout
                pool=5.0          # Pool timeout
            )
        )
        
        return ChatOpenAI(
            model=config["default_model"],
            openai_api_key=config["api_key"],
            openai_api_base=config["base_url"] if config["base_url"] != "https://api.openai.com/v1" else None,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            http_async_client=http_client,  # Pass custom httpx client
            max_retries=settings.max_retries,  # Use max_retries from AI settings
            streaming=streaming,
            **kwargs
        )
    
    def _create_anthropic_llm(self, config: Dict[str, Any], streaming: bool, **kwargs):
        """Create Anthropic LLM."""
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError("Anthropic support requires: pip install langchain-anthropic")
        
        return ChatAnthropic(
            model=config["default_model"],
            anthropic_api_key=config["api_key"],
            anthropic_api_url=config["base_url"] if config["base_url"] != "https://api.anthropic.com/v1" else None,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            timeout=config["timeout"],
            streaming=streaming,
            **kwargs
        )
    
    def _create_deepseek_llm(self, config: Dict[str, Any], streaming: bool, **kwargs):
        """Create DeepSeek LLM (OpenAI-compatible)."""
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("DeepSeek support requires: pip install langchain-openai")
        
        return ChatOpenAI(
            model=config["default_model"],
            openai_api_key=config["api_key"],
            openai_api_base=config["base_url"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            timeout=config["timeout"],
            streaming=streaming,
            **kwargs
        )
    
    def _create_local_llm(self, config: Dict[str, Any], streaming: bool, **kwargs):
        """Create local Ollama LLM with tool calling support."""
        try:
            # Try new langchain-ollama package first (supports tool calling)
            from langchain_ollama import ChatOllama
            logger.info("✅ Using langchain-ollama (tool calling supported)")
        except ImportError:
            # Fallback to old langchain-community (no tool calling)
            try:
                from langchain_community.chat_models import ChatOllama
                logger.warning("⚠️ Using langchain-community (tool calling may not work). Install langchain-ollama for better support.")
            except ImportError:
                raise ImportError("Ollama support requires: pip install langchain-ollama or langchain-community")
        
        # Use ChatOllama instead of Ollama for better vision support
        return ChatOllama(
            model=config["default_model"],
            base_url=config["base_url"],
            temperature=config["temperature"],
            num_predict=config.get("max_tokens"),
            **kwargs
        )
    
    def _create_google_llm(self, config: Dict[str, Any], streaming: bool, **kwargs):
        """Create Google Gemini LLM."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError("Google Gemini support requires: pip install langchain-google-genai")
        
        return ChatGoogleGenerativeAI(
            model=config["default_model"],
            google_api_key=config["api_key"],
            temperature=config["temperature"],
            max_output_tokens=config["max_tokens"],
            timeout=config["timeout"],
            streaming=streaming,
            **kwargs
        )
    
    def _create_cohere_llm(self, config: Dict[str, Any], streaming: bool, **kwargs):
        """Create Cohere LLM (OpenAI-compatible)."""
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("Cohere support requires: pip install langchain-openai")
        
        return ChatOpenAI(
            model=config["default_model"],
            openai_api_key=config["api_key"],
            openai_api_base=config["base_url"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            timeout=config["timeout"],
            streaming=streaming,
            **kwargs
        )
    
    def _create_mistral_llm(self, config: Dict[str, Any], streaming: bool, **kwargs):
        """Create Mistral LLM using official LangChain integration."""
        try:
            from langchain_mistralai import ChatMistralAI
        except ImportError:
            raise ImportError("Mistral support requires: pip install langchain-mistralai")
        
        return ChatMistralAI(
            model=config["default_model"],
            mistral_api_key=config["api_key"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            timeout=config["timeout"],
            streaming=streaming,
            **kwargs
        )
    
    def _create_groq_llm(self, config: Dict[str, Any], streaming: bool, **kwargs):
        """Create Groq LLM (OpenAI-compatible, ultra-fast!)."""
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("Groq support requires: pip install langchain-openai")
        
        return ChatOpenAI(
            model=config["default_model"],
            openai_api_key=config["api_key"],
            openai_api_base=config["base_url"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            timeout=config["timeout"],
            streaming=streaming,
            **kwargs
        )
    
    def _create_perplexity_llm(self, config: Dict[str, Any], streaming: bool, **kwargs):
        """Create Perplexity LLM (OpenAI-compatible with web search)."""
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("Perplexity support requires: pip install langchain-openai")
        
        return ChatOpenAI(
            model=config["default_model"],
            openai_api_key=config["api_key"],
            openai_api_base=config["base_url"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            timeout=config["timeout"],
            streaming=streaming,
            **kwargs
        )
    
    def _create_together_llm(self, config: Dict[str, Any], streaming: bool, **kwargs):
        """Create Together AI LLM (OpenAI-compatible)."""
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("Together AI support requires: pip install langchain-openai")
        
        return ChatOpenAI(
            model=config["default_model"],
            openai_api_key=config["api_key"],
            openai_api_base=config["base_url"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            timeout=config["timeout"],
            streaming=streaming,
            **kwargs
        )
    
    def _create_replicate_llm(self, config: Dict[str, Any], streaming: bool, **kwargs):
        """Create Replicate LLM."""
        try:
            from langchain_community.llms import Replicate
        except ImportError:
            raise ImportError("Replicate support requires: pip install langchain-community")
        
        # Replicate uses a different model format (owner/name:version)
        return Replicate(
            model=config["default_model"],
            replicate_api_token=config["api_key"],
            **kwargs
        )
    
    async def call_llm(
        self,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        fallback: bool = True,
        **kwargs
    ) -> str:
        """
        Call LLM with automatic fallback.
        
        Args:
            prompt: Prompt to send to LLM
            provider: Provider name
            model: Model name
            temperature: Sampling temperature
            max_tokens: Max tokens
            fallback: Enable fallback to secondary provider
            **kwargs: Additional options
            
        Returns:
            LLM response text
        """
        settings = self._load_settings()
        provider = provider or settings.default_provider
        
        # Try primary provider
        try:
            llm = self.get_llm(provider, model, temperature, max_tokens, **kwargs)
            response = await llm.apredict(prompt)
            logger.info(f"✅ LLM call succeeded: {provider}")
            return response
        
        except Exception as e:
            logger.error(f"❌ LLM call failed ({provider}): {e}")
            
            # Try fallback
            if fallback and settings.fallback_provider and settings.fallback_provider != provider:
                logger.info(f"🔄 Trying fallback: {settings.fallback_provider}")
                try:
                    llm = self.get_llm(settings.fallback_provider, model, temperature, max_tokens, **kwargs)
                    response = await llm.apredict(prompt)
                    logger.info(f"✅ Fallback succeeded: {settings.fallback_provider}")
                    return response
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback failed: {fallback_error}")
                    raise fallback_error
            else:
                raise e
    
    async def call_llm_with_messages(
        self,
        messages: List[Dict[str, str]],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        fallback: bool = True,
        **kwargs
    ) -> str:
        """
        Call LLM with chat messages format.
        
        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}]
            provider: Provider name
            model: Model name
            temperature: Sampling temperature
            max_tokens: Max tokens
            fallback: Enable fallback
            **kwargs: Additional options
            
        Returns:
            LLM response text
        """
        from langchain.schema import HumanMessage, SystemMessage, AIMessage
        
        settings = self._load_settings()
        provider = provider or settings.default_provider
        
        # Convert messages to LangChain format
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            images = msg.get("images")  # Ollama-specific field
            
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                # For vision models, content can be a list of dicts with text and images
                # LangChain HumanMessage supports this structured content format
                if images:
                    # Ollama format: For ChatOllama, we need to format images as content parts
                    # ChatOllama expects: content=[{"type": "text", "text": "..."}, {"type": "image_url", "image_url": "..."}]
                    if isinstance(content, str):
                        ollama_content = [{"type": "text", "text": content}]
                        # Add images as image_url parts (ChatOllama converts this internally)
                        for img_b64 in images:
                            ollama_content.append({
                                "type": "image_url",
                                "image_url": f"data:image/jpeg;base64,{img_b64}"
                            })
                        lc_messages.append(HumanMessage(content=ollama_content))
                    else:
                        lc_messages.append(HumanMessage(content=content))
                else:
                    # OpenAI/Anthropic format: structured content
                    lc_messages.append(HumanMessage(content=content))
        
        # Try primary provider
        try:
            llm = self.get_llm(provider, model, temperature, max_tokens, timeout=timeout, **kwargs)
            
            # Use ainvoke instead of apredict_messages for better vision model support
            # ainvoke properly handles structured content (images + text) in messages
            logger.info(f"🚀 Invoking LLM ({provider}/{model}) with {len(lc_messages)} messages...")
            
            response = await llm.ainvoke(lc_messages)
            
            logger.info(f"✅ LLM call (messages) succeeded: {provider} - response length: {len(response.content)} chars")
            return response.content
        
        except Exception as e:
            error_str = str(e)
            logger.error(f"❌ LLM call (messages) failed ({provider}): {error_str}")
            
            # Log more details for timeout errors
            if "timeout" in error_str.lower() or "timed out" in error_str.lower():
                logger.error(f"⏱️ Timeout details: model={model}, messages={len(lc_messages)}, provider={provider}")
                logger.error(f"⏱️ This might indicate: 1) Network issues, 2) API overload, 3) Request too large")
            
            # Try fallback
            if fallback and settings.fallback_provider and settings.fallback_provider != provider:
                logger.info(f"🔄 Trying fallback: {settings.fallback_provider}")
                try:
                    llm = self.get_llm(settings.fallback_provider, model, temperature, max_tokens, timeout=timeout, **kwargs)
                    response = await llm.ainvoke(lc_messages)
                    logger.info(f"✅ Fallback succeeded: {settings.fallback_provider}")
                    return response.content
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback failed: {fallback_error}")
                    raise fallback_error
            else:
                raise e
    
    def get_embeddings(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Get embeddings instance.
        
        Args:
            provider: Provider name (defaults to primary)
            model: Model name (optional)
            
        Returns:
            LangChain Embeddings instance
        """
        # Use existing langchain integration
        from app.core.ai.langchain.embeddings import EmbeddingManager, EmbeddingProvider
        
        embedding_mgr = EmbeddingManager()
        
        settings = self._load_settings()
        provider = provider or settings.default_provider
        
        # Map provider to embedding provider
        if provider == "openai":
            config = self._get_provider_config(provider)
            return embedding_mgr.get_embeddings(
                provider=EmbeddingProvider.OPENAI,
                model_name=model,
                api_key=config["api_key"]
            )
        else:
            # Default to local HuggingFace embeddings (FREE!)
            return embedding_mgr.get_embeddings(
                provider=EmbeddingProvider.HUGGINGFACE_LOCAL,
                model_name=model
            )


# Global instance (lazy-loaded)
_langchain_manager: Optional[LangChainManager] = None


def get_langchain_manager(db: Session) -> LangChainManager:
    """Get the global LangChainManager instance."""
    global _langchain_manager
    if _langchain_manager is None or _langchain_manager.db != db:
        _langchain_manager = LangChainManager(db)
    return _langchain_manager

