"""
Unit tests for Node Base Class

Tests:
- Node initialization
- Port building
- Input validation
- Resource detection
- Variable resolution helpers
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from app.core.nodes.base import Node, NodeExecutionInput
from app.schemas.workflow import NodeConfiguration, NodePort, PortType


# Define a concrete implementation of Node for testing
class ConcreteTestNode(Node):
    """Concrete node implementation for testing"""
    
    # Tell pytest this is NOT a test class
    __test__ = False
    
    @classmethod
    def get_input_ports(cls):
        return [
            {
                "name": "required_input",
                "type": PortType.TEXT,
                "required": True
            },
            {
                "name": "optional_input",
                "type": PortType.TEXT,
                "required": False,
                "default_value": "default"
            }
        ]
    
    @classmethod
    def get_output_ports(cls):
        return [
            {
                "name": "result",
                "type": PortType.TEXT
            }
        ]
    
    @classmethod
    def get_config_schema(cls):
        return {}
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        return {"result": "success"}


@pytest.fixture
def node_config():
    """Create test node configuration"""
    return NodeConfiguration(
        node_id="test-node",
        node_type="test_node",  # Fixed: was 'type'
        name="Test Node",  # Added: required field
        category="processing",  # Fixed: was 'testing' (invalid enum)
        config={
            "test_key": "test_value",
            "variable_ref": "{{var.key}}"
        }
    )


@pytest.fixture
def node_instance(node_config):
    """Create test node instance"""
    return ConcreteTestNode(node_config)


class TestNodeInitialization:
    """Test node initialization logic"""
    
    def test_init_sets_attributes(self, node_config):
        """Test that __init__ sets basic attributes"""
        node = ConcreteTestNode(node_config)
        
        assert node.node_id == "test-node"
        assert node.node_type == "test_node"
        assert node.category == "processing"  # Fixed: was "testing"
        assert node.config == node_config.config
    
    def test_init_builds_ports(self, node_config):
        """Test that ports are built from definitions"""
        node = ConcreteTestNode(node_config)
        
        # Check input ports
        assert len(node.input_ports) == 2
        assert node.input_ports[0].name == "required_input"
        assert node.input_ports[0].required is True
        assert node.input_ports[1].name == "optional_input"
        assert node.input_ports[1].default_value == "default"
        
        # Check output ports
        assert len(node.output_ports) == 1
        assert node.output_ports[0].name == "result"


class TestInputValidation:
    """Test input validation logic"""
    
    def test_validate_inputs_success(self, node_instance):
        """Test validation passes when all required inputs present"""
        inputs = {
            "required_input": "value",
            "optional_input": "value"
        }
        
        errors = node_instance.validate_inputs(inputs)
        assert len(errors) == 0
    
    def test_validate_inputs_missing_optional(self, node_instance):
        """Test validation passes when optional inputs missing (has default)"""
        inputs = {
            "required_input": "value"
        }
        
        errors = node_instance.validate_inputs(inputs)
        assert len(errors) == 0
    
    def test_validate_inputs_missing_required(self, node_instance):
        """Test validation fails when required inputs missing"""
        inputs = {
            "optional_input": "value"
        }
        
        errors = node_instance.validate_inputs(inputs)
        assert len(errors) == 1
        assert "required_input" in errors[0]


class TestPortHelpers:
    """Test helper methods for accessing ports"""
    
    def test_get_input_port(self, node_instance):
        """Test getting input port by name"""
        port = node_instance.get_input_port("required_input")
        assert port is not None
        assert port.name == "required_input"
        
        port = node_instance.get_input_port("non_existent")
        assert port is None
    
    def test_get_output_port(self, node_instance):
        """Test getting output port by name"""
        port = node_instance.get_output_port("result")
        assert port is not None
        assert port.name == "result"
        
        port = node_instance.get_output_port("non_existent")
        assert port is None


class TestVariableResolution:
    """Test variable resolution helpers"""
    
    @pytest.fixture
    def execution_input(self, node_config):
        """Create execution input with variables"""
        return NodeExecutionInput(
            ports={},
            workflow_id="wf-1",
            execution_id="exec-1",
            node_id="node-1",
            variables={
                "user": {"name": "Alice", "role": "admin"},
                "count": 42
            },
            config=node_config.config,
            credentials={
                1: {"api_key": "secret-key"}
            }
        )
    
    def test_resolve_config_simple(self, node_instance, execution_input):
        """Test resolving simple config value"""
        val = node_instance.resolve_config(execution_input, "test_key")
        assert val == "test_value"
    
    def test_resolve_config_with_template(self, node_instance, execution_input):
        """Test resolving config value with template"""
        # Mock the resolve_config_value helper
        with patch('app.core.nodes.variables.resolve_config_value') as mock_resolve:
            mock_resolve.return_value = "resolved_value"
            
            val = node_instance.resolve_config(execution_input, "variable_ref")
            
            mock_resolve.assert_called_once()
            assert val == "resolved_value"
    
    def test_resolve_variable(self, node_instance, execution_input):
        """Test resolving variable path"""
        with patch('app.core.nodes.variables.resolve_variable') as mock_resolve:
            mock_resolve.return_value = "Alice"
            
            val = node_instance.resolve_variable(execution_input, "user.name")
            
            mock_resolve.assert_called_with("user.name", execution_input.variables)
            assert val == "Alice"
    
    def test_resolve_template(self, node_instance, execution_input):
        """Test resolving template string"""
        with patch('app.core.nodes.variables.resolve_template') as mock_resolve:
            mock_resolve.return_value = "Hello Alice"
            
            val = node_instance.resolve_template(execution_input, "Hello {{user.name}}")
            
            mock_resolve.assert_called_with("Hello {{user.name}}", execution_input.variables)
            assert val == "Hello Alice"
    
    def test_resolve_credential(self, node_instance, execution_input):
        """Test resolving credential"""
        # 1. Setup config to point to credential ID 1
        execution_input.config["cred_id"] = 1
        
        # 2. Resolve
        cred = node_instance.resolve_credential(execution_input, "cred_id")
        
        # 3. Assert
        assert cred is not None
        assert cred["api_key"] == "secret-key"
    
    def test_resolve_credential_missing(self, node_instance, execution_input):
        """Test resolving missing credential"""
        execution_input.config["cred_id"] = 999  # Doesn't exist
        
        cred = node_instance.resolve_credential(execution_input, "cred_id")
        
        assert cred is None

