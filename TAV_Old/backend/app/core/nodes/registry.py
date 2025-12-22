"""
Node Registry

Central registry for all node types in the system.
"""

import logging
from typing import Dict, Type, Optional, List

from app.core.nodes.base import Node

logger = logging.getLogger(__name__)


class NodeRegistry:
    """
    Registry for node types.
    
    Maintains mapping of node_type string to Node class.
    Used by executor to instantiate correct node class during execution.
    """
    
    _nodes: Dict[str, Type[Node]] = {}
    _node_metadata: Dict[str, Dict[str, any]] = {}
    
    @classmethod
    def register(
        cls,
        node_type: str,
        node_class: Type[Node],
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        category: Optional[str] = None,
    ) -> None:
        """
        Register a node type.
        
        Args:
            node_type: Unique identifier for node type (e.g., "http_request")
            node_class: Node class (must inherit from Node)
            display_name: Human-readable name for UI
            description: Node description
            icon: Icon identifier
            category: Node category (string or NodeCategory enum)
        
        Example:
            NodeRegistry.register(
                node_type="http_request",
                node_class=HTTPRequestNode,
                display_name="HTTP Request",
                description="Make HTTP requests to external APIs",
                icon="globe",
                category="actions"
            )
        """
        if not issubclass(node_class, Node):
            raise ValueError(f"Node class {node_class} must inherit from Node")
        
        if node_type in cls._nodes:
            logger.warning(f"⚠️ Overwriting existing node type: {node_type}")
        
        # Convert category enum to string if needed
        category_str = category
        if category and hasattr(category, 'value'):
            category_str = category.value
        
        cls._nodes[node_type] = node_class
        cls._node_metadata[node_type] = {
            "display_name": display_name or node_type,
            "description": description or "",
            "icon": icon,
            "category": category_str,
            "class_name": node_class.__name__,
        }
        
        logger.info(f"✅ Registered node type: {node_type} → {node_class.__name__}")
    
    
    @classmethod
    def get(cls, node_type: str) -> Optional[Type[Node]]:
        """
        Get node class by type.
        
        Args:
            node_type: Node type identifier
        
        Returns:
            Node class or None if not found
        """
        return cls._nodes.get(node_type)
    
    @classmethod
    def get_metadata(cls, node_type: str) -> Optional[Dict[str, any]]:
        """Get node metadata"""
        return cls._node_metadata.get(node_type)
    
    @classmethod
    def list_types(cls) -> List[str]:
        """List all registered node types"""
        return list(cls._nodes.keys())
    
    @classmethod
    def list_all(cls) -> Dict[str, Dict[str, any]]:
        """
        List all registered nodes with metadata.
        
        Returns:
            Dictionary of {node_type: metadata}
        """
        return {
            node_type: {
                **cls._node_metadata[node_type],
                "node_type": node_type,
            }
            for node_type in cls._nodes.keys()
        }
    
    @classmethod
    def list_all_with_details(cls) -> Dict[str, Dict[str, any]]:
        """
        List all registered nodes with full metadata including ports and config schema.
        
        Returns:
            Dictionary of {node_type: detailed_metadata}
        """
        from app.core.nodes.loader import get_node_port_definitions, get_node_config_schema
        
        detailed = {}
        for node_type, node_class in cls._nodes.items():
            metadata = cls._node_metadata.get(node_type, {})
            
            # Get port definitions
            port_defs = get_node_port_definitions(node_class)
            
            # Get config schema
            config_schema = get_node_config_schema(node_class)
            
            detailed[node_type] = {
                **metadata,
                "node_type": node_type,
                "input_ports": port_defs.get("input_ports", []),
                "output_ports": port_defs.get("output_ports", []),
                "config_schema": config_schema,
                "docstring": node_class.__doc__ or "",
            }
        
        return detailed
    
    @classmethod
    def is_registered(cls, node_type: str) -> bool:
        """Check if node type is registered"""
        return node_type in cls._nodes
    
    @classmethod
    def unregister(cls, node_type: str) -> bool:
        """
        Unregister a node type.
        
        Args:
            node_type: Node type to remove
        
        Returns:
            True if unregistered, False if not found
        """
        if node_type in cls._nodes:
            del cls._nodes[node_type]
            del cls._node_metadata[node_type]
            logger.info(f"🗑️ Unregistered node type: {node_type}")
            return True
        return False
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered nodes (used for testing)"""
        cls._nodes.clear()
        cls._node_metadata.clear()
        logger.warning("🗑️ Cleared all registered nodes")


# Decorator for easy registration
def register_node(
    node_type: str,
    display_name: Optional[str] = None,
    description: Optional[str] = None,
    icon: Optional[str] = None,
    category: Optional[str] = None,
    name: Optional[str] = None,  # Alias for display_name
    version: Optional[str] = None,  # For version tracking
):
    """
    Decorator to register a node class.
    
    Example:
        @register_node(
            node_type="http_request",
            display_name="HTTP Request",
            description="Make HTTP requests",
            category="actions"
        )
        class HTTPRequestNode(Node):
            async def execute(self, input_data):
                ...
    """
    def decorator(node_class: Type[Node]):
        # Use 'name' as alias for 'display_name' if provided
        _display_name = display_name or name or node_type
        
        NodeRegistry.register(
            node_type=node_type,
            node_class=node_class,
            display_name=_display_name,
            description=description,
            icon=icon,
            category=category,
        )
        return node_class
    
    return decorator
