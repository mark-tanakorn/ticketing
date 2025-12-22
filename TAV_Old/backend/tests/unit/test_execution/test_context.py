"""
Unit tests for Execution Context

Tests:
- ExecutionContext state management
- NodeExecutionResult tracking
- ExecutionProgress tracking
"""

import pytest
from datetime import datetime
from app.core.execution.context import ExecutionContext, NodeExecutionResult, ExecutionMode, ExecutionProgress


class TestExecutionProgress:
    """Test ExecutionProgress tracking"""
    
    def test_progress_initialization(self):
        """Test progress initializes with zeros"""
        progress = ExecutionProgress()
        
        assert progress.total_nodes_in_workflow == 0
        assert progress.pending == 0
        assert progress.running == 0
        assert progress.completed == 0
        assert progress.failed == 0
        assert progress.skipped == 0
    
    def test_node_started_updates_counts(self):
        """Test node_started decrements pending and increments running"""
        progress = ExecutionProgress()
        progress.pending = 5
        
        progress.node_started("node-1")
        assert progress.pending == 4
        assert progress.running == 1
        
        progress.node_started("node-2")
        assert progress.pending == 3
        assert progress.running == 2
    
    def test_node_completed_updates_counts(self):
        """Test node_completed decrements running and increments completed"""
        progress = ExecutionProgress()
        progress.running = 2
        
        progress.node_completed("node-1")
        
        assert progress.running == 1
        assert progress.completed == 1
    
    def test_node_failed_updates_counts(self):
        """Test node_failed decrements running and increments failed"""
        progress = ExecutionProgress()
        progress.running = 2
        
        progress.node_failed("node-1")
        
        assert progress.running == 1
        assert progress.failed == 1
    
    def test_nodes_skipped_updates_counts(self):
        """Test nodes_skipped decrements pending and increments skipped"""
        progress = ExecutionProgress()
        progress.pending = 5
        
        progress.nodes_skipped(3)
        assert progress.pending == 2
        assert progress.skipped == 3
    
    def test_get_progress_percentage(self):
        """Test calculating progress percentage"""
        progress = ExecutionProgress()
        progress.pending = 2
        progress.running = 1
        progress.completed = 5
        progress.failed = 2
        # in_scope = 2 + 1 + 5 + 2 = 10
        # finished = 5 + 2 = 7
        # progress = 7/10 = 70%
        
        percentage = progress.get_progress_percentage()
        assert percentage == 70.0
    
    def test_get_progress_percentage_zero_in_scope(self):
        """Test progress percentage with zero in-scope nodes"""
        progress = ExecutionProgress()
        progress.pending = 0
        progress.running = 0
        progress.completed = 0
        progress.failed = 0
        
        percentage = progress.get_progress_percentage()
        assert percentage == 0.0
    
    def test_to_dict_conversion(self):
        """Test converting progress to dictionary"""
        progress = ExecutionProgress()
        progress.total_nodes_in_workflow = 10
        progress.pending = 2
        progress.running = 1
        progress.completed = 5
        progress.failed = 1
        progress.skipped = 1
        
        data = progress.to_dict()
        
        assert isinstance(data, dict)
        assert data["total_nodes_in_workflow"] == 10
        assert data["pending"] == 2
        assert data["running"] == 1
        assert data["completed"] == 5
        assert data["failed"] == 1
        assert data["skipped"] == 1
        assert data["in_scope"] == 9  # 2+1+5+1
        assert "progress_percentage" in data


class TestNodeExecutionResult:
    """Test NodeExecutionResult dataclass"""
    
    def test_create_success_result(self):
        """Test creating a successful execution result"""
        result = NodeExecutionResult(
            node_id="test-node",
            success=True,
            outputs={"data": "value"},
            error=None,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=1500,
            retry_count=0
        )
        
        assert result.node_id == "test-node"
        assert result.success is True
        assert result.outputs == {"data": "value"}
        assert result.error is None
        assert result.retry_count == 0
    
    def test_create_failure_result(self):
        """Test creating a failed execution result"""
        result = NodeExecutionResult(
            node_id="test-node",
            success=False,
            outputs={},
            error="Execution failed",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            retry_count=3
        )
        
        assert result.success is False
        assert result.error == "Execution failed"
        assert result.retry_count == 3
    
    def test_result_to_dict_conversion(self):
        """Test converting result to dictionary"""
        started = datetime.now()
        completed = datetime.now()
        
        result = NodeExecutionResult(
            node_id="test-node",
            success=True,
            outputs={"key": "value"},
            started_at=started,
            completed_at=completed,
            duration_ms=2500
        )
        
        data = result.to_dict()
        
        assert isinstance(data, dict)
        assert data["node_id"] == "test-node"
        assert data["success"] is True
        assert data["outputs"] == {"key": "value"}
        assert data["duration_ms"] == 2500


class TestExecutionContextState:
    """Test ExecutionContext state management"""
    
    def test_context_initialization(self):
        """Test that context initializes correctly"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={"key": "value"},
            started_by="user-123",
            execution_mode=ExecutionMode.PARALLEL
        )
        
        assert context.workflow_id == "wf-1"
        assert context.execution_id == "exec-1"
        assert context.execution_source == "manual"
        assert context.trigger_data == {"key": "value"}
        assert context.started_by == "user-123"
        assert context.execution_mode == ExecutionMode.PARALLEL
    
    def test_context_has_variables_dict(self):
        """Test that context has variables dictionary"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={},
            execution_mode=ExecutionMode.PARALLEL
        )
        
        assert hasattr(context, "variables")
        assert isinstance(context.variables, dict)
    
    def test_context_has_node_results_dict(self):
        """Test that context has node results dictionary"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={},
            execution_mode=ExecutionMode.PARALLEL
        )
        
        assert hasattr(context, "node_results")
        assert isinstance(context.node_results, dict)
    
    def test_context_tracks_execution_log(self):
        """Test that context has execution log"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={},
            execution_mode=ExecutionMode.PARALLEL
        )
        
        assert hasattr(context, "execution_log")
        assert isinstance(context.execution_log, list)
    
    def test_start_execution(self):
        """Test start_execution sets started_at"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={},
            execution_mode=ExecutionMode.PARALLEL
        )
        
        context.start_execution()
        assert context.started_at is not None
    
    def test_complete_execution(self):
        """Test complete_execution sets completed_at"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={},
            execution_mode=ExecutionMode.PARALLEL
        )
        
        context.start_execution()
        context.complete_execution()
        assert context.completed_at is not None
    
    def test_get_duration_ms(self):
        """Test getting execution duration"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={},
            execution_mode=ExecutionMode.PARALLEL
        )
        
        context.start_execution()
        context.complete_execution()
        
        duration = context.get_duration_ms()
        assert duration is not None
        assert duration >= 0
    
    def test_set_and_get_node_outputs(self):
        """Test setting and getting node outputs"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={},
            execution_mode=ExecutionMode.PARALLEL
        )
        
        outputs = {"result": "test data"}
        context.set_node_outputs("node-1", outputs)
        
        retrieved = context.get_node_outputs("node-1")
        assert retrieved == outputs
    
    def test_get_node_outputs_missing(self):
        """Test getting outputs for non-existent node returns empty dict"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={},
            execution_mode=ExecutionMode.PARALLEL
        )
        
        retrieved = context.get_node_outputs("nonexistent")
        assert retrieved == {}
    
    def test_set_and_get_node_result(self):
        """Test setting and getting node execution result"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={},
            execution_mode=ExecutionMode.PARALLEL
        )
        
        result = NodeExecutionResult(
            node_id="node-1",
            success=True,
            outputs={"data": "test"}
        )
        
        context.set_node_result(result)
        retrieved = context.get_node_result("node-1")
        
        assert retrieved == result
    
    def test_get_node_result_missing(self):
        """Test getting result for non-existent node returns None"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={},
            execution_mode=ExecutionMode.PARALLEL
        )
        
        retrieved = context.get_node_result("nonexistent")
        assert retrieved is None
    
    def test_log_event(self):
        """Test logging events to execution log"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={},
            execution_mode=ExecutionMode.PARALLEL
        )
        
        context.log_event("node_started", {"node_id": "node-1"})
        context.log_event("node_completed", {"node_id": "node-1"})
        
        assert len(context.execution_log) == 2
        assert context.execution_log[0]["event_type"] == "node_started"
        assert context.execution_log[1]["event_type"] == "node_completed"
    
    def test_set_and_get_variable(self):
        """Test setting and getting workflow variables"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={},
            execution_mode=ExecutionMode.PARALLEL
        )
        
        context.set_variable("my_var", "test value")
        retrieved = context.get_variable("my_var")
        
        assert retrieved == "test value"
    
    def test_get_variable_with_default(self):
        """Test getting variable with default value"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={},
            execution_mode=ExecutionMode.PARALLEL
        )
        
        retrieved = context.get_variable("nonexistent", default="default_value")
        assert retrieved == "default_value"
    
    def test_get_summary(self):
        """Test getting execution summary"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={"key": "value"},
            started_by="user-123",
            execution_mode=ExecutionMode.PARALLEL
        )
        
        context.start_execution()
        context.complete_execution()
        
        summary = context.get_summary()
        
        assert isinstance(summary, dict)
        assert summary["workflow_id"] == "wf-1"
        assert summary["execution_id"] == "exec-1"
        assert summary["execution_mode"] == "parallel"
        assert "started_at" in summary
        assert "completed_at" in summary
        assert "total_nodes" in summary
        assert "successful_nodes" in summary
        assert "failed_nodes" in summary
    
    def test_to_dict_conversion(self):
        """Test converting context to dictionary"""
        context = ExecutionContext(
            workflow_id="wf-1",
            execution_id="exec-1",
            execution_source="manual",
            trigger_data={},
            started_by="user-123",
            execution_mode=ExecutionMode.PARALLEL
        )
        
        data = context.to_dict()
        
        assert isinstance(data, dict)
        assert data["workflow_id"] == "wf-1"
        assert data["execution_id"] == "exec-1"
        assert data["execution_source"] == "manual"
        assert data["started_by"] == "user-123"
        assert "variables" in data
        assert "node_outputs" in data
        assert "summary" in data

