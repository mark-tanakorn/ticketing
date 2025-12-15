"""
Embedding Manager

Handles text embeddings for semantic search and RAG.
Supports both local (FREE) and cloud-based embeddings.
"""

import logging
from typing import List, Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """Available embedding providers."""
    HUGGINGFACE_LOCAL = "huggingface_local"  # FREE, runs locally
    OPENAI = "openai"                         # PAID, requires API key
    COHERE = "cohere"                         # PAID, requires API key


class EmbeddingManager:
    """
    Manages embeddings for semantic search and RAG.
    
    Supports multiple providers:
    - HuggingFace (FREE, local, no API key needed)
    - OpenAI (PAID, requires API key)
    - Cohere (PAID, requires API key)
    """
    
    def __init__(self):
        self._embeddings_cache: Dict[str, Any] = {}
        logger.info("🎯 EmbeddingManager initialized")
    
    def get_embeddings(
        self,
        provider: EmbeddingProvider = EmbeddingProvider.HUGGINGFACE_LOCAL,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        Get an embeddings instance for the specified provider.
        
        Args:
            provider: Which embedding provider to use
            model_name: Model name (provider-specific)
            api_key: API key (for cloud providers)
            **kwargs: Additional provider-specific options
            
        Returns:
            LangChain Embeddings instance
        """
        cache_key = f"{provider}:{model_name or 'default'}"
        
        # Return cached instance if available
        if cache_key in self._embeddings_cache:
            logger.debug(f"Using cached embeddings: {cache_key}")
            return self._embeddings_cache[cache_key]
        
        # Create new embeddings instance
        embeddings = self._create_embeddings(provider, model_name, api_key, **kwargs)
        
        # Cache it
        self._embeddings_cache[cache_key] = embeddings
        logger.info(f"✅ Created embeddings: {cache_key}")
        
        return embeddings
    
    def _create_embeddings(
        self,
        provider: EmbeddingProvider,
        model_name: Optional[str],
        api_key: Optional[str],
        **kwargs
    ):
        """Create embeddings instance based on provider."""
        
        if provider == EmbeddingProvider.HUGGINGFACE_LOCAL:
            return self._create_huggingface_embeddings(model_name, **kwargs)
        
        elif provider == EmbeddingProvider.OPENAI:
            return self._create_openai_embeddings(model_name, api_key, **kwargs)
        
        elif provider == EmbeddingProvider.COHERE:
            return self._create_cohere_embeddings(model_name, api_key, **kwargs)
        
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")
    
    def _create_huggingface_embeddings(self, model_name: Optional[str], **kwargs):
        """
        Create HuggingFace embeddings (FREE, local).
        
        Default model: all-MiniLM-L6-v2 (384 dimensions, fast, good quality)
        """
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
        except ImportError:
            raise ImportError(
                "HuggingFace embeddings require: pip install sentence-transformers"
            )
        
        model_name = model_name or "sentence-transformers/all-MiniLM-L6-v2"
        
        logger.info(f"🏠 Creating local HuggingFace embeddings: {model_name}")
        
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'},  # Use 'cuda' if GPU available
            encode_kwargs={'normalize_embeddings': True},
            **kwargs
        )
    
    def _create_openai_embeddings(self, model_name: Optional[str], api_key: Optional[str], **kwargs):
        """Create OpenAI embeddings (PAID, requires API key)."""
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError:
            raise ImportError(
                "OpenAI embeddings require: pip install langchain-openai"
            )
        
        if not api_key:
            raise ValueError("OpenAI embeddings require an API key")
        
        model_name = model_name or "text-embedding-3-small"
        
        logger.info(f"☁️ Creating OpenAI embeddings: {model_name}")
        
        return OpenAIEmbeddings(
            model=model_name,
            openai_api_key=api_key,
            **kwargs
        )
    
    def _create_cohere_embeddings(self, model_name: Optional[str], api_key: Optional[str], **kwargs):
        """Create Cohere embeddings (PAID, requires API key)."""
        try:
            from langchain_community.embeddings import CohereEmbeddings
        except ImportError:
            raise ImportError(
                "Cohere embeddings require: pip install cohere"
            )
        
        if not api_key:
            raise ValueError("Cohere embeddings require an API key")
        
        model_name = model_name or "embed-english-v3.0"
        
        logger.info(f"☁️ Creating Cohere embeddings: {model_name}")
        
        return CohereEmbeddings(
            model=model_name,
            cohere_api_key=api_key,
            **kwargs
        )
    
    def embed_text(self, text: str, provider: EmbeddingProvider = EmbeddingProvider.HUGGINGFACE_LOCAL) -> List[float]:
        """
        Embed a single text string.
        
        Args:
            text: Text to embed
            provider: Which embedding provider to use
            
        Returns:
            List of floats (embedding vector)
        """
        embeddings = self.get_embeddings(provider)
        return embeddings.embed_query(text)
    
    def embed_documents(
        self,
        texts: List[str],
        provider: EmbeddingProvider = EmbeddingProvider.HUGGINGFACE_LOCAL
    ) -> List[List[float]]:
        """
        Embed multiple documents.
        
        Args:
            texts: List of texts to embed
            provider: Which embedding provider to use
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.get_embeddings(provider)
        return embeddings.embed_documents(texts)

