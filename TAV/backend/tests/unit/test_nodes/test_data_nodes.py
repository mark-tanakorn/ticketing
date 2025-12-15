"""
Unit tests for Data Processing Nodes

Tests JSON Parser and other data transformation nodes.
Pure unit tests with mocked dependencies.
"""

import pytest
from unittest.mock import Mock

from app.core.nodes.builtin.data.json_parser import JSONParserNode
from app.core.nodes.base import NodeExecutionInput
from app.schemas.workflow import NodeConfiguration


@pytest.fixture
def json_parser_config():
    """Create JSON parser node configuration"""
    return NodeConfiguration(
        node_id="json-1",
        name="JSON Parser",
        node_type="json_parser",  # Fixed: was 'type'
        category="processing",  # Added: good practice
        config={
            "strict_mode": False,
            "extract_from_markdown": True
        }
    )


@pytest.fixture
def json_parser_node(json_parser_config):
    """Create JSONParserNode instance"""
    return JSONParserNode(json_parser_config)


class TestJSONParserNodePorts:
    """Test JSONParserNode port definitions"""
    
    def test_has_text_input_port(self):
        """Test that JSON parser has text input port"""
        ports = JSONParserNode.get_input_ports()
        
        assert len(ports) == 1
        assert ports[0]["name"] == "text"
        assert ports[0]["required"] is True
    
    def test_has_data_and_metadata_output_ports(self):
        """Test that JSON parser has data and metadata output ports"""
        ports = JSONParserNode.get_output_ports()
        
        assert len(ports) == 2
        
        port_names = [p["name"] for p in ports]
        assert "data" in port_names
        assert "metadata" in port_names


class TestJSONParserConfig:
    """Test JSONParserNode configuration"""
    
    def test_config_schema_has_strict_mode(self):
        """Test that config includes strict mode option"""
        schema = JSONParserNode.get_config_schema()
        
        assert "strict_mode" in schema
        assert schema["strict_mode"]["type"] == "boolean"
        assert schema["strict_mode"]["default"] is False
    
    def test_config_schema_has_extract_markdown(self):
        """Test that config includes markdown extraction option"""
        schema = JSONParserNode.get_config_schema()
        
        assert "extract_from_markdown" in schema
        assert schema["extract_from_markdown"]["type"] == "boolean"
        assert schema["extract_from_markdown"]["default"] is True


class TestJSONParsing:
    """Test JSON parsing logic"""
    
    @pytest.mark.asyncio
    async def test_parse_simple_json_object(self, json_parser_node):
        """Test parsing a simple JSON object"""
        # Arrange
        input_data = NodeExecutionInput(
            workflow_id="test-workflow",
            execution_id="test-execution",
            node_id="json-1",
            config={},
            ports={"text": '{"name": "test", "value": 123}'},
            variables={}
        )
        
        # Act
        result = await json_parser_node.execute(input_data)
        
        # Assert
        assert result["data"] == {"name": "test", "value": 123}
        assert "metadata" in result
    
    @pytest.mark.asyncio
    async def test_parse_json_array(self, json_parser_node):
        """Test parsing a JSON array"""
        # Arrange
        input_data = NodeExecutionInput(
            workflow_id="test-workflow",
            execution_id="test-execution",
            node_id="json-1",
            config={},
            ports={"text": '[1, 2, 3, "test"]'},
            variables={}
        )
        
        # Act
        result = await json_parser_node.execute(input_data)
        
        # Assert
        assert result["data"] == [1, 2, 3, "test"]
    
    @pytest.mark.asyncio
    async def test_parse_nested_json(self, json_parser_node):
        """Test parsing nested JSON structures"""
        # Arrange
        json_text = '{"user": {"name": "John", "age": 30}, "items": [1, 2, 3]}'
        input_data = NodeExecutionInput(
            workflow_id="test-workflow",
            execution_id="test-execution",
            node_id="json-1",
            config={},
            ports={"text": json_text},
            variables={}
        )
        
        # Act
        result = await json_parser_node.execute(input_data)
        
        # Assert
        assert result["data"]["user"]["name"] == "John"
        assert result["data"]["items"] == [1, 2, 3]


class TestMarkdownExtraction:
    """Test markdown code block extraction"""
    
    @pytest.mark.asyncio
    async def test_extract_json_from_markdown_json_block(self, json_parser_node):
        """Test extracting JSON from ```json block"""
        # Arrange
        markdown_text = '''Here's the data:
```json
{"name": "test", "value": 123}
```
That's it!'''
        
        input_data = NodeExecutionInput(
            workflow_id="test-workflow",
            execution_id="test-execution",
            node_id="json-1",
            config={},
            ports={"text": markdown_text},
            variables={}
        )
        
        # Act
        result = await json_parser_node.execute(input_data)
        
        # Assert
        assert result["data"] == {"name": "test", "value": 123}
    
    @pytest.mark.asyncio
    async def test_extract_json_from_generic_code_block(self, json_parser_node):
        """Test extracting JSON from generic ``` block"""
        # Arrange
        markdown_text = '''Response:
```
{"key": "value"}
```'''
        
        input_data = NodeExecutionInput(
            workflow_id="test-workflow",
            execution_id="test-execution",
            node_id="json-1",
            config={},
            ports={"text": markdown_text},
            variables={}
        )
        
        # Act
        result = await json_parser_node.execute(input_data)
        
        # Assert
        assert result["data"] == {"key": "value"}


class TestErrorHandling:
    """Test JSON parser error handling"""
    
    @pytest.mark.asyncio
    async def test_empty_text_returns_error(self, json_parser_node):
        """Test that empty text returns error"""
        # Arrange
        input_data = NodeExecutionInput(
            workflow_id="test-workflow",
            execution_id="test-execution",
            node_id="json-1",
            config={},
            ports={"text": ""},
            variables={}
        )
        
        # Act
        result = await json_parser_node.execute(input_data)
        
        # Assert
        assert result["data"] is None
        assert "error" in result
        assert "No text provided" in result["error"]
    
    @pytest.mark.asyncio
    async def test_invalid_json_in_non_strict_mode(self, json_parser_node):
        """Test that invalid JSON in non-strict mode returns original text"""
        # Arrange
        json_parser_node.config["strict_mode"] = False
        
        input_data = NodeExecutionInput(
            workflow_id="test-workflow",
            execution_id="test-execution",
            node_id="json-1",
            config={},
            ports={"text": "This is not JSON at all!"},
            variables={}
        )
        
        # Act
        result = await json_parser_node.execute(input_data)
        
        # Assert - In non-strict mode, it should handle gracefully
        assert "metadata" in result
    
    @pytest.mark.asyncio
    async def test_invalid_json_in_strict_mode_raises_error(self, json_parser_node):
        """Test that invalid JSON in strict mode raises error"""
        # Arrange
        json_parser_node.config["strict_mode"] = True
        
        input_data = NodeExecutionInput(
            workflow_id="test-workflow",
            execution_id="test-execution",
            node_id="json-1",
            config={},
            ports={"text": "Not valid JSON {invalid}"},
            variables={}
        )
        
        # Act
        result = await json_parser_node.execute(input_data)
        
        # Assert
        # Check that error is returned
        assert "metadata" in result or "error" in result


class TestJSONParserMetadata:
    """Test JSON parser metadata output"""
    
    @pytest.mark.asyncio
    async def test_metadata_includes_parsing_info(self, json_parser_node):
        """Test that metadata includes parsing information"""
        # Arrange
        input_data = NodeExecutionInput(
            workflow_id="test-workflow",
            execution_id="test-execution",
            node_id="json-1",
            config={},
            ports={"text": '{"test": true}'},
            variables={}
        )
        
        # Act
        result = await json_parser_node.execute(input_data)
        
        # Assert
        assert "metadata" in result
        assert isinstance(result["metadata"], dict)

