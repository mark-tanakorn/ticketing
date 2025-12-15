"""
Unit Tests for Variable Resolution System

Tests for the shared information space variable resolvers.
"""

import pytest
from app.core.nodes.variables import (
    resolve_variable,
    resolve_template,
    resolve_config_value,
    get_available_variables,
    get_variable_paths,
)


# ==================== Test Data ====================

@pytest.fixture
def sample_variables():
    """Sample workflow variables for testing"""
    return {
        "_nodes": {
            "trigger_1": {
                "phone": "+1234567890",
                "message": "Hello World",
                "timestamp": "2025-11-06T10:30:00",
                "user_name": "John Doe",
                "order_id": "ORD-12345"
            },
            "http_request_1": {
                "status_code": 200,
                "body": {"data": "response"},
                "tracking_url": "https://track.com/ORD-12345"
            },
            "llm_analyzer_1": {
                "response": "This is a support request",
                "sentiment": "neutral",
                "confidence": 0.95
            }
        }
    }


# ==================== resolve_variable() Tests ====================

def test_resolve_variable_success(sample_variables):
    """Test successful variable resolution"""
    # Basic field resolution
    assert resolve_variable("trigger_1.phone", sample_variables) == "+1234567890"
    assert resolve_variable("trigger_1.message", sample_variables) == "Hello World"
    assert resolve_variable("trigger_1.user_name", sample_variables) == "John Doe"
    
    # Different node
    assert resolve_variable("http_request_1.status_code", sample_variables) == 200
    assert resolve_variable("llm_analyzer_1.sentiment", sample_variables) == "neutral"


def test_resolve_variable_nested_dict(sample_variables):
    """Test resolution of nested dict values"""
    result = resolve_variable("http_request_1.body", sample_variables)
    assert result == {"data": "response"}


def test_resolve_variable_not_found(sample_variables):
    """Test variable not found returns None"""
    # Node not found
    assert resolve_variable("nonexistent.field", sample_variables) is None
    
    # Field not found
    assert resolve_variable("trigger_1.nonexistent", sample_variables) is None


def test_resolve_variable_invalid_path(sample_variables):
    """Test invalid path format returns None"""
    # Missing dot separator
    assert resolve_variable("trigger_1_phone", sample_variables) is None
    
    # Too many parts
    assert resolve_variable("trigger_1.phone.extra", sample_variables) is None
    
    # Empty string
    assert resolve_variable("", sample_variables) is None


def test_resolve_variable_empty_variables():
    """Test resolution with empty variables dict"""
    assert resolve_variable("node.field", {}) is None
    assert resolve_variable("node.field", {"_nodes": {}}) is None


# ==================== resolve_template() Tests ====================

def test_resolve_template_single_variable(sample_variables):
    """Test template with single variable"""
    template = "Phone: {{trigger_1.phone}}"
    result = resolve_template(template, sample_variables)
    assert result == "Phone: +1234567890"


def test_resolve_template_multiple_variables(sample_variables):
    """Test template with multiple variables"""
    template = "Hello {{trigger_1.user_name}}, order #{{trigger_1.order_id}}"
    result = resolve_template(template, sample_variables)
    assert result == "Hello John Doe, order #ORD-12345"


def test_resolve_template_mixed_content(sample_variables):
    """Test template with text and variables mixed"""
    template = "User {{trigger_1.user_name}} sent: {{trigger_1.message}} at {{trigger_1.timestamp}}"
    result = resolve_template(template, sample_variables)
    assert result == "User John Doe sent: Hello World at 2025-11-06T10:30:00"


def test_resolve_template_missing_variable(sample_variables):
    """Test template with missing variable keeps placeholder"""
    template = "Hello {{trigger_1.user_name}}, {{trigger_1.missing}}"
    result = resolve_template(template, sample_variables)
    assert result == "Hello John Doe, {{trigger_1.missing}}"


def test_resolve_template_no_variables():
    """Test template without any variables"""
    template = "Just plain text"
    result = resolve_template(template, {})
    assert result == "Just plain text"


def test_resolve_template_only_variable(sample_variables):
    """Test template that is just a variable"""
    template = "{{trigger_1.phone}}"
    result = resolve_template(template, sample_variables)
    assert result == "+1234567890"


def test_resolve_template_numeric_value(sample_variables):
    """Test template with numeric variable"""
    template = "Status: {{http_request_1.status_code}}"
    result = resolve_template(template, sample_variables)
    assert result == "Status: 200"


def test_resolve_template_non_string_input():
    """Test template resolver with non-string input"""
    # Should convert to string
    assert resolve_template(123, {}) == "123"
    assert resolve_template(True, {}) == "True"
    assert resolve_template(None, {}) == "None"


# ==================== resolve_config_value() Tests ====================

def test_resolve_config_literal(sample_variables):
    """Test literal config value"""
    config = {"source": "literal", "value": "Hello World"}
    result = resolve_config_value(config, sample_variables)
    assert result == "Hello World"


def test_resolve_config_variable(sample_variables):
    """Test variable config value"""
    config = {"source": "variable", "variable_path": "trigger_1.phone"}
    result = resolve_config_value(config, sample_variables)
    assert result == "+1234567890"


def test_resolve_config_template(sample_variables):
    """Test template config value"""
    config = {
        "source": "template",
        "template": "Hello {{trigger_1.user_name}}, order #{{trigger_1.order_id}}"
    }
    result = resolve_config_value(config, sample_variables)
    assert result == "Hello John Doe, order #ORD-12345"


def test_resolve_config_backward_compatible_template(sample_variables):
    """Test backward compatible plain string with template"""
    # Plain string with {{}} should be resolved as template
    config = "Hello {{trigger_1.user_name}}"
    result = resolve_config_value(config, sample_variables)
    assert result == "Hello John Doe"


def test_resolve_config_plain_string(sample_variables):
    """Test plain string without variables"""
    config = "Just a plain string"
    result = resolve_config_value(config, sample_variables)
    assert result == "Just a plain string"


def test_resolve_config_plain_types(sample_variables):
    """Test plain value types (numbers, bools, etc.)"""
    assert resolve_config_value(123, sample_variables) == 123
    assert resolve_config_value(45.67, sample_variables) == 45.67
    assert resolve_config_value(True, sample_variables) is True
    assert resolve_config_value(False, sample_variables) is False
    assert resolve_config_value(None, sample_variables) is None


def test_resolve_config_missing_variable(sample_variables):
    """Test config with missing variable returns None"""
    config = {"source": "variable", "variable_path": "nonexistent.field"}
    result = resolve_config_value(config, sample_variables)
    assert result is None


def test_resolve_config_invalid_structure():
    """Test config with invalid structure"""
    # Dict without "source" key - return as-is
    config = {"some": "dict"}
    result = resolve_config_value(config, {})
    assert result == {"some": "dict"}


# ==================== get_available_variables() Tests ====================

def test_get_available_variables(sample_variables):
    """Test getting all available variables"""
    result = get_available_variables(sample_variables)
    
    assert "trigger_1" in result
    assert "http_request_1" in result
    assert "llm_analyzer_1" in result
    
    assert result["trigger_1"]["phone"] == "+1234567890"
    assert result["http_request_1"]["status_code"] == 200


def test_get_available_variables_empty():
    """Test getting variables from empty dict"""
    result = get_available_variables({})
    assert result == {}
    
    result = get_available_variables({"_nodes": {}})
    assert result == {}


# ==================== get_variable_paths() Tests ====================

def test_get_variable_paths(sample_variables):
    """Test getting all variable paths"""
    result = get_variable_paths(sample_variables)
    
    # Should be sorted
    assert result == sorted(result)
    
    # Check some expected paths
    assert "trigger_1.phone" in result
    assert "trigger_1.message" in result
    assert "trigger_1.user_name" in result
    assert "http_request_1.status_code" in result
    assert "llm_analyzer_1.response" in result


def test_get_variable_paths_count(sample_variables):
    """Test variable paths count"""
    result = get_variable_paths(sample_variables)
    
    # trigger_1 has 5 fields
    # http_request_1 has 3 fields
    # llm_analyzer_1 has 3 fields
    # Total: 11 paths
    assert len(result) == 11


def test_get_variable_paths_empty():
    """Test getting paths from empty dict"""
    result = get_variable_paths({})
    assert result == []
    
    result = get_variable_paths({"_nodes": {}})
    assert result == []


# ==================== Integration Tests ====================

def test_full_workflow_simulation(sample_variables):
    """Test simulating a full workflow variable usage"""
    # Node 1: Trigger shares data (already in sample_variables)
    
    # Node 2: HTTP request uses trigger data
    url_config = {
        "source": "template",
        "template": "https://api.com/user/{{trigger_1.phone}}"
    }
    url = resolve_config_value(url_config, sample_variables)
    assert url == "https://api.com/user/+1234567890"
    
    # Node 3: LLM uses multiple variables
    prompt_config = {
        "source": "template",
        "template": "Analyze message from {{trigger_1.user_name}}: {{trigger_1.message}}"
    }
    prompt = resolve_config_value(prompt_config, sample_variables)
    assert prompt == "Analyze message from John Doe: Hello World"
    
    # Node 4: Response uses LLM output
    response_config = {
        "source": "template",
        "template": "{{trigger_1.user_name}}, {{llm_analyzer_1.response}}"
    }
    response = resolve_config_value(response_config, sample_variables)
    assert response == "John Doe, This is a support request"


def test_complex_template_with_url(sample_variables):
    """Test complex template with URLs and query params"""
    template = "Track your order at {{http_request_1.tracking_url}}?user={{trigger_1.user_name}}"
    result = resolve_template(template, sample_variables)
    assert result == "Track your order at https://track.com/ORD-12345?user=John Doe"


def test_all_three_config_types_in_one_node(sample_variables):
    """Test node using all three config types"""
    # Literal
    static_text = resolve_config_value(
        {"source": "literal", "value": "Static text"},
        sample_variables
    )
    assert static_text == "Static text"
    
    # Variable
    phone = resolve_config_value(
        {"source": "variable", "variable_path": "trigger_1.phone"},
        sample_variables
    )
    assert phone == "+1234567890"
    
    # Template
    message = resolve_config_value(
        {"source": "template", "template": "Hi {{trigger_1.user_name}}!"},
        sample_variables
    )
    assert message == "Hi John Doe!"

