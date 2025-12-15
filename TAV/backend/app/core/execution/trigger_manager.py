"""
Trigger Manager

Manages trigger node lifecycle for persistent workflows:
- Activate/deactivate workflow monitoring
- Start/stop trigger nodes (schedule, webhook, polling, etc.)
- Spawn workflow executions when triggers fire
- Enforce concurrency limits
"""

import asyncio
import logging
from typing import Dict, Optional, Callable, Awaitable, Set, Any
from datetime import datetime

from sqlalchemy.orm import Session
from app.utils.timezone import get_local_now

from app.database.models.workflow import Workflow
from app.database.models.execution import Execution
from app.schemas.workflow import WorkflowDefinition, NodeCategory, ExecutionStatus
from app.core.nodes import NodeRegistry, has_trigger_capability

logger = logging.getLogger(__name__)


class TriggerManager:
    """
    Central manager for workflow trigger nodes.
    
    Replaces V1's complex event-driven system with simple, direct approach:
    - Trigger nodes are regular nodes with TriggerCapability mixin
    - TriggerManager starts/stops trigger monitoring for workflows
    - When trigger fires → directly spawn execution via callback
    - No event queues, no dispatchers, no ack tracking
    
    Design:
    - Singleton pattern (one manager per app instance)
    - In-memory tracking of active triggers
    - Direct callback to orchestrator (no events)
    - Graceful shutdown (stop all triggers)
    
    Lifecycle:
    1. User clicks "Activate" → activate_workflow()
    2. TriggerManager finds trigger nodes in workflow
    3. For each trigger → instantiate node, call start_monitoring()
    4. Trigger node runs monitoring loop (schedule, webhook listener, etc.)
    5. When trigger fires → node calls fire_trigger()
    6. TriggerManager callback → spawns execution via orchestrator
    7. User clicks "Deactivate" → deactivate_workflow()
    8. TriggerManager calls stop_monitoring() on all trigger nodes
    """
    
    def __init__(
        self,
        db_session_factory: Callable[[], Session],
        execution_callback: Callable[[str, Dict, str], Awaitable[str]]
    ):
        """
        Initialize trigger manager.
        
        Args:
            db_session_factory: Factory function to create DB sessions
            execution_callback: Async callback to spawn executions
                                Signature: (workflow_id, trigger_data, execution_source) -> execution_id
        """
        self.db_session_factory = db_session_factory
        self.execution_callback = execution_callback
        
        # In-memory tracking
        self.active_workflows: Dict[str, Dict[str, any]] = {}  # workflow_id → trigger_info
        # trigger_info = {
        #     "workflow": WorkflowDefinition,
        #     "trigger_nodes": {node_id: node_instance},
        #     "started_at": datetime,
        # }
        
        # Execution queues (per workflow)
        self.execution_queues: Dict[str, asyncio.Queue] = {}  # workflow_id → Queue
        
        self._shutdown_requested = False
        
        logger.info("TriggerManager initialized")
    
    async def activate_workflow(self, workflow_id: str) -> Dict[str, any]:
        """
        Activate workflow for trigger monitoring.
        
        Steps:
        1. Load workflow from DB
        2. Find trigger nodes (category=TRIGGERS)
        3. Instantiate trigger nodes
        4. Call start_monitoring() on each
        5. Update workflow state in DB (ACTIVE)
        6. Track in memory
        
        Args:
            workflow_id: Workflow UUID
        
        Returns:
            Activation info: {
                "workflow_id": str,
                "trigger_count": int,
                "trigger_nodes": List[str],
                "started_at": datetime
            }
        
        Raises:
            ValueError: If workflow not found or already active
            RuntimeError: If no trigger nodes found
        """
        logger.info(f"Activating workflow: {workflow_id}")
        
        # Check if already active
        if workflow_id in self.active_workflows:
            raise ValueError(f"Workflow {workflow_id} is already active")
        
        # Load workflow from DB
        db = self.db_session_factory()
        try:
            workflow_db = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if not workflow_db:
                raise ValueError(f"Workflow not found: {workflow_id}")
            
            # Convert to WorkflowDefinition
            workflow_def = WorkflowDefinition(**workflow_db.workflow_data)
            
            # Find trigger nodes
            trigger_nodes = self._find_trigger_nodes(workflow_def)
            
            if not trigger_nodes:
                raise RuntimeError(
                    f"Workflow {workflow_id} has no trigger nodes. "
                    f"Cannot activate for monitoring."
                )
            
            logger.debug(f"Found {len(trigger_nodes)} trigger nodes: {list(trigger_nodes.keys())}")
            
            # Instantiate and start trigger nodes
            trigger_instances = {}
            for node_id, node_config in trigger_nodes.items():
                try:
                    # Get node class
                    node_class = NodeRegistry.get(node_config.node_type)
                    if not node_class:
                        raise ValueError(f"Node type not registered: {node_config.node_type}")
                    
                    # Instantiate
                    node_instance = node_class(node_config)
                    
                    # Verify has TriggerCapability
                    if not has_trigger_capability(node_instance):
                        raise TypeError(
                            f"Node {node_id} has category=TRIGGERS but does not "
                            f"implement TriggerCapability mixin"
                        )
                    
                    # Start monitoring
                    await node_instance.start_monitoring(
                        workflow_id=workflow_id,
                        executor_callback=self._create_trigger_callback(workflow_id)
                    )
                    
                    trigger_instances[node_id] = node_instance
                    
                    logger.info(f"Started monitoring for trigger node: {node_id}")
                
                except Exception as e:
                    # Cleanup already started triggers
                    logger.error(f"Failed to start trigger {node_id}: {e}", exc_info=True)
                    await self._stop_trigger_nodes(trigger_instances)
                    raise RuntimeError(f"Failed to activate workflow {workflow_id}: {e}")
            
            # Update workflow state in DB
            workflow_db.status = ExecutionStatus.PENDING
            workflow_db.monitoring_started_at = get_local_now()
            db.commit()
            
            # Track in memory
            started_at = get_local_now()
            self.active_workflows[workflow_id] = {
                "workflow": workflow_def,
                "trigger_nodes": trigger_instances,
                "started_at": started_at,
            }
            
            activation_info = {
                "workflow_id": workflow_id,
                "trigger_count": len(trigger_instances),
                "trigger_nodes": list(trigger_instances.keys()),
                "started_at": started_at,
            }
            
            logger.info(
                f"Workflow {workflow_id} activated successfully: "
                f"{len(trigger_instances)} triggers"
            )
            
            return activation_info
        
        finally:
            db.close()
    
    async def deactivate_workflow(self, workflow_id: str) -> bool:
        """
        Deactivate workflow trigger monitoring.
        
        Steps:
        1. Check if workflow is active
        2. Call stop_monitoring() on all trigger nodes
        3. Clear execution queue
        4. Update workflow state in DB (INACTIVE)
        5. Remove from memory
        
        Args:
            workflow_id: Workflow UUID
        
        Returns:
            True if deactivated, False if not active
        """
        logger.info(f"Deactivating workflow: {workflow_id}")
        
        # Check if active
        if workflow_id not in self.active_workflows:
            logger.warning(f"Workflow {workflow_id} is not active")
            return False
        
        # Get trigger info
        trigger_info = self.active_workflows[workflow_id]
        trigger_instances = trigger_info["trigger_nodes"]
        
        # Stop all trigger nodes
        await self._stop_trigger_nodes(trigger_instances)
        
        # Clear execution queue
        if workflow_id in self.execution_queues:
            queue = self.execution_queues[workflow_id]
            queue_size = queue.qsize()
            
            # Drain the queue
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            del self.execution_queues[workflow_id]
            
            if queue_size > 0:
                logger.info(
                    f"Cleared {queue_size} queued events for workflow {workflow_id}"
                )
        
        # Update workflow state in DB
        db = self.db_session_factory()
        try:
            workflow_db = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if workflow_db:
                workflow_db.status = ExecutionStatus.STOPPED
                workflow_db.monitoring_stopped_at = get_local_now()
                db.commit()
        finally:
            db.close()
        
        # Remove from memory
        del self.active_workflows[workflow_id]
        
        logger.info(f"Workflow {workflow_id} deactivated successfully")
        
        return True
    
    async def shutdown(self):
        """
        Graceful shutdown: deactivate all workflows.
        
        Called on app shutdown to clean up running triggers.
        """
        logger.info(f"TriggerManager shutdown requested, deactivating {len(self.active_workflows)} workflows")
        
        self._shutdown_requested = True
        
        # Deactivate all workflows
        workflow_ids = list(self.active_workflows.keys())
        for workflow_id in workflow_ids:
            try:
                await self.deactivate_workflow(workflow_id)
            except Exception as e:
                logger.error(f"Error deactivating workflow {workflow_id} during shutdown: {e}")
        
        logger.info("TriggerManager shutdown complete")
    
    def get_active_workflows(self) -> Dict[str, Dict]:
        """
        Get currently active workflows.
        
        Returns:
            Dict of workflow_id → {
                "workflow_name": str,
                "trigger_count": int,
                "trigger_nodes": List[str],
                "started_at": datetime,
                "uptime_seconds": float
            }
        """
        result = {}
        for workflow_id, trigger_info in self.active_workflows.items():
            uptime = (get_local_now() - trigger_info["started_at"]).total_seconds()
            result[workflow_id] = {
                "workflow_name": trigger_info["workflow"].name,
                "trigger_count": len(trigger_info["trigger_nodes"]),
                "trigger_nodes": list(trigger_info["trigger_nodes"].keys()),
                "started_at": trigger_info["started_at"],
                "uptime_seconds": uptime,
            }
        return result
    
    def is_workflow_active(self, workflow_id: str) -> bool:
        """Check if workflow is currently active."""
        return workflow_id in self.active_workflows
    
    # --- Internal Methods ---
    
    def _find_trigger_nodes(self, workflow: WorkflowDefinition) -> Dict[str, any]:
        """
        Find trigger nodes in workflow.
        
        Detection: NodeConfiguration.category == NodeCategory.TRIGGERS
        
        Returns:
            Dict of node_id → NodeConfiguration
        """
        trigger_nodes = {}
        for node in workflow.nodes:
            if node.category == NodeCategory.TRIGGERS:
                trigger_nodes[node.node_id] = node
        return trigger_nodes
    
    def _create_trigger_callback(
        self,
        workflow_id: str
    ) -> Callable[[str, Dict, str], Awaitable[None]]:
        """
        Create callback for trigger nodes with queue support.
        
        When trigger fires, this callback:
        1. Checks concurrency limits
        2. If under limit → execute immediately
        3. If at limit → add to queue
        4. After execution → process queued events
        
        Args:
            workflow_id: Workflow UUID
        
        Returns:
            Async callback function
        """
        async def callback(
            workflow_id: str,
            trigger_data: Dict,
            execution_source: str
        ):
            """
            Trigger callback implementation with queueing.
            
            Args:
                workflow_id: Workflow UUID (from trigger node)
                trigger_data: Trigger-specific data
                execution_source: Execution source (e.g., "schedule", "webhook")
            """
            logger.info(
                f"🔔 Trigger fired: workflow={workflow_id}, "
                f"source={execution_source}"
            )
            
            # Validate workflow is still active
            if workflow_id not in self.active_workflows:
                logger.warning(
                    f"Trigger fired for inactive workflow {workflow_id}, ignoring"
                )
                return
            
            # Check concurrency limit
            active_count = self._count_active_executions(workflow_id)
            max_concurrent = self._get_max_concurrent(workflow_id)
            
            logger.debug(
                f"Concurrency check: {active_count}/{max_concurrent} running"
            )
            
            if active_count >= max_concurrent:
                # AT LIMIT - Add to queue
                logger.info(
                    f"⏸️  At concurrency limit ({active_count}/{max_concurrent}), "
                    f"queuing event for workflow {workflow_id}"
                )
                
                # Get or create queue for this workflow
                if workflow_id not in self.execution_queues:
                    max_queue_depth = self._get_max_queue_depth(workflow_id)
                    self.execution_queues[workflow_id] = asyncio.Queue(
                        maxsize=max_queue_depth
                    )
                
                queue = self.execution_queues[workflow_id]
                
                # Try to add to queue
                try:
                    queue.put_nowait({
                        "trigger_data": trigger_data,
                        "execution_source": execution_source,
                        "queued_at": get_local_now()
                    })
                    logger.info(
                        f"📥 Event queued (queue size: {queue.qsize()}/{queue.maxsize})"
                    )
                
                except asyncio.QueueFull:
                    logger.error(
                        f"❌ Queue full for workflow {workflow_id} "
                        f"({queue.maxsize} events), DROPPING event"
                    )
                
                return  # Done, event queued or dropped
            
            # UNDER LIMIT - Execute immediately
            logger.info(
                f"✅ Under limit ({active_count}/{max_concurrent}), "
                f"executing immediately"
            )
            
            await self._execute_with_queue_processing(
                workflow_id,
                trigger_data,
                execution_source
            )
        
        return callback
    
    async def _stop_trigger_nodes(self, trigger_instances: Dict[str, any]):
        """
        Stop all trigger nodes.
        
        Args:
            trigger_instances: Dict of node_id → node_instance
        """
        for node_id, node_instance in trigger_instances.items():
            try:
                await node_instance.stop_monitoring()
                logger.info(f"Stopped monitoring for trigger node: {node_id}")
            except Exception as e:
                logger.error(f"Error stopping trigger {node_id}: {e}", exc_info=True)
    
    # --- Database Query Methods ---
    
    def _count_active_executions(self, workflow_id: str) -> int:
        """
        Count currently running executions for a workflow.
        
        Args:
            workflow_id: Workflow UUID
        
        Returns:
            Number of RUNNING executions
        """
        db = self.db_session_factory()
        try:
            count = db.query(Execution).filter(
                Execution.workflow_id == workflow_id,
                Execution.status == ExecutionStatus.RUNNING
            ).count()
            return count
        finally:
            db.close()
    
    def _get_max_concurrent(self, workflow_id: str) -> int:
        """
        Get max concurrent runs allowed for workflow.
        
        Checks workflow-specific config first, falls back to global setting.
        
        Args:
            workflow_id: Workflow UUID
        
        Returns:
            Max concurrent runs limit
        """
        db = self.db_session_factory()
        try:
            # Load workflow
            workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if not workflow:
                return 5  # Default fallback
            
            # Check workflow-specific config
            if workflow.execution_config and "max_concurrent_runs" in workflow.execution_config:
                return workflow.execution_config["max_concurrent_runs"]
            
            # Fall back to global settings
            from app.core.config.manager import get_settings_manager
            try:
                settings_manager = get_settings_manager(db)
                execution_settings = settings_manager.get_execution_settings()
                return execution_settings.max_concurrent_runs_per_workflow
            except Exception:
                return 5  # Default fallback
        
        finally:
            db.close()
    
    def _get_max_queue_depth(self, workflow_id: str) -> int:
        """
        Get max queue depth allowed for workflow.
        
        Args:
            workflow_id: Workflow UUID
        
        Returns:
            Max queue depth limit
        """
        db = self.db_session_factory()
        try:
            # Load global settings
            from app.core.config.manager import get_settings_manager
            try:
                settings_manager = get_settings_manager(db)
                execution_settings = settings_manager.get_execution_settings()
                return execution_settings.max_queue_depth_per_workflow
            except Exception:
                return 200  # Default fallback
        
        finally:
            db.close()
    
    # --- Queue Management Methods ---
    
    async def _execute_with_queue_processing(
        self,
        workflow_id: str,
        trigger_data: Dict[str, Any],
        execution_source: str
    ):
        """
        Execute workflow and process queue afterward.
        
        This ensures that after each execution completes, we check if there
        are queued events waiting and process them.
        
        Args:
            workflow_id: Workflow UUID
            trigger_data: Trigger event data
            execution_source: Execution source (e.g., "schedule", "webhook")
        """
        try:
            # Execute the workflow
            execution_id = await self.execution_callback(
                workflow_id,
                trigger_data,
                execution_source
            )
            logger.info(f"✅ Execution {execution_id} completed for workflow {workflow_id}")
        
        except Exception as e:
            logger.error(
                f"❌ Execution failed for workflow {workflow_id}: {e}",
                exc_info=True
            )
        
        finally:
            # ALWAYS check queue after execution (success or failure)
            await self._process_queue(workflow_id)
    
    async def _process_queue(self, workflow_id: str):
        """
        Process queued events if under concurrency limit.
        
        Called after each execution completes to check if there are
        queued events waiting and if we have capacity to run them.
        
        Args:
            workflow_id: Workflow UUID
        """
        # Check if workflow is still active
        if workflow_id not in self.active_workflows:
            return  # Workflow was deactivated
        
        # Check if there are queued events
        queue = self.execution_queues.get(workflow_id)
        if not queue or queue.empty():
            return  # Nothing queued
        
        # Check if we're under limit now
        active_count = self._count_active_executions(workflow_id)
        max_concurrent = self._get_max_concurrent(workflow_id)
        
        if active_count >= max_concurrent:
            logger.debug(
                f"Still at concurrency limit ({active_count}/{max_concurrent}), "
                f"queue remains with {queue.qsize()} events"
            )
            return  # Still at limit, queue stays
        
        # We have capacity! Process next queued event
        try:
            queued_event = queue.get_nowait()
            
            wait_time = (get_local_now() - queued_event["queued_at"]).total_seconds()
            logger.info(
                f"🔄 Processing queued event for workflow {workflow_id} "
                f"(waited {wait_time:.1f}s, {queue.qsize()} remain in queue)"
            )
            
            # Execute it (this will recursively call _process_queue when done)
            await self._execute_with_queue_processing(
                workflow_id,
                queued_event["trigger_data"],
                queued_event["execution_source"]
            )
        
        except asyncio.QueueEmpty:
            # Race condition, queue emptied between checks
            pass
        except Exception as e:
            logger.error(f"Error processing queued event: {e}", exc_info=True)


