"""
State Update Node

Updates existing persistent state (merge/increment).
"""

from typing import Any, Dict, Optional, List
import logging
from datetime import datetime, timezone

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import PortType, NodeCategory
from app.database.session import get_db
from app.database.models.workflow_state import WorkflowState
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@register_node(
    node_type="state_update",
    category=NodeCategory.BUSINESS,
    name="Update State",
    description="Update persistent workflow state (merge or increment)",
    icon="fa-solid fa-edit"
)
class StateUpdateNode(Node):
    """
    Update persistent state (merge or increment).
    
    Updates existing state without overwriting entire object.
    Use cases:
    - Increment inventory count
    - Merge customer data
    - Update specific fields
    - Append to history
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "trigger",
                "type": PortType.SIGNAL,
                "display_name": "Trigger",
                "description": "Trigger state update",
                "required": False
            },
            {
                "name": "state_key",
                "type": PortType.TEXT,
                "display_name": "State Key",
                "description": "State key to update",
                "required": True
            },
            {
                "name": "updates",
                "type": PortType.UNIVERSAL,
                "display_name": "Updates",
                "description": "Updates to apply (object for merge, number for increment)",
                "required": True
            },
            {
                "name": "namespace",
                "type": PortType.TEXT,
                "display_name": "Namespace",
                "description": "Optional namespace",
                "required": False
            },
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "success",
                "type": PortType.SIGNAL,
                "display_name": "Success",
                "description": "State updated successfully"
            },
            {
                "name": "new_value",
                "type": PortType.UNIVERSAL,
                "display_name": "New Value",
                "description": "Updated state value"
            },
            {
                "name": "state_version",
                "type": PortType.UNIVERSAL,
                "display_name": "State Version",
                "description": "New state version number"
            },
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "operation": {
                "label": "Operation",
                "type": "select",
                "options": ["merge", "increment"],
                "default": "merge",
                "description": "Update operation: merge (objects) or increment (numbers)",
            },
            "create_if_missing": {
                "label": "Create If Missing",
                "type": "boolean",
                "default": False,
                "description": "Create state if it doesn't exist",
            },
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Update state in database"""
        state_key = input_data.ports.get("state_key")
        updates = input_data.ports.get("updates")
        namespace = input_data.ports.get("namespace")
        
        operation = self.resolve_config(input_data, "operation", "merge")
        create_if_missing = self.resolve_config(input_data, "create_if_missing", False)
        
        if not state_key:
            raise ValueError("state_key is required")
        
        if updates is None:
            raise ValueError("updates is required")
        
        # Get database session
        db: Session = next(get_db())
        
        try:
            # Query existing state
            query = db.query(WorkflowState).filter(
                WorkflowState.workflow_id == input_data.workflow_id,
                WorkflowState.state_key == state_key
            )
            
            if namespace:
                query = query.filter(WorkflowState.state_namespace == namespace)
            else:
                query = query.filter(WorkflowState.state_namespace.is_(None))
            
            state = query.first()
            
            if not state:
                if create_if_missing:
                    # Create new state
                    import uuid
                    state = WorkflowState(
                        id=str(uuid.uuid4()),
                        workflow_id=input_data.workflow_id,
                        state_key=state_key,
                        state_namespace=namespace,
                        state_value=updates,
                        state_version=1,
                        last_updated_by_execution=input_data.execution_id,
                        last_updated_at=datetime.now(timezone.utc),
                        created_at=datetime.now(timezone.utc),
                    )
                    db.add(state)
                    db.commit()
                    
                    logger.info(f"📦 State created: {state_key}")
                    return {
                        "success": True,
                        "new_value": updates,
                        "state_version": 1,
                    }
                else:
                    raise ValueError(f"State not found: {state_key}")
            
            # Apply update based on operation
            if operation == "merge":
                # Merge objects
                if not isinstance(state.state_value, dict):
                    raise ValueError("State value must be an object for merge operation")
                
                if not isinstance(updates, dict):
                    raise ValueError("Updates must be an object for merge operation")
                
                new_value = {**state.state_value, **updates}
            
            elif operation == "increment":
                # Increment number
                if not isinstance(state.state_value, (int, float)):
                    raise ValueError("State value must be a number for increment operation")
                
                if not isinstance(updates, (int, float)):
                    raise ValueError("Updates must be a number for increment operation")
                
                new_value = state.state_value + updates
            
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            # Update state
            state.state_value = new_value
            state.state_version += 1
            state.last_updated_by_execution = input_data.execution_id
            state.last_updated_at = datetime.now(timezone.utc)
            
            db.commit()
            
            logger.info(f"📦 State updated: {state_key} (version {state.state_version})")
            return {
                "success": True,
                "new_value": new_value,
                "state_version": state.state_version,
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update state: {e}")
            raise
        finally:
            db.close()
