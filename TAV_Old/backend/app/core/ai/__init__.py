"""
AI Module

Central AI management system for TAV Engine.
Now powered by LangChain!
"""

from app.core.ai.manager import (
    LangChainManager,
    get_langchain_manager,
)

__all__ = [
    # LangChain Manager
    "LangChainManager",
    "get_langchain_manager",
]

