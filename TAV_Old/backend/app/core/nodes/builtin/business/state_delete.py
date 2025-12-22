"""
State Delete Node

Deletes persistent state for a workflow to start fresh.
"""

from typing import Any, Dict, Optional, List
import logging

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import PortType, NodeCategory
from app.database.session import get_db
from app.database.models.workflow_state import WorkflowState
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@register_node(
    node_type="state_delete",
    category=NodeCategory.BUSINESS,
    name="Delete State",
    description="Delete persistent workflow state (reset to fresh start)",
    icon="fa-solid fa-trash"
)
class StateDeleteNode(Node):
    """
    Delete persistent state for a workflow.
    
    Use this to reset state to a fresh start, useful for:
    - Starting a new simulation/benchmark from scratch
    - Clearing cached data
    - Resetting counters
    - Cleaning up after tests
    
    Place this node BEFORE your workflow loop to ensure clean state.
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "trigger",
                "type": PortType.SIGNAL,
                "display_name": "Trigger",
                "description": "Trigger state deletion",
                "required": False
            },
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "deleted",
                "type": PortType.SIGNAL,
                "display_name": "Deleted",
                "description": "State was found and deleted"
            },
            {
                "name": "not_found",
                "type": PortType.SIGNAL,
                "display_name": "Not Found",
                "description": "State didn't exist (nothing to delete)"
            },
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "state_key": {
                "label": "State to Delete",
                "type": "string",
                "default": "",
                "required": True,
                "description": "Name of the state to delete (e.g., 'vending_business')",
                "placeholder": "e.g., vending_business"
            },
            "namespace": {
                "label": "Environment (Optional)",
                "type": "string",
                "default": "",
                "required": False,
                "description": "State environment/namespace. Use same namespace as Get/Set State nodes.",
                "placeholder": "e.g., simulation"
            },
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """
        Delete state from database.
        """
        # Get config
        state_key = self.resolve_config(input_data, "state_key")
        namespace = self.resolve_config(input_data, "namespace", None)
        
        if not state_key:
            raise ValueError("state_key is required")
        
        # Get workflow ID from context
        workflow_id = input_data.workflow_id
        
        # Database session
        db: Session = next(get_db())
        
        try:
            # Build query
            query = db.query(WorkflowState).filter(
                WorkflowState.workflow_id == workflow_id,
                WorkflowState.state_key == state_key
            )
            
            if namespace:
                query = query.filter(WorkflowState.state_namespace == namespace)
            else:
                query = query.filter(WorkflowState.state_namespace.is_(None))
            
            # Find and delete state
            state = query.first()
            
            if state:
                db.delete(state)
                db.commit()
                logger.info(f"🗑️ State deleted: {state_key} (namespace={namespace or 'default'})")
                
                return {
                    "deleted": True,
                    "not_found": False,
                    "state_key": state_key,
                    "namespace": namespace,
                    "message": f"State '{state_key}' deleted successfully"
                }
            else:
                logger.info(f"🔍 State not found (nothing to delete): {state_key} (namespace={namespace or 'default'})")
                
                return {
                    "deleted": False,
                    "not_found": True,
                    "state_key": state_key,
                    "namespace": namespace,
                    "message": f"State '{state_key}' does not exist"
                }
        
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete state: {e}")
            raise
        finally:
            db.close()

