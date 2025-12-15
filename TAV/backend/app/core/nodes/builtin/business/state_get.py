"""
State Get Node

Retrieves persistent state for a workflow.
"""

from typing import Any, Dict, Optional, List
import logging
import json

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import PortType, NodeCategory
from app.database.session import get_db
from app.database.models.workflow_state import WorkflowState
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@register_node(
    node_type="state_get",
    category=NodeCategory.BUSINESS,
    name="Get State",
    description="Retrieve persistent workflow state",
    icon="fa-solid fa-database"
)
class StateGetNode(Node):
    """
    Get persistent state for a workflow.
    
    Retrieves state that persists across workflow executions.
    Use cases:
    - Get current inventory levels
    - Load business configuration
    - Read conversation history
    - Load checkpoint data
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "trigger",
                "type": PortType.SIGNAL,
                "display_name": "Trigger",
                "description": "Trigger state retrieval",
                "required": False
            },
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "state_value",
                "type": PortType.UNIVERSAL,
                "display_name": "State Value",
                "description": "State data"
            },
            {
                "name": "state_version",
                "type": PortType.UNIVERSAL,
                "display_name": "State Version",
                "description": "State version number"
            },
            {
                "name": "last_updated_at",
                "type": PortType.TEXT,
                "display_name": "Last Updated",
                "description": "Last update timestamp"
            },
            {
                "name": "found",
                "type": PortType.SIGNAL,
                "display_name": "Found",
                "description": "True if state exists"
            },
            {
                "name": "not_found",
                "type": PortType.SIGNAL,
                "display_name": "Not Found",
                "description": "True if state doesn't exist"
            },
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "state_key": {
                "label": "What to Load",
                "type": "string",
                "default": "",
                "required": True,
                "description": "Name of the data to retrieve (e.g., 'inventory', 'customer_data')",
                "placeholder": "e.g., vending_business"
            },
            "namespace": {
                "label": "Environment (Optional)",
                "type": "string",
                "default": "",
                "description": "Separate environment for your data (e.g., 'test', 'production', 'simulation')",
                "placeholder": "e.g., simulation"
            },
            "default_value": {
                "label": "Starting Value (If Not Found)",
                "type": "json",
                "default": {},
                "description": "Initial data to use if nothing is saved yet (JSON format)",
                "placeholder": '{"inventory": 100, "cash": 0}'
            },
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Get state from database"""
        # Get from config instead of ports
        state_key = self.resolve_config(input_data, "state_key")
        namespace = self.resolve_config(input_data, "namespace")
        default_value = self.resolve_config(input_data, "default_value")
        
        # Parse default_value if it's a string
        if isinstance(default_value, str) and default_value:
            try:
                default_value = json.loads(default_value)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Could not parse default_value as JSON: {default_value}")
                default_value = {}
        
        if not state_key:
            raise ValueError("state_key is required")
        
        # Get database session
        db: Session = next(get_db())
        
        try:
            # Query state
            query = db.query(WorkflowState).filter(
                WorkflowState.workflow_id == input_data.workflow_id,
                WorkflowState.state_key == state_key
            )
            
            if namespace:
                query = query.filter(WorkflowState.state_namespace == namespace)
            else:
                query = query.filter(WorkflowState.state_namespace.is_(None))
            
            state = query.first()
            
            if state:
                logger.info(f"📦 State retrieved: {state_key} (namespace={namespace})")
                return {
                    "state_value": state.state_value,
                    "state_version": state.state_version,
                    "last_updated_at": state.last_updated_at.isoformat() if state.last_updated_at else None,
                    "found": True,
                    "not_found": False,
                }
            else:
                logger.info(f"📦 State not found: {state_key}, using default")
                return {
                    "state_value": default_value,
                    "state_version": 0,
                    "last_updated_at": None,
                    "found": False,
                    "not_found": True,
                }
        finally:
            db.close()

