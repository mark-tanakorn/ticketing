"""
Node Base Class

Abstract interface that all workflow nodes must implement.

⚠️ IMPORTANT: All nodes MUST use the @register_node decorator!

Example:
    from app.core.nodes.base import Node, NodeExecutionInput
    from app.core.nodes.registry import register_node
    from app.schemas.workflow import NodeCategory, PortType
    
    @register_node(
        node_type="my_custom_node",
        category=NodeCategory.ACTIONS,
        name="My Custom Node",
        description="Does something awesome",
        icon="fa-solid fa-star"
    )
    class MyCustomNode(Node):
        @classmethod
        def get_input_ports(cls) -> List[Dict[str, Any]]:
            return [{"name": "input", "type": PortType.UNIVERSAL, ...}]
        
        @classmethod
        def get_output_ports(cls) -> List[Dict[str, Any]]:
            return [{"name": "output", "type": PortType.UNIVERSAL, ...}]
        
        async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
            return {"output": input_data.ports.get("input")}
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

from app.schemas.workflow import NodeConfiguration, NodePort, PortType

@dataclass
class NodeExecutionInput:
    """
    Input data for node execution.
    
    Contains both the port data and metadata about the execution.
    """
    # Port inputs (from connected nodes)
    ports: Dict[str, Any]  # port_name → value
    
    # Execution metadata (framework-provided)
    workflow_id: str
    execution_id: str
    node_id: str
    
    # Workflow variables (can be read/written)
    variables: Dict[str, Any]
    
    # Node configuration
    config: Dict[str, Any]
    
    # Credentials (injected by executor, credential_id → decrypted data)
    credentials: Optional[Dict[int, Dict[str, Any]]] = None
    
    # Callback to execute other nodes (for Agent nodes)
    # Signature: async def node_runner(node_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]
    node_runner: Optional[Callable] = None
    
    # Frontend origin URL (auto-detected from request headers)
    # Used by nodes like Email Approval to generate correct review links
    frontend_origin: Optional[str] = None


class Node(ABC):
    """
    Abstract base class for all workflow nodes.
    
    All custom nodes must inherit from this class and implement:
    - execute() - Node execution logic
    - get_input_ports() - Define input port schema (class method)
    - get_output_ports() - Define output port schema (class method)
    - get_config_schema() - Define configuration schema (class method)
    """
    
    def __init__(self, config: NodeConfiguration):
        """
        Initialize node with configuration.
        
        Args:
            config: Node configuration from workflow definition
        """
        self.node_id = config.node_id
        self.node_type = config.node_type
        self.name = config.name
        self.description = config.description
        self.category = config.category
        self.config = config.config
        
        # Get port definitions from class methods
        self.input_ports = self._build_ports(self.get_input_ports())
        self.output_ports = self._build_ports(self.get_output_ports())
        
        # Initialize capability attributes if they're used by mixins
        # This ensures mixins work correctly even if super().__init__() chain is broken
        if not hasattr(self, '_llm_config_cache'):
            self._llm_config_cache = None
        if not hasattr(self, '_langchain_manager'):
            self._langchain_manager = None
    
    def _build_ports(self, port_defs: List[Dict[str, Any]]) -> List:
        """Convert port definitions to NodePort objects"""
        from app.schemas.workflow import NodePort
        return [
            NodePort(**port) if isinstance(port, dict) else port
            for port in port_defs
        ]
    
    # ==================== Node Definition Class Methods ====================
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """
        Define input ports for this node.
        
        Override this method in your node class to define input ports.
        
        Returns:
            List of port definitions
        
        Example:
            @classmethod
            def get_input_ports(cls):
                return [
                    {
                        "name": "text",
                        "type": PortType.TEXT,
                        "display_name": "Text Input",
                        "description": "Input text to process",
                        "required": True
                    },
                    {
                        "name": "max_length",
                        "type": PortType.UNIVERSAL,
                        "display_name": "Max Length",
                        "description": "Maximum length",
                        "required": False,
                        "default_value": 100
                    }
                ]
        """
        return []
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """
        Define output ports for this node.
        
        Override this method in your node class to define output ports.
        
        Returns:
            List of port definitions
        
        Example:
            @classmethod
            def get_output_ports(cls):
                return [
                    {
                        "name": "result",
                        "type": PortType.TEXT,
                        "display_name": "Result",
                        "description": "Processed text output"
                    }
                ]
        """
        return []
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Define configuration schema for this node.
        
        Override this method in your node class to define configuration fields.
        
        Returns:
            Dictionary of configuration field definitions
        
        Example:
            @classmethod
            def get_config_schema(cls):
                return {
                    "text": {
                        "type": "string",
                        "label": "Text Content",
                        "description": "Text to output",
                        "required": True,
                        "default": "",
                        "widget": "textarea"
                    },
                    "max_length": {
                        "type": "integer",
                        "label": "Max Length",
                        "description": "Maximum character length",
                        "required": False,
                        "default": 1000,
                        "widget": "number",
                        "min": 0,
                        "max": 10000
                    }
                }
        
        Supported types: string, integer, float, boolean, select
        Supported widgets: text, textarea, number, checkbox, select, color, date
        """
        return {}
    
    # ==================== Legacy Port Helpers (Deprecated) ====================
    
    def define_input_ports(self, ports: List[Dict[str, Any]]) -> None:
        """
        Define input ports for this node.
        
        Call this in __init__ to set up your node's input ports.
        
        Args:
            ports: List of port definitions
        
        Example:
            self.define_input_ports([
                {"name": "text", "type": PortType.TEXT, "required": True},
                {"name": "max_length", "type": PortType.UNIVERSAL, "default_value": 100}
            ])
        """
        from app.schemas.workflow import NodePort
        self.input_ports = [
            NodePort(**port) if isinstance(port, dict) else port
            for port in ports
        ]
    
    def define_output_ports(self, ports: List[Dict[str, Any]]) -> None:
        """
        Define output ports for this node.
        
        Call this in __init__ to set up your node's output ports.
        
        Args:
            ports: List of port definitions
        
        Example:
            self.define_output_ports([
                {"name": "result", "type": PortType.TEXT},
                {"name": "word_count", "type": PortType.UNIVERSAL}
            ])
        """
        from app.schemas.workflow import NodePort
        self.output_ports = [
            NodePort(**port) if isinstance(port, dict) else port
            for port in ports
        ]
    
    def add_input_port(
        self, 
        name: str, 
        port_type: PortType, 
        display_name: Optional[str] = None,
        description: str = "",
        required: bool = True,
        default_value: Any = None
    ) -> None:
        """
        Add a single input port (convenience method).
        
        Args:
            name: Port identifier
            port_type: Port type (PortType enum)
            display_name: Human-readable name (defaults to name)
            description: Port description
            required: Is this port required?
            default_value: Default value if not connected
        """
        from app.schemas.workflow import NodePort
        self.input_ports.append(NodePort(
            name=name,
            type=port_type,
            display_name=display_name,
            description=description,
            required=required,
            default_value=default_value
        ))
    
    def add_output_port(
        self, 
        name: str, 
        port_type: PortType,
        display_name: Optional[str] = None,
        description: str = ""
    ) -> None:
        """
        Add a single output port (convenience method).
        
        Args:
            name: Port identifier
            port_type: Port type (PortType enum)
            display_name: Human-readable name (defaults to name)
            description: Port description
        """
        from app.schemas.workflow import NodePort
        self.output_ports.append(NodePort(
            name=name,
            type=port_type,
            display_name=display_name,
            description=description
        ))
    
    # ==================== Abstract Methods ====================
    
    @abstractmethod
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """
        Execute the node's logic.
        
        Args:
            input_data: Input data containing ports, metadata, variables, config
        
        Returns:
            Dictionary of output port values: {port_name: value}
            
        Raises:
            Exception: If execution fails
        
        Example:
            async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
                # Get input from port
                text = input_data.ports.get("input", "")
                
                # Do work
                result = text.upper()
                
                # Return output ports
                return {"output": result}
        """
        pass
    
    def validate_inputs(self, ports: Dict[str, Any]) -> List[str]:
        """
        Validate that required input ports are present.
        
        Args:
            ports: Input port data
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for port in self.input_ports:
            if port.required and port.name not in ports:
                if port.default_value is None:
                    errors.append(f"Required input port '{port.name}' is missing")
        
        return errors
    
    def get_input_port(self, name: str) -> Optional[NodePort]:
        """Get input port definition by name"""
        for port in self.input_ports:
            if port.name == name:
                return port
        return None
    
    def get_output_port(self, name: str) -> Optional[NodePort]:
        """Get output port definition by name"""
        for port in self.output_ports:
            if port.name == name:
                return port
        return None
    
    @property
    def resource_classes(self) -> List[str]:
        """
        Get required resource pools based on node capabilities.
        
        Auto-detected from capability mixins (LLMCapability, AICapability, etc.).
        Used by executor for resource management (rate limiting, concurrency control).
        
        Returns:
            List of resource class names: ["standard"], ["llm"], ["ai"], or ["llm", "ai"]
        
        Examples:
            - Standard node: ["standard"]
            - LLM node: ["llm"]
            - AI compute node: ["ai"]
            - LLM + AI node: ["llm", "ai"]
        """
        from app.core.nodes.capabilities import get_resource_classes
        return get_resource_classes(self)
    
    # ==================== Variable Resolution Helpers ====================
    
    def resolve_config(self, input_data: NodeExecutionInput, config_key: str, default: Any = None) -> Any:
        """
        Resolve config value with variable support.
        
        This is a convenience helper for nodes to easily resolve config values
        that might contain variable references or templates.
        
        Args:
            input_data: Node execution input (contains config and variables)
            config_key: Config key to resolve
            default: Default value if key not found
        
        Returns:
            Resolved value (with variables/templates replaced)
        
        Examples:
            # In node execute method:
            async def execute(self, input_data: NodeExecutionInput):
                # Automatically resolves variables/templates
                phone = self.resolve_config(input_data, "phone_number")
                message = self.resolve_config(input_data, "message", "Default message")
                
                # phone might be from variable: trigger_1.phone
                # message might be template: "Hello {{trigger_1.name}}"
        """
        from app.core.nodes.variables import resolve_config_value
        
        config_value = input_data.config.get(config_key, default)
        return resolve_config_value(config_value, input_data.variables)
    
    def resolve_variable(self, input_data: NodeExecutionInput, variable_path: str) -> Optional[Any]:
        """
        Resolve a specific variable path from shared space.
        
        Args:
            input_data: Node execution input (contains variables)
            variable_path: Variable path like "node_id.field"
        
        Returns:
            Resolved value or None if not found
        
        Example:
            # In node execute method:
            phone = self.resolve_variable(input_data, "trigger_1.phone")
            user_name = self.resolve_variable(input_data, "trigger_1.user_name")
        """
        from app.core.nodes.variables import resolve_variable
        
        return resolve_variable(variable_path, input_data.variables)
    
    def resolve_template(self, input_data: NodeExecutionInput, template: str) -> str:
        """
        Resolve template string with {{variable}} placeholders.
        
        Args:
            input_data: Node execution input (contains variables)
            template: Template string like "Hello {{node_id.name}}"
        
        Returns:
            Resolved string with variables replaced
        
        Example:
            # In node execute method:
            message = self.resolve_template(
                input_data,
                "Hello {{trigger_1.name}}, order #{{trigger_1.order_id}}"
            )
        """
        from app.core.nodes.variables import resolve_template
        
        return resolve_template(template, input_data.variables)
    
    def resolve_credential(self, input_data: NodeExecutionInput, config_key: str) -> Optional[Dict[str, Any]]:
        """
        Resolve credential from config and return decrypted data.
        
        This helper retrieves a credential ID from the node's configuration,
        then looks it up in the injected credentials dictionary to get the
        decrypted credential data.
        
        Args:
            input_data: Node execution input (contains config and credentials)
            config_key: Config key that contains the credential ID
        
        Returns:
            Decrypted credential data dictionary or None if not found
            
        Example:
            # In node execute method:
            async def execute(self, input_data: NodeExecutionInput):
                # Get credential data
                credential = self.resolve_credential(input_data, "credential_id")
                
                if not credential:
                    raise ValueError("Credential not found")
                
                # Access credential fields based on type
                # API Key:
                api_key = credential.get("api_key")
                
                # Basic Auth:
                username = credential.get("username")
                password = credential.get("password")
                
                # SMTP:
                host = credential.get("host")
                password = credential.get("password")
                
                # Use credential in your node logic
                response = await make_api_call(api_key=api_key)
        """
        # Get credential ID from config
        credential_id = self.resolve_config(input_data, config_key)
        
        if not credential_id:
            return None
        
        # Convert to int if string
        if isinstance(credential_id, str):
            try:
                credential_id = int(credential_id)
            except (ValueError, TypeError):
                return None
        
        # Get credentials dictionary (injected by executor)
        if not input_data.credentials:
            return None
        
        # Return decrypted credential data
        return input_data.credentials.get(credential_id)
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id='{self.node_id}', type='{self.node_type}')>"
