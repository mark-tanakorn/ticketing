"""
Workflow Schemas - Pydantic Models

Modern, type-safe workflow schema based on V1's excellent design
but rebuilt with Pydantic for validation and serialization.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
import uuid


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class WorkflowFormatVersion(str, Enum):
    """Supported workflow format versions"""
    V1_0_0 = "1.0.0"  # Legacy format
    V1_1_0 = "1.1.0"  # Transitional format
    V2_0_0 = "2.0.0"  # Current standardized format


# Current version and supported versions (derived from enum)
WORKFLOW_FORMAT_VERSION = WorkflowFormatVersion.V2_0_0.value
SUPPORTED_VERSIONS = [v.value for v in WorkflowFormatVersion]


class NodeCategory(str, Enum):
    """Industry-standard node categories for workflow organization"""
    # Core workflow categories
    TRIGGERS = "triggers"
    ACTIONS = "actions"
    INPUT = "input"
    OUTPUT = "output"
    PROCESSING = "processing"
    COMMUNICATION = "communication"
    EXPORT = "export"
    
    # Specialized categories
    AI = "ai"
    IMAGE = "image"
    STORAGE = "storage"
    WORKFLOW = "workflow"  # Start, End, Decision, Merge, etc.
    UI = "ui"
    PRODUCTIVITY = "productivity"
    DEVELOPMENT = "development"
    
    # NEW: Business Operations & Analytics
    BUSINESS = "business"  # Business operations, state management, simulations
    ANALYTICS = "analytics"  # Monitoring, metrics, event analysis


class PortType(str, Enum):
    """
    Port types for multimodal workflow data flow.
    
    Core Types:
    - SIGNAL: Control flow
    - UNIVERSAL: General data (JSON, text, numbers)
    
    Multimodal Types:
    - TEXT, IMAGE, AUDIO, VIDEO, DOCUMENT: Specific media types
    
    Special Types:
    - TOOLS, MEMORY, UI: Advanced node interactions
    """
    # Core types
    SIGNAL = "signal"       # Control flow (true/false, triggered/not triggered)
    UNIVERSAL = "universal" # General data (JSON, text, numbers, mixed)
    
    # Multimodal types
    TEXT = "text"           # Plain text, markdown, code
    IMAGE = "image"         # Images (PNG, JPG, base64, URL, etc.)
    AUDIO = "audio"         # Audio files (MP3, WAV, base64, URL, etc.)
    VIDEO = "video"         # Video files (MP4, WebM, URL, etc.)
    DOCUMENT = "document"   # Documents (PDF, DOCX, etc.)
    
    # Special ports
    TOOLS = "tools"         # Tool definitions/capabilities
    MEMORY = "memory"       # Memory/retrieval context
    UI = "ui"               # Human-in-the-loop UI attachment


class ExecutionStatus(str, Enum):
    """Unified status for workflows and executions"""
    NA = "na"                # Never run (no execution record exists)
    PENDING = "pending"      # Monitoring/waiting for triggers (persistent workflows only)
    RUNNING = "running"      # Currently executing
    COMPLETED = "completed"  # Execution finished successfully
    FAILED = "failed"        # Execution finished with error
    STOPPED = "stopped"      # User manually stopped (was "cancelled")
    PAUSED = "paused"        # Execution paused (for resume feature)


# =============================================================================
# WORKFLOW STRUCTURE MODELS
# =============================================================================

class NodePort(BaseModel):
    """
    Node port definition with progressive complexity.
    
    Simple Mode (non-tech users):
    - Just name and type
    - Defaults handle the rest
    
    Advanced Mode (developers):
    - Full control over validation, connections, metadata
    """
    # Core (required)
    name: str = Field(..., description="Port identifier (e.g., 'input', 'url', 'true', 'false')")
    type: PortType = Field(..., description="Port type")
    
    # Display (for visual editor)
    display_name: Optional[str] = Field(
        default=None,
        description="Human-readable name shown in UI (falls back to name if not set)"
    )
    description: str = Field(default="", description="Port description")
    
    # Behavior
    required: bool = Field(default=True, description="Is this port required?")
    max_connections: int = Field(
        default=1,
        description="Maximum connections allowed (-1 for unlimited, used in merge nodes)"
    )
    
    # Validation
    default_value: Any = Field(default=None, description="Default value if not connected")
    validation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Validation rules (e.g., {'min': 0, 'max': 100, 'pattern': '.*'})"
    )
    
    # Advanced
    hidden: bool = Field(
        default=False,
        description="Hidden ports (for framework-injected data)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional port metadata"
    )

    def get_display_name(self) -> str:
        """Get display name for UI (falls back to name)"""
        return self.display_name or self.name.replace("_", " ").title()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "input",
                "type": "universal",
                "display_name": "Input Data",
                "description": "Data to process",
                "required": True,
                "max_connections": 1,
                "default_value": None,
                "validation": None,
                "hidden": False,
                "metadata": {}
            }
        }


class NodeConfiguration(BaseModel):
    """
    Node configuration within a workflow.
    
    Smart Defaults:
    - input_ports = None → Auto-creates 1 universal input (except triggers)
    - output_ports = None → Auto-creates 1 universal output
    - input_ports = [] → Explicitly no inputs (triggers, start nodes)
    - output_ports = [] → Explicitly no outputs (end nodes, sinks)
    """
    node_id: str = Field(..., description="Unique node identifier")
    node_type: str = Field(..., description="Node type identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="Node description")
    
    # Node classification
    category: Optional[NodeCategory] = Field(default=None, description="Node category")
    
    # Port definitions (None = use smart defaults, [] = no ports, [ports] = explicit)
    input_ports: Optional[List[NodePort]] = Field(
        default=None,
        description="Input ports (None = auto-detect, [] = no inputs, [ports] = explicit)"
    )
    output_ports: Optional[List[NodePort]] = Field(
        default=None,
        description="Output ports (None = auto-detect, [] = no outputs, [ports] = explicit)"
    )
    
    # Node-specific configuration
    config: Dict[str, Any] = Field(default_factory=dict, description="Node configuration")
    
    # Shared state configuration
    share_output_to_variables: bool = Field(
        default=False,
        description="Automatically share node outputs to workflow variables (opt-in)"
    )
    variable_name: Optional[str] = Field(
        default=None,
        description="Custom variable name for shared state (defaults to node name if not provided)"
    )
    
    # Visual positioning (for editors)
    position: Dict[str, float] = Field(
        default_factory=lambda: {"x": 0, "y": 0},
        description="Node position in editor"
    )
    
    # Visual flipping (for editors)
    flipped: bool = Field(
        default=False,
        description="Whether node ports are flipped horizontally in the visual editor"
    )
    icon: Optional[str] = Field(
        default=None,
        description="Icon class for visual representation (e.g., 'fa-solid fa-bolt')"
    )
    
    # Node metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @model_validator(mode='after')
    def apply_smart_defaults(self) -> 'NodeConfiguration':
        """
        Apply smart defaults for ports based on node category.
        
        This enables the "it just works" experience for non-technical users
        while allowing developers to override when needed.
        """
        # Apply input port defaults
        if self.input_ports is None:
            self.input_ports = self._get_default_input_ports()
        
        # Apply output port defaults
        if self.output_ports is None:
            self.output_ports = self._get_default_output_ports()
        
        return self
    
    def _get_default_input_ports(self) -> List[NodePort]:
        """
        Smart input port defaults based on node category and type.
        
        Returns:
            List of default input ports
        """
        # Source nodes have no inputs (triggers, start nodes)
        if self.category == NodeCategory.TRIGGERS:
            return []
        
        # Start node (explicit workflow start)
        if self.node_type.lower() in ("start", "workflow_start"):
            return []
        
        # All other nodes get 1 universal input by default
        return [
            NodePort(
                name="input",
                type=PortType.UNIVERSAL,
                display_name="Input",
                description="Input data"
            )
        ]
    
    def _get_default_output_ports(self) -> List[NodePort]:
        """
        Smart output port defaults based on node category.
        
        Returns:
            List of default output ports
        """
        # Most nodes get 1 universal output by default
        return [
            NodePort(
                name="output",
                type=PortType.UNIVERSAL,
                display_name="Output",
                description="Output data"
            )
        ]
    
    def is_simple_node(self) -> bool:
        """
        Check if this is a simple node (1 input, 1 output with default names).
        
        Simple nodes can have their ports hidden in the visual editor for cleaner UX.
        
        Returns:
            True if node has default single input/output configuration
        """
        has_single_input = (
            len(self.input_ports) == 1 
            and self.input_ports[0].name == "input"
        )
        has_single_output = (
            len(self.output_ports) == 1 
            and self.output_ports[0].name == "output"
        )
        return has_single_input and has_single_output
    
    def get_display_mode(self) -> str:
        """
        Get display mode for visual editor.
        
        Returns:
            "simple" for basic nodes (hide port labels)
            "advanced" for complex nodes (show port labels)
        """
        return "simple" if self.is_simple_node() else "advanced"

    class Config:
        json_schema_extra = {
            "example": {
                "node_id": "node_1",
                "node_type": "http_request",
                "name": "HTTP Request",
                "description": "Make an HTTP request",
                "category": "actions",
                "input_ports": None,  # Will auto-create default input
                "output_ports": None,  # Will auto-create default output
                "config": {"url": "https://api.example.com"},
                "position": {"x": 100, "y": 100},
                "metadata": {}
            }
        }


class Connection(BaseModel):
    """Connection between node ports"""
    connection_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique connection identifier"
    )
    source_node_id: str = Field(..., description="Source node ID")
    source_port: str = Field(..., description="Source port name")
    target_node_id: str = Field(..., description="Target node ID")
    target_port: str = Field(..., description="Target port name")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Connection metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "connection_id": "conn_1",
                "source_node_id": "node_1",
                "source_port": "output",
                "target_node_id": "node_2",
                "target_port": "input",
                "metadata": {}
            }
        }


class WorkflowMetadata(BaseModel):
    """Workflow metadata and analytics"""
    # Required metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="unknown", description="Creator username")
    
    # Optional metadata
    tags: List[str] = Field(default_factory=list, description="Workflow tags")
    category: str = Field(default="", description="Workflow category")
    complexity: int = Field(default=1, ge=1, le=5, description="Complexity rating (1-5)")
    estimated_duration: Optional[int] = Field(default=None, description="Estimated duration in seconds")
    
    # Version control
    version: str = Field(default="1.0.0", description="Workflow version")
    parent_workflow_id: Optional[str] = Field(default=None, description="Parent workflow if cloned")
    
    # Deployment metadata
    target_environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Target environment"
    )
    deployment_config: Dict[str, Any] = Field(default_factory=dict, description="Deployment configuration")
    
    # Analytics metadata
    usage_count: int = Field(default=0, ge=0, description="Number of executions")
    last_executed: Optional[datetime] = Field(default=None, description="Last execution timestamp")
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Success rate (0.0-1.0)")
    
    # Custom metadata
    custom: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


class WorkflowDefinition(BaseModel):
    """
    Complete workflow definition.
    
    This is the core workflow structure that defines nodes, connections,
    and configuration. Separate from execution state.
    """
    # Core identification
    workflow_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique workflow identifier"
    )
    name: str = Field(..., description="Workflow name")
    description: str = Field(default="", description="Workflow description")
    
    # Format versioning
    format_version: str = Field(
        default=WORKFLOW_FORMAT_VERSION,
        description="Workflow format version"
    )
    
    # Workflow structure
    nodes: List[NodeConfiguration] = Field(
        default_factory=list,
        description="Workflow nodes"
    )
    connections: List[Connection] = Field(
        default_factory=list,
        description="Node connections"
    )
    
    # Global configuration
    global_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Global workflow configuration"
    )
    variables: Dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow variables"
    )
    
    # Metadata
    metadata: WorkflowMetadata = Field(
        default_factory=WorkflowMetadata,
        description="Workflow metadata"
    )
    
    # Execution constraints
    execution_constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution constraints (timeouts, retries, etc.)"
    )

    @field_validator('format_version')
    @classmethod
    def validate_format_version(cls, v: str) -> str:
        """Validate format version is supported"""
        if v not in SUPPORTED_VERSIONS:
            raise ValueError(f"Unsupported format version: {v}. Supported: {SUPPORTED_VERSIONS}")
        return v

    def get_node_by_id(self, node_id: str) -> Optional[NodeConfiguration]:
        """Get node by ID"""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def validate_structure(self) -> List[str]:
        """
        Validate workflow structure.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check for duplicate node IDs
        node_ids = [node.node_id for node in self.nodes]
        duplicates = [nid for nid in node_ids if node_ids.count(nid) > 1]
        if duplicates:
            errors.append(f"Duplicate node IDs: {set(duplicates)}")
        
        # Validate connections reference existing nodes
        node_id_set = set(node_ids)
        for conn in self.connections:
            if conn.source_node_id not in node_id_set:
                errors.append(f"Connection references unknown source node: {conn.source_node_id}")
            if conn.target_node_id not in node_id_set:
                errors.append(f"Connection references unknown target node: {conn.target_node_id}")
        
        # Validate port connections
        for conn in self.connections:
            source_node = self.get_node_by_id(conn.source_node_id)
            target_node = self.get_node_by_id(conn.target_node_id)
            
            if source_node:
                source_port_names = [p.name for p in source_node.output_ports]
                if conn.source_port not in source_port_names:
                    errors.append(
                        f"Connection references unknown source port: "
                        f"{conn.source_node_id}.{conn.source_port}"
                    )
            
            if target_node:
                target_port_names = [p.name for p in target_node.input_ports]
                if conn.target_port not in target_port_names:
                    errors.append(
                        f"Connection references unknown target port: "
                        f"{conn.target_node_id}.{conn.target_port}"
                    )
        
        return errors

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "wf_123",
                "name": "Example Workflow",
                "description": "A sample workflow",
                "format_version": "2.0.0",
                "nodes": [
                    {
                        "node_id": "node_1",
                        "node_type": "manual_trigger",
                        "name": "Start",
                        "category": "triggers",
                        "output_ports": [{"name": "signal", "type": "signal"}],
                        "config": {},
                        "position": {"x": 100, "y": 100}
                    }
                ],
                "connections": [],
                "global_config": {},
                "variables": {},
                "metadata": {
                    "created_at": "2025-01-01T00:00:00",
                    "updated_at": "2025-01-01T00:00:00",
                    "created_by": "user"
                },
                "execution_constraints": {}
            }
        }


# =============================================================================
# EXECUTION STATE MODELS
# =============================================================================

class NodeExecutionState(BaseModel):
    """State of a single node execution"""
    node_id: str
    status: ExecutionStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowExecutionState(BaseModel):
    """
    Runtime execution state.
    
    Separate from WorkflowDefinition - tracks execution progress and results.
    """
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    status: ExecutionStatus
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # Trigger information
    execution_source: str = Field(
        ..., 
        description="How execution was initiated (manual, webhook, schedule, api, polling, event, child_workflow, retry, etc.)"
    )
    trigger_data: Dict[str, Any] = Field(default_factory=dict)
    started_by: Optional[str] = None
    
    # Node execution states
    node_states: Dict[str, NodeExecutionState] = Field(default_factory=dict)
    
    # Overall results
    error_message: Optional[str] = None
    final_outputs: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "execution_id": "exec_123",
                "workflow_id": "wf_123",
                "status": "running",
                "started_at": "2025-01-01T00:00:00",
                "execution_source": "manual",
                "trigger_data": {},
                "node_states": {},
                "execution_metadata": {}
            }
        }


# =============================================================================
# HELPER MODELS
# =============================================================================

class WorkflowValidationResult(BaseModel):
    """Result of workflow validation"""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    workflow_id: str
    format_version: str


class WorkflowExecutionRequest(BaseModel):
    """Request to execute a workflow"""
    workflow_id: str
    execution_source: str = Field(
        default="manual",
        description="How execution was initiated (manual, webhook, schedule, api, polling, event, etc.)"
    )
    trigger_data: Dict[str, Any] = Field(default_factory=dict)
    started_by: Optional[str] = None
    execution_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Override execution constraints (timeout, retry, etc.)"
    )
