"""
State Management Service

Provides programmatic access to workflow state.
"""

from typing import Any, Dict, Optional, List
import logging
import uuid
from datetime import datetime, timezone, timedelta

from app.database.session import get_db
from app.database.models.workflow_state import WorkflowState
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class StateService:
    """
    State management service for workflows.
    
    Provides CRUD operations for persistent workflow state.
    """
    
    @staticmethod
    def get_state(
        workflow_id: str,
        state_key: str,
        namespace: Optional[str] = None,
        default: Any = None
    ) -> Any:
        """
        Get state value.
        
        Args:
            workflow_id: Workflow ID
            state_key: State key
            namespace: Optional namespace
            default: Default value if not found
        
        Returns:
            State value or default
        """
        db: Session = next(get_db())
        
        try:
            query = db.query(WorkflowState).filter(
                WorkflowState.workflow_id == workflow_id,
                WorkflowState.state_key == state_key
            )
            
            if namespace:
                query = query.filter(WorkflowState.state_namespace == namespace)
            else:
                query = query.filter(WorkflowState.state_namespace.is_(None))
            
            state = query.first()
            
            if state:
                return state.state_value
            return default
        finally:
            db.close()
    
    @staticmethod
    def set_state(
        workflow_id: str,
        state_key: str,
        state_value: Any,
        namespace: Optional[str] = None,
        execution_id: Optional[str] = None,
        expires_in_seconds: Optional[int] = None
    ) -> int:
        """
        Set state value (create or update).
        
        Args:
            workflow_id: Workflow ID
            state_key: State key
            state_value: State value
            namespace: Optional namespace
            execution_id: Execution ID that updated this state
            expires_in_seconds: Optional expiration time
        
        Returns:
            State version number
        """
        db: Session = next(get_db())
        
        try:
            # Check if state exists
            query = db.query(WorkflowState).filter(
                WorkflowState.workflow_id == workflow_id,
                WorkflowState.state_key == state_key
            )
            
            if namespace:
                query = query.filter(WorkflowState.state_namespace == namespace)
            else:
                query = query.filter(WorkflowState.state_namespace.is_(None))
            
            state = query.first()
            
            # Calculate expiration
            expires_at = None
            if expires_in_seconds:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
            
            if state:
                # Update existing
                state.state_value = state_value
                state.state_version += 1
                state.last_updated_by_execution = execution_id
                state.last_updated_at = datetime.now(timezone.utc)
                if expires_at:
                    state.expires_at = expires_at
                
                db.commit()
                return state.state_version
            else:
                # Create new
                new_state = WorkflowState(
                    id=str(uuid.uuid4()),
                    workflow_id=workflow_id,
                    state_key=state_key,
                    state_namespace=namespace,
                    state_value=state_value,
                    state_version=1,
                    last_updated_by_execution=execution_id,
                    last_updated_at=datetime.now(timezone.utc),
                    created_at=datetime.now(timezone.utc),
                    expires_at=expires_at,
                )
                
                db.add(new_state)
                db.commit()
                return 1
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to set state: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def update_state(
        workflow_id: str,
        state_key: str,
        updates: Any,
        namespace: Optional[str] = None,
        execution_id: Optional[str] = None,
        operation: str = "merge"
    ) -> tuple[Any, int]:
        """
        Update state (merge or increment).
        
        Args:
            workflow_id: Workflow ID
            state_key: State key
            updates: Updates to apply
            namespace: Optional namespace
            execution_id: Execution ID
            operation: Update operation (merge or increment)
        
        Returns:
            Tuple of (new_value, version)
        """
        db: Session = next(get_db())
        
        try:
            # Query existing state
            query = db.query(WorkflowState).filter(
                WorkflowState.workflow_id == workflow_id,
                WorkflowState.state_key == state_key
            )
            
            if namespace:
                query = query.filter(WorkflowState.state_namespace == namespace)
            else:
                query = query.filter(WorkflowState.state_namespace.is_(None))
            
            state = query.first()
            
            if not state:
                raise ValueError(f"State not found: {state_key}")
            
            # Apply update
            if operation == "merge":
                if not isinstance(state.state_value, dict):
                    raise ValueError("State value must be an object for merge")
                if not isinstance(updates, dict):
                    raise ValueError("Updates must be an object for merge")
                
                new_value = {**state.state_value, **updates}
            
            elif operation == "increment":
                if not isinstance(state.state_value, (int, float)):
                    raise ValueError("State value must be a number for increment")
                if not isinstance(updates, (int, float)):
                    raise ValueError("Updates must be a number for increment")
                
                new_value = state.state_value + updates
            
            else:
                raise ValueError(f"Unknown operation: {operation}")
            
            # Update state
            state.state_value = new_value
            state.state_version += 1
            state.last_updated_by_execution = execution_id
            state.last_updated_at = datetime.now(timezone.utc)
            
            db.commit()
            return new_value, state.state_version
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update state: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def delete_state(
        workflow_id: str,
        state_key: str,
        namespace: Optional[str] = None
    ) -> bool:
        """
        Delete state.
        
        Args:
            workflow_id: Workflow ID
            state_key: State key
            namespace: Optional namespace
        
        Returns:
            True if deleted, False if not found
        """
        db: Session = next(get_db())
        
        try:
            query = db.query(WorkflowState).filter(
                WorkflowState.workflow_id == workflow_id,
                WorkflowState.state_key == state_key
            )
            
            if namespace:
                query = query.filter(WorkflowState.state_namespace == namespace)
            else:
                query = query.filter(WorkflowState.state_namespace.is_(None))
            
            state = query.first()
            
            if state:
                db.delete(state)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete state: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def list_states(
        workflow_id: str,
        namespace: Optional[str] = None,
        key_pattern: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all states for a workflow.
        
        Args:
            workflow_id: Workflow ID
            namespace: Optional namespace filter
            key_pattern: Optional key pattern filter (SQL LIKE)
        
        Returns:
            List of state dictionaries
        """
        db: Session = next(get_db())
        
        try:
            query = db.query(WorkflowState).filter(
                WorkflowState.workflow_id == workflow_id
            )
            
            if namespace:
                query = query.filter(WorkflowState.state_namespace == namespace)
            
            if key_pattern:
                query = query.filter(WorkflowState.state_key.like(key_pattern))
            
            states = query.all()
            
            return [
                {
                    "state_key": s.state_key,
                    "state_namespace": s.state_namespace,
                    "state_value": s.state_value,
                    "state_version": s.state_version,
                    "last_updated_at": s.last_updated_at.isoformat() if s.last_updated_at else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in states
            ]
        finally:
            db.close()
    
    @staticmethod
    def cleanup_expired_states() -> int:
        """
        Clean up expired states.
        
        Returns:
            Number of states deleted
        """
        db: Session = next(get_db())
        
        try:
            now = datetime.now(timezone.utc)
            
            deleted_count = db.query(WorkflowState).filter(
                WorkflowState.expires_at.isnot(None),
                WorkflowState.expires_at <= now
            ).delete()
            
            db.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired states")
            
            return deleted_count
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to cleanup expired states: {e}")
            raise
        finally:
            db.close()

