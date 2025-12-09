"""
Unit tests for JSONParserNode

Tests:
- Parsing valid JSON (dict & list)
- Extracting JSON from markdown blocks
- Finding JSON in mixed text
- Strict vs non-strict mode handling
- Error handling
"""

import pytest
import json
from unittest.mock import Mock

from app.core.nodes.builtin.data.json_parser import JSONParserNode
from app.core.nodes.base import NodeExecutionInput


@pytest.fixture
def node():
    """Create JSON parser node instance"""
    config = Mock()
    config.node_id = "json-parser"
    config.type = "json_parser"
    config.category = "processing"
    config.name = "JSON Parser"
    config.description = "Test"
    config.config = {}
    return JSONParserNode(config)


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


class TestJSONParsing:
    """Test core JSON parsing logic"""
    
    @pytest.mark.asyncio
    async def test_parse_valid_json_object(self, node, execution_input):
        """Test parsing valid JSON object"""
        data = {"name": "Alice", "age": 30}
        json_str = json.dumps(data)
        
        execution_input.ports["text"] = json_str
        
        result = await node.execute(execution_input)
        
        assert result["data"] == data
        assert result["metadata"]["success"] is True
        assert result["metadata"]["type"] == "dict"
    
    @pytest.mark.asyncio
    async def test_parse_valid_json_array(self, node, execution_input):
        """Test parsing valid JSON array"""
        data = [{"id": 1}, {"id": 2}]
        json_str = json.dumps(data)
        
        execution_input.ports["text"] = json_str
        
        result = await node.execute(execution_input)
        
        assert result["data"] == data
        assert result["metadata"]["success"] is True
        assert result["metadata"]["type"] == "list"
        assert result["metadata"]["size"] == 2


class TestMarkdownExtraction:
    """Test extraction from markdown"""
    
    @pytest.mark.asyncio
    async def test_extract_from_markdown_block(self, node, execution_input):
        """Test extracting JSON from ```json code block"""
        data = {"status": "ok"}
        text = f"""
        Here is the result:
        
        ```json
        {json.dumps(data, indent=2)}
        ```
        
        Hope this helps!
        """
        
        execution_input.ports["text"] = text
        # Enable extraction
        execution_input.config["extract_from_markdown"] = True
        
        result = await node.execute(execution_input)
        
        assert result["data"] == data
        assert result["metadata"]["success"] is True
    
    @pytest.mark.asyncio
    async def test_extract_from_generic_block(self, node, execution_input):
        """Test extracting JSON from generic ``` code block"""
        data = {"status": "ok"}
        text = f"""
        ```
        {json.dumps(data)}
        ```
        """
        
        execution_input.ports["text"] = text
        execution_input.config["extract_from_markdown"] = True
        
        result = await node.execute(execution_input)
        
        assert result["data"] == data


class TestMixedContentExtraction:
    """Test finding JSON in mixed content without markdown"""
    
    @pytest.mark.asyncio
    async def test_find_json_in_text(self, node, execution_input):
        """Test finding JSON pattern in text"""
        data = {"key": "value"}
        text = f"Some prefix text {json.dumps(data)} some suffix text"
        
        execution_input.ports["text"] = text
        
        result = await node.execute(execution_input)
        
        assert result["data"] == data
        assert result["metadata"]["extracted"] is True


class TestErrorHandling:
    """Test error handling and strict mode"""
    
    @pytest.mark.asyncio
    async def test_invalid_json_strict_mode(self, node, execution_input):
        """Test strict mode fails on invalid JSON"""
        text = "Not JSON at all"
        
        execution_input.ports["text"] = text
        execution_input.config["strict_mode"] = True
        
        result = await node.execute(execution_input)
        
        assert result["data"] is None
        assert "Invalid JSON" in result["error"]
        assert result["metadata"]["success"] is False
    
    @pytest.mark.asyncio
    async def test_invalid_json_non_strict_mode(self, node, execution_input):
        """Test non-strict mode returns original text"""
        text = "Not JSON at all"
        
        execution_input.ports["text"] = text
        execution_input.config["strict_mode"] = False
        
        result = await node.execute(execution_input)
        
        assert result["data"] == text
        assert result["metadata"]["success"] is False
        assert result["metadata"]["type"] == "string"
    
    @pytest.mark.asyncio
    async def test_empty_input(self, node, execution_input):
        """Test handling empty input"""
        execution_input.ports["text"] = ""
        
        result = await node.execute(execution_input)
        
        assert result["data"] is None
        assert "No text provided" in result["error"]

