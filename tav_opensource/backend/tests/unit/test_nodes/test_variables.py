"""
Unit tests for Variable Resolution Utilities

Tests variable references, templates, and system variables.
"""

import pytest
from datetime import datetime
from app.core.nodes.variables import (
    get_system_variable,
    resolve_variable,
    resolve_template,
    resolve_config_value,
    get_available_variables,
    get_variable_paths
)


class TestSystemVariables:
    """Test system variable resolution"""
    
    def test_get_system_variable_current_date(self):
        """Test getting current_date system variable"""
        result = get_system_variable("current_date")
        
        assert result is not None
        assert len(result) == 10  # YYYY-MM-DD format
        assert result.count('-') == 2
    
    def test_get_system_variable_current_time(self):
        """Test getting current_time system variable"""
        result = get_system_variable("current_time")
        
        assert result is not None
        assert result.count(':') == 2  # HH:MM:SS format
    
    def test_get_system_variable_timestamp(self):
        """Test getting timestamp system variable"""
        result = get_system_variable("timestamp")
        
        assert result is not None
        assert result.isdigit()
        assert int(result) > 0
    
    def test_get_system_variable_year(self):
        """Test getting year system variable"""
        result = get_system_variable("year")
        
        assert result is not None
        assert int(result) == datetime.now().year
    
    def test_get_system_variable_invalid(self):
        """Test getting invalid system variable returns None"""
        result = get_system_variable("invalid_var")
        assert result is None


class TestResolveVariable:
    """Test variable path resolution"""
    
    def test_resolve_simple_path(self):
        """Test resolving simple variable path"""
        variables = {
            "_nodes": {
                "node1": {"phone": "+1234"}
            }
        }
        
        result = resolve_variable("node1.phone", variables)
        assert result == "+1234"
    
    def test_resolve_nested_path(self):
        """Test resolving nested variable path"""
        variables = {
            "_nodes": {
                "http_request": {
                    "response": {
                        "full_name": "Markepattsu/tav"
                    }
                }
            }
        }
        
        result = resolve_variable("http_request.response.full_name", variables)
        assert result == "Markepattsu/tav"
    
    def test_resolve_missing_path(self):
        """Test resolving non-existent path returns None"""
        variables = {
            "_nodes": {
                "node1": {"phone": "+1234"}
            }
        }
        
        result = resolve_variable("node1.invalid", variables)
        assert result is None
    
    def test_resolve_invalid_format(self):
        """Test resolving invalid path format returns None"""
        variables = {"_nodes": {}}
        
        # Single part path (no dot)
        result = resolve_variable("node1", variables)
        assert result is None
    
    def test_resolve_missing_node(self):
        """Test resolving path with missing node returns None"""
        variables = {"_nodes": {}}
        
        result = resolve_variable("nonexistent.field", variables)
        assert result is None


class TestResolveTemplate:
    """Test template string resolution"""
    
    def test_resolve_template_no_variables(self):
        """Test template with no variable references"""
        template = "Hello world"
        variables = {}
        
        result = resolve_template(template, variables)
        assert result == "Hello world"
    
    def test_resolve_template_single_variable(self):
        """Test template with single variable"""
        template = "Hello {{node1.name}}"
        variables = {
            "_nodes": {
                "node1": {"name": "Alice"}
            }
        }
        
        result = resolve_template(template, variables)
        assert result == "Hello Alice"
    
    def test_resolve_template_multiple_variables(self):
        """Test template with multiple variables"""
        template = "{{node1.greeting}} {{node1.name}}, today is {{system.current_date}}"
        variables = {
            "_nodes": {
                "node1": {
                    "greeting": "Hello",
                    "name": "Alice"
                }
            }
        }
        
        result = resolve_template(template, variables)
        assert "Hello Alice" in result
        assert "today is" in result
    
    def test_resolve_template_system_variable(self):
        """Test template with system variable"""
        template = "Current date: {{system.current_date}}"
        variables = {}
        
        result = resolve_template(template, variables)
        assert "Current date:" in result
        assert len(result) > 15  # Should have date appended
    
    def test_resolve_template_missing_variable(self):
        """Test template with missing variable keeps placeholder"""
        template = "Hello {{node1.name}}"
        variables = {}
        
        result = resolve_template(template, variables)
        # Missing variables are kept as-is
        assert "{{node1.name}}" in result or "Hello" in result
    
    def test_resolve_template_nested_braces(self):
        """Test template handles nested/adjacent braces"""
        template = "{{node1.field}}"
        variables = {
            "_nodes": {
                "node1": {"field": "value"}
            }
        }
        
        result = resolve_template(template, variables)
        assert result == "value"


class TestResolveConfigValue:
    """Test config value resolution"""
    
    def test_resolve_literal_string(self):
        """Test resolving literal string value"""
        result = resolve_config_value("hello", {})
        assert result == "hello"
    
    def test_resolve_literal_number(self):
        """Test resolving literal number value"""
        result = resolve_config_value(123, {})
        assert result == 123
    
    def test_resolve_literal_bool(self):
        """Test resolving literal boolean value"""
        result = resolve_config_value(True, {})
        assert result is True
    
    def test_resolve_literal_dict(self):
        """Test resolving literal dict value"""
        config = {"key": "value"}
        result = resolve_config_value(config, {})
        assert result == config
    
    def test_resolve_literal_list(self):
        """Test resolving literal list value"""
        config = [1, 2, 3]
        result = resolve_config_value(config, {})
        assert result == config
    
    def test_resolve_variable_reference(self):
        """Test resolving variable reference in structured format"""
        config = {"source": "variable", "variable_path": "node1.phone"}
        variables = {
            "_nodes": {
                "node1": {"phone": "+1234"}
            }
        }
        
        result = resolve_config_value(config, variables)
        assert result == "+1234"
    
    def test_resolve_template_in_config(self):
        """Test resolving template string in structured format"""
        config = {"source": "template", "template": "Call {{node1.phone}} at {{system.current_time}}"}
        variables = {
            "_nodes": {
                "node1": {"phone": "+1234"}
            }
        }
        
        result = resolve_config_value(config, variables)
        assert "+1234" in result
        assert "Call" in result
    
    def test_resolve_template_string_backward_compat(self):
        """Test resolving template string (backward compatible format)"""
        config = "Call {{node1.phone}}"
        variables = {
            "_nodes": {
                "node1": {"phone": "+1234"}
            }
        }
        
        result = resolve_config_value(config, variables)
        assert result == "Call +1234"
    
    def test_resolve_plain_dict_no_resolution(self):
        """Test that plain dicts are returned as-is (no recursive resolution)"""
        config = {
            "phone": "{{node1.phone}}",
            "message": "Hello {{node1.name}}"
        }
        variables = {
            "_nodes": {
                "node1": {
                    "phone": "+1234",
                    "name": "Alice"
                }
            }
        }
        
        # Plain dicts are NOT recursively resolved
        result = resolve_config_value(config, variables)
        assert isinstance(result, dict)
        assert result["phone"] == "{{node1.phone}}"  # Not resolved
        assert "{{node1.name}}" in result["message"]  # Not resolved
    
    def test_resolve_plain_list_no_resolution(self):
        """Test that plain lists are returned as-is (no recursive resolution)"""
        config = [
            "{{node1.item1}}",
            "literal",
            "{{node1.item2}}"
        ]
        variables = {
            "_nodes": {
                "node1": {
                    "item1": "first",
                    "item2": "second"
                }
            }
        }
        
        # Plain lists are NOT recursively resolved
        result = resolve_config_value(config, variables)
        assert isinstance(result, list)
        assert result[0] == "{{node1.item1}}"  # Not resolved
        assert result[1] == "literal"
        assert result[2] == "{{node1.item2}}"  # Not resolved


class TestGetAvailableVariables:
    """Test getting available variables from shared space"""
    
    def test_get_available_variables_with_data(self):
        """Test getting all available variables"""
        variables = {
            "_nodes": {
                "node1": {"phone": "+1234", "message": "Hello"},
                "node2": {"status": "ok"}
            }
        }
        
        result = get_available_variables(variables)
        
        assert isinstance(result, dict)
        assert "node1" in result
        assert "node2" in result
        assert result["node1"]["phone"] == "+1234"
        assert result["node1"]["message"] == "Hello"
        assert result["node2"]["status"] == "ok"
    
    def test_get_available_variables_empty(self):
        """Test getting variables from empty shared space"""
        variables = {}
        
        result = get_available_variables(variables)
        assert result == {}
    
    def test_get_available_variables_no_nodes_key(self):
        """Test getting variables when _nodes key doesn't exist"""
        variables = {"other_key": "value"}
        
        result = get_available_variables(variables)
        assert result == {}


class TestGetVariablePaths:
    """Test getting variable paths for autocomplete"""
    
    def test_get_variable_paths_with_data(self):
        """Test getting all variable paths"""
        variables = {
            "_nodes": {
                "node1": {"phone": "+1234", "message": "Hello"},
                "node2": {"status": "ok"}
            }
        }
        
        result = get_variable_paths(variables)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert "node1.phone" in result
        assert "node1.message" in result
        assert "node2.status" in result
    
    def test_get_variable_paths_sorted(self):
        """Test that variable paths are sorted"""
        variables = {
            "_nodes": {
                "zebra": {"field": "z"},
                "alpha": {"field": "a"}
            }
        }
        
        result = get_variable_paths(variables)
        
        # Should be sorted alphabetically
        assert result == ["alpha.field", "zebra.field"]
    
    def test_get_variable_paths_empty(self):
        """Test getting paths from empty shared space"""
        variables = {}
        
        result = get_variable_paths(variables)
        assert result == []
    
    def test_get_variable_paths_no_nodes_key(self):
        """Test getting paths when _nodes key doesn't exist"""
        variables = {"other_key": "value"}
        
        result = get_variable_paths(variables)
        assert result == []
    
    def test_get_variable_paths_nested_dict_only_top_level(self):
        """Test that only top-level fields are included, not nested"""
        variables = {
            "_nodes": {
                "node1": {
                    "simple": "value",
                    "nested": {"deep": "value"}
                }
            }
        }
        
        result = get_variable_paths(variables)
        
        # Should include both simple and nested (but not nested.deep)
        assert "node1.simple" in result
        assert "node1.nested" in result
        assert len(result) == 2

