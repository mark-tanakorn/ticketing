"""
LangChain Integration Layer

This module provides LangChain features while preserving the existing AIGovernor system.

Architecture:
- AIGovernor: Core LLM routing, fallback, retry
- LangChain: Document loading, embeddings, RAG, memory

Usage:
    from app.core.ai.langchain import get_embedding_manager, get_vectorstore_manager
"""

from typing import Optional

# Lazy imports to avoid loading heavy dependencies unless needed
_embedding_manager: Optional["EmbeddingManager"] = None
_vectorstore_manager: Optional["VectorStoreManager"] = None


def get_embedding_manager():
    """Get the global EmbeddingManager instance (lazy-loaded)."""
    global _embedding_manager
    if _embedding_manager is None:
        from .embeddings import EmbeddingManager
        _embedding_manager = EmbeddingManager()
    return _embedding_manager


def get_vectorstore_manager():
    """Get the global VectorStoreManager instance (lazy-loaded)."""
    global _vectorstore_manager
    if _vectorstore_manager is None:
        from .vectorstores import VectorStoreManager
        _vectorstore_manager = VectorStoreManager()
    return _vectorstore_manager


__all__ = [
    "get_embedding_manager",
    "get_vectorstore_manager",
]

