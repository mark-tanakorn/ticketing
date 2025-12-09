"""
Workflow CRUD and Execution API Endpoints

Workflow Management:
POST /workflows - Create/save new workflow
GET /workflows - List all workflows
GET /workflows/{id} - Load single workflow
PUT /workflows/{id} - Update existing workflow
DELETE /workflows/{id} - Delete workflow
PATCH /workflows/{id}/name - Quick rename
POST /workflows/{id}/duplicate - Clone workflow

Workflow Execution:
POST /workflows/{id}/execute - Smart "Run" button (auto-detects oneshot vs trigger)
POST /workflows/{id}/stop - Universal stop (oneshot or persistent)
GET /workflows/{id}/status - Get workflow status
GET /executions/{id} - Get execution details
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Body, Header
from app.utils.timezone import get_local_now
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user_smart, get_user_identifier, get_current_user, get_trigger_manager, get_current_active_user
from app.database.models.user import User
from app.core.execution.orchestrator import WorkflowOrchestrator
from app.core.execution.context import ExecutionMode
from app.security.encryption import encrypt_dict, decrypt_dict
# NOTE: TriggerManager will be initialized at app startup, passed via dependency
# For now, we'll mock it or use direct instantiation

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Test Endpoints ---

@router.get(
    "/test",
    summary="Test endpoint (no auth)",
    description="Test endpoint to verify API connectivity without authentication"
)
async def test_workflows():
    """
    Test endpoint without authentication for debugging API connectivity.
    
    Returns sample workflow data to verify the API is working.
    """
    return {
        "message": "API is working!",
        "timestamp": "2025-01-01T00:00:00Z",
        "sample_workflows": [
            {
                "id": "test-1",
                "name": "Test Workflow 1",
                "description": "Sample workflow for testing",
                "status": "Completed",
                "author_id": 1,
                "created_at": "2025-01-01T00:00:00Z",
                "last_run_at": "2025-01-01T00:05:00Z"
            },
            {
                "id": "test-2",
                "name": "Test Workflow 2", 
                "description": "Another sample workflow",
                "status": "Running",
                "author_id": 1,
                "created_at": "2025-01-01T00:01:00Z",
                "last_run_at": "2025-01-01T00:06:00Z"
            }
        ]
    }


# --- Request/Response Models ---

class WorkflowCreate(BaseModel):
    """Request to create a new workflow."""
    name: str = Field(..., min_length=1, max_length=255, description="Workflow name")
    description: Optional[str] = Field(default="", description="Workflow description")
    version: str = Field(default="1.0", description="Workflow version")
    nodes: list = Field(..., description="List of node configurations")
    connections: list = Field(..., description="List of connections between nodes")
    canvas_objects: Optional[list] = Field(default=None, description="Canvas objects (groups and text annotations)")
    tags: Optional[list[str]] = Field(default=None, description="Tags for categorization")
    execution_config: Optional[Dict[str, Any]] = Field(default=None, description="Execution configuration overrides")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    recommended_await_completion: Optional[str] = Field(
        default="false", 
        description="Recommended X-Await-Completion header value for this workflow (e.g., 'true', 'false', 'timeout=30'). Hint for API consumers, not enforced."
    )


class WorkflowUpdate(BaseModel):
    """Request to update an existing workflow."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    version: Optional[str] = Field(default=None)
    nodes: Optional[list] = Field(default=None)
    connections: Optional[list] = Field(default=None)
    canvas_objects: Optional[list] = Field(default=None)
    tags: Optional[list[str]] = Field(default=None)
    execution_config: Optional[Dict[str, Any]] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    recommended_await_completion: Optional[str] = Field(
        default="false",
        description="Recommended X-Await-Completion header value for this workflow (e.g., 'true', 'false', 'timeout=30')"
    )


class WorkflowNameUpdate(BaseModel):
    """Request to update workflow name only."""
    name: str = Field(..., min_length=1, max_length=255)


class WorkflowResponse(BaseModel):
    """Complete workflow data response."""
    id: str
    name: str
    description: Optional[str]
    version: str
    nodes: list
    connections: list
    canvas_objects: Optional[list] = []
    tags: Optional[list[str]]
    execution_config: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    status: str
    is_active: bool
    is_template: bool
    author_id: Optional[int]
    created_at: str
    updated_at: str
    last_run_at: Optional[str]
    recommended_await_completion: str = Field(
        default="false",
        description="Recommended X-Await-Completion header value (e.g., 'true', 'false', 'timeout=30'). Hint for API consumers."
    )


class WorkflowSummary(BaseModel):
    """Summary of a workflow for list view."""
    id: str
    name: str
    description: Optional[str]
    version: str
    status: str
    is_active: bool
    is_template: bool
    author_id: Optional[int]
    created_at: str
    updated_at: str
    last_run_at: Optional[str]
    monitoring_started_at: Optional[str]
    monitoring_stopped_at: Optional[str]
    tags: Optional[list[str]]
    recommended_await_completion: str = Field(
        default="false",
        description="Recommended X-Await-Completion header value. Hint for API consumers."
    )


class ExecuteWorkflowRequest(BaseModel):
    """Request to execute a workflow."""
    trigger_data: Optional[Dict[str, Any]] = Field(default=None, description="Optional trigger data")
    initial_data: Optional[Dict[str, Any]] = Field(default=None, description="Initial data (conversation context from TKV chat)")
    execution_mode: ExecutionMode = Field(default=ExecutionMode.PARALLEL, description="Execution mode")


class ExecuteWorkflowResponse(BaseModel):
    """Response after workflow execution/activation."""
    workflow_id: str = Field(..., description="Workflow UUID")
    mode: str = Field(..., description="oneshot or persistent")
    status: str = Field(..., description="Current workflow status")
    execution_id: Optional[str] = Field(default=None, description="Execution UUID (for oneshot)")
    trigger_count: Optional[int] = Field(default=None, description="Number of triggers (for persistent)")
    trigger_nodes: Optional[list[str]] = Field(default=None, description="Trigger node IDs (for persistent)")
    message: str = Field(..., description="Human-readable message")
    
    # Sync mode fields (when X-Await-Completion header is used)
    duration_seconds: Optional[float] = Field(default=None, description="Execution duration in seconds (sync mode)")
    final_outputs: Optional[Dict[str, Any]] = Field(default=None, description="Final node outputs (sync mode)")
    error_message: Optional[str] = Field(default=None, description="Error message if failed (sync mode)")
    execution_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Execution metadata (sync mode)")
    timeout_exceeded: Optional[bool] = Field(default=None, description="True if timeout was exceeded (sync mode)")


class StopWorkflowResponse(BaseModel):
    """Response after workflow stop."""
    workflow_id: str
    mode: str  # oneshot or persistent
    status: str
    message: str


class ExecutionStatusResponse(BaseModel):
    """Execution status and results."""
    execution_id: str
    workflow_id: str
    status: str
    execution_source: str
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: Optional[float]
    final_outputs: Optional[Dict[str, Any]]
    error_message: Optional[str]
    execution_metadata: Optional[Dict[str, Any]]
    node_results: Optional[Dict[str, Any]] = Field(default=None, description="Individual node execution results")


# --- Helper Functions ---

def _encrypt_workflow_secrets(workflow_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Encrypt sensitive fields in workflow node configurations.
    
    Scans through all nodes and encrypts fields that contain sensitive data
    (passwords, API keys, tokens, etc.)
    """
    from app.security.encryption import encrypt_value, is_encrypted
    
    # Fields that should be encrypted
    sensitive_fields = [
        'password', 'api_key', 'apikey', 'api_token', 'token',
        'secret', 'secret_key', 'access_token', 'private_key',
        'auth_token', 'bearer_token', 'credentials'
    ]
    
    result = workflow_data.copy()
    nodes = result.get('nodes', [])
    
    for node in nodes:
        config = node.get('config', {})
        for key, value in config.items():
            # Check if field name suggests it's sensitive
            key_lower = key.lower()
            if any(sensitive_field in key_lower for sensitive_field in sensitive_fields):
                if value and isinstance(value, str) and not is_encrypted(value):
                    config[key] = encrypt_value(value)
                    logger.debug(f"Encrypted field '{key}' in node {node.get('id')}")
    
    return result


def _decrypt_workflow_secrets(workflow_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decrypt sensitive fields in workflow node configurations.
    
    Scans through all nodes and decrypts encrypted fields.
    """
    from app.security.encryption import decrypt_value, is_encrypted
    
    result = workflow_data.copy()
    nodes = result.get('nodes', [])
    
    for node in nodes:
        config = node.get('config', {})
        for key, value in config.items():
            if value and isinstance(value, str) and is_encrypted(value):
                try:
                    config[key] = decrypt_value(value)
                    logger.debug(f"Decrypted field '{key}' in node {node.get('id')}")
                except Exception as e:
                    logger.warning(f"Failed to decrypt field '{key}': {e}")
                    # Keep encrypted value if decryption fails
    
    return result


def _validate_workflow_structure(nodes: list, connections: list) -> None:
    """
    Validate workflow structure.
    
    Raises:
        ValueError: If validation fails
    """
    if not nodes:
        raise ValueError("Workflow must have at least one node")
    
    # Check node IDs are unique
    # Handle both 'id' and 'node_id' formats
    node_ids = [node.get('id') or node.get('node_id') for node in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise ValueError("Duplicate node IDs found")
    
    # Validate connections reference valid nodes
    node_id_set = set(node_ids)
    for conn in connections:
        source = conn.get('sourceNodeId') or conn.get('source_node_id')
        target = conn.get('targetNodeId') or conn.get('target_node_id')
        
        if source and source not in node_id_set:
            raise ValueError(f"Connection references non-existent source node: {source}")
        if target and target not in node_id_set:
            raise ValueError(f"Connection references non-existent target node: {target}")


# --- CRUD Endpoints ---

@router.post(
    "",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new workflow",
    description="Create and save a new workflow definition"
)
async def create_workflow(
    workflow: WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Create a new workflow.
    
    - Validates workflow structure
    - Encrypts sensitive fields (passwords, API keys)
    - Stores in database
    - Returns complete workflow data with generated ID
    """
    from app.database.models.workflow import Workflow
    
    try:
        # Validate structure
        _validate_workflow_structure(workflow.nodes, workflow.connections)
        
        # Create workflow ID
        workflow_id = str(uuid.uuid4())
        
        # Build workflow data (include fields required by WorkflowDefinition)
        workflow_data = {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "description": workflow.description or "",
            "format_version": "2.0.0",  # Current format version
            "nodes": workflow.nodes,
            "connections": workflow.connections,
            "canvas_objects": workflow.canvas_objects or [],  # Include canvas objects
            "global_config": {},
            "variables": {},
            "metadata": workflow.metadata or {},
            "execution_constraints": workflow.execution_config or {}
        }
        
        # Encrypt sensitive fields
        workflow_data = _encrypt_workflow_secrets(workflow_data)
        
        # Create workflow model
        db_workflow = Workflow(
            id=workflow_id,
            name=workflow.name,
            description=workflow.description,
            version=workflow.version,
            workflow_data=workflow_data,
            tags=workflow.tags,
            execution_config=workflow.execution_config,
            author_id=current_user.id,
            status="na",  # No executions yet
            is_active=True,
            is_template=False,
            recommended_await_completion=workflow.recommended_await_completion or "false"
        )
        
        db.add(db_workflow)
        db.commit()
        db.refresh(db_workflow)
        
        logger.info(f"Created workflow {workflow_id}: '{workflow.name}' by user {get_user_identifier(current_user)}")
        
        # Return response (decrypt for display)
        decrypted_data = _decrypt_workflow_secrets(db_workflow.workflow_data)
        
        return WorkflowResponse(
            id=db_workflow.id,
            name=db_workflow.name,
            description=db_workflow.description,
            version=db_workflow.version,
            nodes=decrypted_data.get('nodes', []),
            connections=decrypted_data.get('connections', []),
            canvas_objects=decrypted_data.get('canvas_objects', []),
            tags=db_workflow.tags,
            execution_config=db_workflow.execution_config,
            metadata=decrypted_data.get('metadata', {}),
            status=db_workflow.status,
            is_active=db_workflow.is_active,
            is_template=db_workflow.is_template,
            author_id=db_workflow.author_id,
            created_at=db_workflow.created_at.isoformat(),
            updated_at=db_workflow.updated_at.isoformat(),
            last_run_at=db_workflow.last_run_at.isoformat() if db_workflow.last_run_at else None,
            recommended_await_completion=db_workflow.recommended_await_completion or "false"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {str(e)}"
        )


# --- Endpoints ---

@router.get(
    "",
    response_model=list[WorkflowSummary],
    summary="List all workflows",
    description="Get all workflows with summary information"
)
async def list_workflows(
    skip: int = 0,
    limit: int = 100,
    include_templates: bool = False,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    List all workflows.
    
    Query Parameters:
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    - include_templates: Include template workflows
    - include_inactive: Include inactive workflows
    
    Returns:
    - List of workflow summaries
    
    Note: Authentication temporarily disabled for testing.
    """
    from app.database.models.workflow import Workflow
    
    # Build query
    query = db.query(Workflow)
    
    # Apply filters
    if not include_inactive:
        query = query.filter(Workflow.is_active == True)
    
    if not include_templates:
        query = query.filter(Workflow.is_template == False)
    
    # Order by most recently updated
    query = query.order_by(Workflow.updated_at.desc())
    
    # Pagination
    workflows = query.offset(skip).limit(limit).all()
    
    # Convert to response model
    result = []
    for wf in workflows:
        result.append(WorkflowSummary(
            id=wf.id,
            name=wf.name,
            description=wf.description,
            version=wf.version,
            status=wf.status,
            is_active=wf.is_active,
            is_template=wf.is_template,
            author_id=wf.author_id,
            created_at=wf.created_at.isoformat() if wf.created_at else None,
            updated_at=wf.updated_at.isoformat() if wf.updated_at else None,
            last_run_at=wf.last_run_at.isoformat() if wf.last_run_at else None,
            monitoring_started_at=wf.monitoring_started_at.isoformat() if wf.monitoring_started_at else None,
            monitoring_stopped_at=wf.monitoring_stopped_at.isoformat() if wf.monitoring_stopped_at else None,
            tags=wf.tags if wf.tags else [],
            recommended_await_completion=wf.recommended_await_completion or "false"
        ))
    
    return result


@router.get(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    summary="Load single workflow",
    description="Get complete workflow data by ID"
)
async def get_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Load a single workflow by ID.
    
    Returns:
    - Complete workflow data including nodes, connections, configuration
    - Decrypted sensitive fields
    """
    from app.database.models.workflow import Workflow
    
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # Decrypt sensitive fields for display
    decrypted_data = _decrypt_workflow_secrets(workflow.workflow_data)
    
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        version=workflow.version,
        nodes=decrypted_data.get('nodes', []),
        connections=decrypted_data.get('connections', []),
        canvas_objects=decrypted_data.get('canvas_objects', []),
        tags=workflow.tags,
        execution_config=workflow.execution_config,
        metadata=decrypted_data.get('metadata', {}),
        status=workflow.status,
        is_active=workflow.is_active,
        is_template=workflow.is_template,
        author_id=workflow.author_id,
        created_at=workflow.created_at.isoformat(),
        updated_at=workflow.updated_at.isoformat(),
        last_run_at=workflow.last_run_at.isoformat() if workflow.last_run_at else None,
        recommended_await_completion=workflow.recommended_await_completion or "false"
    )


@router.put(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    summary="Update workflow",
    description="Update existing workflow definition"
)
async def update_workflow(
    workflow_id: str,
    workflow_update: WorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Update an existing workflow.
    
    - Allows partial updates (only specified fields are updated)
    - Validates structure if nodes/connections are updated
    - Re-encrypts sensitive fields
    - Increments version (optional)
    """
    from app.database.models.workflow import Workflow
    
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    try:
        # Update basic fields
        if workflow_update.name is not None:
            workflow.name = workflow_update.name
        if workflow_update.description is not None:
            workflow.description = workflow_update.description
        if workflow_update.version is not None:
            workflow.version = workflow_update.version
        if workflow_update.tags is not None:
            workflow.tags = workflow_update.tags
        if workflow_update.execution_config is not None:
            workflow.execution_config = workflow_update.execution_config
        if workflow_update.recommended_await_completion is not None:
            workflow.recommended_await_completion = workflow_update.recommended_await_completion
        
        # Update workflow data if nodes/connections are provided
        if workflow_update.nodes is not None or workflow_update.connections is not None or workflow_update.canvas_objects is not None:
            # Get existing data
            current_data = workflow.workflow_data.copy()
            
            # Update nodes and connections
            nodes = workflow_update.nodes if workflow_update.nodes is not None else current_data.get('nodes', [])
            connections = workflow_update.connections if workflow_update.connections is not None else current_data.get('connections', [])
            canvas_objects = workflow_update.canvas_objects if workflow_update.canvas_objects is not None else current_data.get('canvas_objects', [])
            
            # Validate
            _validate_workflow_structure(nodes, connections)
            
            # Build new workflow data (include fields required by WorkflowDefinition)
            new_data = {
                "workflow_id": workflow.id,
                "name": workflow.name,
                "description": workflow.description or "",
                "format_version": "2.0.0",
                "nodes": nodes,
                "connections": connections,
                "canvas_objects": canvas_objects,  # Include canvas objects
                "global_config": current_data.get('global_config', {}),
                "variables": current_data.get('variables', {}),
                "metadata": workflow_update.metadata if workflow_update.metadata is not None else current_data.get('metadata', {}),
                "execution_constraints": workflow.execution_config or current_data.get('execution_constraints', {})
            }
            
            # Encrypt sensitive fields
            workflow.workflow_data = _encrypt_workflow_secrets(new_data)
        elif workflow_update.metadata is not None:
            # Only metadata updated
            current_data = workflow.workflow_data.copy()
            current_data['metadata'] = workflow_update.metadata
            workflow.workflow_data = current_data
        
        workflow.updated_at = get_local_now()
        
        db.commit()
        db.refresh(workflow)
        
        logger.info(f"Updated workflow {workflow_id}: '{workflow.name}' by user {get_user_identifier(current_user)}")
        
        # Return decrypted data
        decrypted_data = _decrypt_workflow_secrets(workflow.workflow_data)
        
        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            version=workflow.version,
            nodes=decrypted_data.get('nodes', []),
            connections=decrypted_data.get('connections', []),
            canvas_objects=decrypted_data.get('canvas_objects', []),
            tags=workflow.tags,
            execution_config=workflow.execution_config,
            metadata=decrypted_data.get('metadata', {}),
            status=workflow.status,
            is_active=workflow.is_active,
            is_template=workflow.is_template,
            author_id=workflow.author_id,
            created_at=workflow.created_at.isoformat(),
            updated_at=workflow.updated_at.isoformat(),
            last_run_at=workflow.last_run_at.isoformat() if workflow.last_run_at else None,
            recommended_await_completion=workflow.recommended_await_completion or "false"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update workflow {workflow_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workflow: {str(e)}"
        )


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workflow",
    description="Permanently delete a workflow"
)
async def delete_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Delete a workflow permanently.
    
    - Removes from database
    - Cannot be undone
    - Associated executions are preserved (orphaned)
    """
    from app.database.models.workflow import Workflow
    
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    try:
        workflow_name = workflow.name
        db.delete(workflow)
        db.commit()
        
        logger.info(f"Deleted workflow {workflow_id}: '{workflow_name}' by user {get_user_identifier(current_user)}")
        
        return None  # 204 No Content
        
    except Exception as e:
        logger.error(f"Failed to delete workflow {workflow_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workflow: {str(e)}"
        )


@router.patch(
    "/{workflow_id}/name",
    response_model=WorkflowResponse,
    summary="Quick rename workflow",
    description="Update workflow name only (quick edit)"
)
async def rename_workflow(
    workflow_id: str,
    name_update: WorkflowNameUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Quick rename workflow.
    
    Convenience endpoint for updating just the name without sending
    the entire workflow structure.
    """
    from app.database.models.workflow import Workflow
    
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    try:
        old_name = workflow.name
        workflow.name = name_update.name
        workflow.updated_at = get_local_now()
        
        db.commit()
        db.refresh(workflow)
        
        logger.info(f"Renamed workflow {workflow_id}: '{old_name}' → '{name_update.name}' by user {get_user_identifier(current_user)}")
        
        # Return complete workflow data
        decrypted_data = _decrypt_workflow_secrets(workflow.workflow_data)
        
        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            version=workflow.version,
            nodes=decrypted_data.get('nodes', []),
            connections=decrypted_data.get('connections', []),
            canvas_objects=decrypted_data.get('canvas_objects', []),
            tags=workflow.tags,
            execution_config=workflow.execution_config,
            metadata=decrypted_data.get('metadata', {}),
            status=workflow.status,
            is_active=workflow.is_active,
            is_template=workflow.is_template,
            author_id=workflow.author_id,
            created_at=workflow.created_at.isoformat(),
            updated_at=workflow.updated_at.isoformat(),
            last_run_at=workflow.last_run_at.isoformat() if workflow.last_run_at else None,
            recommended_await_completion=workflow.recommended_await_completion or "false"
        )
        
    except Exception as e:
        logger.error(f"Failed to rename workflow {workflow_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rename workflow: {str(e)}"
        )


@router.post(
    "/{workflow_id}/duplicate",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate workflow",
    description="Create a copy of an existing workflow"
)
async def duplicate_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Clone an existing workflow.
    
    - Creates a complete copy with new ID
    - Appends " (Copy)" to name
    - Resets status to "na"
    - Resets execution history
    """
    from app.database.models.workflow import Workflow
    
    original = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    try:
        # Create duplicate
        new_id = str(uuid.uuid4())
        duplicate = Workflow(
            id=new_id,
            name=f"{original.name} (Copy)",
            description=original.description,
            version=original.version,
            workflow_data=original.workflow_data.copy(),  # Deep copy
            tags=original.tags.copy() if original.tags else None,
            execution_config=original.execution_config.copy() if original.execution_config else None,
            author_id=current_user.id,
            status="na",  # Reset status
            is_active=True,
            is_template=False
        )
        
        db.add(duplicate)
        db.commit()
        db.refresh(duplicate)
        
        logger.info(f"Duplicated workflow {workflow_id} → {new_id}: '{duplicate.name}' by user {get_user_identifier(current_user)}")
        
        # Return decrypted data
        decrypted_data = _decrypt_workflow_secrets(duplicate.workflow_data)
        
        return WorkflowResponse(
            id=duplicate.id,
            name=duplicate.name,
            description=duplicate.description,
            version=duplicate.version,
            nodes=decrypted_data.get('nodes', []),
            connections=decrypted_data.get('connections', []),
            canvas_objects=decrypted_data.get('canvas_objects', []),
            tags=duplicate.tags,
            execution_config=duplicate.execution_config,
            metadata=decrypted_data.get('metadata', {}),
            status=duplicate.status,
            is_active=duplicate.is_active,
            is_template=duplicate.is_template,
            author_id=duplicate.author_id,
            created_at=duplicate.created_at.isoformat(),
            updated_at=duplicate.updated_at.isoformat(),
            last_run_at=duplicate.last_run_at.isoformat() if duplicate.last_run_at else None,
            recommended_await_completion=duplicate.recommended_await_completion or "false"
        )
        
    except Exception as e:
        logger.error(f"Failed to duplicate workflow {workflow_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to duplicate workflow: {str(e)}"
        )


@router.post(
    "/{workflow_id}/execute",
    response_model=ExecuteWorkflowResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute workflow (smart run button)",
    description="Auto-detects oneshot vs persistent workflow and executes accordingly. Supports sync/async modes via X-Await-Completion header."
)
async def execute_workflow(
    workflow_id: str,
    request: ExecuteWorkflowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
    trigger_manager=Depends(get_trigger_manager),
    x_await_completion: Optional[str] = Header(None, alias="X-Await-Completion"),
    origin: Optional[str] = Header(None, alias="Origin"),
    referer: Optional[str] = Header(None, alias="Referer")
):
    """
    Smart "Run" button - auto-detects workflow type.
    
    Behavior:
    - **Has trigger nodes** → Activate monitoring (persistent)
    - **No trigger nodes** → Execute once (oneshot)
    
    This matches the V1 system's intelligent "Run" button behavior.
    
    Headers:
    - **X-Await-Completion**: Control sync/async execution
      - Not set or "false": Return immediately (async, default)
      - "true": Wait for completion (sync, uses workflow_timeout from settings)
      - "timeout=30": Wait up to 30 seconds (sync with custom timeout, capped at workflow_timeout)
    
    Args:
        workflow_id: Workflow UUID
        request: Execution request with optional trigger data
        db: Database session
        current_user: Authenticated user
        x_await_completion: Optional header to control sync/async mode
    
    Returns:
        Execution/activation info (immediate or after completion)
    
    Raises:
        404: Workflow not found
        500: Execution/activation failed
    """
    logger.info(
        f"User {get_user_identifier(current_user)} pressed 'Run' on workflow {workflow_id}"
    )
    
    # Parse X-Await-Completion header
    await_completion = False
    timeout_seconds = None
    
    # Load execution settings from database to get default timeout
    from app.core.config.manager import SettingsManager
    settings_manager = SettingsManager(db)
    execution_settings = settings_manager.get_execution_settings()
    
    if x_await_completion:
        x_await_lower = x_await_completion.lower().strip()
        if x_await_lower == "true":
            await_completion = True
            timeout_seconds = execution_settings.workflow_timeout  # Use workflow_timeout from DB settings
            logger.info(f"Sync execution requested (default timeout: {timeout_seconds}s from settings)")
        elif x_await_lower.startswith("timeout="):
            await_completion = True
            try:
                timeout_seconds = int(x_await_lower.split("=")[1])
                # Cap timeout at workflow_timeout from settings
                max_timeout = execution_settings.workflow_timeout
                if timeout_seconds > max_timeout:
                    logger.warning(f"Requested timeout {timeout_seconds}s exceeds max {max_timeout}s, capping")
                    timeout_seconds = max_timeout
                logger.info(f"Sync execution requested with timeout: {timeout_seconds}s")
            except (ValueError, IndexError):
                timeout_seconds = execution_settings.http_timeout  # Fallback to http_timeout from DB
                logger.warning(f"Invalid timeout format, using http_timeout from settings: {timeout_seconds}s")
    
    # Determine frontend origin for auto-detection (used by Email Approval node)
    # Priority: Origin header > Referer header (extract origin) > None
    frontend_origin = None
    if origin:
        frontend_origin = origin
        logger.debug(f"Using Origin header for frontend_origin: {frontend_origin}")
    elif referer:
        # Extract origin from Referer (e.g., "http://192.168.1.100:3000/workflows/123" -> "http://192.168.1.100:3000")
        try:
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            frontend_origin = f"{parsed.scheme}://{parsed.netloc}"
            logger.debug(f"Extracted frontend_origin from Referer: {frontend_origin}")
        except Exception as e:
            logger.warning(f"Failed to parse Referer header: {e}")
    
    try:
        # Load workflow to detect mode
        from app.database.models.workflow import Workflow
        from app.schemas.workflow import WorkflowDefinition, NodeCategory
        
        workflow_db = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow_db:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        workflow_def = WorkflowDefinition(**workflow_db.workflow_data)
        
        # Detect if workflow has trigger nodes
        has_triggers = any(
            node.category == NodeCategory.TRIGGERS
            for node in workflow_def.nodes
        )
        
        if has_triggers:
            # --- PERSISTENT MODE: Activate trigger monitoring ---
            logger.info(f"Workflow {workflow_id} has triggers, activating monitoring...")
            
            try:
                activation_info = await trigger_manager.activate_workflow(workflow_id)
                
                logger.info(
                    f"✅ Workflow {workflow_id} activated with "
                    f"{activation_info['trigger_count']} triggers"
                )
                
                return ExecuteWorkflowResponse(
                    workflow_id=workflow_id,
                    mode="persistent",
                    status="monitoring",
                    monitoring_state="active",
                    trigger_count=activation_info["trigger_count"],
                    trigger_nodes=activation_info["trigger_nodes"],
                    message=f"Workflow activated with {activation_info['trigger_count']} trigger(s)"
                )
            
            except ValueError as e:
                # Workflow already active or no triggers found
                logger.warning(f"⚠️  Failed to activate workflow {workflow_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except RuntimeError as e:
                # Activation failed
                logger.error(f"❌ Failed to activate workflow {workflow_id}: {e}", exc_info=True)
                
                # Provide helpful error message
                error_msg = str(e)
                if "mount" in error_msg.lower() or "network" in error_msg.lower():
                    detail = (
                        f"Failed to activate workflow - Network share connection error. "
                        f"Check logs at backend/logs/tav_engine.log for details. "
                        f"Common issues: invalid credentials, network unreachable, or incorrect path."
                    )
                else:
                    detail = f"Failed to activate workflow: {error_msg}. Check backend/logs/tav_engine.log for details."
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=detail
                )
        
        else:
            # --- ONESHOT MODE: Execute once ---
            logger.info(f"Workflow {workflow_id} has no triggers, executing once...")
            
            # Persistent workflows don't support sync mode (they run indefinitely)
            if await_completion:
                logger.info("Sync mode enabled for oneshot execution")
            
            # Extract user ID now (before background task, while DB session is active)
            user_id = str(current_user.id)
            
            # Merge initial_data into trigger_data
            # This allows TKV chat to pass conversation context that will be
            # injected into execution variables for all nodes to access
            merged_trigger_data = request.trigger_data or {}
            if request.initial_data:
                logger.info(f"Merging initial_data into trigger_data: {list(request.initial_data.keys())}")
                merged_trigger_data.update(request.initial_data)
            
            # Create execution record FIRST so SSE endpoint can find it
            from app.database.models.execution import Execution
            from app.schemas.workflow import ExecutionStatus
            from app.utils.timezone import get_local_now
            
            execution_id = str(uuid.uuid4())
            
            # Create execution record with PENDING status initially
            execution_db = Execution(
                id=execution_id,
                workflow_id=workflow_id,
                status=ExecutionStatus.PENDING,  # Will be updated to RUNNING when execution starts
                execution_source="manual",
                trigger_data=merged_trigger_data,  # Store merged trigger + initial data
                started_by=user_id,
                started_at=get_local_now(),
                execution_mode=request.execution_mode,
                workflow_snapshot=workflow_db.workflow_data,
                metadata={}
            )
            db.add(execution_db)
            db.commit()
            db.refresh(execution_db)
            
            logger.info(f"Created execution record: {execution_id}")
            
            if not await_completion:
                # --- ASYNC MODE (Current behavior): Return immediately ---
                
                # Run execution in background task (don't await!)
                async def run_execution_background():
                    """Background task to execute workflow"""
                    try:
                        # Small delay to allow SSE connection to establish first
                        # This ensures the frontend receives real-time node_start events
                        await asyncio.sleep(0.3)  # 300ms delay
                        
                        # Create new DB session for background task
                        from app.database.session import SessionLocal
                        bg_db = SessionLocal()
                        try:
                            orchestrator = WorkflowOrchestrator(bg_db)
                            # Pass execution_id - orchestrator will update the existing record
                            await orchestrator.execute_workflow(
                                workflow_id=workflow_id,
                                trigger_data=merged_trigger_data,  # Pass merged data to orchestrator
                                execution_source="manual",
                                started_by=user_id,  # Use extracted user_id, not current_user.id
                                execution_mode=request.execution_mode,
                                execution_id=execution_id,  # Use existing execution record
                                frontend_origin=frontend_origin  # Auto-detected from request headers
                            )
                        finally:
                            bg_db.close()
                    except Exception as e:
                        logger.error(f"Background execution {execution_id} failed: {e}", exc_info=True)
                        # Update execution record to failed status
                        try:
                            from app.database.session import SessionLocal
                            error_db = SessionLocal()
                            try:
                                error_execution = error_db.query(Execution).filter(Execution.id == execution_id).first()
                                if error_execution:
                                    error_execution.status = ExecutionStatus.FAILED
                                    error_execution.error_message = str(e)
                                    error_execution.completed_at = get_local_now()
                                    error_db.commit()
                            finally:
                                error_db.close()
                        except Exception as update_error:
                            logger.error(f"Failed to update execution status: {update_error}")
                
                # Start background task
                asyncio.create_task(run_execution_background())
                
                logger.info(f"Oneshot execution started in background: {execution_id}")
                
                return ExecuteWorkflowResponse(
                    workflow_id=workflow_id,
                    mode="oneshot",
                    status="running",
                    execution_id=execution_id,
                    message="Workflow execution started"
                )
            
            else:
                # --- SYNC MODE (NEW): Wait for completion ---
                logger.info(f"Sync execution: waiting for completion (timeout={timeout_seconds}s)")
                
                try:
                    # Small delay to allow SSE connection to establish if client connects
                    await asyncio.sleep(0.1)
                    
                    # Execute workflow and wait (with timeout)
                    orchestrator = WorkflowOrchestrator(db)
                    
                    await asyncio.wait_for(
                        orchestrator.execute_workflow(
                            workflow_id=workflow_id,
                            trigger_data=merged_trigger_data,
                            execution_source="manual",
                            started_by=user_id,
                            execution_mode=request.execution_mode,
                            execution_id=execution_id,
                            frontend_origin=frontend_origin  # Auto-detected from request headers
                        ),
                        timeout=timeout_seconds
                    )
                    
                    # Execution completed! Refresh to get latest data
                    db.refresh(execution_db)
                    
                    logger.info(f"✅ Sync execution completed: {execution_id}, status={execution_db.status}")
                    
                    # Calculate duration
                    duration = None
                    if execution_db.started_at and execution_db.completed_at:
                        duration = (execution_db.completed_at - execution_db.started_at).total_seconds()
                    
                    return ExecuteWorkflowResponse(
                        workflow_id=workflow_id,
                        mode="oneshot",
                        status=execution_db.status,
                        execution_id=execution_id,
                        message=f"Workflow execution {execution_db.status}",
                        duration_seconds=duration,
                        final_outputs=execution_db.final_outputs,
                        error_message=execution_db.error_message,
                        execution_metadata=execution_db.metadata,
                        timeout_exceeded=False
                    )
                
                except asyncio.TimeoutError:
                    # Timeout exceeded - execution still running
                    logger.warning(f"⏱️ Sync execution timeout after {timeout_seconds}s: {execution_id}")
                    
                    # Refresh to get current status
                    db.refresh(execution_db)
                    
                    return ExecuteWorkflowResponse(
                        workflow_id=workflow_id,
                        mode="oneshot",
                        status=execution_db.status or "running",
                        execution_id=execution_id,
                        message=f"Execution still running after {timeout_seconds}s timeout. Poll /executions/{execution_id} for results.",
                        timeout_exceeded=True
                    )
                
                except Exception as e:
                    # Execution failed
                    logger.error(f"❌ Sync execution failed: {execution_id}, error={e}", exc_info=True)
                    
                    # Try to refresh execution record to get error details
                    try:
                        db.refresh(execution_db)
                    except:
                        pass
                    
                    return ExecuteWorkflowResponse(
                        workflow_id=workflow_id,
                        mode="oneshot",
                        status=execution_db.status or "failed",
                        execution_id=execution_id,
                        message="Workflow execution failed",
                        error_message=execution_db.error_message or str(e),
                        execution_metadata=execution_db.metadata
                    )
    
    except ValueError as e:
        logger.error(f"Workflow execution failed (ValueError): {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {str(e)}"
        )


@router.post(
    "/{workflow_id}/stop",
    response_model=StopWorkflowResponse,
    summary="Stop workflow (universal hard stop)",
    description="Stop workflow - works for both oneshot executions and persistent monitoring"
)
async def stop_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
    trigger_manager=Depends(get_trigger_manager)
):
    """
    Universal "Stop" button - works for any workflow mode.
    
    Behavior:
    - **Persistent (monitoring)** → Deactivate triggers, cancel in-flight executions
    - **Oneshot (running)** → Cancel current execution
    - **Idle** → No-op (returns success)
    
    This is a hard stop that immediately terminates all activity.
    
    Args:
        workflow_id: Workflow UUID
        db: Database session
        current_user: Authenticated user
    
    Returns:
        Stop status
    
    Raises:
        404: Workflow not found
        500: Stop failed
    """
    logger.info(
        f"User {get_user_identifier(current_user)} pressed 'Stop' on workflow {workflow_id}"
    )
    
    try:
        from app.database.models.workflow import Workflow
        from app.database.models.execution import Execution
        
        # Load workflow
        workflow_db = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow_db:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        stopped_mode = None
        stopped_count = 0
        
        # 1. Check if workflow is actively monitoring in TriggerManager
        if trigger_manager.is_workflow_active(workflow_id):
            logger.info(f"Workflow {workflow_id} is monitoring, deactivating...")
            
            # Deactivate via TriggerManager
            deactivated = await trigger_manager.deactivate_workflow(workflow_id)
            
            if deactivated:
                stopped_mode = "persistent"
                logger.info(f"✅ Deactivated monitoring for workflow {workflow_id}")
            else:
                logger.warning(f"Failed to deactivate workflow {workflow_id}")
                stopped_mode = "persistent"
        
        # Also update DB status if it's in pending/running state
        elif workflow_db.status in ["pending", "running"]:
            logger.info(f"Workflow {workflow_id} status is {workflow_db.status}, updating to stopped...")
            workflow_db.status = "stopped"
            workflow_db.monitoring_stopped_at = get_local_now()
            db.commit()
            stopped_mode = "persistent"
        
        # 2. Cancel any running executions (for both oneshot and persistent)
        running_executions = db.query(Execution).filter(
            Execution.workflow_id == workflow_id,
            Execution.status == "running"
        ).all()
        
        if running_executions:
            logger.info(
                f"Found {len(running_executions)} running executions, cancelling..."
            )
            
            orchestrator = WorkflowOrchestrator(db)
            for execution in running_executions:
                try:
                    await orchestrator.cancel_execution(execution.id)
                    stopped_count += 1
                except Exception as e:
                    logger.error(f"Failed to cancel execution {execution.id}: {e}")
            
            if not stopped_mode:
                stopped_mode = "oneshot"
        
        # 3. No activity detected
        if not stopped_mode:
            logger.info(f"Workflow {workflow_id} is idle, nothing to stop")
            return StopWorkflowResponse(
                workflow_id=workflow_id,
                mode="idle",
                status="stopped",
                message="Workflow is already stopped"
            )
        
        # Success
        message = f"Stopped {stopped_mode} workflow"
        if stopped_count > 0:
            message += f" (cancelled {stopped_count} executions)"
        
        return StopWorkflowResponse(
            workflow_id=workflow_id,
            mode=stopped_mode,
            status="stopped",
            message=message
        )
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
    except Exception as e:
        logger.error(f"Workflow stop failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop workflow: {str(e)}"
        )


@router.get(
    "/{workflow_id}/status",
    summary="Get workflow status",
    description="Get current workflow state (monitoring, running, idle)"
)
async def get_workflow_status(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
    trigger_manager = Depends(get_trigger_manager)
):
    """
    Get workflow status.
    
    Returns:
    - mode: persistent, oneshot, or idle
    - monitoring_state: active, inactive (for persistent)
    - running_executions: count of active executions
    - last_execution: most recent execution info
    """
    from app.database.models.workflow import Workflow
    from app.database.models.execution import Execution
    from sqlalchemy import desc
    
    workflow_db = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    
    # Check if workflow is actively monitoring (THIS IS THE SOURCE OF TRUTH)
    is_monitoring_active = trigger_manager.is_workflow_active(workflow_id)
    
    # Count running executions
    running_count = db.query(Execution).filter(
        Execution.workflow_id == workflow_id,
        Execution.status == "running"
    ).count()
    
    # Get last execution
    last_execution = db.query(Execution).filter(
        Execution.workflow_id == workflow_id
    ).order_by(desc(Execution.started_at)).first()
    
    # Get trigger info if monitoring
    trigger_info = None
    if is_monitoring_active and workflow_id in trigger_manager.active_workflows:
        trigger_info = trigger_manager.active_workflows[workflow_id]
    
    # Check if execution is paused (from in-memory executor registry)
    is_paused = False
    from app.core.execution.orchestrator import get_active_executor
    active_executor = get_active_executor(workflow_id)
    if active_executor:
        is_paused = active_executor.paused
    
    return {
        "workflow_id": workflow_id,
        "status": workflow_db.status,  # na/pending/running/completed/failed/stopped
        "is_monitoring": is_monitoring_active,  # TRUE SOURCE OF TRUTH
        "is_paused": is_paused,  # From in-memory executor
        "running_executions": running_count,
        "monitoring_started_at": trigger_info["started_at"].isoformat() if trigger_info else (workflow_db.monitoring_started_at.isoformat() if workflow_db.monitoring_started_at else None),
        "monitoring_stopped_at": workflow_db.monitoring_stopped_at.isoformat() if workflow_db.monitoring_stopped_at else None,
        "trigger_count": len(trigger_info["trigger_nodes"]) if trigger_info else 0,
        "last_execution": {
            "execution_id": last_execution.id,
            "status": last_execution.status,
            "started_at": last_execution.started_at.isoformat() if last_execution.started_at else None,
            "completed_at": last_execution.completed_at.isoformat() if last_execution.completed_at else None,
        } if last_execution else None
    }


@router.get(
    "/executions/{execution_id}",
    response_model=ExecutionStatusResponse,
    summary="Get execution status",
    description="Get detailed execution status and results"
)
async def get_execution_status(
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Get execution status and results.
    
    Args:
        execution_id: Execution UUID
        db: Database session
        current_user: Authenticated user
    
    Returns:
        Execution details
    
    Raises:
        404: Execution not found
    """
    orchestrator = WorkflowOrchestrator(db)
    execution_data = orchestrator.get_execution_status(execution_id)
    
    if not execution_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution not found: {execution_id}"
        )
    
    # Calculate duration
    duration_seconds = None
    if execution_data.get("completed_at") and execution_data.get("started_at"):
        duration = execution_data["completed_at"] - execution_data["started_at"]
        duration_seconds = duration.total_seconds()
    
    return ExecutionStatusResponse(
        execution_id=execution_data["execution_id"],
        workflow_id=execution_data["workflow_id"],
        status=execution_data["status"],
        execution_source=execution_data.get("execution_source", "unknown"),
        started_at=execution_data["started_at"].isoformat() if execution_data.get("started_at") else None,
        completed_at=execution_data["completed_at"].isoformat() if execution_data.get("completed_at") else None,
        duration_seconds=duration_seconds,
        final_outputs=execution_data.get("final_outputs"),
        error_message=execution_data.get("error_message"),
        execution_metadata=execution_data.get("execution_metadata"),
        node_results=execution_data.get("node_results")
    )


@router.post(
    "/{workflow_id}/pause",
    summary="Pause workflow execution",
    description="Pause a currently running workflow"
)
async def pause_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Pause a running workflow execution.
    
    Current running nodes will finish, but no new nodes will start
    until resume is called.
    """
    logger.info(f"User {get_user_identifier(current_user)} requested pause for workflow {workflow_id}")
    
    # Import here to avoid circular dependency
    from app.core.execution.orchestrator import get_active_executor
    
    # Get the active executor for this workflow
    executor = get_active_executor(workflow_id)
    
    if not executor:
        raise HTTPException(
            status_code=404,
            detail="No active execution found for this workflow"
        )
    
    # Pause the executor
    executor.pause()
    
    # Broadcast pause event via SSE
    try:
        await publish_workflow_event(workflow_id, {
            "type": "execution_paused",
            "workflow_id": workflow_id,
            "message": "Execution paused - current nodes will finish"
        })
    except Exception as e:
        logger.warning(f"Failed to broadcast execution_paused event: {e}")
    
    return {
        "status": "paused",
        "message": "Execution paused successfully",
        "workflow_id": workflow_id
    }


@router.post(
    "/{workflow_id}/resume",
    summary="Resume workflow execution",
    description="Resume a paused workflow"
)
async def resume_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Resume a paused workflow execution.
    
    Allows new nodes to start executing again.
    """
    logger.info(f"User {get_user_identifier(current_user)} requested resume for workflow {workflow_id}")
    
    # Import here to avoid circular dependency
    from app.core.execution.orchestrator import get_active_executor
    
    # Get the active executor for this workflow
    executor = get_active_executor(workflow_id)
    
    if not executor:
        raise HTTPException(
            status_code=404,
            detail="No active execution found for this workflow"
        )
    
    # Resume the executor
    executor.resume()
    
    # Broadcast resume event via SSE
    try:
        await publish_workflow_event(workflow_id, {
            "type": "execution_resumed",
            "workflow_id": workflow_id,
            "message": "Execution resumed"
        })
    except Exception as e:
        logger.warning(f"Failed to broadcast execution_resumed event: {e}")
    
    return {
        "status": "resumed",
        "message": "Execution resumed successfully",
        "workflow_id": workflow_id
    }