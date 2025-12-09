"""
Unit Tests for Node Registry
"""

import pytest

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import NodeRegistry, register_node
from app.schemas.workflow import NodeConfiguration


class MockNode(Node):
    """Mock node for testing"""
    
    async def execute(self, input_data: NodeExecutionInput):
        return {"output": "mock result"}


class TestNodeRegistry:
    """Tests for NodeRegistry"""
    
    def setup_method(self):
        """Clear registry before each test"""
        NodeRegistry.clear()
    
    def teardown_method(self):
        """Clean up after each test"""
        NodeRegistry.clear()
    
    def test_register_node_class(self):
        """Test registering a node class"""
        NodeRegistry.register(
            node_type="test_node",
            node_class=MockNode,
            display_name="Test Node",
            description="Test node description",
            category="processing"
        )
        
        assert NodeRegistry.is_registered("test_node")
        assert NodeRegistry.get("test_node") == MockNode
    
    def test_get_node_metadata(self):
        """Test getting node metadata"""
        NodeRegistry.register(
            node_type="test_node",
            node_class=MockNode,
            display_name="Test Node",
            description="Test description",
            icon="test-icon",
            category="processing"
        )
        
        metadata = NodeRegistry.get_metadata("test_node")
        
        assert metadata is not None
        assert metadata["display_name"] == "Test Node"
        assert metadata["description"] == "Test description"
        assert metadata["icon"] == "test-icon"
        assert metadata["category"] == "processing"  # Fixed: was "testing"
        assert metadata["class_name"] == "MockNode"
    
    def test_list_types(self):
        """Test listing all node types"""
        NodeRegistry.register("node1", MockNode, "Node 1")
        NodeRegistry.register("node2", MockNode, "Node 2")
        
        types = NodeRegistry.list_types()
        
        assert len(types) == 2
        assert "node1" in types
        assert "node2" in types
    
    def test_list_all(self):
        """Test listing all nodes with metadata"""
        NodeRegistry.register("test_node", MockNode, "Test Node", "Description")
        
        all_nodes = NodeRegistry.list_all()
        
        assert "test_node" in all_nodes
        assert all_nodes["test_node"]["node_type"] == "test_node"
        assert all_nodes["test_node"]["display_name"] == "Test Node"
        assert all_nodes["test_node"]["description"] == "Description"
    
    def test_unregister(self):
        """Test unregistering a node"""
        NodeRegistry.register("test_node", MockNode)
        
        assert NodeRegistry.is_registered("test_node")
        
        result = NodeRegistry.unregister("test_node")
        
        assert result is True
        assert not NodeRegistry.is_registered("test_node")
    
    def test_unregister_nonexistent(self):
        """Test unregistering a node that doesn't exist"""
        result = NodeRegistry.unregister("nonexistent")
        assert result is False
    
    def test_clear_registry(self):
        """Test clearing the registry"""
        NodeRegistry.register("node1", MockNode)
        NodeRegistry.register("node2", MockNode)
        
        assert len(NodeRegistry.list_types()) == 2
        
        NodeRegistry.clear()
        
        assert len(NodeRegistry.list_types()) == 0
    
    def test_register_decorator(self):
        """Test the @register_node decorator"""
        
        @register_node(
            node_type="decorated_node",
            display_name="Decorated Node",
            description="Node registered via decorator",
            category="processing"
        )
        class DecoratedNode(Node):
            async def execute(self, input_data: NodeExecutionInput):
                return {"output": "decorated"}
        
        assert NodeRegistry.is_registered("decorated_node")
        assert NodeRegistry.get("decorated_node") == DecoratedNode
        
        metadata = NodeRegistry.get_metadata("decorated_node")
        assert metadata["display_name"] == "Decorated Node"
        assert metadata["description"] == "Node registered via decorator"
        assert metadata["category"] == "processing"  # Fixed: was "testing"
    
    def test_register_decorator_with_name_alias(self):
        """Test decorator with 'name' parameter as alias for display_name"""
        
        @register_node(
            node_type="alias_node",
            name="Alias Node",  # Using 'name' instead of 'display_name'
            category="processing"
        )
        class AliasNode(Node):
            async def execute(self, input_data: NodeExecutionInput):
                return {}
        
        metadata = NodeRegistry.get_metadata("alias_node")
        assert metadata["display_name"] == "Alias Node"
    
    def test_register_duplicate_warning(self, caplog):
        """Test that registering duplicate node type logs warning"""
        NodeRegistry.register("test_node", MockNode)
        
        # Register again with same type
        with caplog.at_level("WARNING"):
            NodeRegistry.register("test_node", MockNode)
        
        assert "Overwriting existing node type" in caplog.text
    
    def test_register_non_node_class_raises_error(self):
        """Test that registering non-Node class raises ValueError"""
        
        class NotANode:
            pass
        
        with pytest.raises(ValueError, match="must inherit from Node"):
            NodeRegistry.register("invalid", NotANode)
    
    def test_get_nonexistent_node(self):
        """Test getting a node that doesn't exist"""
        node_class = NodeRegistry.get("nonexistent")
        assert node_class is None
    
    def test_get_metadata_nonexistent(self):
        """Test getting metadata for nonexistent node"""
        metadata = NodeRegistry.get_metadata("nonexistent")
        assert metadata is None

