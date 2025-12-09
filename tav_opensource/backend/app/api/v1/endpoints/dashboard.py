"""
Dashboard API - Real-time execution overview

Provides aggregated views of active executions and monitoring status
for dashboard display without storing progress in DB.
"""

import logging
from datetime import timedelta
from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_trigger_manager, get_current_user_smart
from app.database.models.execution import Execution
from app.database.models.workflow import Workflow as WorkflowModel
from app.database.models.user import User
from app.schemas.workflow import WorkflowDefinition, ExecutionStatus, NodeCategory
from app.utils.timezone import get_local_now, to_local
from app.core.execution.orchestrator import get_active_executor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/active-executions")
async def get_active_executions(
    db: Session = Depends(get_db),
    trigger_manager = Depends(get_trigger_manager),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Get all currently running executions across all workflows.
    
    Returns real-time progress for dashboard display.
    Calculates progress from node_results (no need to store in DB).
    
    Response:
    ```json
    {
        "active_executions": [
            {
                "execution_id": "...",
                "workflow_id": "...",
                "workflow_name": "...",
                "started_at": "...",
                "duration_seconds": 10.5,
                "progress": {
                    "progress_percentage": 45.0,
                    "completed": 3,
                    "running": 1,
                    "pending": 2,
                    "failed": 0,
                    "skipped": 0,
                    "in_scope": 6
                },
                "execution_source": "schedule",
                "is_trigger_workflow": true
            }
        ],
        "monitoring_workflows": [
            {
                "workflow_id": "...",
                "workflow_name": "...",
                "trigger_count": 1,
                "monitoring_started_at": "...",
                "recent_execution_count": 5,
                "last_execution_at": "..."
            }
        ]
    }
    ```
    """
    try:
        # Get all running executions
        running_executions = db.query(Execution)\
            .filter(Execution.status == ExecutionStatus.RUNNING)\
            .order_by(Execution.started_at.desc())\
            .all()
        
        active_list = []
        for exec in running_executions:
            # Get workflow info
            workflow_db = db.query(WorkflowModel)\
                .filter(WorkflowModel.id == exec.workflow_id)\
                .first()
            
            if not workflow_db:
                logger.warning(f"Workflow {exec.workflow_id} not found for execution {exec.id}")
                continue
            
            workflow_def = None
            has_triggers = False
            total_nodes = 0
            
            try:
                workflow_def = WorkflowDefinition(**workflow_db.workflow_data)
                has_triggers = any(n.category == NodeCategory.TRIGGERS for n in workflow_def.nodes)
                total_nodes = len(workflow_def.nodes)
            except Exception as e:
                logger.warning(f"Failed to parse workflow {workflow_db.id}: {e}")
            
            # Calculate duration
            duration = 0
            if exec.started_at:
                # Ensure started_at is timezone-aware before subtracting
                started_at_aware = to_local(exec.started_at) if exec.started_at.tzinfo is None else exec.started_at
                duration = (get_local_now() - started_at_aware).total_seconds()
            
            # Calculate progress from node_results
            # First try to get progress from active executor (real-time, phase-based)
            executor = get_active_executor(exec.workflow_id)
            if executor and executor.graph:
                # Use real-time progress from execution graph (phase-based counting)
                graph_progress = executor.get_progress()
                progress_info = {
                    "progress_percentage": graph_progress.get("progress_percent", 0),
                    "completed": graph_progress.get("completed", 0),
                    "running": graph_progress.get("executing", 0),
                    "pending": graph_progress.get("pending", 0),
                    "failed": graph_progress.get("failed", 0),
                    "skipped": graph_progress.get("skipped", 0),
                    "in_scope": graph_progress.get("effective_total", 0),
                }
                logger.info(f"📊 Real-time progress for {exec.workflow_id}: {progress_info['progress_percentage']}%")
            else:
                # Fall back to database node_results (for completed/failed executions)
                progress_info = _calculate_progress_from_results(
                    exec.node_results or {},
                    total_nodes
                )
                logger.debug(f"📊 Database progress for {exec.workflow_id}: {progress_info['progress_percentage']}%")
            
            active_list.append({
                "execution_id": exec.id,
                "workflow_id": exec.workflow_id,
                "workflow_name": workflow_db.name,
                "started_at": exec.started_at.isoformat() if exec.started_at else None,
                "duration_seconds": round(duration, 1),
                "progress": progress_info,
                "execution_source": exec.execution_source,
                "is_trigger_workflow": has_triggers
            })
        
        # Get actively monitoring workflows
        monitoring_list = []
        active_workflow_ids = list(trigger_manager.active_workflows.keys())
        
        for workflow_id in active_workflow_ids:
            workflow_db = db.query(WorkflowModel)\
                .filter(WorkflowModel.id == workflow_id)\
                .first()
            
            if not workflow_db:
                continue
            
            trigger_info = trigger_manager.active_workflows[workflow_id]
            
            # Count recent executions (last hour)
            one_hour_ago = get_local_now() - timedelta(hours=1)
            recent_count = db.query(Execution)\
                .filter(
                    Execution.workflow_id == workflow_id,
                    Execution.started_at >= one_hour_ago.replace(tzinfo=None)  # Compare with naive datetime
                )\
                .count()
            
            # Get last execution time
            last_execution = db.query(Execution)\
                .filter(Execution.workflow_id == workflow_id)\
                .order_by(Execution.started_at.desc())\
                .first()
            
            monitoring_list.append({
                "workflow_id": workflow_id,
                "workflow_name": workflow_db.name,
                "trigger_count": len(trigger_info["trigger_nodes"]),
                "monitoring_started_at": trigger_info["started_at"].isoformat(),
                "recent_execution_count": recent_count,
                "last_execution_at": last_execution.started_at.isoformat() if last_execution and last_execution.started_at else None
            })
        
        return {
            "active_executions": active_list,
            "monitoring_workflows": monitoring_list,
            "timestamp": get_local_now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Failed to get active executions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve active executions: {str(e)}"
        )


@router.get("/workflow/{workflow_id}/monitoring-status")
async def get_workflow_monitoring_status(
    workflow_id: str,
    db: Session = Depends(get_db),
    trigger_manager = Depends(get_trigger_manager),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Get monitoring status for a specific workflow.
    
    Used for:
    - Page reload recovery (detect if workflow is actively monitoring)
    - Monitoring indicator UI
    - Recent execution dropdown
    
    Response:
    ```json
    {
        "workflow_id": "...",
        "workflow_name": "...",
        "has_triggers": true,
        "monitoring_active": true,
        "running_executions": [...],
        "recent_executions": [...]
    }
    ```
    """
    try:
        # Check if actively monitoring
        is_monitoring = trigger_manager.is_workflow_active(workflow_id)
        
        # Get workflow
        workflow_db = db.query(WorkflowModel)\
            .filter(WorkflowModel.id == workflow_id)\
            .first()
        
        if not workflow_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        workflow_def = WorkflowDefinition(**workflow_db.workflow_data)
        has_triggers = any(node.category == NodeCategory.TRIGGERS for node in workflow_def.nodes)
        
        # Get recent executions (last 3 hours)
        three_hours_ago = get_local_now() - timedelta(hours=3)
        recent_executions = db.query(Execution)\
            .filter(
                Execution.workflow_id == workflow_id,
                Execution.started_at >= three_hours_ago.replace(tzinfo=None)  # Compare with naive datetime
            )\
            .order_by(Execution.started_at.desc())\
            .limit(50)\
            .all()
        
        # Get currently running
        running = [e for e in recent_executions if e.status == ExecutionStatus.RUNNING]
        
        return {
            "workflow_id": workflow_id,
            "workflow_name": workflow_db.name,
            "has_triggers": has_triggers,
            "monitoring_active": is_monitoring,
            "running_executions": [
                {
                    "execution_id": e.id,
                    "started_at": e.started_at.isoformat() if e.started_at else None,
                    "duration_seconds": (get_local_now() - to_local(e.started_at)).total_seconds() if e.started_at else 0
                }
                for e in running
            ],
            "recent_executions": [
                {
                    "execution_id": e.id,
                    "started_at": e.started_at.isoformat() if e.started_at else None,
                    "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                    "status": e.status,
                    "duration_seconds": (to_local(e.completed_at) - to_local(e.started_at)).total_seconds() if e.completed_at and e.started_at else None
                }
                for e in recent_executions[:10]  # Last 10 for dropdown
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow monitoring status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve monitoring status: {str(e)}"
        )


def _calculate_progress_from_results(
    node_results: Dict[str, Any],
    total_nodes: int
) -> Dict[str, Any]:
    """
    Calculate execution progress from node_results stored in DB.
    
    This allows us to show progress without storing it separately.
    
    Args:
        node_results: Dict of node_id -> result from execution record
        total_nodes: Total nodes in workflow definition
    
    Returns:
        Progress dict with percentages and counts
    """
    if not node_results or not total_nodes:
        return {
            "progress_percentage": 0.0,
            "completed": 0,
            "running": 0,
            "pending": total_nodes,
            "failed": 0,
            "skipped": 0,
            "in_scope": total_nodes
        }
    
    # Count nodes by status
    completed = 0
    failed = 0
    
    for result in node_results.values():
        if isinstance(result, dict):
            if result.get("success"):
                completed += 1
            elif result.get("success") is False:
                failed += 1
    
    # Calculate in-scope (nodes that have been touched)
    in_scope = len(node_results)
    
    # Assume remaining nodes are pending
    pending = max(0, total_nodes - in_scope)
    
    # At least 1 node is likely running if execution is active
    running = 1 if in_scope < total_nodes else 0
    
    # Progress percentage based on finished nodes out of in-scope
    finished = completed + failed
    progress_pct = round((finished / in_scope) * 100, 1) if in_scope > 0 else 0.0
    
    return {
        "progress_percentage": progress_pct,
        "completed": completed,
        "running": running,
        "pending": pending,
        "failed": failed,
        "skipped": 0,  # Can't determine from DB results
        "in_scope": in_scope
    }

