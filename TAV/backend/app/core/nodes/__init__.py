"""
Core Nodes Module

Provides base node class, registry, and capabilities for workflow nodes.
"""

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import NodeRegistry, register_node
from app.core.nodes.capabilities import (
    LLMCapability,
    AICapability,
    ComputeCapability,
    TriggerCapability,
    ExportCapability,
    get_resource_classes,
    has_llm_capability,
    has_ai_capability,
    has_trigger_capability,
)

__all__ = [
    # Base classes
    "Node",
    "NodeExecutionInput",
    
    # Registry
    "NodeRegistry",
    "register_node",
    
    # Capabilities
    "LLMCapability",
    "AICapability",
    "ComputeCapability",
    "TriggerCapability",
    "get_resource_classes",
    "has_llm_capability",
    "has_ai_capability",
    "has_trigger_capability",
]
