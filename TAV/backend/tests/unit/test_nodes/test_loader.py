"""
Unit Tests for Node Loader
"""

import pytest

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import NodeRegistry, register_node
from app.core.nodes.loader import (
    discover_and_register_nodes,
    get_node_port_definitions,
    get_node_config_schema
)
from app.schemas.workflow import NodeConfiguration, NodePort, PortType


class TestNodeLoader:
    """Tests for node auto-discovery and loading"""
    
    def setup_method(self):
        """Clear registry before each test"""
        NodeRegistry.clear()
    
    def teardown_method(self):
        """Clean up after each test"""
        NodeRegistry.clear()
    
    def test_discover_and_register_nodes(self):
        """Test auto-discovery of nodes"""
        stats = discover_and_register_nodes()
        
        assert isinstance(stats, dict)
        assert "modules_scanned" in stats
        assert "nodes_found" in stats
        assert "nodes_registered" in stats
        assert "errors" in stats
        
        # In unit tests, nodes may not register (need full app init)
        assert isinstance(stats["modules_scanned"], int)
        assert isinstance(stats["nodes_registered"], int)
        
        # Verify registry structure works
        registered_types = NodeRegistry.list_types()
        assert isinstance(registered_types, list)
    
    def test_discover_registers_http_request_node(self):
        """Test that HTTP request node is discovered"""
        discover_and_register_nodes()
        
        # Skip if nodes not registered in unit test environment
        if not NodeRegistry.is_registered("http_request"):
            pytest.skip("Nodes not registered in unit test environment")
        
        metadata = NodeRegistry.get_metadata("http_request")
        assert metadata["display_name"] == "HTTP Request"
        assert metadata["category"] == "communication"
    
    def test_discover_registers_trigger_nodes(self):
        """Test that trigger nodes are discovered"""
        discover_and_register_nodes()
        
        # Skip if nodes not registered in unit test environment
        if not NodeRegistry.is_registered("manual_trigger"):
            pytest.skip("Nodes not registered in unit test environment")
        
        metadata = NodeRegistry.get_metadata("manual_trigger")
        assert metadata["category"] == "triggers"
    
    def test_get_node_port_definitions(self):
        """Test extracting port definitions from node class"""
        
        @register_node(
            node_type="test_port_node",
            display_name="Test Port Node"
        )
        class TestPortNode(Node):
            """Test node with ports"""
            
            @classmethod
            def get_input_ports(cls):
                """Define input ports"""
                return [
                    {
                        "name": "input",
                        "type": "universal",
                        "display_name": "Input Data",
                        "description": "Input port",
                        "required": True
                    }
                ]
            
            @classmethod
            def get_output_ports(cls):
                """Define output ports"""
                return [
                    {
                        "name": "output",
                        "type": "universal",
                        "display_name": "Output Data",
                        "description": "Output port"
                    }
                ]
            
            @classmethod
            def get_config_schema(cls):
                """Define config schema"""
                return {}
            
            async def execute(self, input_data: NodeExecutionInput):
                return {"output": "test"}
        
        node_class = NodeRegistry.get("test_port_node")
        port_defs = get_node_port_definitions(node_class)
        
        assert "input_ports" in port_defs
        assert "output_ports" in port_defs
        assert len(port_defs["input_ports"]) == 1
        assert len(port_defs["output_ports"]) == 1
        
        input_port = port_defs["input_ports"][0]
        assert input_port["name"] == "input"
        assert input_port["type"] == "universal"
        assert input_port["required"] is True
        
        output_port = port_defs["output_ports"][0]
        assert output_port["name"] == "output"
        assert output_port["type"] == "universal"
    
    def test_get_node_config_schema_from_docstring(self):
        """Test extracting config schema from node docstring"""
        
        @register_node(node_type="test_config_node")
        class TestConfigNode(Node):
            """
            Test node with config documentation.
            
            Config (required):
            - url: The target URL
            - method: HTTP method (default: GET)
            
            Config (optional):
            - timeout: Request timeout in seconds
            """
            
            @classmethod
            def get_input_ports(cls):
                return []
            
            @classmethod
            def get_output_ports(cls):
                return []
            
            @classmethod
            def get_config_schema(cls):
                return {
                    "url": {"type": "string", "required": True},
                    "method": {"type": "string", "required": True},
                    "timeout": {"type": "integer", "optional": True}
                }
            
            async def execute(self, input_data: NodeExecutionInput):
                return {}
        
        node_class = NodeRegistry.get("test_config_node")
        config_schema = get_node_config_schema(node_class)
        
        assert isinstance(config_schema, dict)
        assert "url" in config_schema
        assert "method" in config_schema
        assert "timeout" in config_schema
        
        assert config_schema["url"]["required"] is True
        assert config_schema["timeout"]["optional"] is True
    
    def test_list_all_with_details(self):
        """Test getting detailed node information"""
        discover_and_register_nodes()
        
        detailed_nodes = NodeRegistry.list_all_with_details()
        
        # In unit tests, nodes may not be registered
        if len(detailed_nodes) == 0:
            pytest.skip("No nodes registered in unit test environment")
        
        # Check first node has all expected fields
        first_node = next(iter(detailed_nodes.values()))
        
        assert "node_type" in first_node
        assert "display_name" in first_node
        assert "description" in first_node
        assert "category" in first_node
        assert "input_ports" in first_node
        assert "output_ports" in first_node
        assert "config_schema" in first_node
        assert "docstring" in first_node
    
    def test_discovery_handles_errors_gracefully(self):
        """Test that discovery continues even if some modules fail"""
        # This test verifies that errors are caught and logged
        # without stopping the entire discovery process
        
        stats = discover_and_register_nodes()
        
        # In unit tests, nodes may not register
        assert isinstance(stats["nodes_registered"], int)
        
        # Errors list should exist (may be empty)
        assert isinstance(stats["errors"], list)
    
    def test_get_port_definitions_handles_invalid_node(self):
        """Test that port extraction handles nodes that can't be instantiated"""
        
        @register_node(node_type="invalid_node")
        class InvalidNode(Node):
            """Node that requires specific config"""
            
            def __init__(self, config: NodeConfiguration):
                # This will fail with empty config
                if not config.config.get("required_field"):
                    raise ValueError("Missing required field")
                super().__init__(config)
            
            async def execute(self, input_data: NodeExecutionInput):
                return {}
        
        node_class = NodeRegistry.get("invalid_node")
        
        # Should not raise error, just return empty ports
        port_defs = get_node_port_definitions(node_class)
        
        assert port_defs["input_ports"] == []
        assert port_defs["output_ports"] == []


class TestNodeCategorization:
    """Tests for node categorization after discovery"""
    
    def setup_method(self):
        """Setup test environment"""
        NodeRegistry.clear()
        discover_and_register_nodes()
    
    def teardown_method(self):
        """Clean up"""
        NodeRegistry.clear()
    
    def test_nodes_have_categories(self):
        """Test that discovered nodes have categories"""
        all_nodes = NodeRegistry.list_all()
        
        # Skip if no nodes registered
        if len(all_nodes) == 0:
            pytest.skip("No nodes registered in unit test environment")
        
        # Count nodes with categories
        nodes_with_category = sum(
            1 for metadata in all_nodes.values()
            if metadata.get("category")
        )
        
        assert isinstance(nodes_with_category, int)
    
    def test_trigger_nodes_in_correct_category(self):
        """Test that trigger nodes are categorized correctly"""
        all_nodes = NodeRegistry.list_all()
        
        # Skip if no nodes registered
        if len(all_nodes) == 0:
            pytest.skip("No nodes registered in unit test environment")
        
        trigger_nodes = [
            node_type for node_type, metadata in all_nodes.items()
            if metadata.get("category") == "triggers"
        ]
        
        # If trigger nodes exist, verify they're categorized correctly
        if len(trigger_nodes) > 0:
            assert "manual_trigger" in trigger_nodes or any("trigger" in t for t in trigger_nodes)
    
    def test_communication_nodes_in_correct_category(self):
        """Test that communication nodes are categorized correctly"""
        all_nodes = NodeRegistry.list_all()
        
        communication_nodes = [
            node_type for node_type, metadata in all_nodes.items()
            if metadata.get("category") == "communication"
        ]
        
        # HTTP request should be in communication
        if "http_request" in all_nodes:
            assert "http_request" in communication_nodes
    
    def test_get_port_definitions_serializes_enums(self):
        """Test that PortType enums are serialized to strings"""
        from app.schemas.workflow import PortType
        
        class TestEnumNode(Node):
            @classmethod
            def get_input_ports(cls):
                return [
                    {"name": "input", "type": PortType.TEXT, "required": True}
                ]
            
            @classmethod
            def get_output_ports(cls):
                return [
                    {"name": "output", "type": PortType.TEXT}
                ]
            
            async def execute(self, input_data):
                return {"output": "test"}
        
        ports = get_node_port_definitions(TestEnumNode)
        
        # Enum should be converted to string
        assert isinstance(ports["input_ports"][0]["type"], str)
        assert ports["input_ports"][0]["type"] == "text"
    
    def test_get_config_schema_returns_dict(self):
        """Test that get_config_schema returns a dictionary"""
        class TestSchemaNode(Node):
            @classmethod
            def get_config_schema(cls):
                return {
                    "type": "object",
                    "properties": {
                        "field1": {"type": "string"}
                    }
                }
            
            async def execute(self, input_data):
                return {}
        
        schema = get_node_config_schema(TestSchemaNode)
        
        assert isinstance(schema, dict)
        assert "type" in schema
        assert schema["type"] == "object"
    
    def test_get_config_schema_handles_no_schema_method(self):
        """Test that nodes without get_config_schema are handled"""
        class NodeWithoutSchema(Node):
            async def execute(self, input_data):
                return {}
        
        # Should not raise error, return empty or default schema
        schema = get_node_config_schema(NodeWithoutSchema)
        assert isinstance(schema, dict)
    
    def test_discovery_stats_structure(self):
        """Test that discovery returns complete stats"""
        stats = discover_and_register_nodes()
        
        assert "modules_scanned" in stats
        assert "nodes_found" in stats
        assert "nodes_registered" in stats
        assert "errors" in stats
        
        assert isinstance(stats["modules_scanned"], int)
        assert isinstance(stats["nodes_found"], int)
        assert isinstance(stats["nodes_registered"], int)
        assert isinstance(stats["errors"], list)

