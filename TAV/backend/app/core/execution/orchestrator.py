"""
Workflow Orchestrator

High-level coordinator for workflow execution. Responsibilities:
- Load workflow from database
- Build execution graph
- Merge execution config (workflow + global)
- Instantiate ParallelExecutor
- Persist execution records
- Handle execution lifecycle
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import timedelta

from app.utils.timezone import get_local_now

from sqlalchemy.orm import Session

from app.database.models.workflow import Workflow
from app.database.models.execution import Execution
from app.schemas.workflow import WorkflowDefinition, ExecutionStatus, NodeCategory
from app.core.execution.graph.builder import GraphBuilder
from app.core.execution.context import ExecutionContext, ExecutionMode
from app.core.execution.executor.parallel import ParallelExecutor
from app.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# ACTIVE EXECUTIONS REGISTRY
# ============================================================================
# Track all currently running executions for pause/resume/stop control
_active_executions: Dict[str, ParallelExecutor] = {}  # execution_id -> executor
_active_executions_by_workflow: Dict[str, str] = {}  # workflow_id -> execution_id
_pause_timeout_task: Optional[asyncio.Task] = None  # Background monitoring task


def register_execution(execution_id: str, workflow_id: str, executor: ParallelExecutor):
    """Register an active execution."""
    _active_executions[execution_id] = executor
    _active_executions_by_workflow[workflow_id] = execution_id
    logger.debug(f"Registered execution {execution_id} for workflow {workflow_id}")
    
    # Start pause timeout monitor if not already running
    global _pause_timeout_task
    if _pause_timeout_task is None or _pause_timeout_task.done():
        _pause_timeout_task = asyncio.create_task(_monitor_paused_executions())


def unregister_execution(execution_id: str, workflow_id: str):
    """Unregister a completed execution."""
    if execution_id in _active_executions:
        del _active_executions[execution_id]
    if workflow_id in _active_executions_by_workflow:
        del _active_executions_by_workflow[workflow_id]
    logger.debug(f"Unregistered execution {execution_id}")


def get_active_executor(workflow_id: str) -> Optional[ParallelExecutor]:
    """Get the active executor for a workflow."""
    execution_id = _active_executions_by_workflow.get(workflow_id)
    if execution_id:
        return _active_executions.get(execution_id)
    return None


async def _monitor_paused_executions():
    """
    Background task to monitor paused executions and auto-cancel after 30 minutes.
    
    Runs indefinitely, checking every 60 seconds.
    """
    logger.info("Started pause timeout monitor")
    
    try:
        while True:
            await asyncio.sleep(60)  # Check every minute
            
            if not _active_executions:
                # No active executions, can exit
                logger.debug("No active executions, pause monitor exiting")
                break
            
            # Check each active execution for pause timeout
            now = get_local_now()
            timeout_limit = timedelta(minutes=30)
            
            for execution_id, executor in list(_active_executions.items()):
                if executor.paused and executor.paused_at:
                    paused_duration = now - executor.paused_at
                    
                    if paused_duration > timeout_limit:
                        logger.warning(
                            f"Execution {execution_id} has been paused for "
                            f"{paused_duration.total_seconds():.0f}s (>30min), "
                            f"auto-cancelling..."
                        )
                        
                        # Auto-cancel the execution
                        await executor.cancel_execution()
                        
                        # Broadcast timeout event
                        try:
                            from app.api.v1.endpoints.executions import publish_execution_event
                            await publish_execution_event(execution_id, {
                                "type": "execution_stopped",
                                "execution_id": execution_id,
                                "reason": "pause_timeout",
                                "message": "Execution cancelled due to 30-minute pause timeout"
                            })
                        except Exception as e:
                            logger.warning(f"Failed to broadcast timeout event: {e}")
    
    except Exception as e:
        logger.error(f"Error in pause timeout monitor: {e}", exc_info=True)
    finally:
        logger.info("Pause timeout monitor stopped")


class WorkflowOrchestrator:
    """
    High-level workflow execution coordinator.
    
    Responsibilities:
    1. Load workflow definition from DB
    2. Build execution graph
    3. Merge execution config (workflow-specific + global settings)
    4. Create execution record in DB
    5. Instantiate and run ParallelExecutor
    6. Update execution record with results
    7. Handle errors and cleanup
    
    Design: Single Responsibility Principle
    - Orchestrator = coordination/persistence
    - Executor = actual execution logic
    - Graph Builder = dependency resolution
    - Context = state tracking
    """
    
    def __init__(self, db: Session):
        """
        Initialize orchestrator.
        
        Args:
            db: Database session for persistence
        """
        self.db = db
        logger.debug("WorkflowOrchestrator initialized")
    
    async def execute_workflow(
        self,
        workflow_id: str,
        trigger_data: Optional[Dict[str, Any]] = None,
        execution_source: str = "manual",
        started_by: Optional[str] = None,
        execution_mode: ExecutionMode = ExecutionMode.PARALLEL,
        execution_id: Optional[str] = None,
        frontend_origin: Optional[str] = None
    ) -> str:
        """
        Execute workflow end-to-end.
        
        Steps:
        1. Load workflow from DB
        2. Validate workflow state
        3. Build execution graph
        4. Merge execution config
        5. Create execution record
        6. Execute via ParallelExecutor
        7. Update execution record
        
        Args:
            workflow_id: Workflow UUID
            trigger_data: Optional trigger data (for trigger-initiated executions)
            execution_source: How execution was initiated (manual, webhook, schedule, etc.)
            started_by: User ID who initiated execution
            execution_mode: Parallel or sequential (default: parallel)
            execution_id: Optional execution ID (if None, will be auto-generated)
        
        Returns:
            Execution ID (UUID)
        
        Raises:
            ValueError: If workflow not found or invalid
            Exception: If execution fails
        """
        logger.info(
            f"Starting workflow execution: workflow_id={workflow_id}, "
            f"source={execution_source}, mode={execution_mode}"
        )
        
        # 1. Load workflow from DB
        workflow_db = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow_db:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        # Use workflow author as fallback if no started_by user
        # This allows schedule triggers to work with credentials
        if not started_by and workflow_db.author_id:
            started_by = str(workflow_db.author_id)
            logger.info(f"Using workflow author {started_by} as started_by (no user for schedule trigger)")
        
        # Convert to WorkflowDefinition (Pydantic)
        workflow_def = WorkflowDefinition(**workflow_db.workflow_data)
        
        logger.debug(
            f"Loaded workflow: {workflow_def.name}, nodes={len(workflow_def.nodes)}, "
            f"connections={len(workflow_def.connections)}"
        )
        
        # 2. Build execution graph
        graph_builder = GraphBuilder(workflow_def)
        graph = graph_builder.build()
        
        logger.debug(
            f"Built execution graph: source_nodes={len(graph.source_nodes)}, "
            f"sink_nodes={len(graph.sink_nodes)}"
        )
        
        # 3. Merge execution config
        execution_config = self._merge_execution_config(workflow_db)
        
        logger.debug(f"Merged execution config: {list(execution_config.keys())}")
        
        # 4. Create or update execution record
        if execution_id is None:
            execution_id = str(uuid4())
        
        # Check if execution record already exists (created by endpoint)
        execution_db = self.db.query(Execution).filter(Execution.id == execution_id).first()
        
        if execution_db:
            # Update existing record to RUNNING status
            execution_db.status = ExecutionStatus.RUNNING
            execution_db.started_at = get_local_now()
            # Also update workflow status to RUNNING so DB accurately reflects active executions
            workflow_db.status = ExecutionStatus.RUNNING
            workflow_db.last_execution_id = execution_id
            workflow_db.last_run_at = execution_db.started_at
            self.db.commit()
            logger.info(f"Updated existing execution record to RUNNING: {execution_id}")
        else:
            # Create new execution record
            execution_db = Execution(
                id=execution_id,
                workflow_id=workflow_id,
                status=ExecutionStatus.RUNNING,
                execution_source=execution_source,
                trigger_data=trigger_data or {},
                started_by=started_by,
                started_at=get_local_now(),
                execution_mode=execution_mode,
                workflow_snapshot=workflow_db.workflow_data,  # Snapshot for audit
                metadata={}
            )
            self.db.add(execution_db)
            # Also set workflow DB status to RUNNING and update last_run info
            workflow_db.status = ExecutionStatus.RUNNING
            workflow_db.last_execution_id = execution_id
            workflow_db.last_run_at = execution_db.started_at
            self.db.commit()
            self.db.refresh(execution_db)
            
            logger.info(f"Created execution record: {execution_id}")
        
        # 5. Create execution context
        context = ExecutionContext(
            workflow_id=workflow_id,
            execution_id=execution_id,
            execution_source=execution_source,
            trigger_data=trigger_data or {},
            started_by=started_by,
            execution_mode=execution_mode,
            frontend_origin=frontend_origin
        )
        
        # Inject trigger data into execution-scoped variables
        # This makes the trigger data (e.g., conversation context from TKV chat)
        # available to ALL nodes during this execution
        if trigger_data:
            logger.debug(f"Injecting trigger data into execution context variables: {list(trigger_data.keys())}")
            
            # Store the full trigger_data object
            context.variables["trigger_data"] = trigger_data
            
            # Also inject ALL keys from trigger_data directly into variables
            # This makes them accessible via variable references like {{trigger_data.conversation_history}}
            for key, value in trigger_data.items():
                variable_key = f"trigger_{key}"
                context.variables[variable_key] = value
                logger.debug(f"Injected trigger data field: {variable_key}")
            
            # Legacy field names for backward compatibility (TKV chat integration)
            if "conversation" in trigger_data:
                context.variables["trigger_conversation"] = trigger_data["conversation"]
            if "latest_reply" in trigger_data:
                context.variables["trigger_latest_reply"] = trigger_data["latest_reply"]
            if "topic" in trigger_data:
                context.variables["trigger_topic"] = trigger_data["topic"]
            if "priority" in trigger_data:
                context.variables["trigger_priority"] = trigger_data["priority"]
            if "timestamp" in trigger_data:
                context.variables["trigger_timestamp"] = trigger_data["timestamp"]
            
            logger.info(f"Injected {len(trigger_data)} trigger data fields into execution context")
        
        # Broadcast execution start event via SSE
        try:
            from app.api.v1.endpoints.executions import publish_execution_event
            await publish_execution_event(execution_id, {
                "type": "execution_start",
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "status": "running",
                "message": "Workflow execution started"
            })
        except Exception as e:
            logger.warning(f"Failed to broadcast execution_start event: {e}")
        
        # 6. Execute workflow
        try:
            # Instantiate executor
            executor = ParallelExecutor(execution_config)
            
            # Register executor for pause/resume control
            register_execution(execution_id, workflow_id, executor)
            
            # Execute
            context = await executor.execute_workflow(workflow_def, graph, context)
            
            # Unregister executor after completion
            unregister_execution(execution_id, workflow_id)
            
            # 7. Update execution record - SUCCESS
            execution_db.status = ExecutionStatus.COMPLETED
            execution_db.completed_at = context.completed_at
            execution_db.final_outputs = context.final_outputs
            execution_db.node_results = {
                node_id: result.to_dict() for node_id, result in context.node_results.items()
            }
            execution_db.execution_log = context.execution_log
            execution_db.execution_metadata = {
                "duration_seconds": (
                    (context.completed_at - context.started_at).total_seconds()
                    if context.completed_at and context.started_at else 0
                )
            }
            
            # Update workflow status
            workflow_db.status = ExecutionStatus.COMPLETED
            workflow_db.last_execution_id = execution_id
            workflow_db.last_run_at = execution_db.completed_at
            
            self.db.commit()
            
            logger.info(
                f"Workflow execution completed successfully: {execution_id}, "
                f"duration={execution_db.execution_metadata.get('duration_seconds')}s"
            )
            
            # Broadcast execution complete event via SSE
            try:
                from app.api.v1.endpoints.executions import publish_execution_event
                await publish_execution_event(execution_id, {
                    "type": "execution_complete",
                    "execution_id": execution_id,
                    "workflow_id": workflow_id,
                    "status": "completed",
                    "duration_seconds": execution_db.execution_metadata.get('duration_seconds'),
                    "message": "Workflow execution completed successfully"
                })
            except Exception as e:
                logger.warning(f"Failed to broadcast execution_complete event: {e}")
            
            # Auto-revert for persistent workflows (back to monitoring after 2 sec)
            # Detect if workflow has trigger nodes by checking the workflow definition
            has_triggers = any(
                node.category == NodeCategory.TRIGGERS
                for node in workflow_def.nodes
            )
            
            if has_triggers:
                import asyncio
                await asyncio.sleep(2)
                
                # Refresh workflow to check if status is still "completed"
                self.db.refresh(workflow_db)
                if workflow_db.status == ExecutionStatus.COMPLETED:
                    workflow_db.status = ExecutionStatus.PENDING
                    self.db.commit()
                    logger.info(f"Auto-reverted workflow {workflow_id} status to PENDING (monitoring)")
            
            return execution_id
        
        except Exception as e:
            # Unregister executor on failure
            unregister_execution(execution_id, workflow_id)
            
            # 7. Update execution record - FAILURE
            logger.error(f"Workflow execution failed: {execution_id}, error={e}", exc_info=True)
            
            execution_db.status = ExecutionStatus.FAILED
            execution_db.completed_at = get_local_now()
            execution_db.error_message = str(e)
            execution_db.execution_log = context.execution_log
            execution_db.node_results = {
                node_id: result.to_dict() for node_id, result in context.node_results.items()
            }
            
            # Update workflow status
            workflow_db.status = ExecutionStatus.FAILED
            workflow_db.last_execution_id = execution_id
            workflow_db.last_run_at = execution_db.completed_at
            
            self.db.commit()
            
            # Broadcast execution failed event via SSE
            try:
                from app.api.v1.endpoints.executions import publish_execution_event
                await publish_execution_event(execution_id, {
                    "type": "execution_failed",
                    "execution_id": execution_id,
                    "workflow_id": workflow_id,
                    "status": "failed",
                    "error": str(e),
                    "message": f"Workflow execution failed: {str(e)}"
                })
            except Exception as broadcast_error:
                logger.warning(f"Failed to broadcast execution_failed event: {broadcast_error}")
            
            # Auto-revert for persistent workflows (back to monitoring after 2 sec)
            # Detect if workflow has trigger nodes
            has_triggers = any(
                node.category == NodeCategory.TRIGGERS
                for node in workflow_def.nodes
            )
            
            if has_triggers:
                import asyncio
                await asyncio.sleep(2)
                
                # Refresh workflow to check if status is still "failed"
                self.db.refresh(workflow_db)
                if workflow_db.status == ExecutionStatus.FAILED:
                    workflow_db.status = ExecutionStatus.PENDING
                    self.db.commit()
                    logger.info(f"Auto-reverted workflow {workflow_id} status to PENDING (monitoring) after failure")
            
            raise
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel running execution.
        
        Hard stop: immediately cancels all running tasks.
        
        Args:
            execution_id: Execution UUID
        
        Returns:
            True if stopped, False if not running
        """
        # Load execution from DB
        execution_db = self.db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution_db:
            raise ValueError(f"Execution not found: {execution_id}")
        
        if execution_db.status != ExecutionStatus.RUNNING:
            logger.warning(f"Execution {execution_id} is not running, cannot stop")
            return False
        
        # Signal the executor to cancel all tasks (hard stop)
        if execution_id in _active_executions:
            executor = _active_executions[execution_id]
            logger.info(f"Sending cancel signal to executor for {execution_id}")
            await executor.cancel_execution()
        else:
            logger.warning(f"Executor not found in registry for {execution_id}, updating DB only")
        
        # Update DB status
        execution_db.status = ExecutionStatus.STOPPED
        execution_db.completed_at = get_local_now()
        execution_db.error_message = "Execution stopped by user"
        
        self.db.commit()
        
        # Broadcast stop event to SSE clients
        try:
            from app.api.v1.endpoints.executions import publish_execution_event
            await publish_execution_event(execution_id, {
                "type": "execution_stopped",
                "execution_id": execution_id,
                "status": "stopped",
                "message": "Execution stopped by user"
            })
        except Exception as e:
            logger.warning(f"Failed to broadcast execution_stopped event: {e}")
        
        logger.info(f"Execution stopped: {execution_id}")
        
        return True
    
    async def retry_from_checkpoint(
        self,
        original_execution_id: str,
        started_by: Optional[str] = None,
        frontend_origin: Optional[str] = None,
        force: bool = False,
        prepare_only: bool = False
    ) -> Dict[str, Any]:
        """
        Retry a failed execution from where it stopped.
        
        This creates a NEW execution that:
        1. Uses the CURRENT workflow definition (not snapshot) - allows user to fix issues
        2. Pre-marks nodes that completed successfully in the original execution
        3. Restores outputs from completed nodes
        4. Only executes pending/failed nodes
        
        Args:
            original_execution_id: The failed execution to retry from
            started_by: User ID who initiated the retry
            frontend_origin: Frontend origin URL for links
            force: If True, skip structure change warnings
            prepare_only: If True, only prepare execution and return (don't execute)
        
        Returns:
            Dict with:
                - execution_id: New execution ID
                - skipped_nodes: List of node IDs that were skipped (already completed)
                - warnings: List of structure change warnings (if any)
                - If prepare_only=True, also includes: workflow_def, graph, context, execution_config
        
        Raises:
            ValueError: If execution not found, not retryable, or structure changed (without force)
        """
        logger.info(f"🔄 Retry from checkpoint requested for execution {original_execution_id}")
        
        # 1. Load original execution
        original_execution = self.db.query(Execution).filter(
            Execution.id == original_execution_id
        ).first()
        
        if not original_execution:
            raise ValueError(f"Execution not found: {original_execution_id}")
        
        # 2. Validate execution is retryable
        retryable_statuses = [ExecutionStatus.FAILED, ExecutionStatus.STOPPED]
        if original_execution.status not in retryable_statuses:
            raise ValueError(
                f"Cannot retry execution with status '{original_execution.status}'. "
                f"Only failed or stopped executions can be retried."
            )
        
        # 3. Load current workflow (NOT the snapshot - allows user to fix issues)
        workflow_db = self.db.query(Workflow).filter(
            Workflow.id == original_execution.workflow_id
        ).first()
        
        if not workflow_db:
            raise ValueError(f"Workflow not found: {original_execution.workflow_id}")
        
        # Parse current workflow definition
        current_workflow_def = WorkflowDefinition(**workflow_db.workflow_data)
        
        # 4. Detect structure changes between snapshot and current workflow
        warnings = []
        if original_execution.workflow_snapshot:
            snapshot_def = WorkflowDefinition(**original_execution.workflow_snapshot)
            warnings = self._detect_structure_changes(snapshot_def, current_workflow_def)
            
            if warnings and not force:
                # Return warnings without executing - let frontend decide
                return {
                    "execution_id": None,
                    "skipped_nodes": [],
                    "warnings": warnings,
                    "requires_confirmation": True
                }
        
        # 5. Identify completed nodes from original execution
        completed_node_ids = set()
        completed_node_outputs = {}
        
        if original_execution.node_results:
            for node_id, result in original_execution.node_results.items():
                if result.get("success") is True:
                    # Check if this node still exists in current workflow
                    node_exists = any(
                        node.node_id == node_id 
                        for node in current_workflow_def.nodes
                    )
                    
                    if node_exists:
                        completed_node_ids.add(node_id)
                        completed_node_outputs[node_id] = result.get("outputs", {})
                        logger.debug(f"  ✅ Will skip completed node: {node_id}")
                    else:
                        logger.warning(f"  ⚠️ Completed node {node_id} no longer exists in workflow")
        
        logger.info(f"📊 Found {len(completed_node_ids)} completed nodes to skip")
        
        # 6. Build execution graph from CURRENT workflow
        graph_builder = GraphBuilder(current_workflow_def)
        graph = graph_builder.build()
        
        # 7. Pre-mark completed nodes in the graph
        from app.core.execution.graph.types import NodeExecutionPhase
        
        for node_id in completed_node_ids:
            if node_id in graph.nodes:
                # Mark node as completed
                graph.nodes[node_id].phase = NodeExecutionPhase.COMPLETED
                graph.completed_nodes.add(node_id)
                
                # Decrement dependency counters for all dependent nodes
                for dependent_id in graph.nodes[node_id].dependents:
                    if dependent_id in graph.nodes:
                        graph.nodes[dependent_id].remaining_deps -= 1
                        logger.debug(
                            f"  📉 Decremented deps for {dependent_id}: "
                            f"remaining={graph.nodes[dependent_id].remaining_deps}"
                        )
        
        # 8. Create new execution record
        new_execution_id = str(uuid4())
        
        # Determine retry count
        retry_count = 1
        original_metadata = original_execution.execution_metadata or {}
        if original_metadata.get("retry_count"):
            retry_count = original_metadata.get("retry_count") + 1
        
        new_execution_db = Execution(
            id=new_execution_id,
            workflow_id=original_execution.workflow_id,
            status=ExecutionStatus.RUNNING,
            execution_source="retry",
            trigger_data=original_execution.trigger_data or {},
            started_by=started_by or original_execution.started_by,
            started_at=get_local_now(),
            execution_mode=original_execution.execution_mode,
            workflow_snapshot=workflow_db.workflow_data,  # Snapshot CURRENT workflow
            execution_metadata={
                "retry_from": original_execution_id,
                "retry_count": retry_count,
                "skipped_nodes": list(completed_node_ids),
                "original_failed_at": original_execution.completed_at.isoformat() if original_execution.completed_at else None,
                "structure_warnings": warnings if warnings else None
            }
        )
        self.db.add(new_execution_db)
        
        # Update workflow status
        workflow_db.status = ExecutionStatus.RUNNING
        workflow_db.last_execution_id = new_execution_id
        workflow_db.last_run_at = new_execution_db.started_at
        
        self.db.commit()
        self.db.refresh(new_execution_db)
        
        logger.info(f"✅ Created retry execution: {new_execution_id} (retry #{retry_count})")
        
        # 9. Create execution context with restored outputs
        context = ExecutionContext(
            workflow_id=original_execution.workflow_id,
            execution_id=new_execution_id,
            execution_source="retry",
            trigger_data=original_execution.trigger_data or {},
            started_by=started_by or original_execution.started_by,
            execution_mode=ExecutionMode.PARALLEL,
            frontend_origin=frontend_origin
        )
        
        # Restore outputs from completed nodes
        for node_id, outputs in completed_node_outputs.items():
            context.node_outputs[node_id] = outputs
            logger.debug(f"  📦 Restored outputs for node {node_id}: {list(outputs.keys())}")
        
        # Inject trigger data (same as original execution)
        if original_execution.trigger_data:
            context.variables["trigger_data"] = original_execution.trigger_data
            for key, value in original_execution.trigger_data.items():
                context.variables[f"trigger_{key}"] = value
        
        # Get execution config
        execution_config = self._merge_execution_config(workflow_db)
        
        # If prepare_only, return all info needed for background execution
        if prepare_only:
            return {
                "execution_id": new_execution_id,
                "skipped_nodes": list(completed_node_ids),
                "warnings": warnings,
                "requires_confirmation": False,
                # Include execution context for background task
                "_workflow_def": current_workflow_def,
                "_graph": graph,
                "_context": context,
                "_execution_config": execution_config,
                "_workflow_db": workflow_db,
                "_original_execution": original_execution
            }
        
        # Broadcast retry start event
        try:
            from app.api.v1.endpoints.executions import publish_execution_event
            await publish_execution_event(new_execution_id, {
                "type": "execution_start",
                "execution_id": new_execution_id,
                "workflow_id": original_execution.workflow_id,
                "status": "running",
                "message": f"Retry from checkpoint (attempt #{retry_count})",
                "retry_from": original_execution_id,
                "skipped_nodes": list(completed_node_ids)
            })
        except Exception as e:
            logger.warning(f"Failed to broadcast retry start event: {e}")
        
        # 10. Execute workflow (with pre-marked completed nodes)
        
        try:
            executor = ParallelExecutor(execution_config)
            register_execution(new_execution_id, original_execution.workflow_id, executor)
            
            # Execute - completed nodes will be skipped automatically
            context = await executor.execute_workflow(current_workflow_def, graph, context)
            
            unregister_execution(new_execution_id, original_execution.workflow_id)
            
            # Update execution record - SUCCESS
            new_execution_db.status = ExecutionStatus.COMPLETED
            new_execution_db.completed_at = context.completed_at
            new_execution_db.final_outputs = context.final_outputs
            new_execution_db.node_results = {
                node_id: result.to_dict() for node_id, result in context.node_results.items()
            }
            new_execution_db.execution_log = context.execution_log
            
            workflow_db.status = ExecutionStatus.COMPLETED
            workflow_db.last_execution_id = new_execution_id
            workflow_db.last_run_at = new_execution_db.completed_at
            
            self.db.commit()
            
            logger.info(f"✅ Retry execution completed successfully: {new_execution_id}")
            
            # Broadcast completion
            try:
                from app.api.v1.endpoints.executions import publish_execution_event
                await publish_execution_event(new_execution_id, {
                    "type": "execution_complete",
                    "execution_id": new_execution_id,
                    "workflow_id": original_execution.workflow_id,
                    "status": "completed",
                    "message": "Retry completed successfully"
                })
            except Exception as e:
                logger.warning(f"Failed to broadcast retry complete event: {e}")
            
            return {
                "execution_id": new_execution_id,
                "skipped_nodes": list(completed_node_ids),
                "warnings": warnings,
                "requires_confirmation": False
            }
        
        except Exception as e:
            unregister_execution(new_execution_id, original_execution.workflow_id)
            
            logger.error(f"❌ Retry execution failed: {new_execution_id}, error={e}", exc_info=True)
            
            new_execution_db.status = ExecutionStatus.FAILED
            new_execution_db.completed_at = get_local_now()
            new_execution_db.error_message = str(e)
            new_execution_db.execution_log = context.execution_log
            new_execution_db.node_results = {
                node_id: result.to_dict() for node_id, result in context.node_results.items()
            }
            
            workflow_db.status = ExecutionStatus.FAILED
            workflow_db.last_execution_id = new_execution_id
            workflow_db.last_run_at = new_execution_db.completed_at
            
            self.db.commit()
            
            # Broadcast failure
            try:
                from app.api.v1.endpoints.executions import publish_execution_event
                await publish_execution_event(new_execution_id, {
                    "type": "execution_failed",
                    "execution_id": new_execution_id,
                    "workflow_id": original_execution.workflow_id,
                    "status": "failed",
                    "error": str(e),
                    "message": f"Retry failed: {str(e)}"
                })
            except Exception as broadcast_error:
                logger.warning(f"Failed to broadcast retry failed event: {broadcast_error}")
            
            raise
    
    async def run_prepared_retry(
        self,
        prepared_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run a prepared retry execution (from prepare_only=True call).
        
        This is called by background tasks to actually execute the retry.
        
        Args:
            prepared_info: Dict returned by retry_from_checkpoint(prepare_only=True)
        
        Returns:
            Dict with execution results
        """
        new_execution_id = prepared_info["execution_id"]
        completed_node_ids = set(prepared_info["skipped_nodes"])
        warnings = prepared_info.get("warnings", [])
        
        current_workflow_def = prepared_info["_workflow_def"]
        graph = prepared_info["_graph"]
        context = prepared_info["_context"]
        execution_config = prepared_info["_execution_config"]
        workflow_db = prepared_info["_workflow_db"]
        original_execution = prepared_info["_original_execution"]
        
        retry_count = (original_execution.execution_metadata or {}).get("retry_count", 0) + 1
        
        # Broadcast retry start event
        try:
            from app.api.v1.endpoints.executions import publish_execution_event
            await publish_execution_event(new_execution_id, {
                "type": "execution_start",
                "execution_id": new_execution_id,
                "workflow_id": original_execution.workflow_id,
                "status": "running",
                "message": f"Retry from checkpoint (attempt #{retry_count})",
                "retry_from": str(original_execution.id),
                "skipped_nodes": list(completed_node_ids)
            })
        except Exception as e:
            logger.warning(f"Failed to broadcast retry start event: {e}")
        
        # Get fresh db connection for background task
        from app.database.session import SessionLocal
        db = SessionLocal()
        
        try:
            # Re-fetch the execution and workflow records
            new_execution_db = db.query(Execution).filter(
                Execution.id == new_execution_id
            ).first()
            workflow_db = db.query(Workflow).filter(
                Workflow.id == original_execution.workflow_id
            ).first()
            
            if not new_execution_db or not workflow_db:
                raise ValueError("Execution or workflow not found")
            
            # Execute workflow
            executor = ParallelExecutor(execution_config)
            register_execution(new_execution_id, original_execution.workflow_id, executor)
            
            context = await executor.execute_workflow(current_workflow_def, graph, context)
            
            unregister_execution(new_execution_id, original_execution.workflow_id)
            
            # Update execution record - SUCCESS
            new_execution_db.status = ExecutionStatus.COMPLETED
            new_execution_db.completed_at = context.completed_at
            new_execution_db.final_outputs = context.final_outputs
            new_execution_db.node_results = {
                node_id: result.to_dict() for node_id, result in context.node_results.items()
            }
            new_execution_db.execution_log = context.execution_log
            
            workflow_db.status = ExecutionStatus.COMPLETED
            workflow_db.last_execution_id = new_execution_id
            workflow_db.last_run_at = new_execution_db.completed_at
            
            db.commit()
            
            logger.info(f"✅ Retry execution completed successfully: {new_execution_id}")
            
            # Broadcast completion
            try:
                from app.api.v1.endpoints.executions import publish_execution_event
                await publish_execution_event(new_execution_id, {
                    "type": "execution_complete",
                    "execution_id": new_execution_id,
                    "workflow_id": str(original_execution.workflow_id),
                    "status": "completed",
                    "message": "Retry completed successfully"
                })
            except Exception as e:
                logger.warning(f"Failed to broadcast retry complete event: {e}")
            
            return {
                "execution_id": new_execution_id,
                "skipped_nodes": list(completed_node_ids),
                "warnings": warnings,
                "success": True
            }
        
        except Exception as e:
            unregister_execution(new_execution_id, original_execution.workflow_id)
            
            logger.error(f"❌ Retry execution failed: {new_execution_id}, error={e}", exc_info=True)
            
            # Re-fetch records for update
            new_execution_db = db.query(Execution).filter(
                Execution.id == new_execution_id
            ).first()
            workflow_db = db.query(Workflow).filter(
                Workflow.id == original_execution.workflow_id
            ).first()
            
            if new_execution_db:
                new_execution_db.status = ExecutionStatus.FAILED
                new_execution_db.completed_at = get_local_now()
                new_execution_db.error_message = str(e)
                new_execution_db.execution_log = context.execution_log
                new_execution_db.node_results = {
                    node_id: result.to_dict() for node_id, result in context.node_results.items()
                }
            
            if workflow_db:
                workflow_db.status = ExecutionStatus.FAILED
                workflow_db.last_execution_id = new_execution_id
                workflow_db.last_run_at = new_execution_db.completed_at if new_execution_db else get_local_now()
            
            db.commit()
            
            # Broadcast failure
            try:
                from app.api.v1.endpoints.executions import publish_execution_event
                await publish_execution_event(new_execution_id, {
                    "type": "execution_failed",
                    "execution_id": new_execution_id,
                    "workflow_id": str(original_execution.workflow_id),
                    "status": "failed",
                    "error": str(e),
                    "message": f"Retry failed: {str(e)}"
                })
            except Exception as broadcast_error:
                logger.warning(f"Failed to broadcast retry failed event: {broadcast_error}")
            
            raise
        finally:
            db.close()
    
    def _detect_structure_changes(
        self,
        snapshot: WorkflowDefinition,
        current: WorkflowDefinition
    ) -> list:
        """
        Detect structural changes between workflow snapshot and current version.
        
        Returns list of warning messages about changes that might affect retry.
        
        Args:
            snapshot: Workflow definition from when execution ran
            current: Current workflow definition
        
        Returns:
            List of warning strings
        """
        warnings = []
        
        snapshot_node_ids = {node.node_id for node in snapshot.nodes}
        current_node_ids = {node.node_id for node in current.nodes}
        
        # Detect deleted nodes
        deleted_nodes = snapshot_node_ids - current_node_ids
        if deleted_nodes:
            warnings.append(
                f"Deleted nodes: {len(deleted_nodes)} node(s) were removed from the workflow. "
                f"IDs: {', '.join(list(deleted_nodes)[:5])}{'...' if len(deleted_nodes) > 5 else ''}"
            )
        
        # Detect added nodes
        added_nodes = current_node_ids - snapshot_node_ids
        if added_nodes:
            # This is usually fine, just informational
            warnings.append(
                f"New nodes: {len(added_nodes)} node(s) were added to the workflow. "
                f"They will be executed if their dependencies are met."
            )
        
        # Detect connection changes
        snapshot_connections = {
            (conn.source_node_id, conn.target_node_id) 
            for conn in snapshot.connections
        }
        current_connections = {
            (conn.source_node_id, conn.target_node_id) 
            for conn in current.connections
        }
        
        removed_connections = snapshot_connections - current_connections
        added_connections = current_connections - snapshot_connections
        
        if removed_connections:
            warnings.append(
                f"Removed connections: {len(removed_connections)} connection(s) were removed. "
                f"Data flow between nodes may have changed."
            )
        
        if added_connections:
            warnings.append(
                f"New connections: {len(added_connections)} connection(s) were added. "
                f"This may affect which nodes receive data."
            )
        
        return warnings
    
    def _merge_execution_config(self, workflow_db: Workflow) -> Dict[str, Any]:
        """
        Merge execution config from workflow and global settings.
        
        Priority: Workflow-specific > Global settings (from DB) > Defaults
        
        Args:
            workflow_db: Workflow DB model
        
        Returns:
            Merged config dictionary
        """
        # Load execution settings from database
        from app.core.config.manager import get_settings_manager
        
        try:
            settings_manager = get_settings_manager(self.db)
            execution_settings = settings_manager.get_execution_settings()
            
            # Convert ExecutionSettings to dict
            global_config = {
                # Concurrency
                "max_concurrent_nodes": execution_settings.max_concurrent_nodes,
                "ai_concurrent_limit": execution_settings.ai_concurrent_limit,
                "global_max_concurrent_runs": execution_settings.max_concurrent_runs_global,
                
                # Timeouts
                "default_timeout": execution_settings.default_timeout,
                "http_timeout": execution_settings.http_timeout,
                "workflow_timeout": execution_settings.workflow_timeout,
                
                # Retry
                "stop_on_error": execution_settings.error_handling == "stop_on_error",
                "max_retries": execution_settings.max_retries,
                "retry_delay": execution_settings.retry_delay,
                "backoff_multiplier": execution_settings.backoff_multiplier,
                "max_retry_delay": execution_settings.max_retry_delay,
                
                # Resources (using defaults as these aren't in ExecutionSettings yet)
                "max_memory_mb": 512,
                "max_execution_history_count": 100,
                "validate_payloads": True,
                "sandbox_enabled": False,
                "allow_external_requests": True,
                
                # Payload limits
                "max_payload_chars": 1000000,
                "max_payload_items": 10000,
                "max_inline_bytes": 1048576,
            }
        except Exception as e:
            logger.warning(f"Failed to load execution settings from database, using defaults: {e}")
            # Fallback to defaults if settings can't be loaded
            global_config = {
                # Concurrency
                "max_concurrent_nodes": 5,
                "ai_concurrent_limit": 1,
                "global_max_concurrent_runs": 8,
                
                # Timeouts
                "default_timeout": 300,
                "http_timeout": 60,
                "workflow_timeout": 1800,
                
                # Retry
                "stop_on_error": True,
                "max_retries": 3,
                "retry_delay": 5.0,
                "backoff_multiplier": 1.5,
                "max_retry_delay": 60,
                
                # Resources
                "max_memory_mb": 512,
                "max_execution_history_count": 100,
                "validate_payloads": True,
                "sandbox_enabled": False,
                "allow_external_requests": True,
                
                # Payload limits
                "max_payload_chars": 1000000,
                "max_payload_items": 10000,
                "max_inline_bytes": 1048576,
            }
        
        # Overlay workflow-specific config (if exists)
        if workflow_db.execution_config:
            workflow_config = workflow_db.execution_config
            
            # Merge: workflow config overrides global
            for key, value in workflow_config.items():
                if value is not None:  # Only override if explicitly set
                    global_config[key] = value
        
        return global_config
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution status and results.
        
        Args:
            execution_id: Execution UUID
        
        Returns:
            Execution data dict or None if not found
        """
        execution_db = self.db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution_db:
            return None
        
        return {
            "execution_id": execution_db.id,
            "workflow_id": execution_db.workflow_id,
            "status": execution_db.status,
            "execution_source": execution_db.execution_source,
            "started_at": execution_db.started_at,
            "completed_at": execution_db.completed_at,
            "final_outputs": execution_db.final_outputs,
            "error_message": execution_db.error_message,
            "execution_metadata": execution_db.execution_metadata,
            "node_results": execution_db.node_results,
        }
    
    def get_retry_info(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get retry information for an execution.
        
        Returns info about whether execution can be retried and what would be skipped.
        
        Args:
            execution_id: Execution UUID
        
        Returns:
            Dict with retry info or None if execution not found
        """
        execution_db = self.db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution_db:
            return None
        
        # Check if retryable
        retryable_statuses = [ExecutionStatus.FAILED, ExecutionStatus.STOPPED]
        can_retry = execution_db.status in retryable_statuses
        
        # Count completed nodes
        completed_nodes = []
        failed_nodes = []
        
        if execution_db.node_results:
            for node_id, result in execution_db.node_results.items():
                if result.get("success") is True:
                    completed_nodes.append(node_id)
                else:
                    failed_nodes.append({
                        "node_id": node_id,
                        "error": result.get("error")
                    })
        
        # Check for structure changes if we have a snapshot
        warnings = []
        if can_retry and execution_db.workflow_snapshot:
            workflow_db = self.db.query(Workflow).filter(
                Workflow.id == execution_db.workflow_id
            ).first()
            
            if workflow_db:
                try:
                    snapshot_def = WorkflowDefinition(**execution_db.workflow_snapshot)
                    current_def = WorkflowDefinition(**workflow_db.workflow_data)
                    warnings = self._detect_structure_changes(snapshot_def, current_def)
                except Exception as e:
                    logger.warning(f"Failed to detect structure changes: {e}")
        
        # Get retry count from metadata
        retry_count = 0
        if execution_db.execution_metadata:
            retry_count = execution_db.execution_metadata.get("retry_count", 0)
        
        return {
            "execution_id": execution_id,
            "can_retry": can_retry,
            "status": execution_db.status,
            "completed_nodes": completed_nodes,
            "completed_count": len(completed_nodes),
            "failed_nodes": failed_nodes,
            "failed_count": len(failed_nodes),
            "retry_count": retry_count,
            "has_structure_changes": len(warnings) > 0,
            "structure_warnings": warnings,
            "error_message": execution_db.error_message
        }
