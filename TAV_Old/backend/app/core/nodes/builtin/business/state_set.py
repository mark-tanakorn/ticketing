"""
State Set Node

Sets/creates persistent state for a workflow.
"""

from typing import Any, Dict, Optional, List
import logging
import uuid
from datetime import datetime, timezone

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import PortType, NodeCategory
from app.database.session import get_db
from app.database.models.workflow_state import WorkflowState
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@register_node(
    node_type="state_set",
    category=NodeCategory.BUSINESS,
    name="Set State",
    description="Create or overwrite persistent workflow state",
    icon="fa-solid fa-save"
)
class StateSetNode(Node):
    """
    Set/create persistent state for a workflow.
    
    Creates or overwrites state that persists across workflow executions.
    Use cases:
    - Initialize business state
    - Save inventory levels
    - Store configuration
    - Create checkpoint
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "trigger",
                "type": PortType.SIGNAL,
                "display_name": "Trigger",
                "description": "Trigger state save",
                "required": False
            },
            {
                "name": "state_value",
                "type": PortType.UNIVERSAL,
                "display_name": "State Value",
                "description": "State data to store",
                "required": True
            },
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "success",
                "type": PortType.SIGNAL,
                "display_name": "Success",
                "description": "State saved successfully"
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
            "state_key": {
                "label": "What to Save",
                "type": "string",
                "default": "",
                "required": True,
                "description": "Name of the data to save (e.g., 'inventory', 'customer_data')",
                "placeholder": "e.g., vending_business"
            },
            "namespace": {
                "label": "Environment (Optional)",
                "type": "string",
                "default": "",
                "description": "Separate environment for your data (e.g., 'test', 'production', 'simulation')",
                "placeholder": "e.g., simulation"
            },
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Set state in database"""
        # Get from config
        state_key = self.resolve_config(input_data, "state_key")
        namespace = self.resolve_config(input_data, "namespace")
        
        # Get from ports
        state_value = input_data.ports.get("state_value")
        expires_in_seconds = input_data.ports.get("expires_in_seconds")
        
        if not state_key:
            raise ValueError("state_key is required")
        
        if state_value is None:
            raise ValueError("state_value is required")
        
        # Calculate expiration
        expires_at = None
        if expires_in_seconds:
            from datetime import timedelta
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
        
        # Get database session
        db: Session = next(get_db())
        
        try:
            # Check if state already exists
            query = db.query(WorkflowState).filter(
                WorkflowState.workflow_id == input_data.workflow_id,
                WorkflowState.state_key == state_key
            )
            
            if namespace:
                query = query.filter(WorkflowState.state_namespace == namespace)
            else:
                query = query.filter(WorkflowState.state_namespace.is_(None))
            
            existing_state = query.first()
            
            if existing_state:
                # Update existing state
                existing_state.state_value = state_value
                existing_state.state_version += 1
                existing_state.last_updated_by_execution = input_data.execution_id
                existing_state.last_updated_at = datetime.now(timezone.utc)
                if expires_at:
                    existing_state.expires_at = expires_at
                
                db.commit()
                
                logger.info(f"📦 State updated: {state_key} (version {existing_state.state_version})")
                return {
                    "success": True,
                    "state_version": existing_state.state_version,
                }
            else:
                # Create new state
                new_state = WorkflowState(
                    id=str(uuid.uuid4()),
                    workflow_id=input_data.workflow_id,
                    state_key=state_key,
                    state_namespace=namespace,
                    state_value=state_value,
                    state_version=1,
                    last_updated_by_execution=input_data.execution_id,
                    last_updated_at=datetime.now(timezone.utc),
                    created_at=datetime.now(timezone.utc),
                    expires_at=expires_at,
                )
                
                db.add(new_state)
                db.commit()
                
                logger.info(f"📦 State created: {state_key} (namespace={namespace})")
                return {
                    "success": True,
                    "state_version": 1,
                }
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to set state: {e}")
            raise
        finally:
            db.close()
