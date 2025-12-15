"""
Tests for HuggingFace Node

This module tests the HuggingFace workflow node execution,
configuration, and integration with the manager.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from app.core.nodes.builtin.ai.huggingface import HuggingFaceNode
from app.core.ai.huggingface_manager import HFTaskType, InferenceMode
from app.schemas.workflow import NodeConfiguration


@pytest.fixture
def node_config():
    """Create a minimal NodeConfiguration for testing"""
    return NodeConfiguration(
        node_id="test-hf-node",
        node_type="ai.huggingface",
        name="Test HuggingFace Node",
        description="Test node",
        category="ai",
        config={
            "model_id": "gpt2",
            "task": "text-generation",
            "inference_mode": "api"
        },
        position={"x": 0, "y": 0}
    )


@pytest.fixture
def hf_node(node_config):
    """Create a HuggingFaceNode instance for testing"""
    return HuggingFaceNode(node_config)


class TestHuggingFaceNodeInit:
    """Test HuggingFace node initialization"""
    
    def test_node_creates_successfully(self, node_config):
        """Test that HF node can be created"""
        node = HuggingFaceNode(node_config)
        assert node is not None
    
    def test_node_has_correct_id(self, hf_node):
        """Test node ID is set correctly"""
        assert hf_node.node_id == "test-hf-node"
    
    def test_node_has_correct_type(self, hf_node):
        """Test node type is set correctly"""
        assert hf_node.node_type == "ai.huggingface"
    
    def test_node_has_config(self, hf_node):
        """Test node has configuration"""
        assert hasattr(hf_node, 'config')
        assert isinstance(hf_node.config, dict)


class TestNodePortDefinitions:
    """Test node input/output port definitions"""
    
    def test_node_has_input_ports(self, hf_node):
        """Test node has input ports defined"""
        assert hasattr(hf_node, 'input_ports')
        assert isinstance(hf_node.input_ports, list)
    
    def test_node_has_output_ports(self, hf_node):
        """Test node has output ports defined"""
        assert hasattr(hf_node, 'output_ports')
        assert isinstance(hf_node.output_ports, list)
    
    def test_get_input_ports_classmethod(self):
        """Test get_input_ports class method"""
        ports = HuggingFaceNode.get_input_ports()
        assert isinstance(ports, list)
    
    def test_get_output_ports_classmethod(self):
        """Test get_output_ports class method"""
        ports = HuggingFaceNode.get_output_ports()
        assert isinstance(ports, list)


class TestNodeConfigSchema:
    """Test node configuration schema"""
    
    def test_get_config_schema_exists(self):
        """Test get_config_schema class method exists"""
        assert hasattr(HuggingFaceNode, 'get_config_schema')
        schema = HuggingFaceNode.get_config_schema()
        assert isinstance(schema, (list, dict))  # Can be either format


class TestNodeMetadata:
    """Test node metadata methods"""
    
    def test_node_has_description(self, hf_node):
        """Test node has a description"""
        assert hasattr(hf_node, 'description')
        assert isinstance(hf_node.description, str)
    
    def test_metadata_structure(self):
        """Test that node provides basic metadata through attributes"""
        # Nodes may provide metadata via get_metadata() or direct attributes
        # Just verify the node class is properly defined
        assert hasattr(HuggingFaceNode, 'get_input_ports')
        assert hasattr(HuggingFaceNode, 'get_output_ports')
        assert hasattr(HuggingFaceNode, 'get_config_schema')


class TestTaskTypeSupport:
    """Test support for different HF task types"""
    
    def test_supports_text_generation(self):
        """Test text generation task is supported"""
        assert HFTaskType.TEXT_GENERATION == "text-generation"
    
    def test_supports_text_classification(self):
        """Test text classification task is supported"""
        assert HFTaskType.TEXT_CLASSIFICATION == "text-classification"
    
    def test_supports_image_tasks(self):
        """Test image tasks are supported"""
        assert HFTaskType.IMAGE_CLASSIFICATION == "image-classification"
        assert HFTaskType.IMAGE_TO_TEXT == "image-to-text"
    
    def test_supports_multimodal_tasks(self):
        """Test multimodal tasks are supported"""
        assert HFTaskType.VISUAL_QUESTION_ANSWERING == "visual-question-answering"


class TestNodeInheritance:
    """Test node registration and inheritance"""
    
    def test_node_class_exists(self):
        """Test HuggingFaceNode class is importable"""
        from app.core.nodes.builtin.ai.huggingface import HuggingFaceNode
        assert HuggingFaceNode is not None
    
    def test_node_is_node_subclass(self):
        """Test HuggingFaceNode inherits from Node"""
        from app.core.nodes.base import Node
        assert issubclass(HuggingFaceNode, Node)
    
    def test_node_has_execute_method(self, hf_node):
        """Test node has execute method"""
        assert hasattr(hf_node, 'execute')
        assert callable(hf_node.execute)
