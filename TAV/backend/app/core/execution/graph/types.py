"""
Execution Graph Types

Data structures for representing workflow execution dependencies.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from enum import Enum


class NodeExecutionPhase(str, Enum):
    """Node execution lifecycle phases"""
    PENDING = "pending"          # Not yet ready to execute
    READY = "ready"              # Dependencies met, can execute
    EXECUTING = "executing"      # Currently executing
    COMPLETED = "completed"      # Successfully completed
    FAILED = "failed"            # Execution failed
    SKIPPED = "skipped"          # Skipped (e.g., decision branch not taken)
    STOPPED = "stopped"          # Stopped by user/system
    AWAITING_INTERACTION = "awaiting_interaction"  # Paused, waiting for human interaction


@dataclass
class NodeDependencies:
    """
    Tracks dependencies for a single node.
    
    This is the core data structure for reactive execution:
    - dependencies: nodes that must complete before this node can run
    - dependents: nodes that depend on this node
    - remaining_deps: countdown of unfinished dependencies (mutable during execution)
    """
    node_id: str
    
    # Static dependency information (never changes after initialization)
    dependencies: Set[str] = field(default_factory=set)      # Nodes this node depends on
    dependents: Set[str] = field(default_factory=set)        # Nodes that depend on this node
    original_dep_count: int = 0                              # Original dependency count
    
    # Loop-specific fields
    loop_back_dependencies: Set[str] = field(default_factory=set)  # Dependencies that are loop-back edges
    
    # Dynamic execution state (changes during execution)
    remaining_deps: int = 0                                  # Countdown: decrements as dependencies complete
    phase: NodeExecutionPhase = NodeExecutionPhase.PENDING
    
    # Port-specific connection information
    input_connections: List[Dict[str, Any]] = field(default_factory=list)
    output_connections: List[Dict[str, Any]] = field(default_factory=list)
    
    def is_ready(self) -> bool:
        """Check if node is ready to execute (all dependencies met)"""
        return self.remaining_deps == 0 and self.phase == NodeExecutionPhase.PENDING
    
    def is_source_node(self) -> bool:
        """Check if this is a source node (no dependencies)"""
        return self.original_dep_count == 0
    
    def mark_dependency_completed(self) -> None:
        """Decrement remaining dependencies counter"""
        if self.remaining_deps > 0:
            self.remaining_deps -= 1
    
    def reset(self) -> None:
        """Reset node to initial state for re-execution (used in loops)"""
        # For loop iterations after the first, restore loop-back dependencies
        if self.loop_back_dependencies:
            self.dependencies = self.dependencies | self.loop_back_dependencies
            self.original_dep_count = len(self.dependencies)
        
        self.remaining_deps = self.original_dep_count
        self.phase = NodeExecutionPhase.PENDING


@dataclass
class ExecutionGraph:
    """
    Complete execution dependency graph.
    
    This represents the entire workflow's dependency structure and tracks
    execution progress across all nodes.
    """
    workflow_id: str
    
    # Node dependency information
    nodes: Dict[str, NodeDependencies] = field(default_factory=dict)
    
    # Quick lookups
    source_nodes: Set[str] = field(default_factory=set)        # Nodes with no dependencies
    sink_nodes: Set[str] = field(default_factory=set)          # Nodes with no dependents
    
    # Special node tracking (for reactive execution)
    tools_memory_only_nodes: Set[str] = field(default_factory=set)  # Nodes only connected via tools/memory
    ui_nodes: Set[str] = field(default_factory=set)                 # UI nodes (human-in-loop)
    
    # Loop detection
    has_loops: bool = False                                          # Whether workflow contains loops
    loop_back_edges: List[List[str]] = field(default_factory=list)  # Detected loop cycles
    
    # Execution progress tracking
    completed_nodes: Set[str] = field(default_factory=set)
    skipped_nodes: Set[str] = field(default_factory=set)
    failed_nodes: Set[str] = field(default_factory=set)
    
    def get_node(self, node_id: str) -> Optional[NodeDependencies]:
        """Get node dependencies by ID"""
        return self.nodes.get(node_id)
    
    def get_ready_nodes(self) -> List[str]:
        """
        Get all nodes that are ready to execute.
        
        A node is ready if:
        - It has no remaining dependencies (remaining_deps == 0)
        - It's in PENDING phase
        """
        return [
            node_id 
            for node_id, deps in self.nodes.items() 
            if deps.is_ready()
        ]
    
    def mark_node_completed(self, node_id: str) -> List[str]:
        """
        Mark node as completed and return newly ready nodes.
        
        This is the core of reactive execution:
        1. Mark node as completed
        2. Decrement dependency counters for all dependent nodes
        3. Return list of nodes that just became ready
        
        Returns:
            List of node IDs that are now ready to execute
        """
        node = self.nodes.get(node_id)
        if not node:
            return []
        
        # Mark as completed
        node.phase = NodeExecutionPhase.COMPLETED
        self.completed_nodes.add(node_id)
        
        # Notify all dependent nodes
        newly_ready = []
        for dependent_id in node.dependents:
            dependent = self.nodes.get(dependent_id)
            if dependent:
                dependent.mark_dependency_completed()
                if dependent.is_ready():
                    newly_ready.append(dependent_id)
        
        return newly_ready
    
    def mark_node_failed(self, node_id: str) -> None:
        """Mark node as failed"""
        node = self.nodes.get(node_id)
        if node:
            node.phase = NodeExecutionPhase.FAILED
            self.failed_nodes.add(node_id)
    
    def mark_node_skipped(self, node_id: str) -> List[str]:
        """
        Mark node as skipped and propagate to dependents.
        
        Used for decision branches not taken.
        
        Returns:
            List of node IDs that were also skipped
        """
        node = self.nodes.get(node_id)
        if not node:
            return []
        
        # If already skipped, don't recurse (prevents infinite loops in cycles)
        if node_id in self.skipped_nodes:
            return []
        
        node.phase = NodeExecutionPhase.SKIPPED
        self.skipped_nodes.add(node_id)
        
        # Recursively skip all dependents
        skipped = []
        for dependent_id in node.dependents:
            if dependent_id not in self.completed_nodes and dependent_id not in self.skipped_nodes:
                skipped.append(dependent_id)  # Add the dependent itself
                skipped.extend(self.mark_node_skipped(dependent_id))  # Recursively skip its dependents
        
        return skipped
    
    def is_execution_complete(self) -> bool:
        """
        Check if workflow execution is complete.
        
        Execution is complete when all nodes are in a terminal state:
        COMPLETED, FAILED, SKIPPED, or STOPPED
        
        Note: AWAITING_INTERACTION is NOT a terminal state - workflow is paused.
        """
        for node in self.nodes.values():
            if node.phase not in (
                NodeExecutionPhase.COMPLETED,
                NodeExecutionPhase.FAILED,
                NodeExecutionPhase.SKIPPED,
                NodeExecutionPhase.STOPPED
            ):
                # If any node is in AWAITING_INTERACTION, workflow is paused (not complete)
                return False
        return True
    
    def get_execution_progress(self) -> Dict[str, Any]:
        """
        Get execution progress summary.
        
        Uses phase-based counting for accuracy. Progress is calculated as:
        - completed / effective_total * 100
        - where effective_total = total - skipped (nodes that will actually run)
        
        This correctly handles:
        - Branches: skipped nodes don't count toward 100%
        - Loops: use reset_nodes_for_loop() before each iteration
        """
        total = len(self.nodes)
        completed = len(self.completed_nodes)
        failed = len(self.failed_nodes)
        skipped = len(self.skipped_nodes)
        
        executing = sum(
            1 for node in self.nodes.values() 
            if node.phase == NodeExecutionPhase.EXECUTING
        )
        
        pending = sum(
            1 for node in self.nodes.values() 
            if node.phase == NodeExecutionPhase.PENDING
        )
        
        # Effective total = nodes that will actually execute (excludes skipped)
        effective_total = total - skipped
        
        # Calculate progress based on effective total
        # If all non-skipped nodes are done, we're at 100%
        if effective_total <= 0:
            progress_percent = 100.0 if skipped > 0 else 0.0
        else:
            finished = completed + failed
            progress_percent = round((finished / effective_total) * 100, 1)
        
        return {
            "total_nodes": total,
            "effective_total": effective_total,
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "executing": executing,
            "pending": pending,
            "progress_percent": progress_percent,
        }
    
    def reset_nodes_for_loop(self, node_ids: Set[str]) -> None:
        """
        Reset specific nodes for loop iteration.
        
        This properly clears both:
        - The node's phase (back to PENDING)
        - The tracking Sets (completed_nodes, skipped_nodes, failed_nodes)
        
        Args:
            node_ids: Set of node IDs to reset for the next loop iteration
        """
        for node_id in node_ids:
            # Reset the node's phase
            if node_id in self.nodes:
                self.nodes[node_id].reset()
            
            # Remove from tracking Sets (so they can be re-counted)
            self.completed_nodes.discard(node_id)
            self.skipped_nodes.discard(node_id)
            self.failed_nodes.discard(node_id)
    
    def reset(self) -> None:
        """Reset graph to initial state for re-execution"""
        for node in self.nodes.values():
            node.reset()
        
        self.completed_nodes.clear()
        self.skipped_nodes.clear()
        self.failed_nodes.clear()


@dataclass
class ConnectionInfo:
    """Information about a connection between nodes"""
    connection_id: str
    source_node_id: str
    source_port: str
    target_node_id: str
    target_port: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_special_port(self) -> bool:
        """Check if this connection uses a special port (tools/memory/ui)"""
        return self.target_port in ('tools', 'memory', 'ui')
