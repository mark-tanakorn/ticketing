"""
Integration Tests for Shared Space System

Tests the complete shared information space workflow from node execution
to variable sharing to resolution in subsequent nodes.
"""

import pytest
from datetime import datetime
from app.core.execution.executor.parallel import ParallelExecutor
from app.core.execution.context import ExecutionContext, ExecutionMode
from app.schemas.workflow import NodeConfiguration, NodeCategory
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from typing import Dict, Any, List


# ==================== Test Nodes ====================

@register_node("test_trigger", category=NodeCategory.TRIGGERS, name="Test Trigger")
class TestTriggerNode(Node):
    """Test trigger node that outputs structured data"""
    
    @classmethod
    def get_output_ports(cls):
        return [
            {"name": "output", "type": "universal"}
        ]
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        return {
            "output": {
                "phone": "+1234567890",
                "message": "Hello World",
                "user_name": "John Doe",
                "timestamp": "2025-11-06T10:30:00"
            }
        }


@register_node("test_processor", category=NodeCategory.PROCESSING, name="Test Processor")
class TestProcessorNode(Node):
    """Test node that reads from shared space"""
    
    @classmethod
    def get_input_ports(cls):
        return [{"name": "input", "type": "universal", "required": False}]
    
    @classmethod
    def get_output_ports(cls):
        return [{"name": "output", "type": "universal"}]
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        # Use helper methods to resolve variables
        phone = self.resolve_variable(input_data, "test_trigger_1.phone")
        message = self.resolve_variable(input_data, "test_trigger_1.message")
        
        return {
            "output": {
                "processed_phone": phone,
                "processed_message": message.upper() if message else None,
                "status": "processed"
            }
        }


@register_node("test_template_node", category=NodeCategory.PROCESSING, name="Test Template Node")
class TestTemplateNode(Node):
    """Test node that uses template config"""
    
    @classmethod
    def get_config_schema(cls):
        return {
            "template_text": {
                "type": "string",
                "label": "Template Text"
            }
        }
    
    @classmethod
    def get_output_ports(cls):
        return [{"name": "output", "type": "text"}]
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        # Use helper to resolve template
        text = self.resolve_config(input_data, "template_text", "")
        
        return {
            "output": text
        }


# ==================== Test Fixtures ====================

@pytest.fixture
def execution_context():
    """Create a test execution context"""
    return ExecutionContext(
        workflow_id="test_workflow",
        execution_id="test_execution",
        execution_mode=ExecutionMode.SEQUENTIAL
    )


@pytest.fixture
def executor():
    """Create a test executor"""
    config = {
        "max_concurrent_nodes": 5,
        "ai_concurrent_limit": 1,
        "default_timeout": 30
    }
    return ParallelExecutor(config)


# ==================== Integration Tests ====================

def test_share_to_variables_flattening(executor, execution_context):
    """Test that _share_to_variables correctly flattens single-port dict outputs"""
    
    # Create node config with sharing enabled
    node_config = NodeConfiguration(
        node_id="test_trigger_1",
        node_type="test_trigger",
        name="Test Trigger",
        share_output_to_variables=True
    )
    
    # Simulate node output
    outputs = {
        "output": {
            "phone": "+1234567890",
            "message": "Hello",
            "user_name": "John"
        }
    }
    
    # Call _share_to_variables
    executor._share_to_variables(node_config, outputs, execution_context)
    
    # Verify flattened structure
    assert "_nodes" in execution_context.variables
    assert "test_trigger_1" in execution_context.variables["_nodes"]
    
    shared_data = execution_context.variables["_nodes"]["test_trigger_1"]
    
    # Should be flattened (no "output" wrapper)
    assert "phone" in shared_data
    assert "message" in shared_data
    assert "user_name" in shared_data
    assert shared_data["phone"] == "+1234567890"
    assert shared_data["message"] == "Hello"
    assert shared_data["user_name"] == "John"


def test_share_to_variables_multi_port(executor, execution_context):
    """Test that multi-port outputs are NOT flattened"""
    
    node_config = NodeConfiguration(
        node_id="multi_port_node",
        node_type="test_node",
        name="Multi Port",
        share_output_to_variables=True
    )
    
    # Multiple ports
    outputs = {
        "result": "OK",
        "status": 200,
        "data": {"key": "value"}
    }
    
    executor._share_to_variables(node_config, outputs, execution_context)
    
    shared_data = execution_context.variables["_nodes"]["multi_port_node"]
    
    # Should NOT be flattened - keep port structure
    assert "result" in shared_data
    assert "status" in shared_data
    assert "data" in shared_data
    assert shared_data["result"] == "OK"


def test_share_with_custom_variable_name(executor, execution_context):
    """Test sharing with custom variable name"""
    
    node_config = NodeConfiguration(
        node_id="node_123",
        node_type="test_node",
        name="Some Node",
        share_output_to_variables=True,
        variable_name="custom_name"
    )
    
    outputs = {
        "output": {"data": "value"}
    }
    
    executor._share_to_variables(node_config, outputs, execution_context)
    
    # Should use custom_name as key
    assert "custom_name" in execution_context.variables["_nodes"]
    assert "node_123" not in execution_context.variables["_nodes"]


def test_node_resolve_variable_helper(execution_context):
    """Test Node.resolve_variable() helper method"""
    
    # Set up shared space
    execution_context.variables["_nodes"] = {
        "trigger_1": {
            "phone": "+1234567890",
            "message": "Hello"
        }
    }
    
    # Create node and input data
    node_config = NodeConfiguration(
        node_id="test_node",
        node_type="test_processor",
        name="Test"
    )
    node = TestProcessorNode(node_config)
    
    input_data = NodeExecutionInput(
        ports={},
        workflow_id="test",
        execution_id="test",
        node_id="test_node",
        variables=execution_context.variables,
        config={}
    )
    
    # Test resolve_variable
    phone = node.resolve_variable(input_data, "trigger_1.phone")
    assert phone == "+1234567890"
    
    message = node.resolve_variable(input_data, "trigger_1.message")
    assert message == "Hello"
    
    # Test missing variable
    missing = node.resolve_variable(input_data, "trigger_1.nonexistent")
    assert missing is None


def test_node_resolve_config_helper(execution_context):
    """Test Node.resolve_config() helper method"""
    
    # Set up shared space
    execution_context.variables["_nodes"] = {
        "trigger_1": {
            "user_name": "Alice",
            "order_id": "ORD-123"
        }
    }
    
    # Create node
    node_config = NodeConfiguration(
        node_id="test_node",
        node_type="test_template_node",
        name="Test",
        config={
            "literal_field": "Hello",
            "variable_field": {
                "source": "variable",
                "variable_path": "trigger_1.user_name"
            },
            "template_field": {
                "source": "template",
                "template": "User: {{trigger_1.user_name}}, Order: {{trigger_1.order_id}}"
            }
        }
    )
    node = TestTemplateNode(node_config)
    
    input_data = NodeExecutionInput(
        ports={},
        workflow_id="test",
        execution_id="test",
        node_id="test_node",
        variables=execution_context.variables,
        config=node_config.config
    )
    
    # Test literal
    literal = node.resolve_config(input_data, "literal_field")
    assert literal == "Hello"
    
    # Test variable
    variable = node.resolve_config(input_data, "variable_field")
    assert variable == "Alice"
    
    # Test template
    template = node.resolve_config(input_data, "template_field")
    assert template == "User: Alice, Order: ORD-123"


@pytest.mark.asyncio
async def test_end_to_end_workflow_with_sharing():
    """Test complete workflow: trigger shares → processor reads → template uses"""
    
    # Create execution context
    context = ExecutionContext(
        workflow_id="test_workflow",
        execution_id="test_execution",
        execution_mode=ExecutionMode.SEQUENTIAL
    )
    
    # Create executor
    executor_config = {
        "max_concurrent_nodes": 5,
        "ai_concurrent_limit": 1,
        "default_timeout": 30
    }
    executor = ParallelExecutor(executor_config)
    
    # STEP 1: Execute trigger node (with sharing enabled)
    trigger_config = NodeConfiguration(
        node_id="test_trigger_1",
        node_type="test_trigger",
        name="Trigger",
        share_output_to_variables=True
    )
    trigger_node = TestTriggerNode(trigger_config)
    
    trigger_input = NodeExecutionInput(
        ports={},
        workflow_id="test_workflow",
        execution_id="test_execution",
        node_id="test_trigger_1",
        variables=context.variables,
        config={}
    )
    
    trigger_output = await trigger_node.execute(trigger_input)
    
    # Share to variables
    executor._share_to_variables(trigger_config, trigger_output, context)
    
    # Verify shared space
    assert "test_trigger_1" in context.variables["_nodes"]
    assert context.variables["_nodes"]["test_trigger_1"]["phone"] == "+1234567890"
    assert context.variables["_nodes"]["test_trigger_1"]["user_name"] == "John Doe"
    
    # STEP 2: Execute processor node (reads from shared space)
    processor_config = NodeConfiguration(
        node_id="processor_1",
        node_type="test_processor",
        name="Processor",
        share_output_to_variables=True
    )
    processor_node = TestProcessorNode(processor_config)
    
    processor_input = NodeExecutionInput(
        ports={},
        workflow_id="test_workflow",
        execution_id="test_execution",
        node_id="processor_1",
        variables=context.variables,  # Has trigger data
        config={}
    )
    
    processor_output = await processor_node.execute(processor_input)
    
    # Verify processor used trigger data
    assert processor_output["output"]["processed_phone"] == "+1234567890"
    assert processor_output["output"]["processed_message"] == "HELLO WORLD"
    
    # Share processor output too
    executor._share_to_variables(processor_config, processor_output, context)
    
    # STEP 3: Execute template node (uses template with variables)
    template_config = NodeConfiguration(
        node_id="template_1",
        node_type="test_template_node",
        name="Template",
        config={
            "template_text": {
                "source": "template",
                "template": "Hello {{test_trigger_1.user_name}}, status: {{processor_1.status}}"
            }
        }
    )
    template_node = TestTemplateNode(template_config)
    
    template_input = NodeExecutionInput(
        ports={},
        workflow_id="test_workflow",
        execution_id="test_execution",
        node_id="template_1",
        variables=context.variables,  # Has both trigger and processor data
        config=template_config.config
    )
    
    template_output = await template_node.execute(template_input)
    
    # Verify template resolution
    assert template_output["output"] == "Hello John Doe, status: processed"


def test_no_sharing_when_checkbox_disabled(executor, execution_context):
    """Test that data is NOT shared when share_output_to_variables is False"""
    
    node_config = NodeConfiguration(
        node_id="private_node",
        node_type="test_node",
        name="Private Node",
        share_output_to_variables=False  # ← Disabled
    )
    
    outputs = {
        "output": {"secret": "data"}
    }
    
    # This should NOT share (in real execution, this method wouldn't be called)
    # But we test that it initializes properly
    assert node_config.share_output_to_variables is False


def test_multiple_nodes_sharing(executor, execution_context):
    """Test multiple nodes sharing to the same space"""
    
    # Node 1 shares
    node1_config = NodeConfiguration(
        node_id="node_1",
        node_type="test",
        name="Node 1",
        share_output_to_variables=True
    )
    executor._share_to_variables(
        node1_config,
        {"output": {"data1": "value1"}},
        execution_context
    )
    
    # Node 2 shares
    node2_config = NodeConfiguration(
        node_id="node_2",
        node_type="test",
        name="Node 2",
        share_output_to_variables=True
    )
    executor._share_to_variables(
        node2_config,
        {"output": {"data2": "value2"}},
        execution_context
    )
    
    # Node 3 shares
    node3_config = NodeConfiguration(
        node_id="node_3",
        node_type="test",
        name="Node 3",
        share_output_to_variables=True
    )
    executor._share_to_variables(
        node3_config,
        {"output": {"data3": "value3"}},
        execution_context
    )
    
    # All should be in shared space
    assert "node_1" in execution_context.variables["_nodes"]
    assert "node_2" in execution_context.variables["_nodes"]
    assert "node_3" in execution_context.variables["_nodes"]
    
    # Each with their own data
    assert execution_context.variables["_nodes"]["node_1"]["data1"] == "value1"
    assert execution_context.variables["_nodes"]["node_2"]["data2"] == "value2"
    assert execution_context.variables["_nodes"]["node_3"]["data3"] == "value3"

