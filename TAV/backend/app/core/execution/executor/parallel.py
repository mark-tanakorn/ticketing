"""
Parallel Executor

Reactive, parallel workflow execution engine with:
- Worker pool pattern (bounded concurrency)
- Resource management (standard/llm/ai pools)
- Config-driven error handling, retries, timeouts
- Connection-based data flow
- Shared state management
- Push-based reactive execution
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from contextlib import AsyncExitStack

from app.utils.timezone import get_local_now

from app.schemas.workflow import WorkflowDefinition, NodeConfiguration, ExecutionStatus
from app.core.execution.graph.types import ExecutionGraph, NodeExecutionPhase
from app.core.execution.context import ExecutionContext, NodeExecutionResult, ExecutionMode, ExecutionProgress
from app.core.nodes import NodeRegistry, NodeExecutionInput, get_resource_classes

logger = logging.getLogger(__name__)


class ParallelExecutor:
    """
    Parallel workflow executor with reactive dependency resolution.
    
    Features:
    - Reactive execution (push-based, nodes execute as soon as dependencies complete)
    - Worker pool (bounded concurrency via semaphores)
    - Resource management (separate pools for standard/llm/ai nodes)
    - Config-driven (reads from workflow.execution_config + global settings)
    - Error handling with retries and exponential backoff
    - Timeouts at node and workflow level
    - Connection-based data flow with optional shared state
    
    Design:
    - No event queues (direct async/await)
    - No complex orchestration (simple, testable logic)
    - 40% of V1 code with 100% of functionality
    """
    
    def __init__(self, execution_config: Dict[str, Any]):
        """
        Initialize parallel executor with config.
        
        Args:
            execution_config: Merged config (workflow overrides + global settings)
                Expected keys:
                - max_concurrent_nodes: Worker pool size
                - ai_concurrent_limit: AI/LLM pool size
                - default_timeout: Node timeout (seconds)
                - workflow_timeout: Overall timeout (seconds)
                - stop_on_error: Stop on first error vs continue
                - max_retries: Retry attempts
                - retry_delay: Initial retry delay
                - backoff_multiplier: Exponential backoff multiplier
                - max_retry_delay: Max retry delay
        """
        self.config = execution_config
        
        # Resource pools (semaphores for bounded concurrency)
        self.standard_pool = asyncio.Semaphore(self.config.get("max_concurrent_nodes", 5))
        self.llm_pool = asyncio.Semaphore(self.config.get("ai_concurrent_limit", 1))
        self.ai_pool = asyncio.Semaphore(self.config.get("ai_concurrent_limit", 1))
        
        # Execution tracking
        self.active_tasks: Dict[str, asyncio.Task] = {}  # node_id → task
        self.cancel_requested = False
        
        # Execution context and graph (set when execute_workflow is called)
        self.context: Optional[ExecutionContext] = None
        self.graph: Optional[ExecutionGraph] = None  # For progress tracking
        
        # Variable name mapping for duplicate detection (node_id → variable_name)
        self.variable_name_mapping: Dict[str, str] = {}
        
        # Pause/Resume control
        self.paused = False
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # Start unpaused (event is "set" means proceed)
        self.paused_at: Optional[Any] = None  # Track when paused for timeout
        
        logger.info(
            f"ParallelExecutor initialized: "
            f"workers={self.config.get('max_concurrent_nodes')}, "
            f"ai_limit={self.config.get('ai_concurrent_limit')}, "
            f"timeout={self.config.get('default_timeout')}s"
        )
    
    def _build_variable_name_mapping(self, workflow: WorkflowDefinition):
        """
        Build mapping of node_id to variable_name for all nodes that share outputs.
        Handles duplicate node names by appending _1, _2, etc.
        
        Args:
            workflow: Workflow definition with all nodes
        """
        # Group nodes by their sanitized name
        from collections import defaultdict
        name_groups = defaultdict(list)
        
        for node in workflow.nodes:
            if node.share_output_to_variables:
                if node.variable_name:
                    # Use custom variable name
                    self.variable_name_mapping[node.node_id] = node.variable_name
                else:
                    # Sanitize node name
                    base_key = (
                        node.name
                        .strip()
                        .replace(" ", "_")
                        .lower()
                    )
                    # Remove non-alphanumeric chars (except underscore)
                    base_key = "".join(c for c in base_key if c.isalnum() or c == "_")
                    # Prepend underscore if starts with number
                    if base_key and base_key[0].isdigit():
                        base_key = f"_{base_key}"
                    
                    name_groups[base_key].append(node.node_id)
        
        # For each group with multiple nodes, assign suffixes deterministically
        for base_key, node_ids in name_groups.items():
            if len(node_ids) == 1:
                # No duplicates, use base name
                self.variable_name_mapping[node_ids[0]] = base_key
            else:
                # Duplicates detected, sort by node_id and assign _1, _2, etc.
                sorted_ids = sorted(node_ids)
                for idx, node_id in enumerate(sorted_ids, start=1):
                    self.variable_name_mapping[node_id] = f"{base_key}_{idx}"
                    logger.debug(
                        f"Duplicate variable name detected: assigned '{base_key}_{idx}' to node {node_id}"
                    )
    
    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        graph: ExecutionGraph,
        context: ExecutionContext
    ) -> ExecutionContext:
        """
        Execute workflow with reactive parallel execution.
        
        Algorithm:
        1. Start with source nodes (no dependencies)
        2. Execute nodes as soon as all dependencies complete
        3. When node completes, check what became ready
        4. Continue until all nodes complete or error
        
        Args:
            workflow: Workflow definition
            graph: Execution graph with dependencies
            context: Execution context for state tracking
        
        Returns:
            Updated execution context with results
        
        Raises:
            asyncio.TimeoutError: If workflow timeout exceeded
            Exception: If stop_on_error=True and node fails
        """
        # Store context and graph for progress tracking
        self.context = context
        self.graph = graph
        
        # Build variable name mapping for duplicate detection
        self._build_variable_name_mapping(workflow)
        
        logger.info(
            f"Starting parallel execution: workflow={workflow.workflow_id}, "
            f"nodes={len(workflow.nodes)}, mode={context.execution_mode}"
        )
        
        # Start execution timing
        context.started_at = get_local_now()
        
        try:
            # Apply workflow timeout
            workflow_timeout = self.config.get("workflow_timeout", 1800)
            
            # Use asyncio.wait_for for Python 3.10 compatibility
            await asyncio.wait_for(
                self._execute_reactive_loop(workflow, graph, context),
                timeout=workflow_timeout
            )
            
            # Mark as completed
            context.completed_at = get_local_now()
            
            logger.info(
                f"Workflow execution completed: {workflow.workflow_id}, "
                f"duration={(context.completed_at - context.started_at).total_seconds()}s"
            )
            
            return context
        
        except asyncio.TimeoutError:
            context.completed_at = get_local_now()
            context.errors.append(f"Workflow timeout after {workflow_timeout}s")
            logger.error(f"Workflow {workflow.workflow_id} timed out")
            raise
        
        except Exception as e:
            context.completed_at = get_local_now()
            context.errors.append(str(e))
            logger.error(f"Workflow {workflow.workflow_id} failed: {e}", exc_info=True)
            raise
    
    async def _execute_reactive_loop(
        self,
        workflow: WorkflowDefinition,
        graph: ExecutionGraph,
        context: ExecutionContext
    ):
        """
        Main reactive execution loop.
        
        Push-based: When node completes, immediately check what became ready.
        Supports cyclic workflows (loops) by detecting loop completion and resetting.
        """
        # Get initial ready nodes (source nodes with no dependencies)
        ready_nodes = self._get_ready_nodes(graph)
        
        logger.info(f"🎯 Initial ready nodes: {ready_nodes}")
        
        # Track loop iterations if workflow has loops
        if graph.has_loops:
            logger.info(f"🔁 Workflow contains loops, will support iterative execution")
        
        # Execute until all nodes complete OR workflow is paused
        while ready_nodes or self.active_tasks or (self.paused and not graph.is_execution_complete()):
            # Check for cancellation
            if self.cancel_requested:
                logger.warning("Execution cancelled, stopping...")
                await self._cancel_all_tasks()
                
                # Mark all non-terminal nodes as STOPPED
                stopped_count = 0
                for node_id, node in graph.nodes.items():
                    if node.phase not in (
                        NodeExecutionPhase.COMPLETED,
                        NodeExecutionPhase.FAILED,
                        NodeExecutionPhase.STOPPED,
                        NodeExecutionPhase.SKIPPED
                    ):
                        node.phase = NodeExecutionPhase.STOPPED
                        graph.failed_nodes.add(node_id)  # Track stopped as failed for progress
                        stopped_count += 1
                        
                        # Add a result entry for stopped nodes
                        if node_id not in context.node_results:
                            context.node_results[node_id] = NodeExecutionResult(
                                node_id=node_id,
                                success=False,
                                outputs={},
                                error="Execution stopped by user",
                                started_at=get_local_now(),
                                completed_at=get_local_now(),
                                metadata={"stopped": True}
                            )
                
                logger.info(f"Marked {stopped_count} pending/ready nodes as STOPPED")
                break
            
            # Wait if paused (current nodes continue, but no new nodes start)
            await self.pause_event.wait()
            
            # If paused and no active tasks, we're waiting for human interaction
            # Check if execution is actually complete (no nodes awaiting interaction)
            if self.paused and not self.active_tasks:
                if graph.is_execution_complete():
                    # All nodes done (even awaiting ones resolved)
                    break
                else:
                    # Still waiting for interaction - sleep and check again
                    await asyncio.sleep(0.5)
                    continue
            
            # Start tasks for ready nodes
            for node_id in ready_nodes:
                if node_id not in self.active_tasks:
                    task = asyncio.create_task(
                        self._execute_node_with_tracking(node_id, workflow, graph, context)
                    )
                    self.active_tasks[node_id] = task
            
            ready_nodes = []
            
            # Wait for at least one task to complete
            if self.active_tasks:
                done, pending = await asyncio.wait(
                    self.active_tasks.values(),
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Process completed tasks
                for task in done:
                    # Find which node completed
                    completed_node_id = None
                    for node_id, node_task in self.active_tasks.items():
                        if node_task == task:
                            completed_node_id = node_id
                            break
                    
                    if completed_node_id:
                        # Remove from active tasks
                        del self.active_tasks[completed_node_id]
                        
                        # Check if node succeeded or failed
                        try:
                            task.result()  # Raises exception if task failed
                            
                            # Check if node is awaiting interaction (don't mark as completed!)
                            if graph.nodes[completed_node_id].phase == NodeExecutionPhase.AWAITING_INTERACTION:
                                logger.info(f"Node {completed_node_id} is awaiting interaction, not marking as completed")
                                # Don't decrement dependency counters - workflow is paused
                                continue
                            
                            # Mark node as completed in graph (both phase and tracking Set)
                            graph.nodes[completed_node_id].phase = NodeExecutionPhase.COMPLETED
                            graph.completed_nodes.add(completed_node_id)
                            
                            # Decrement dependency counters for dependent nodes
                            newly_ready = self._mark_node_completed(
                                completed_node_id, graph, workflow, context
                            )
                            ready_nodes.extend(newly_ready)
                            
                            logger.debug(f"Node {completed_node_id} completed, newly ready: {newly_ready}")
                        
                        except Exception as e:
                            # Node failed
                            logger.error(f"Node {completed_node_id} failed: {e}")
                            
                            # Check stop_on_error
                            if self.config.get("stop_on_error", True):
                                # Stop immediately
                                logger.error("stop_on_error=True, halting execution")
                                await self._cancel_all_tasks()
                                raise
                            else:
                                # Continue with other nodes
                                logger.warning(f"stop_on_error=False, continuing despite failure")
                                graph.nodes[completed_node_id].phase = NodeExecutionPhase.FAILED
                                graph.failed_nodes.add(completed_node_id)
            
            # Check if we've completed a loop iteration
            # This happens when we have no more ready nodes, no active tasks, but workflow has loops
            if not ready_nodes and not self.active_tasks and graph.has_loops:
                logger.info(f"🔁 Checking if loop should continue...")
                logger.info(f"   Completed nodes: {len(graph.completed_nodes)}")
                logger.info(f"   Node phases: {[(nid, n.phase.value) for nid, n in list(graph.nodes.items())[:3]]}")
                
                # Check if there are any nodes in COMPLETED state that are loop entry points
                loop_should_continue = self._check_loop_continuation(workflow, graph, context)
                
                if loop_should_continue:
                    logger.info(f"🔁 Loop iteration complete, resetting for next iteration")
                    # Reset nodes in the loop for next iteration
                    ready_nodes = self._reset_loop_nodes(graph, context)
                else:
                    logger.info(f"🏁 Loop terminated (continue condition is false)")
                    break
        
        logger.info(f"Reactive execution loop completed")
    
    def _check_loop_continuation(self, workflow: "WorkflowDefinition", graph: ExecutionGraph, context: ExecutionContext) -> bool:
        """
        Check if the loop should continue for another iteration.
        
        Looks for a node (typically While Loop or Loop Orchestrator) that outputs
        a 'continue_loop' signal indicating whether to continue.
        
        Priority:
        1. Check if the loop entry point (While Loop node) was SKIPPED
           (meaning a Decision node blocked the loop-back path)
        2. Check for continue_loop signals from While Loop nodes
        """
        # First, check if the loop entry point was skipped
        # This happens when a Decision node activates FALSE branch instead of looping back
        for node_id in graph.skipped_nodes:
            node_def = next((n for n in workflow.nodes if n.node_id == node_id), None)
            if node_def and 'loop' in node_def.node_type.lower():
                logger.info(f"🔁 Loop entry point {node_id} was skipped - loop will exit")
                return False
        
        # Second, look for continue_loop signal in node outputs
        for node_id, result in context.node_results.items():
            if result.success and result.outputs:
                # Check for continue_loop output
                continue_signal = result.outputs.get("continue_loop")
                if continue_signal is not None:
                    logger.info(f"🔁 Loop control node {node_id} says continue={continue_signal}")
                    return bool(continue_signal)
        
        # Default: don't continue if no signal found
        return False
    
    def _reset_loop_nodes(self, graph: ExecutionGraph, context: ExecutionContext) -> List[str]:
        """
        Reset nodes in the loop for the next iteration.
        
        Returns list of nodes that are ready to execute in the next iteration.
        """
        # Find all nodes that are part of the loop
        # Strategy: Start from the loop back-edge cycle and expand to include ALL descendants
        # of the entry point up until the decision node
        loop_nodes = set()
        for cycle in graph.loop_back_edges:
            loop_nodes.update(cycle)
        
        # Find the loop entry point (should have loop-back dependencies)
        entry_point = None
        decision_node = None  # The node that decides whether to continue
        
        for node_id in loop_nodes:
            node_deps = graph.nodes.get(node_id)
            if node_deps:
                if node_deps.loop_back_dependencies:
                    entry_point = node_id
                # Find decision node (typically named "decision" and in control category)
                node_config = None
                for wf_node in [n for n in graph.nodes.keys() if n == node_id]:
                    for nconfig in context.workflow_definition.nodes if hasattr(context, 'workflow_definition') else []:
                        if nconfig.node_id == node_id:
                            node_config = nconfig
                            break
                if node_config and ('decision' in node_config.node_type.lower() or node_config.category == 'control'):
                    # Check if this node has the entry point as a dependent
                    if entry_point and entry_point in node_deps.dependents:
                        decision_node = node_id
        
        # If we found an entry point, expand to include ALL reachable nodes
        if entry_point:
            def find_all_descendants_until_decision(node_id, visited=None, depth=0):
                """Find ALL descendants until we hit the decision node"""
                if visited is None:
                    visited = set()
                if node_id in visited or depth > 50:  # Prevent infinite recursion
                    return visited
                visited.add(node_id)
                
                node_deps = graph.nodes.get(node_id)
                if node_deps:
                    # Don't traverse past the decision node's dependents (the back edge)
                    if node_id == decision_node:
                        return visited
                    
                    for dependent_id in node_deps.dependents:
                        find_all_descendants_until_decision(dependent_id, visited, depth + 1)
                
                return visited
            
            # Get ALL nodes from entry to decision (inclusive)
            loop_nodes = find_all_descendants_until_decision(entry_point)
        
        logger.info(f"🔄 Resetting {len(loop_nodes)} loop nodes for next iteration: {list(loop_nodes)[:5]}...")
        
        # Clear outputs and results for loop nodes (except loop control node itself)
        # This ensures fresh data flows through on each iteration
        for node_id in loop_nodes:
            # Keep the loop control node's outputs (While Loop) so we can check iteration count
            node = graph.nodes.get(node_id)
            if node and node_id in context.node_outputs:
                # Check if this is the loop control node (has continue_loop output)
                outputs = context.node_outputs.get(node_id, {})
                if "continue_loop" not in outputs:
                    # Not the loop control node, clear its outputs
                    del context.node_outputs[node_id]
                    logger.debug(f"🔄 Cleared outputs for loop node: {node_id}")
            
            # Clear from node_results as well (except loop control)
            if node_id in context.node_results:
                result = context.node_results[node_id]
                if not (result.outputs and "continue_loop" in result.outputs):
                    del context.node_results[node_id]
                    logger.debug(f"🔄 Cleared result for loop node: {node_id}")
        
        # Reset all loop nodes to PENDING and clear from tracking Sets
        # This uses the new reset_nodes_for_loop method which properly clears
        # completed_nodes, skipped_nodes, and failed_nodes Sets
        graph.reset_nodes_for_loop(loop_nodes)
        logger.debug(f"🔄 Reset {len(loop_nodes)} loop nodes (phases and tracking Sets)")
        
        # Find loop entry points (nodes with loop-back dependencies)
        loop_entry_points = set()
        for node_id in loop_nodes:
            if node_id in graph.nodes:
                node_deps = graph.nodes[node_id]
                if node_deps.loop_back_dependencies:
                    loop_entry_points.add(node_id)
        
        # Temporarily clear loop-back dependencies for entry points (same as first iteration)
        for entry_id in loop_entry_points:
            if entry_id in graph.nodes:
                entry_deps = graph.nodes[entry_id]
                logger.info(
                    f"🔄 Entry point {entry_id}: "
                    f"remaining_deps={entry_deps.remaining_deps}, "
                    f"phase={entry_deps.phase.value}, "
                    f"loop_back_deps={len(entry_deps.loop_back_dependencies) if entry_deps.loop_back_dependencies else 0}"
                )
                if entry_deps.loop_back_dependencies:
                    # For loop iterations after the first:
                    # - The entry point should ONLY wait for loop-back dependencies (e.g., Decision node)
                    # - It should IGNORE initial triggers (e.g., Delete State) which only fire once
                    # 
                    # Example:
                    #   First iteration:  Delete State → While Loop (wait for Delete State)
                    #   Next iterations:  Decision → While Loop (only wait for Decision)
                    #
                    # Set remaining_deps to 0 because the loop-back edges will decrement it
                    # when the decision node completes (already handled by _mark_node_completed)
                    entry_deps.remaining_deps = 0
                    logger.info(
                        f"🔄 Entry point ready for next iteration (ignoring initial triggers, "
                        f"will wait for loop-back from previous iteration's completion)"
                    )
        
        # Return the loop entry points as ready nodes
        ready = self._get_ready_nodes(graph)
        logger.info(f"🔁 Next iteration ready nodes: {ready}")
        
        # If no nodes are ready, log WHY
        if not ready:
            logger.warning("⚠️ No nodes ready after loop reset! Debugging info:")
            for node_id in loop_entry_points:
                if node_id in graph.nodes:
                    node = graph.nodes[node_id]
                    logger.warning(
                        f"  Entry {node_id}: remaining_deps={node.remaining_deps}, "
                        f"phase={node.phase.value}, is_ready={node.is_ready()}"
                    )
        
        return ready
    
    def _get_ready_nodes(self, graph: ExecutionGraph) -> List[str]:
        """
        Get list of nodes that are ready to execute.
        
        Excludes tool-only nodes (nodes that should only be invoked by Agents).
        """
        ready = []
        for node_id, node_deps in graph.nodes.items():
            if node_deps.is_ready():
                # Exclude tool-only nodes - they should only execute when Agent calls them
                if node_id in graph.tools_memory_only_nodes:
                    logger.debug(f"🚫 Skipping tool-only node from ready list: {node_id}")
                    continue
                ready.append(node_id)
        return ready
    
    def _mark_node_completed(
        self,
        node_id: str,
        graph: ExecutionGraph,
        workflow: "WorkflowDefinition",
        context: "ExecutionContext"
    ) -> List[str]:
        """
        Mark node as completed and return newly ready nodes.
        
        Handles decision node branching by skipping blocked paths.
        
        Decrements remaining_deps for all dependent nodes.
        Returns list of nodes that just became ready.
        """
        newly_ready = []
        node_deps = graph.nodes[node_id]
        
        # Check if this is a decision node
        node_result = context.node_results.get(node_id)
        is_decision = self._is_decision_node(node_id, node_result)
        
        if is_decision:
            logger.info(f"🔀 Processing decision node: {node_id}")
            active_path = self._get_decision_active_path(node_result)
            blocked_outputs = self._get_decision_blocked_outputs(node_result)
            logger.info(f"  Active path: {active_path}, Blocked: {blocked_outputs}")
        
        # Decrement dependency count for all dependent nodes
        for dependent_id in node_deps.dependents:
            # For decision nodes, check if this dependent is on an active branch
            if is_decision:
                branch = self._get_connection_branch(
                    node_id,
                    dependent_id,
                    workflow.connections
                )
                
                # Check if this branch is blocked
                if self._is_branch_blocked(branch, node_result):
                    logger.info(f"🚫 Skipping blocked branch: {dependent_id} (branch: {branch})")
                    # Mark dependent and its descendants as skipped
                    skipped = graph.mark_node_skipped(dependent_id)
                    logger.info(f"   Skipped {len(skipped) + 1} nodes on blocked path")
                    continue
                else:
                    logger.info(f"✅ Allowing dependent: {dependent_id} (branch: {branch})")
            
            # Decrement dependency for allowed nodes
            dependent_deps = graph.nodes[dependent_id]
            dependent_deps.remaining_deps -= 1
            
            # Check if dependent became ready
            if dependent_deps.is_ready():
                newly_ready.append(dependent_id)
        
        return newly_ready
    
    def _is_decision_node(
        self,
        node_id: str,
        node_result: Optional["NodeExecutionResult"]
    ) -> bool:
        """Check if a node is a decision node"""
        if not node_result or not node_result.outputs:
            return False
        
        outputs = node_result.outputs
        
        # Check for decision node markers
        has_active_path = "active_path" in outputs
        has_blocked_outputs = "blocked_outputs" in outputs
        has_decision_result = "decision_result" in outputs
        
        return has_active_path or (has_blocked_outputs and has_decision_result)
    
    def _get_decision_active_path(
        self,
        node_result: Optional["NodeExecutionResult"]
    ) -> Optional[str]:
        """Get the active path from decision node result"""
        if not node_result or not node_result.outputs:
            return None
        
        return node_result.outputs.get("active_path")
    
    def _get_decision_blocked_outputs(
        self,
        node_result: Optional["NodeExecutionResult"]
    ) -> List[str]:
        """Get blocked outputs from decision node result"""
        if not node_result or not node_result.outputs:
            return []
        
        blocked = node_result.outputs.get("blocked_outputs", [])
        return blocked if isinstance(blocked, list) else []
    
    def _get_connection_branch(
        self,
        source_node_id: str,
        target_node_id: str,
        connections: List["Connection"]
    ) -> str:
        """
        Determine which branch a connection represents.
        
        Checks (in order of priority):
        1. Explicit branch metadata
        2. Source port name (contains "true" or "false")
        3. Default to "true"
        """
        for conn in connections:
            if conn.source_node_id == source_node_id and conn.target_node_id == target_node_id:
                # Check explicit branch metadata
                if "branch" in conn.metadata:
                    return str(conn.metadata["branch"])
                
                # Check source port name
                source_port = conn.source_port.lower()
                if "true" in source_port:
                    return "true"
                elif "false" in source_port:
                    return "false"
                
                # Default to true
                return "true"
        
        # Default if connection not found
        return "true"
    
    def _is_branch_blocked(
        self,
        branch: str,
        node_result: Optional["NodeExecutionResult"]
    ) -> bool:
        """
        Check if a branch is blocked by a decision node.
        
        A branch is blocked if:
        1. It's in the blocked_outputs list, OR
        2. It doesn't match the active_path
        """
        if not node_result or not node_result.outputs:
            return False
        
        outputs = node_result.outputs
        
        # Check blocked_outputs list
        blocked_outputs = self._get_decision_blocked_outputs(node_result)
        if branch in blocked_outputs:
            return True
        
        # Check active_path
        active_path = outputs.get("active_path")
        if active_path and branch != active_path:
            return True
        
        return False
    
    async def _execute_node_with_tracking(
        self,
        node_id: str,
        workflow: WorkflowDefinition,
        graph: ExecutionGraph,
        context: ExecutionContext
    ):
        """
        Execute single node with error handling and retry logic.
        
        Wrapper around _execute_node() that handles retries.
        """
        node_config = self._get_node_config(workflow, node_id)
        max_retries = self.config.get("max_retries", 3)
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                # Execute node
                await self._execute_node(node_id, workflow, graph, context)
                return  # Success!
            
            except Exception as e:
                last_error = e
                
                if attempt < max_retries:
                    # Calculate retry delay with exponential backoff
                    retry_delay = self.config.get("retry_delay", 5.0)
                    backoff_multiplier = self.config.get("backoff_multiplier", 1.5)
                    max_retry_delay = self.config.get("max_retry_delay", 60)
                    
                    delay = min(
                        retry_delay * (backoff_multiplier ** attempt),
                        max_retry_delay
                    )
                    
                    logger.warning(
                        f"Node {node_id} failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay}s: {e}"
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    # Max retries exceeded
                    logger.error(
                        f"Node {node_id} failed after {max_retries + 1} attempts: {e}"
                    )
                    raise
        
        # Should not reach here, but just in case
        if last_error:
            raise last_error
    
    async def _execute_node(
        self,
        node_id: str,
        workflow: WorkflowDefinition,
        graph: ExecutionGraph,
        context: ExecutionContext,
        override_inputs: Optional[Dict[str, Any]] = None
    ):
        """
        Execute single node with resource management and timeout.
        
        Args:
            node_id: ID of node to execute
            workflow: Workflow definition
            graph: Execution graph
            context: Execution context
            override_inputs: Optional inputs to override connection-based inputs (used by Agents)
        
        Steps:
        1. Get node configuration
        2. Instantiate node class
        3. Assemble inputs from connections (and overrides)
        4. Acquire resource semaphores
        5. Execute with timeout
        6. Store outputs
        7. Share to variables (if configured)
        """
        # Get node configuration
        node_config = self._get_node_config(workflow, node_id)
        
        logger.debug(f"Executing node: {node_id} ({node_config.node_type})")
        
        # Update phase
        graph.nodes[node_id].phase = NodeExecutionPhase.EXECUTING
        
        # Create a "running" node result entry
        node_start_time = get_local_now()
        context.node_results[node_id] = NodeExecutionResult(
            node_id=node_id,
            success=False,  # Will be updated to True on success
            outputs={},
            error=None,
            started_at=node_start_time,
            completed_at=None,
            metadata={"status": "executing"}
        )
        
        # Broadcast node start event
        try:
            from app.api.v1.endpoints.executions import publish_execution_event
            await publish_execution_event(context.execution_id, {
                "type": "node_start",
                "node_id": node_id,
                "node_type": node_config.node_type,
                "node_name": node_config.name,
                "status": "executing",
                "progress": graph.get_execution_progress()
            })
        except Exception as e:
            logger.warning(f"Failed to broadcast node_start event: {e}")
        
        # Persist "running" status to database for state recovery
        try:
            from app.database.session import SessionLocal
            from app.database.models import Execution
            
            db = SessionLocal()
            try:
                execution_db = db.query(Execution).filter(Execution.id == context.execution_id).first()
                if execution_db:
                    # Serialize all node_results to database
                    execution_db.node_results = {
                        nid: result.to_dict() for nid, result in context.node_results.items()
                    }
                    db.commit()
                    logger.info(f"✅ Persisted running status for node {node_id} to database")
            finally:
                db.close()
        except Exception as persist_error:
            logger.warning(f"Failed to persist running node status to database: {persist_error}")
        
        # Instantiate node
        node_class = NodeRegistry.get(node_config.node_type)
        if not node_class:
            raise ValueError(f"Node type not registered: {node_config.node_type}")
        
        node_instance = node_class(node_config)
        
        # IMPORTANT: Set execution_context on node so LLMCapability can access it
        # This enables automatic conversation context injection for all LLM nodes
        node_instance.execution_context = context
        
        # Assemble inputs from connections
        input_ports = self.assemble_inputs(node_id, graph, context, workflow)
        
        # Apply override inputs (from Agent execution)
        if override_inputs:
            input_ports.update(override_inputs)
            logger.debug(f"📥 Applied override inputs for node {node_id}: {list(override_inputs.keys())}")
        
        # INJECT TRIGGER DATA into input ports (if available)
        # This makes trigger_data available to ALL nodes via their input ports
        # Now supports ANY fields from initial_data, not just hardcoded ones
        if context.variables.get("trigger_data"):
            trigger_data = context.variables["trigger_data"]
            
            # If node has no input port yet (first node), inject entire trigger_data as "input"
            # Otherwise inject as "_trigger_data" port so it doesn't override existing connections
            if not input_ports or not input_ports.get("input"):
                input_ports["input"] = trigger_data
                logger.debug(f"💬 Injected trigger_data into 'input' port for node {node_id}: {list(trigger_data.keys())}")
            else:
                input_ports["_trigger_data"] = trigger_data
                logger.debug(f"💬 Injected trigger_data into '_trigger_data' port for node {node_id}: {list(trigger_data.keys())}")
        
        # Legacy: Also inject old format for backward compatibility
        elif context.variables.get("trigger_conversation"):
            # Create a special input port with conversation context
            conversation_input = {
                "conversation": context.variables.get("trigger_conversation"),
                "topic": context.variables.get("trigger_topic"),
                "priority": context.variables.get("trigger_priority"),
                "timestamp": context.variables.get("trigger_timestamp"),
                "latest_reply": context.variables.get("trigger_latest_reply")
            }
            
            # If node has no input port yet (first node), inject as "input"
            # Otherwise inject as "context" port so it doesn't override existing connections
            if not input_ports or not input_ports.get("input"):
                input_ports["input"] = conversation_input
                logger.debug(f"💬 Injected conversation context into 'input' port for node {node_id}")
            else:
                input_ports["_conversation_context"] = conversation_input
                logger.debug(f"💬 Injected conversation context into '_conversation_context' port for node {node_id}")
        
        # Inject credentials (if node config references any)
        # Get user_id from context.started_by (it's a string user_id)
        user_id = None
        if context.started_by:
            try:
                user_id = int(context.started_by)
                logger.info(f"🔐 Extracted user_id={user_id} from context.started_by={context.started_by}")
            except (ValueError, TypeError):
                logger.warning(f"Could not parse user_id from started_by: {context.started_by}")
        else:
            logger.warning(f"⚠️ context.started_by is None! Cannot inject credentials for node {node_id}")
        
        credentials_dict = await self._inject_credentials(node_config, user_id)
        
        # Define node runner callback for Agents
        async def node_runner(target_node_id: str, inputs: Dict[str, Any], config_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            """Execute a specific node with inputs and optional config overrides."""
            logger.info(f"🤖 Agent triggering execution of node {target_node_id}")
            
            # If config overrides provided, we need to temporarily modify the node config
            original_config = None
            if config_overrides:
                # Get the node config and apply overrides
                target_config = self._get_node_config(workflow, target_node_id)
                original_config = target_config.config.copy()
                target_config.config.update(config_overrides)
                logger.info(f"🔧 Applied config overrides to {target_node_id}: {list(config_overrides.keys())}")
            
            try:
                # Recursively call _execute_node with override inputs
                await self._execute_node(
                    target_node_id, 
                    workflow, 
                    graph, 
                    context, 
                    override_inputs=inputs
                )
                
                # Return the outputs from context
                return context.node_outputs.get(target_node_id, {})
            finally:
                # Restore original config
                if original_config and config_overrides:
                    target_config = self._get_node_config(workflow, target_node_id)
                    target_config.config = original_config

        # Build NodeExecutionInput
        input_data = NodeExecutionInput(
            ports=input_ports,
            workflow_id=context.workflow_id,
            execution_id=context.execution_id,
            node_id=node_id,
            variables=context.variables,
            config=node_config.config,
            credentials=credentials_dict,
            node_runner=node_runner,
            frontend_origin=context.frontend_origin
        )
        
        # Validate inputs
        validation_errors = node_instance.validate_inputs(input_ports)
        if validation_errors:
            raise ValueError(f"Node {node_id} input validation failed: {validation_errors}")
        
        # Get resource classes for this node
        resource_classes = get_resource_classes(node_instance)
        
        # Acquire resource semaphores and execute
        semaphores = self._get_semaphores(resource_classes)
        
        node_timeout = self.config.get("default_timeout", 300)
        
        try:
            async with AsyncExitStack() as stack:
                # Acquire all needed semaphores
                for sem in semaphores:
                    await stack.enter_async_context(sem)
                
                logger.debug(
                    f"Node {node_id} acquired resources: {resource_classes}, "
                    f"timeout={node_timeout}s"
                )
                
                # Execute with timeout (use asyncio.wait_for for Python 3.10 compatibility)
                outputs = await asyncio.wait_for(
                    node_instance.execute(input_data),
                    timeout=node_timeout
                )
            
            # Store outputs in context
            context.node_outputs[node_id] = outputs
            
            # ========== HUMAN-IN-THE-LOOP DETECTION ==========
            # Check if node is requesting human interaction (email approval, form input, etc.)
            if isinstance(outputs, dict) and outputs.get("_await") == "human_input":
                logger.info(f"🔔 Node {node_id} requesting human interaction, pausing workflow")
                
                # Store interaction data in context
                context.pending_interactions[node_id] = outputs
                
                # Mark node as awaiting interaction (not completed yet!)
                graph.nodes[node_id].phase = NodeExecutionPhase.AWAITING_INTERACTION
                
                # Pause the workflow (stops new nodes from starting)
                self.pause()
                logger.info(f"⏸️ Workflow paused at node {node_id}, waiting for user interaction")
                
                # Store a special result indicating pause
                context.node_results[node_id] = NodeExecutionResult(
                    node_id=node_id,
                    success=True,  # Not an error, just paused
                    outputs=outputs,
                    error=None,
                    started_at=get_local_now(),
                    completed_at=None,  # Not completed yet!
                    metadata={
                        "awaiting_interaction": True,
                        "interaction_id": outputs.get("interaction_id"),
                        "interaction_type": outputs.get("interaction_type", "unknown")
                    }
                )
                
                # Broadcast interaction_required event
                try:
                    from app.api.v1.endpoints.executions import publish_execution_event
                    await publish_execution_event(context.execution_id, {
                        "type": "interaction_required",
                        "node_id": node_id,
                        "interaction_type": outputs.get("interaction_type", "human_input"),
                        "interaction_id": outputs.get("interaction_id"),
                        "review_url": outputs.get("review_url"),
                        "message": outputs.get("message", "User interaction required"),
                        "status": "paused",
                        "progress": graph.get_execution_progress()
                    })
                except Exception as e:
                    logger.warning(f"Failed to broadcast interaction_required event: {e}")
                
                # Exit early - don't mark as completed
                # Workflow will resume when API endpoint receives submission
                return
            # ========== END HUMAN-IN-THE-LOOP DETECTION ==========
            
            # ========== SOFT ERROR DETECTION ==========
            # Check if node returned an error in output dictionary (common pattern for AI nodes)
            # This catches cases where nodes swallow exceptions and return error in output
            soft_error = None
            if isinstance(outputs, dict):
                # Check for common error indicators
                if outputs.get("error"):
                    soft_error = str(outputs.get("error"))
                elif outputs.get("_error"):
                    soft_error = str(outputs.get("_error"))
                elif outputs.get("success") is False:
                    soft_error = outputs.get("message", "Node reported failure")
            
            if soft_error:
                logger.warning(f"⚠️ Node {node_id} returned soft error in output: {soft_error}")
                # Preserve the original started_at time from when the node began
                original_started_at = context.node_results.get(node_id).started_at if node_id in context.node_results else get_local_now()
                
                context.node_results[node_id] = NodeExecutionResult(
                    node_id=node_id,
                    success=False,  # Mark as FAILED
                    outputs=outputs,
                    error=soft_error,
                    started_at=original_started_at,
                    completed_at=get_local_now(),
                    metadata={"soft_error": True}  # Indicate this was a soft error
                )
                
                # Raise as exception so retry/stop_on_error logic kicks in
                raise RuntimeError(f"Node {node_id} failed: {soft_error}")
            # ========== END SOFT ERROR DETECTION ==========
            
            # Store result (normal completion)
            # Preserve the original started_at time from when the node began
            original_started_at = context.node_results.get(node_id).started_at if node_id in context.node_results else get_local_now()
            
            context.node_results[node_id] = NodeExecutionResult(
                node_id=node_id,
                success=True,
                outputs=outputs,
                error=None,
                started_at=original_started_at,
                completed_at=get_local_now()
            )
            
            # Share to variables if configured
            if node_config.share_output_to_variables:
                self._share_to_variables(node_config, outputs, context)
            
            logger.info(f"Node {node_id} completed successfully")
            
            # Broadcast node complete event
            try:
                from app.api.v1.endpoints.executions import publish_execution_event
                
                # Get outputs safely
                result_outputs = {}
                if node_id in context.node_results:
                    result_outputs = context.node_results[node_id].outputs
                
                await publish_execution_event(context.execution_id, {
                    "type": "node_complete",
                    "node_id": node_id,
                    "node_type": node_config.node_type,
                    "node_name": node_config.name,
                    "status": "completed",
                    "outputs": result_outputs,  # Include outputs for preview
                    "progress": graph.get_execution_progress()
                })
            except Exception as e:
                logger.warning(f"Failed to broadcast node_complete event: {e}")
            
            # Persist node_results to database for state recovery
            try:
                from app.database.session import SessionLocal
                from app.database.models import Execution
                
                db = SessionLocal()
                try:
                    execution_db = db.query(Execution).filter(Execution.id == context.execution_id).first()
                    if execution_db:
                        # Serialize all node_results to database
                        execution_db.node_results = {
                            nid: result.to_dict() for nid, result in context.node_results.items()
                        }
                        db.commit()
                        logger.info(f"✅ Persisted node_results to database for execution {context.execution_id}")
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"Failed to persist node_results to database: {e}")
        
        except asyncio.TimeoutError:
            logger.error(f"Node {node_id} timed out after {node_timeout}s")
            # Preserve the original started_at time from when the node began
            original_started_at = context.node_results.get(node_id).started_at if node_id in context.node_results else get_local_now()
            
            context.node_results[node_id] = NodeExecutionResult(
                node_id=node_id,
                success=False,
                outputs={},
                error=f"Timeout after {node_timeout}s",
                started_at=original_started_at,
                completed_at=get_local_now()
            )
            raise
        
        except asyncio.CancelledError:
            logger.warning(f"Node {node_id} was cancelled (execution stopped by user)")
            
            # Preserve the original started_at time from when the node began
            original_started_at = context.node_results.get(node_id).started_at if node_id in context.node_results else get_local_now()
            
            # Mark node as stopped
            context.node_results[node_id] = NodeExecutionResult(
                node_id=node_id,
                success=False,
                outputs={},
                error="Execution stopped by user",
                started_at=original_started_at,
                completed_at=get_local_now(),
                metadata={"stopped": True}
            )
            
            # Update graph phase and tracking Set
            graph.nodes[node_id].phase = NodeExecutionPhase.STOPPED
            graph.failed_nodes.add(node_id)  # Track stopped as failed for progress
            
            # Broadcast node stopped event
            try:
                from app.api.v1.endpoints.executions import publish_execution_event
                await publish_execution_event(context.execution_id, {
                    "type": "node_stopped",
                    "node_id": node_id,
                    "node_type": node_config.node_type,
                    "node_name": node_config.name,
                    "status": "stopped",
                    "message": "Execution stopped by user",
                    "progress": graph.get_execution_progress()
                })
            except Exception as broadcast_error:
                logger.warning(f"Failed to broadcast node_stopped event: {broadcast_error}")
            
            # Re-raise to propagate cancellation up the call stack
            raise
        
        except Exception as e:
            logger.error(f"Node {node_id} execution failed: {e}", exc_info=True)
            
            # Preserve the original started_at time from when the node began
            original_started_at = context.node_results.get(node_id).started_at if node_id in context.node_results else get_local_now()
            
            context.node_results[node_id] = NodeExecutionResult(
                node_id=node_id,
                success=False,
                outputs={},
                error=str(e),
                started_at=original_started_at,
                completed_at=get_local_now()
            )
            
            # Broadcast node failed event
            try:
                from app.api.v1.endpoints.executions import publish_execution_event
                await publish_execution_event(context.execution_id, {
                    "type": "node_failed",
                    "node_id": node_id,
                    "node_type": node_config.node_type,
                    "node_name": node_config.name,
                    "status": "failed",
                    "error": str(e),
                    "progress": graph.get_execution_progress()
                })
            except Exception as broadcast_error:
                logger.warning(f"Failed to broadcast node_failed event: {broadcast_error}")
            
            # Persist node_results to database for state recovery
            try:
                from app.database.session import SessionLocal
                from app.database.models import Execution
                
                db = SessionLocal()
                try:
                    execution_db = db.query(Execution).filter(Execution.id == context.execution_id).first()
                    if execution_db:
                        # Serialize all node_results to database
                        execution_db.node_results = {
                            nid: result.to_dict() for nid, result in context.node_results.items()
                        }
                        db.commit()
                        logger.info(f"✅ Persisted node_results to database for execution {context.execution_id}")
                finally:
                    db.close()
            except Exception as persist_error:
                logger.warning(f"Failed to persist node_results to database: {persist_error}")
            
            raise
        
        finally:
            # Cleanup node resources (close database sessions, etc.)
            if hasattr(node_instance, 'cleanup'):
                try:
                    node_instance.cleanup()
                except Exception as cleanup_error:
                    logger.warning(f"Error during node cleanup for {node_id}: {cleanup_error}")
    
    def _get_node_config(self, workflow: WorkflowDefinition, node_id: str) -> NodeConfiguration:
        """Get node configuration from workflow."""
        for node in workflow.nodes:
            if node.node_id == node_id:
                return node
        raise ValueError(f"Node not found: {node_id}")
    
    def _get_semaphores(self, resource_classes: List[str]) -> List[asyncio.Semaphore]:
        """Get semaphores for resource classes."""
        semaphores = []
        for resource_class in resource_classes:
            if resource_class == "llm":
                semaphores.append(self.llm_pool)
            elif resource_class == "ai":
                semaphores.append(self.ai_pool)
            else:  # "standard"
                semaphores.append(self.standard_pool)
        return semaphores
    
    def assemble_inputs(
        self,
        node_id: str,
        graph: ExecutionGraph,
        context: ExecutionContext,
        workflow: Optional[WorkflowDefinition] = None
    ) -> Dict[str, Any]:
        """
        Assemble input data for node from connections.
        
        Maps connected node outputs to target node inputs based on connections.
        
        Args:
            node_id: Target node ID
            graph: Execution graph with connection info
            context: Execution context with node outputs
            workflow: Workflow definition (needed for tool config lookup)
        
        Returns:
            Dictionary of input port values: {port_name: value}
        """
        inputs = {}
        node_deps = graph.nodes[node_id]
        
        # For each input connection
        for conn_info in node_deps.input_connections:
            # conn_info is a dict (converted from ConnectionInfo object)
            source_node_id = conn_info.get('source_node_id') or conn_info.get('source_node')
            source_port = conn_info.get('source_port')
            target_port = conn_info.get('target_port')
            
            # SPECIAL CASE: Tools Port
            # If connecting to a "tools" port, pass the NODE CONFIGURATION itself
            if target_port == "tools" and workflow:
                try:
                    source_config = self._get_node_config(workflow, source_node_id)
                    if source_config:
                        # Append to list of tools
                        if target_port in inputs:
                            inputs[target_port].append(source_config)
                        else:
                            inputs[target_port] = [source_config]
                        logger.debug(f"🛠️ Attached tool node {source_node_id} to {node_id}")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to attach tool node {source_node_id}: {e}")
                    continue

            # Get source node's outputs
            if source_node_id not in context.node_outputs:
                logger.warning(
                    f"Source node {source_node_id} has no outputs yet "
                    f"(dependency not satisfied?)"
                )
                continue
            
            source_outputs = context.node_outputs[source_node_id]
            
            # Map source port to target port
            if source_port in source_outputs:
                value = source_outputs[source_port]
                
                # If target port already has a value, convert to list and append
                # This supports multiple connections to the same input port (e.g. list of images)
                if target_port in inputs:
                    existing_value = inputs[target_port]
                    if isinstance(existing_value, list):
                        if isinstance(value, list):
                            existing_value.extend(value)
                        else:
                            existing_value.append(value)
                    else:
                        if isinstance(value, list):
                            inputs[target_port] = [existing_value] + value
                        else:
                            inputs[target_port] = [existing_value, value]
                else:
                    inputs[target_port] = value
            else:
                logger.warning(
                    f"Source node {source_node_id} missing output port '{source_port}'"
                )
        
        return inputs
    
    def _share_to_variables(
        self,
        node_config: NodeConfiguration,
        outputs: Dict[str, Any],
        context: ExecutionContext
    ):
        """
        Share node outputs to workflow variables (flattened structure).
        
        Stores outputs in context.variables under _nodes namespace.
        
        New flattened structure:
        - If output is {"output": {dict}} → flatten to just the dict
        - Otherwise → store as-is
        
        This enables: variables._nodes[node_id][field] access pattern
        
        Args:
            node_config: Node configuration
            outputs: Node outputs to share (dict of port_name → value)
            context: Execution context
        
        Examples:
            Input: {"output": {"phone": "+1234", "message": "Hello"}}
            Stored: _nodes[node_id] = {"phone": "+1234", "message": "Hello"}
            
            Input: {"result": "OK", "status": 200}
            Stored: _nodes[node_id] = {"result": "OK", "status": 200}
        """
        # Initialize namespace if needed
        if "_nodes" not in context.variables:
            context.variables["_nodes"] = {}
        
        # Use pre-built variable name mapping (handles duplicates deterministically)
        node_key = self.variable_name_mapping.get(node_config.node_id)
        
        if not node_key:
            # Fallback: Node not in mapping (shouldn't happen if share_output_to_variables is true)
            logger.warning(
                f"Node {node_config.node_id} not found in variable_name_mapping, "
                f"this shouldn't happen if share_output_to_variables is enabled"
            )
            # Use variable_name if set, otherwise sanitize node name
            if node_config.variable_name:
                node_key = node_config.variable_name
            else:
                base_key = (
                    node_config.name
                    .strip()
                    .replace(" ", "_")
                    .lower()
                )
                base_key = "".join(c for c in base_key if c.isalnum() or c == "_")
                if base_key and base_key[0].isdigit():
                    base_key = f"_{base_key}"
                node_key = base_key
        
        # Flatten output structure for single-port dicts
        if "output" in outputs and isinstance(outputs["output"], dict) and len(outputs) == 1:
            # Single output port with dict payload - flatten it
            shared_data = outputs["output"]
            logger.debug(
                f"Flattening single 'output' port dict for node {node_config.node_id}: "
                f"fields={list(shared_data.keys())}"
            )
        else:
            # Multiple ports or non-dict output - store as-is
            shared_data = outputs
        
        # Store in shared space
        context.variables["_nodes"][node_key] = shared_data
        
        logger.info(
            f"📤 Shared node '{node_config.name}' (id={node_config.node_id}) outputs to variables "
            f"(key='{node_key}', fields={list(shared_data.keys()) if isinstance(shared_data, dict) else 'non-dict'})"
        )
    
    async def _inject_credentials(
        self, 
        node_config: NodeConfiguration, 
        user_id: Optional[int]
    ) -> Optional[Dict[int, Dict[str, Any]]]:
        """
        Inject credentials into node execution input.
        
        Scans node config for credential_id fields, fetches and decrypts
        the credentials, and returns them as a dictionary.
        
        Args:
            node_config: Node configuration that may contain credential_id
            user_id: User ID who owns the workflow (for credential access)
            
        Returns:
            Dictionary of credential_id → decrypted credential data
            Returns None if no credentials needed
        """
        if not user_id or not node_config.config:
            return None
        
        # Scan config for credential_id fields
        credential_ids = set()
        for key, value in node_config.config.items():
            # Match both "credential_id" and fields ending with "_credential_id"
            if (key == "credential_id" or key.endswith("_credential_id")) and value:
                try:
                    cred_id = int(value)
                    credential_ids.add(cred_id)
                    logger.info(f"Found credential reference: {key}={cred_id} in node {node_config.node_id}")
                except (ValueError, TypeError):
                    logger.warning(f"Invalid credential_id in node {node_config.node_id}: {value}")
        
        if not credential_ids:
            logger.debug(f"No credentials needed for node {node_config.node_id}")
            return None
        
        # Fetch and decrypt credentials
        try:
            from app.database.session import SessionLocal
            from app.services.credential_manager import CredentialManager
            
            credentials_dict = {}
            
            db = SessionLocal()
            try:
                credential_manager = CredentialManager(db)
                
                for cred_id in credential_ids:
                    cred_data = credential_manager.get_credential_data(cred_id, user_id)
                    if cred_data:
                        credentials_dict[cred_id] = cred_data
                        logger.info(
                            f"✅ Injected credential {cred_id} for node {node_config.node_id} "
                            f"(fields: {list(cred_data.keys())})"
                        )
                    else:
                        logger.warning(
                            f"❌ Credential {cred_id} not found for user {user_id} "
                            f"(node: {node_config.node_id})"
                        )
                
                if credentials_dict:
                    logger.info(f"🔐 Total credentials injected: {len(credentials_dict)}")
                    return credentials_dict
                else:
                    logger.warning(f"No valid credentials found for node {node_config.node_id}")
                    return None
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error injecting credentials: {e}", exc_info=True)
            return None
    
    async def _cancel_all_tasks(self):
        """Cancel all active node execution tasks."""
        for node_id, task in self.active_tasks.items():
            if not task.done():
                logger.warning(f"Cancelling node {node_id}")
                task.cancel()
        
        # Wait for all cancellations
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
    
    def pause(self):
        """
        Pause execution.
        
        Current running nodes will finish, but no new nodes will start
        until resume() is called.
        """
        if not self.paused:
            self.paused = True
            self.paused_at = get_local_now()
            self.pause_event.clear()  # Block new nodes from starting
            logger.info("Execution paused - current nodes will finish, new nodes blocked")
        else:
            logger.warning("Execution already paused")
    
    def resume(self):
        """
        Resume paused execution.
        
        Allows new nodes to start executing.
        """
        if self.paused:
            self.paused = False
            self.paused_at = None
            self.pause_event.set()  # Unblock execution
            logger.info("Execution resumed")
        else:
            logger.warning("Execution is not paused")
    
    def is_paused(self) -> bool:
        """Check if execution is currently paused."""
        return self.paused
    
    async def cancel_execution(self):
        """Request cancellation of workflow execution."""
        logger.warning("Execution cancellation requested")
        self.cancel_requested = True
        await self._cancel_all_tasks()
        
        # Pending nodes will be marked as STOPPED in the reactive loop
        logger.info("Cancellation complete - pending nodes will be marked as stopped in reactive loop")
    
    def get_progress(self) -> Dict[str, Any]:
        """
        Get current execution progress from the graph.
        
        Uses phase-based counting for accurate progress tracking:
        - Handles branches correctly (skipped nodes don't count toward 100%)
        - Handles loops correctly (nodes are reset for each iteration)
        
        Returns:
            Progress dictionary with:
            - total_nodes: Total nodes in workflow
            - effective_total: Nodes that will actually run (excludes skipped)
            - completed: Successfully completed nodes
            - failed: Failed nodes
            - skipped: Skipped nodes (branch not taken)
            - executing: Currently executing nodes
            - pending: Nodes waiting to execute
            - progress_percent: Percentage complete (0-100)
        """
        if self.graph:
            return self.graph.get_execution_progress()
        else:
            # Fallback if graph not available
            return {
                "total_nodes": 0,
                "effective_total": 0,
                "completed": 0,
                "failed": 0,
                "skipped": 0,
                "executing": 0,
                "pending": 0,
                "progress_percent": 0.0,
            }
