"""
Execution Context

Tracks runtime state during workflow execution.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    """Execution mode"""
    SEQUENTIAL = "sequential"     # Execute nodes one at a time (for debugging)
    PARALLEL = "parallel"          # Execute independent nodes in parallel (default)
    DRY_RUN = "dry_run"           # Simulate execution without running nodes
    SIMULATION = "simulation"     # Simulation mode (accelerated time)


class TimeMode(str, Enum):
    """Time management mode for workflows"""
    REAL_TIME = "real_time"       # Standard real-world time
    VIRTUAL = "virtual"           # Simulated time (accelerated or decelerated)


@dataclass
class ExecutionProgress:
    """
    Real-time execution progress tracker.
    
    Tracks node execution state dynamically to calculate accurate progress
    even when branches are skipped.
    """
    total_nodes_in_workflow: int = 0  # Total nodes defined in workflow
    pending: int = 0                   # Nodes waiting to execute
    running: int = 0                   # Nodes currently executing
    completed: int = 0                 # Nodes successfully completed
    failed: int = 0                    # Nodes that failed
    skipped: int = 0                   # Nodes skipped due to branches
    
    def get_progress_percentage(self) -> float:
        """
        Calculate progress percentage based on nodes in execution scope.
        
        Returns:
            Progress percentage (0-100)
        """
        # Nodes that are "in scope" for this execution
        in_scope = self.completed + self.failed + self.running + self.pending
        
        if in_scope == 0:
            return 0.0
        
        # Progress is completed+failed out of in-scope
        # (failed nodes are "done" even though they failed)
        finished = self.completed + self.failed
        return round((finished / in_scope) * 100, 1)
    
    def node_started(self, node_id: str):
        """Mark node as started"""
        self.pending -= 1
        self.running += 1
    
    def node_completed(self, node_id: str):
        """Mark node as completed successfully"""
        self.running -= 1
        self.completed += 1
    
    def node_failed(self, node_id: str):
        """Mark node as failed"""
        self.running -= 1
        self.failed += 1
    
    def nodes_skipped(self, count: int):
        """Mark multiple nodes as skipped (branch not taken)"""
        self.pending -= count
        self.skipped += count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_nodes_in_workflow": self.total_nodes_in_workflow,
            "pending": self.pending,
            "running": self.running,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "progress_percentage": self.get_progress_percentage(),
            "in_scope": self.completed + self.failed + self.running + self.pending,
        }


@dataclass
class NodeExecutionResult:
    """Result from executing a single node"""
    node_id: str
    success: bool
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "node_id": self.node_id,
            "success": self.success,
            "outputs": self.outputs,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionContext:
    """
    Execution context - tracks runtime state during workflow execution.
    
    This is the mutable state object that's passed through the execution pipeline.
    Separate from ExecutionGraph (which tracks dependencies).
    """
    # Identification
    workflow_id: str
    execution_id: str
    
    # Execution configuration
    execution_source: str = "manual"  # How was this execution initiated
    trigger_data: Dict[str, Any] = field(default_factory=dict)  # Initial input data
    started_by: Optional[str] = None
    execution_mode: ExecutionMode = ExecutionMode.PARALLEL
    
    # Business Operations (NEW)
    business_mode: Optional[str] = None  # production, simulation, test, sandbox
    
    # Time Management (NEW)
    time_mode: TimeMode = TimeMode.REAL_TIME  # real_time or virtual
    time_scale: float = 1.0  # Time acceleration factor (1.0 = real-time, 10.0 = 10x faster)
    virtual_time: Optional[datetime] = None  # Current virtual timestamp (for simulation)
    
    # Loop/Iteration Tracking (NEW)
    loop_iteration: Optional[int] = None  # Current iteration number
    loop_max_iterations: Optional[int] = None  # Max iterations (if limited)
    
    # Business State Tracking (NEW)
    detected_anomalies: List[Dict[str, Any]] = field(default_factory=list)  # Anomalies detected
    performance_metrics: Dict[str, Any] = field(default_factory=dict)  # KPIs, metrics
    customer_interactions: List[Dict[str, Any]] = field(default_factory=list)  # Customer events
    customer_satisfaction_history: List[float] = field(default_factory=list)  # Satisfaction over time
    
    # Runtime state
    node_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # node_id → {port_name: value}
    node_results: Dict[str, NodeExecutionResult] = field(default_factory=dict)  # node_id → result
    execution_log: List[Dict[str, Any]] = field(default_factory=list)  # Chronological execution log
    
    # Workflow variables (can be modified during execution)
    variables: Dict[str, Any] = field(default_factory=dict)
    
    # Human-in-the-loop interactions (pending user input)
    pending_interactions: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # node_id → interaction data
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Global outputs (from sink nodes)
    final_outputs: Dict[str, Any] = field(default_factory=dict)
    
    # Error tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Progress tracking (real-time, in-memory only)
    progress: Optional[ExecutionProgress] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Frontend origin URL (auto-detected from request headers)
    # Used by nodes like Email Approval to generate correct review links
    frontend_origin: Optional[str] = None
    
    def advance_virtual_time(self, delta_seconds: float) -> None:
        """
        Advance virtual time (for simulations).
        
        Args:
            delta_seconds: Seconds to advance (in virtual time)
        """
        if self.time_mode != TimeMode.VIRTUAL:
            logger.warning("Cannot advance virtual time in REAL_TIME mode")
            return
        
        if self.virtual_time is None:
            self.virtual_time = self.started_at or datetime.now(timezone.utc)
        
        from datetime import timedelta
        self.virtual_time += timedelta(seconds=delta_seconds)
        
        logger.debug(f"⏰ Virtual time advanced by {delta_seconds}s to {self.virtual_time.isoformat()}")
    
    def get_current_time(self) -> datetime:
        """
        Get current time (virtual or real).
        
        Returns:
            Current timestamp based on time_mode
        """
        if self.time_mode == TimeMode.VIRTUAL and self.virtual_time:
            return self.virtual_time
        return datetime.now(timezone.utc)
    
    def record_anomaly(self, anomaly_type: str, description: str, severity: str, 
                       affected_metrics: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a detected anomaly/failure.
        
        Args:
            anomaly_type: Type of anomaly (stock_out, long_wait, crash, etc.)
            description: Human-readable description
            severity: Severity level (low, medium, high, critical)
            affected_metrics: Metrics at the time of anomaly
        """
        anomaly = {
            "timestamp": self.get_current_time().isoformat(),
            "iteration": self.loop_iteration,
            "type": anomaly_type,
            "description": description,
            "severity": severity,
            "affected_metrics": affected_metrics or {},
        }
        self.detected_anomalies.append(anomaly)
        logger.warning(f"🚨 Anomaly detected: {anomaly_type} - {description}")
    
    def update_metric(self, metric_name: str, value: Any) -> None:
        """
        Update a performance metric.
        
        Args:
            metric_name: Metric identifier
            value: Metric value
        """
        self.performance_metrics[metric_name] = value
        logger.debug(f"📊 Metric updated: {metric_name} = {value}")
    
    def record_customer_interaction(self, interaction_type: str, customer_id: str, 
                                   satisfaction: Optional[float] = None,
                                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a customer interaction.
        
        Args:
            interaction_type: Type of interaction (purchase, complaint, query, etc.)
            customer_id: Customer identifier
            satisfaction: Customer satisfaction score (0-10)
            metadata: Additional interaction data
        """
        interaction = {
            "timestamp": self.get_current_time().isoformat(),
            "iteration": self.loop_iteration,
            "type": interaction_type,
            "customer_id": customer_id,
            "satisfaction": satisfaction,
            "metadata": metadata or {},
        }
        self.customer_interactions.append(interaction)
        
        if satisfaction is not None:
            self.customer_satisfaction_history.append(satisfaction)
        
        logger.debug(f"👤 Customer interaction: {interaction_type} by {customer_id}")
    
    def start_execution(self) -> None:
        """Mark execution as started"""
        self.started_at = datetime.now(timezone.utc)
        self.log_event("execution_started", {
            "execution_source": self.execution_source,
            "execution_mode": self.execution_mode.value,
        })
    
    def complete_execution(self) -> None:
        """Mark execution as completed"""
        self.completed_at = datetime.now(timezone.utc)
        duration_ms = None
        if self.started_at and self.completed_at:
            duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        
        self.log_event("execution_completed", {
            "duration_ms": duration_ms,
            "total_nodes": len(self.node_results),
            "successful_nodes": sum(1 for r in self.node_results.values() if r.success),
            "failed_nodes": sum(1 for r in self.node_results.values() if not r.success),
        })
    
    def get_node_outputs(self, node_id: str) -> Dict[str, Any]:
        """
        Get outputs from a specific node.
        
        Args:
            node_id: Node ID to get outputs from
        
        Returns:
            Dictionary of port_name → value
        """
        return self.node_outputs.get(node_id, {})
    
    def set_node_outputs(self, node_id: str, outputs: Dict[str, Any]) -> None:
        """
        Set outputs for a specific node.
        
        Args:
            node_id: Node ID
            outputs: Dictionary of port_name → value
        """
        self.node_outputs[node_id] = outputs
        logger.debug(f"📤 Node {node_id} outputs: {list(outputs.keys())}")
    
    def set_node_result(self, result: NodeExecutionResult) -> None:
        """
        Store node execution result.
        
        Args:
            result: Node execution result
        """
        self.node_results[result.node_id] = result
        
        # Also store outputs for easy access
        if result.success:
            self.set_node_outputs(result.node_id, result.outputs)
        
        # Log execution
        self.log_event("node_executed", {
            "node_id": result.node_id,
            "success": result.success,
            "duration_ms": result.duration_ms,
            "error": result.error,
        })
        
        # Track errors
        if not result.success and result.error:
            self.errors.append({
                "node_id": result.node_id,
                "error": result.error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    
    def get_node_result(self, node_id: str) -> Optional[NodeExecutionResult]:
        """Get execution result for a node"""
        return self.node_results.get(node_id)
    
    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Log an execution event.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "data": data,
        }
        self.execution_log.append(event)
        logger.debug(f"📝 Event: {event_type} - {data}")
    
    def set_variable(self, name: str, value: Any) -> None:
        """Set a workflow variable"""
        self.variables[name] = value
        logger.debug(f"💾 Variable set: {name} = {value}")
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a workflow variable"""
        return self.variables.get(name, default)
    
    def get_duration_ms(self) -> Optional[int]:
        """Get execution duration in milliseconds"""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        elif self.started_at:
            # Still running
            now = datetime.now(timezone.utc)
            return int((now - self.started_at).total_seconds() * 1000)
        return None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary"""
        total_nodes = len(self.node_results)
        successful = sum(1 for r in self.node_results.values() if r.success)
        failed = sum(1 for r in self.node_results.values() if not r.success)
        
        summary = {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.get_duration_ms(),
            "execution_mode": self.execution_mode.value,
            "total_nodes": total_nodes,
            "successful_nodes": successful,
            "failed_nodes": failed,
            "total_errors": len(self.errors),
            "has_errors": len(self.errors) > 0,
        }
        
        # Add progress if available
        if self.progress:
            summary["progress"] = self.progress.to_dict()
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization"""
        return {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "execution_source": self.execution_source,
            "trigger_data": self.trigger_data,
            "started_by": self.started_by,
            "execution_mode": self.execution_mode.value,
            "node_outputs": self.node_outputs,
            "node_results": {
                node_id: result.to_dict()
                for node_id, result in self.node_results.items()
            },
            "execution_log": self.execution_log,
            "variables": self.variables,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "final_outputs": self.final_outputs,
            "errors": self.errors,
            "metadata": self.metadata,
            "summary": self.get_summary(),
        }
