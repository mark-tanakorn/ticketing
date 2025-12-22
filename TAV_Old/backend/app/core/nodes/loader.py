"""
Node Loader - Auto-Discovery and Registration

Automatically discovers and registers all node classes from the nodes directory.
"""

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Type, List

from app.core.nodes.base import Node
from app.core.nodes.registry import NodeRegistry

logger = logging.getLogger(__name__)


def discover_and_register_nodes() -> dict:
    """
    Auto-discover all node classes and register them.
    
    Scans builtin/, custom/, business/, and analytics/ directories for:
    - Classes that inherit from Node
    - Auto-registers them using class metadata (type, display_name, category, etc.)
    
    NO __init__.py imports required! Just drop a node file in a folder and it's auto-discovered.
    
    Returns:
        Dict with discovery statistics
    """
    logger.info("🔍 Starting node auto-discovery...")
    
    stats = {
        "modules_scanned": 0,
        "nodes_found": 0,
        "nodes_registered": 0,
        "errors": []
    }
    
    # Get the nodes package path
    import app.core.nodes as nodes_package
    package_path = Path(nodes_package.__file__).parent
    
    # Scan all node directories (builtin subdirectories + custom)
    node_directories = [
        (package_path / "builtin", "app.core.nodes.builtin"),
        (package_path / "custom", "app.core.nodes.custom"),
    ]
    
    for dir_path, prefix in node_directories:
        if not dir_path.exists():
            logger.debug(f"Directory {dir_path} does not exist, skipping...")
            continue
            
        # Recursively discover all Python modules in this directory
        for module_info in pkgutil.walk_packages(
            path=[str(dir_path)],
            prefix=f"{prefix}."
        ):
            module_name = module_info.name
            
            # Skip __pycache__, __init__, and test files
            if "__pycache__" in module_name or "__init__" in module_name or "test_" in module_name:
                continue
            
            try:
                # Import the module
                module = importlib.import_module(module_name)
                stats["modules_scanned"] += 1
                
                # Find all classes that inherit from Node
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Skip if not a Node subclass
                    if not issubclass(obj, Node) or obj is Node:
                        continue
                    
                    # Skip abstract classes
                    if inspect.isabstract(obj):
                        continue
                    
                    # Skip classes from other modules (imports)
                    if obj.__module__ != module_name:
                        continue
                    
                    stats["nodes_found"] += 1
                    
                    # Auto-register the node if not already registered
                    node_type = getattr(obj, 'type', None)
                    
                    if not node_type:
                        logger.warning(f"⚠️  Node {obj.__name__} has no 'type' attribute, skipping...")
                        continue
                    
                    if NodeRegistry.is_registered(node_type):
                        logger.debug(f"   Node {node_type} already registered, skipping...")
                        continue
                    
                    # Extract metadata from class attributes
                    display_name = getattr(obj, 'display_name', node_type)
                    description = getattr(obj, 'description', obj.__doc__ or "")
                    category = getattr(obj, 'category', None)
                    icon = getattr(obj, 'icon', None)
                    
                    # Register the node
                    NodeRegistry.register(
                        node_type=node_type,
                        node_class=obj,
                        display_name=display_name,
                        description=description,
                        icon=icon,
                        category=category,
                    )
                    
                    stats["nodes_registered"] += 1
                    logger.debug(f"   ✅ Registered: {node_type} ({obj.__name__})")
                    
            except Exception as e:
                error_msg = f"Error loading module {module_name}: {e}"
                logger.warning(f"⚠️  {error_msg}")
                stats["errors"].append(error_msg)
    
    # Count actually registered nodes
    stats["nodes_registered"] = len(NodeRegistry.list_types())
    
    logger.info(
        f"✅ Node discovery complete: "
        f"Scanned {stats['modules_scanned']} modules, "
        f"Found {stats['nodes_found']} node classes, "
        f"Registered {stats['nodes_registered']} nodes"
    )
    
    if stats["errors"]:
        logger.warning(f"⚠️  {len(stats['errors'])} errors during discovery")
    
    return stats


def get_node_port_definitions(node_class: Type[Node]) -> dict:
    """
    Extract port definitions from a node class.
    
    Calls the class methods get_input_ports() and get_output_ports().
    
    Args:
        node_class: Node class to inspect
    
    Returns:
        Dict with input_ports and output_ports metadata
    """
    try:
        # Call class methods to get port definitions
        input_ports = node_class.get_input_ports()
        output_ports = node_class.get_output_ports()
        
        # Convert PortType enums to strings
        def serialize_port(port):
            if isinstance(port, dict):
                serialized = port.copy()
                if 'type' in serialized and hasattr(serialized['type'], 'value'):
                    serialized['type'] = serialized['type'].value
                return serialized
            return port
        
        return {
            "input_ports": [serialize_port(p) for p in input_ports],
            "output_ports": [serialize_port(p) for p in output_ports],
        }
            
    except Exception as e:
        logger.debug(f"Error extracting ports from {node_class.__name__}: {e}")
        return {
            "input_ports": [],
            "output_ports": []
        }


def get_node_config_schema(node_class: Type[Node]) -> dict:
    """
    Extract configuration schema from node class method.
    
    Automatically injects:
    - LLM config fields for nodes with LLMCapability
    - Export config fields for nodes with ExportCapability
    
    Calls the class method get_config_schema().
    
    Args:
        node_class: Node class to inspect
    
    Returns:
        Dict with configuration schema (with auto-injected fields if applicable)
    """
    try:
        # Get base config schema from node
        schema = node_class.get_config_schema()
        
        # Check if node has LLMCapability and inject LLM config
        from app.core.nodes.capabilities import LLMCapability, PasswordProtectedFileCapability
        if issubclass(node_class, LLMCapability):
            # Inject LLM config fields at the beginning
            llm_schema = {
                "llm_provider": {
                    "type": "string",
                    "label": "LLM Provider",
                    "description": "AI provider for inference (uses default from settings if not specified)",
                    "required": False,
                    "widget": "provider_select",  # Special widget that fetches from DB
                    "placeholder": "Default from settings",
                    "group": "AI Configuration",
                    "api_endpoint": "/api/v1/ai/providers/available"  # Fetch available providers
                },
                "llm_model": {
                    "type": "string",
                    "label": "Model",
                    "description": "Model to use (uses default from provider settings if not specified)",
                    "required": False,
                    "widget": "model_select",  # Dynamic widget based on provider
                    "placeholder": "Default from provider settings",
                    "group": "AI Configuration",
                    "depends_on": "llm_provider",  # Frontend will fetch models when provider changes
                    "api_endpoint": "/api/v1/ai/providers/{llm_provider}/models"  # Dynamic endpoint with provider
                },
                "llm_temperature": {
                    "type": "float",
                    "label": "Temperature",
                    "description": "Controls randomness (0.0 = deterministic, 1.0 = creative)",
                    "required": False,
                    "widget": "slider",
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.1,
                    "default": 0.7,
                    "group": "AI Configuration"
                }
            }
            
            # Merge LLM schema at the beginning (so it appears first in UI)
            schema = {**llm_schema, **schema}
        
        # Check if node has PasswordProtectedFileCapability and inject password field
        if issubclass(node_class, PasswordProtectedFileCapability):
            # Inject password field at the end (after node-specific fields)
            password_schema = {
                "file_password": {
                    "type": "string",
                    "label": "File Password (Optional)",
                    "description": "Password for encrypted/protected files (PDF, Office docs, etc.)",
                    "required": False,
                    "widget": "password",
                    "placeholder": "",
                    "help": "Leave empty if file is not password-protected. Supports PDF, DOCX, XLSX, PPTX encryption."
                }
            }
            
            # Merge password schema at the end (so it appears last in UI)
            schema = {**schema, **password_schema}
            
            logger.debug(f"✨ Injected LLM config fields for {node_class.__name__}")
        
        # Check if node has ExportCapability and inject export config
        from app.core.nodes.capabilities import ExportCapability
        if issubclass(node_class, ExportCapability):
            # Inject export config fields at the beginning (or after LLM fields)
            export_schema = {
                "export_mode": {
                    "type": "select",
                    "widget": "select",
                    "label": "Export Mode",
                    "description": "Where to save the exported file",
                    "required": False,
                    "default": "download",
                    "options": [
                        {"label": "Quick Download (to Downloads folder)", "value": "download"},
                        {"label": "Save to Path", "value": "path"}
                    ],
                    "help": "'Quick Download' saves to browser Downloads folder. 'Save to Path' saves to a folder you specify.",
                    "group": "Export Configuration"
                },
                "output_folder": {
                    "type": "string",
                    "label": "Output Folder",
                    "description": "Folder where file will be saved (supports UNC paths like \\\\server\\share\\path)",
                    "required": False,
                    "placeholder": "C:\\Users\\YourName\\Desktop\\exports or \\\\192.168.1.100\\shared\\folder",
                    "widget": "folder_picker",
                    "help": "Full path to folder. Supports local paths (C:\\...) and network shares (\\\\server\\share\\path). Only used in 'Save to Path' mode.",
                    "show_if": {"export_mode": "path"},
                    "group": "Export Configuration"
                },
                "network_credential": {
                    "type": "string",
                    "label": "Network Share Credential (Optional)",
                    "description": "Credential for network share authentication",
                    "required": False,
                    "widget": "credential",
                    "help": "Only needed for UNC network paths that require authentication (e.g., \\\\server\\share). Create a Basic Auth credential with username/password.",
                    "show_if": {"export_mode": "path"},
                    "group": "Export Configuration"
                },
                "filename": {
                    "type": "string",
                    "label": "Filename",
                    "description": "Name of the exported file",
                    "required": False,
                    "default": "export_{timestamp}",
                    "placeholder": "export_{timestamp}.csv",
                    "widget": "text",
                    "help": "Use {timestamp}, {date}, {time} for dynamic names. File extension will be added automatically.",
                    "group": "Export Configuration"
                }
            }
            
            # Merge export schema at the beginning (after LLM if present)
            schema = {**export_schema, **schema}
            
            logger.debug(f"✨ Injected Export config fields for {node_class.__name__}")
        
        return schema
    except Exception as e:
        logger.debug(f"Error extracting config schema from {node_class.__name__}: {e}")
        return {}
