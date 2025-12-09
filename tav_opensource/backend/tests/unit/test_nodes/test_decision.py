"""
Unit tests for DecisionNode

Tests:
- Simple rule-based evaluation
- Intelligent (LLM) evaluation
- Output structure (active/blocked paths)
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.core.nodes.builtin.control.decision import DecisionNode
from app.core.nodes.base import NodeExecutionInput
from app.schemas.workflow import PortType


@pytest.fixture
def node():
    """Create decision node instance"""
    config = Mock()
    config.node_id = "decision-1"
    config.type = "decision"
    config.category = "control"
    config.name = "Decision"
    config.description = "Test"
    config.config = {}
    return DecisionNode(config)


class TestDecisionNodePortDefinitions:
    """Test DecisionNode port definitions"""
    
    def test_has_input_port(self):
        """Test that DecisionNode has input port"""
        ports = DecisionNode.get_input_ports()
        
        assert len(ports) == 1
        assert ports[0]["name"] == "input"
        assert ports[0]["type"] == PortType.UNIVERSAL
    
    def test_has_true_and_false_output_ports(self):
        """Test that DecisionNode has true and false output ports"""
        ports = DecisionNode.get_output_ports()
        
        assert len(ports) == 2
        
        port_names = [p["name"] for p in ports]
        assert "true" in port_names
        assert "false" in port_names
        
        # Verify they are signal ports (for branching)
        for port in ports:
            assert port["type"] == PortType.SIGNAL


class TestDecisionNodeConfiguration:
    """Test DecisionNode configuration schema"""
    
    def test_config_schema_has_condition_field(self):
        """Test that config schema includes condition field"""
        schema = DecisionNode.get_config_schema()
        
        assert "condition" in schema
        assert schema["condition"]["required"] is True
        assert schema["condition"]["type"] == "string"
    
    def test_config_schema_has_evaluation_mode(self):
        """Test that config schema includes evaluation mode"""
        schema = DecisionNode.get_config_schema()
        
        assert "evaluation_mode" in schema
        options = [opt["value"] for opt in schema["evaluation_mode"]["options"]]
        assert "intelligent" in options
        assert "simple" in options
    
    def test_config_schema_has_include_reasoning(self):
        """Test that config schema includes reasoning option"""
        schema = DecisionNode.get_config_schema()
        
        assert "include_reasoning" in schema
        assert schema["include_reasoning"]["type"] == "boolean"


@pytest.fixture
def execution_input():
    """Create base execution input"""
    return NodeExecutionInput(
        ports={},
        workflow_id="wf-1",
        execution_id="exec-1",
        node_id="node-1",
        variables={},
        config={}
    )


class TestSimpleEvaluation:
    """Test simple rule-based evaluation logic"""
    
    @pytest.mark.asyncio
    async def test_keyword_matching_positive(self, node, execution_input):
        """Test simple keyword matching (positive)"""
        execution_input.config = {
            "condition": "contains error",
            "evaluation_mode": "simple"
        }
        execution_input.ports["input"] = "This is a system error message"
        
        result = await node.execute(execution_input)
        
        assert result["decision_result"] is True
        assert result["active_path"] == "true"
        assert result["active_outputs"] == ["true"]
        assert result["blocked_outputs"] == ["false"]
        
        # Check rich output structure
        assert result["true"]["decision_result"] is True
        assert "skipped" in result["false"]
    
    @pytest.mark.asyncio
    async def test_keyword_matching_negative(self, node, execution_input):
        """Test simple keyword matching (negative)"""
        execution_input.config = {
            "condition": "contains error",
            "evaluation_mode": "simple"
        }
        execution_input.ports["input"] = "System is running normally"
        
        result = await node.execute(execution_input)
        
        assert result["decision_result"] is False
        assert result["active_path"] == "false"
        assert result["active_outputs"] == ["false"]
        assert result["blocked_outputs"] == ["true"]
        
        # Check rich output structure
        assert result["false"]["decision_result"] is False
        assert "skipped" in result["true"]
    
    @pytest.mark.asyncio
    async def test_threshold_evaluation(self, node, execution_input):
        """Test numeric threshold evaluation"""
        execution_input.config = {
            "condition": "score > 0.8",
            "evaluation_mode": "simple"
        }
        execution_input.ports["input"] = {"classification": {"positive": 0.9}}
        
        result = await node.execute(execution_input)
        
        assert result["decision_result"] is True
        assert result["active_path"] == "true"


class TestIntelligentEvaluation:
    """Test LLM-based evaluation logic"""
    
    @pytest.mark.asyncio
    async def test_intelligent_evaluation_true(self, node, execution_input):
        """Test intelligent evaluation (TRUE result)"""
        execution_input.config = {
            "condition": "Is this a complaint?",
            "evaluation_mode": "intelligent"
        }
        execution_input.ports["input"] = "I am very unhappy with this service!"
        
        # Mock LLM response
        with patch.object(node, 'call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "TRUE\nThe customer expresses clear dissatisfaction."
            
            result = await node.execute(execution_input)
            
            assert result["decision_result"] is True
            assert result["active_path"] == "true"
            assert "dissatisfaction" in result["reasoning"]
            mock_llm.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_intelligent_evaluation_false(self, node, execution_input):
        """Test intelligent evaluation (FALSE result)"""
        execution_input.config = {
            "condition": "Is this a complaint?",
            "evaluation_mode": "intelligent"
        }
        execution_input.ports["input"] = "Just wanted to say thanks!"
        
        # Mock LLM response
        with patch.object(node, 'call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "FALSE\nThe customer is expressing gratitude."
            
            result = await node.execute(execution_input)
            
            assert result["decision_result"] is False
            assert result["active_path"] == "false"
            assert "gratitude" in result["reasoning"]
            mock_llm.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self, node, execution_input):
        """Test fallback to simple evaluation on LLM failure"""
        execution_input.config = {
            "condition": "contains error",  # Simple keyword
            "evaluation_mode": "intelligent"
        }
        execution_input.ports["input"] = "This is an error message"
        
        # Mock LLM failure
        with patch.object(node, 'call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("API Error")
            
            result = await node.execute(execution_input)
            
            # Should fallback to simple keyword match
            assert result["decision_result"] is True
            assert result["active_path"] == "true"
            # Reasoning should indicate fallback
            # (We can't easily assert reasoning because simple eval creates its own reasoning)


class TestErrorHandling:
    """Test error handling"""
    
    @pytest.mark.asyncio
    async def test_empty_condition_error(self, node, execution_input):
        """Test error on empty condition"""
        execution_input.config = {
            "condition": "",
            "evaluation_mode": "simple"
        }
        
        result = await node.execute(execution_input)
        
        # Should return error structure, defaulted to false
        assert result["decision_result"] is False
        assert result["active_path"] == "false"
        assert "Condition cannot be empty" in result["error"]

