"""
Variable Resolution Utilities

Helpers for resolving variable references in node configurations.
Supports three modes:
1. Literal values - Direct values
2. Variable references - Read from shared space (e.g., "node1.phone")
3. Template strings - Mix text and variables (e.g., "Hello {{node1.name}}")
4. System variables - Built-in variables (e.g., "{{system.current_date}}")
"""

import re
import logging
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def get_system_variable(var_name: str) -> Optional[str]:
    """
    Get value for system variables.
    
    Args:
        var_name: System variable name (e.g., 'current_date', 'current_time')
    
    Returns:
        Value of the system variable or None if not found
    """
    now = datetime.now()
    
    system_vars = {
        'current_date': now.strftime('%Y-%m-%d'),
        'current_time': now.strftime('%H:%M:%S'),
        'current_datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
        'timestamp': str(int(now.timestamp())),
        'year': str(now.year),
        'month': str(now.month),
        'day': str(now.day),
        'hour': str(now.hour),
        'minute': str(now.minute),
        'second': str(now.second),
    }
    
    return system_vars.get(var_name)


def resolve_variable(variable_path: str, variables: Dict[str, Any]) -> Optional[Any]:
    """
    Resolve variable path to actual value from shared space.
    Supports nested field access with dot notation.
    
    Args:
        variable_path: Path like "node1.phone" or "node1.response.full_name"
        variables: Workflow variables dict with structure:
                   {"_nodes": {"node1": {"phone": "+1234", "response": {"full_name": "User"}}}}
    
    Returns:
        Resolved value or None if not found
    
    Examples:
        >>> variables = {"_nodes": {"node1": {"phone": "+1234"}}}
        >>> resolve_variable("node1.phone", variables)
        "+1234"
        
        >>> variables = {"_nodes": {"http_request": {"response": {"full_name": "Markepattsu/tav"}}}}
        >>> resolve_variable("http_request.response.full_name", variables)
        "Markepattsu/tav"
        
        >>> resolve_variable("node1.invalid", variables)
        None
    """
    # Split path: "node1.response.full_name" → ["node1", "response", "full_name"]
    parts = variable_path.split(".")
    
    if len(parts) < 2:
        logger.warning(f"Invalid variable path format: {variable_path} (expected 'node_id.field' or deeper)")
        return None
    
    node_key = parts[0]
    field_path = parts[1:]  # ["response", "full_name"]
    
    # Navigate through _nodes namespace
    nodes = variables.get("_nodes", {})
    node_data = nodes.get(node_key, {})
    
    if not node_data:
        logger.debug(f"Node '{node_key}' not found in shared space")
        return None
    
    # Navigate through nested fields
    current_value = node_data
    for i, field_key in enumerate(field_path):
        if isinstance(current_value, dict):
            current_value = current_value.get(field_key)
            if current_value is None:
                partial_path = ".".join([node_key] + field_path[:i+1])
                logger.debug(f"Field '{partial_path}' not found")
                return None
        else:
            # Can't navigate further if not a dict
            partial_path = ".".join([node_key] + field_path[:i])
            logger.debug(f"Cannot access field '{field_key}' on non-dict value at '{partial_path}'")
            return None
    
    logger.debug(f"Resolved variable '{variable_path}' → {current_value}")
    return current_value


def resolve_template(template: str, variables: Dict[str, Any]) -> str:
    """
    Resolve template string with {{variable}} and {system} placeholders.
    
    Supports two types of placeholders:
    - {{node_id.field}} - Node variables from shared space (double braces)
    - {system_var} - System variables like current_date (single braces)
    
    If a variable is not found, the placeholder is kept as-is.
    
    Args:
        template: String like "Hello {{node1.name}}, today is {current_date}"
        variables: Workflow variables dict
    
    Returns:
        Resolved string with variables replaced
    
    Examples:
        >>> variables = {
        ...     "_nodes": {
        ...         "trigger": {"name": "John", "order_id": "12345"}
        ...     }
        ... }
        >>> resolve_template("Hello {{trigger.name}}, order #{{trigger.order_id}}", variables)
        "Hello John, order #12345"
        
        >>> resolve_template("Today is {current_date}", variables)
        "Today is 2024-01-15"
        
        >>> resolve_template("Hello {{trigger.invalid}}", variables)
        "Hello {{trigger.invalid}}"  # Keeps placeholder if not found
    """
    if not isinstance(template, str):
        return str(template)
    
    # First, resolve system variables {var} (single braces)
    def system_replacer(match):
        var_name = match.group(1).strip()
        value = get_system_variable(var_name)
        
        if value is not None:
            logger.debug(f"Resolved system variable '{var_name}' → {value}")
            return str(value)
        else:
            # Keep placeholder if system variable not found
            logger.debug(f"System variable '{var_name}' not found, keeping placeholder")
            return f"{{{var_name}}}"
    
    # Resolve single braces first (system variables)
    # Match {word} but NOT {{word}} - use negative lookbehind and lookahead
    resolved = re.sub(r'(?<!\{)\{([^{}]+)\}(?!\})', system_replacer, template)
    
    # Then resolve node variables {{...}} (double braces)
    def node_replacer(match):
        var_path = match.group(1).strip()
        value = resolve_variable(var_path, variables)
        
        if value is not None:
            logger.debug(f"Resolved node variable '{var_path}' → {value}")
            return str(value)
        else:
            # Keep placeholder if variable not found
            logger.debug(f"Node variable '{var_path}' not found, keeping placeholder")
            return f"{{{{{var_path}}}}}"
    
    resolved = re.sub(r'\{\{([^}]+)\}\}', node_replacer, resolved)
    
    if resolved != template:
        logger.debug(f"Resolved template: {template} → {resolved}")
    
    return resolved


def resolve_config_value(config_value: Any, variables: Dict[str, Any]) -> Any:
    """
    Universal config value resolver.
    
    Handles four formats:
    1. Encrypted values (decrypted first, then resolved)
    2. Structured format (new):
       {"source": "literal", "value": "Hello"}
       {"source": "variable", "variable_path": "node1.phone"}
       {"source": "template", "template": "Hello {{node1.name}}"}
    
    3. Plain string with templates (backward compatible):
       "Hello {{node1.name}}"
    
    4. Plain value (pass-through):
       "literal string", 123, True, etc.
    
    Args:
        config_value: Config value in any supported format
        variables: Workflow variables dict
    
    Returns:
        Resolved value
    
    Examples:
        >>> variables = {"_nodes": {"node1": {"phone": "+1234", "name": "John"}}}
        
        # Structured format
        >>> resolve_config_value({"source": "literal", "value": "Hello"}, variables)
        "Hello"
        
        >>> resolve_config_value({"source": "variable", "variable_path": "node1.phone"}, variables)
        "+1234"
        
        >>> resolve_config_value({"source": "template", "template": "Hi {{node1.name}}"}, variables)
        "Hi John"
        
        # Backward compatible
        >>> resolve_config_value("Hi {{node1.name}}", variables)
        "Hi John"
        
        >>> resolve_config_value("plain text", variables)
        "plain text"
    """
    # Step 1: Decrypt if encrypted (must happen before any template resolution)
    if isinstance(config_value, str):
        try:
            from app.security.encryption import decrypt_value, is_encrypted
            if is_encrypted(config_value):
                config_value = decrypt_value(config_value)
        except Exception:
            # If decryption fails or encryption module unavailable, continue with original value
            pass
    
    # Step 2: Handle structured format (new)
    if isinstance(config_value, dict) and "source" in config_value:
        source = config_value.get("source")
        
        if source == "literal":
            # Return literal value directly
            return config_value.get("value")
        
        elif source == "variable":
            # Resolve single variable reference
            var_path = config_value.get("variable_path")
            if var_path:
                resolved = resolve_variable(var_path, variables)
                # If variable not found, return None (let node handle it)
                return resolved
            return None
        
        elif source == "template":
            # Resolve template string
            template = config_value.get("template")
            if template:
                return resolve_template(template, variables)
            return ""
    
    # Step 3: Backward compatibility - plain string with {{...}} or {...}
    elif isinstance(config_value, str) and ("{{" in config_value or "{" in config_value):
        return resolve_template(config_value, variables)
    
    # Step 4: Plain value - return as-is
    return config_value


def get_available_variables(variables: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Get all available variables in shared space (for UI/debugging).
    
    Args:
        variables: Workflow variables dict
    
    Returns:
        Dictionary of {node_id: {field: value}} from shared space
    
    Example:
        >>> variables = {
        ...     "_nodes": {
        ...         "node1": {"phone": "+1234", "message": "Hello"},
        ...         "node2": {"status": "ok"}
        ...     }
        ... }
        >>> get_available_variables(variables)
        {
            "node1": {"phone": "+1234", "message": "Hello"},
            "node2": {"status": "ok"}
        }
    """
    return variables.get("_nodes", {})


def get_variable_paths(variables: Dict[str, Any]) -> list[str]:
    """
    Get all available variable paths in shared space (for autocomplete).
    
    Args:
        variables: Workflow variables dict
    
    Returns:
        List of variable paths like ["node1.phone", "node1.message", "node2.status"]
    
    Example:
        >>> variables = {
        ...     "_nodes": {
        ...         "node1": {"phone": "+1234", "message": "Hello"},
        ...         "node2": {"status": "ok"}
        ...     }
        ... }
        >>> get_variable_paths(variables)
        ["node1.phone", "node1.message", "node2.status"]
    """
    paths = []
    nodes = variables.get("_nodes", {})
    
    for node_id, node_data in nodes.items():
        if isinstance(node_data, dict):
            for field_name in node_data.keys():
                paths.append(f"{node_id}.{field_name}")
    
    return sorted(paths)

