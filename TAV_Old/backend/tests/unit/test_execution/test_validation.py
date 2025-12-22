"""
Unit tests for Workflow Validation

Tests:
- Schema validation (Pydantic)
- Structure validation (connectivity, unique IDs)
- Format versioning
"""

import pytest
from pydantic import ValidationError

from app.schemas.workflow import (
    WorkflowDefinition,
    NodeConfiguration,
    Connection,
    PortType,
    NodeCategory,
    WorkflowFormatVersion
)


@pytest.fixture
def valid_workflow_data():
    """Create valid workflow dictionary"""
    return {
        "workflow_id": "wf-1",
        "name": "Valid Workflow",
        "description": "Test",
        "format_version": "2.0.0",
        "nodes": [
            {
                "node_id": "node-1",
                "node_type": "start",
                "name": "Start",
                "category": "triggers",
                "output_ports": [{"name": "signal", "type": "signal"}]
            },
            {
                "node_id": "node-2",
                "node_type": "end",
                "name": "End",
                "category": "workflow",
                "input_ports": [{"name": "signal", "type": "signal"}]
            }
        ],
        "connections": [
            {
                "source_node_id": "node-1",
                "source_port": "signal",
                "target_node_id": "node-2",
                "target_port": "signal"
            }
        ]
    }


class TestSchemaValidation:
    """Test Pydantic schema validation"""
    
    def test_valid_workflow_schema(self, valid_workflow_data):
        """Test that valid data parses correctly"""
        wf = WorkflowDefinition(**valid_workflow_data)
        assert wf.workflow_id == "wf-1"
        assert len(wf.nodes) == 2
        assert len(wf.connections) == 1
    
    def test_invalid_format_version(self, valid_workflow_data):
        """Test that invalid format version raises error"""
        valid_workflow_data["format_version"] = "0.0.1"
        
        with pytest.raises(ValidationError) as exc:
            WorkflowDefinition(**valid_workflow_data)
        
        assert "Unsupported format version" in str(exc.value)
    
    def test_missing_required_fields(self):
        """Test missing required fields"""
        with pytest.raises(ValidationError):
            WorkflowDefinition(workflow_id="wf-1")  # Missing name


class TestStructureValidation:
    """Test structural validation (validate_structure method)"""
    
    def test_valid_structure(self, valid_workflow_data):
        """Test that valid structure returns no errors"""
        wf = WorkflowDefinition(**valid_workflow_data)
        errors = wf.validate_structure()
        assert len(errors) == 0
    
    def test_duplicate_node_ids(self, valid_workflow_data):
        """Test detection of duplicate node IDs"""
        # Add duplicate node
        valid_workflow_data["nodes"].append({
            "node_id": "node-1",  # Duplicate!
            "node_type": "test",
            "name": "Duplicate",
            "category": "processing"
        })
        
        wf = WorkflowDefinition(**valid_workflow_data)
        errors = wf.validate_structure()
        
        assert len(errors) > 0
        assert "Duplicate node IDs" in errors[0]
    
    def test_connection_to_unknown_node(self, valid_workflow_data):
        """Test connection to non-existent node"""
        valid_workflow_data["connections"].append({
            "source_node_id": "node-1",
            "source_port": "signal",
            "target_node_id": "node-99",  # Doesn't exist
            "target_port": "signal"
        })
        
        wf = WorkflowDefinition(**valid_workflow_data)
        errors = wf.validate_structure()
        
        assert len(errors) > 0
        assert "unknown target node" in errors[0]
    
    def test_connection_to_unknown_port(self, valid_workflow_data):
        """Test connection to non-existent port"""
        valid_workflow_data["connections"].append({
            "source_node_id": "node-1",
            "source_port": "fake_port",  # Doesn't exist
            "target_node_id": "node-2",
            "target_port": "signal"
        })
        
        wf = WorkflowDefinition(**valid_workflow_data)
        errors = wf.validate_structure()
        
        assert len(errors) > 0
        assert "unknown source port" in errors[0]


class TestNodeSmartDefaults:
    """Test NodeConfiguration smart defaults"""
    
    def test_smart_defaults_applied(self):
        """Test that defaults are applied when ports are None"""
        node = NodeConfiguration(
            node_id="test",
            node_type="processing",
            name="Test",
            category="processing"
            # ports are None by default
        )
        
        # Should have 1 input and 1 output
        assert len(node.input_ports) == 1
        assert node.input_ports[0].name == "input"
        
        assert len(node.output_ports) == 1
        assert node.output_ports[0].name == "output"
    
    def test_trigger_defaults(self):
        """Test trigger defaults (no input)"""
        node = NodeConfiguration(
            node_id="test",
            node_type="trigger",
            name="Trigger",
            category="triggers"
        )
        
        # Should have NO input, 1 output
        assert len(node.input_ports) == 0
        assert len(node.output_ports) == 1
    
    def test_explicit_empty_ports(self):
        """Test explicit empty ports overrides defaults"""
        node = NodeConfiguration(
            node_id="test",
            node_type="processing",
            name="Test",
            category="processing",
            input_ports=[]  # Explicitly empty
        )
        
        assert len(node.input_ports) == 0
        assert len(node.output_ports) == 1  # Default

