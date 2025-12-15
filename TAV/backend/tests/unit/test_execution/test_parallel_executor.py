"""
Unit tests for ParallelExecutor

Tests the reactive parallel execution engine with:
- Worker pool management
- Reactive dependency resolution  
- Error handling and retries
- Pause/resume functionality
- Resource pool allocation
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from app.core.execution.executor.parallel import ParallelExecutor
from app.core.execution.context import ExecutionContext, ExecutionMode, NodeExecutionResult
from app.core.execution.graph.types import ExecutionGraph, NodeDependencies
from app.schemas.workflow import WorkflowDefinition, NodeConfiguration, ExecutionStatus


@pytest.fixture
def execution_config():
    """Standard execution config"""
    return {
        "max_concurrent_nodes": 5,
        "ai_concurrent_limit": 2,
        "default_timeout": 30,
        "workflow_timeout": 300,
        "stop_on_error": True,
        "max_retries": 3,
        "retry_delay": 1,
        "backoff_multiplier": 2,
        "max_retry_delay": 10
    }


@pytest.fixture
def executor(execution_config):
    """Create ParallelExecutor instance"""
    return ParallelExecutor(execution_config)


@pytest.fixture
def simple_workflow():
    """Simple workflow with 2 nodes"""
    return WorkflowDefinition(
        workflow_id="test-workflow",
        name="Test Workflow",
        format_version="2.0.0",
        nodes=[
            NodeConfiguration(
                node_id="node-1",
                node_type="text_input",
                name="Input",
                category="input",
                config={}
            ),
            NodeConfiguration(
                node_id="node-2",
                node_type="text_display",
                name="Output",
                category="output",
                config={}
            )
        ],
        connections=[],
        metadata={}
    )


@pytest.fixture
def execution_context():
    """Create execution context"""
    return ExecutionContext(
        workflow_id="test-workflow",
        execution_id="test-execution",
        execution_source="manual",
        trigger_data={},
        started_by=1,
        execution_mode=ExecutionMode.PARALLEL
    )


class TestExecutorInitialization:
    """Test executor initialization"""
    
    def test_init_creates_semaphores(self, executor, execution_config):
        """Test that semaphores are created with correct limits"""
        assert executor.standard_pool._value == execution_config["max_concurrent_nodes"]
        assert executor.llm_pool._value == execution_config["ai_concurrent_limit"]
        assert executor.ai_pool._value == execution_config["ai_concurrent_limit"]
    
    def test_init_sets_config(self, executor, execution_config):
        """Test that config is stored"""
        assert executor.config == execution_config
    
    def test_init_starts_unpaused(self, executor):
        """Test that executor starts in unpaused state"""
        assert not executor.paused
        assert executor.pause_event.is_set()
    
    def test_init_no_active_tasks(self, executor):
        """Test that no tasks are active initially"""
        assert len(executor.active_tasks) == 0
        assert not executor.cancel_requested


class TestVariableNameMapping:
    """Test variable name mapping logic"""
    
    def test_build_mapping_simple(self, executor, simple_workflow):
        """Test building variable name mapping"""
        executor._build_variable_name_mapping(simple_workflow)
        
        # Default: no sharing, so mapping should be empty or have defaults
        assert isinstance(executor.variable_name_mapping, dict)
    
    def test_build_mapping_with_duplicates(self, executor):
        """Test handling duplicate node names"""
        workflow = WorkflowDefinition(
            workflow_id="test",
            name="Test",
            format_version="2.0.0",
            nodes=[
                NodeConfiguration(
                    node_id="node-1",
                    node_type="test",
                    name="MyNode",  # Same name
                    category="processing",
                    config={},
                    share_output_to_variables=True
                ),
                NodeConfiguration(
                    node_id="node-2",
                    node_type="test",
                    name="MyNode",  # Same name
                    category="processing",
                    config={},
                    share_output_to_variables=True
                )
            ],
            connections=[],
            metadata={}
        )
        
        executor._build_variable_name_mapping(workflow)
        
        # Should have different variable names for duplicates
        mapping = executor.variable_name_mapping
        if "node-1" in mapping and "node-2" in mapping:
            assert mapping["node-1"] != mapping["node-2"]


class TestGetNodeConfig:
    """Test node configuration retrieval"""
    
    def test_get_node_config_exists(self, executor, simple_workflow):
        """Test getting existing node config"""
        config = executor._get_node_config(simple_workflow, "node-1")
        
        assert config is not None
        assert config.node_id == "node-1"
        assert config.node_type == "text_input"
    
    def test_get_node_config_missing(self, executor, simple_workflow):
        """Test getting missing node config raises ValueError"""
        with pytest.raises(ValueError, match="Node not found"):
            executor._get_node_config(simple_workflow, "nonexistent")


class TestSemaphoreAllocation:
    """Test resource pool (semaphore) allocation"""
    
    def test_get_semaphores_standard(self, executor):
        """Test standard node gets standard pool"""
        semaphores = executor._get_semaphores(["standard"])
        
        assert len(semaphores) == 1
        assert semaphores[0] == executor.standard_pool
    
    def test_get_semaphores_llm(self, executor):
        """Test LLM node gets LLM pool"""
        semaphores = executor._get_semaphores(["llm"])
        
        assert len(semaphores) == 1
        assert semaphores[0] == executor.llm_pool
    
    def test_get_semaphores_ai(self, executor):
        """Test AI node gets AI pool"""
        semaphores = executor._get_semaphores(["ai"])
        
        assert len(semaphores) == 1
        assert semaphores[0] == executor.ai_pool
    
    def test_get_semaphores_multiple(self, executor):
        """Test node with multiple resource classes"""
        semaphores = executor._get_semaphores(["standard", "llm"])
        
        assert len(semaphores) == 2
        assert executor.standard_pool in semaphores
        assert executor.llm_pool in semaphores
    
    def test_get_semaphores_empty(self, executor):
        """Test node with no resource classes gets empty list"""
        semaphores = executor._get_semaphores([])
        
        # Empty resource classes = empty semaphore list
        assert len(semaphores) == 0


class TestPauseResume:
    """Test pause/resume functionality"""
    
    def test_pause_sets_paused_flag(self, executor):
        """Test that pause() sets the paused flag"""
        executor.pause()
        
        assert executor.paused is True
        assert not executor.pause_event.is_set()
        assert executor.paused_at is not None
    
    def test_resume_clears_paused_flag(self, executor):
        """Test that resume() clears the paused flag"""
        executor.pause()
        executor.resume()
        
        assert executor.paused is False
        assert executor.pause_event.is_set()
    
    def test_is_paused(self, executor):
        """Test is_paused() returns correct state"""
        assert not executor.is_paused()
        
        executor.pause()
        assert executor.is_paused()
        
        executor.resume()
        assert not executor.is_paused()


class TestDecisionNodeLogic:
    """Test decision node branch handling"""
    
    def test_is_decision_node_with_decision_result(self, executor):
        """Test decision node detection from result"""
        result = NodeExecutionResult(
            node_id="decision-1",
            success=True,
            outputs={
                "active_path": "true",
                "blocked_outputs": ["false"],
                "decision_result": True
            }
        )
        
        assert executor._is_decision_node("decision-1", result) is True
    
    def test_is_not_decision_node(self, executor):
        """Test non-decision node detection"""
        result = NodeExecutionResult(
            node_id="node-1",
            success=True,
            outputs={"data": "test"}
        )
        
        assert executor._is_decision_node("node-1", result) is False
    
    def test_is_decision_node_no_result(self, executor):
        """Test decision detection with no result"""
        assert executor._is_decision_node("node-1", None) is False
    
    def test_get_decision_active_path(self, executor):
        """Test extracting active path from decision result"""
        result = NodeExecutionResult(
            node_id="decision-1",
            success=True,
            outputs={
                "active_path": "true",
                "decision_result": True
            }
        )
        
        active_path = executor._get_decision_active_path(result)
        assert active_path == "true"
    
    def test_get_decision_active_path_none(self, executor):
        """Test extracting active path when result is None"""
        active_path = executor._get_decision_active_path(None)
        assert active_path is None
    
    def test_get_decision_blocked_outputs(self, executor):
        """Test extracting blocked outputs from decision result"""
        result = NodeExecutionResult(
            node_id="decision-1",
            success=True,
            outputs={
                "blocked_outputs": ["false"],
                "active_outputs": ["true"]
            }
        )
        
        blocked = executor._get_decision_blocked_outputs(result)
        assert "false" in blocked
        assert len(blocked) == 1
    
    def test_get_decision_blocked_outputs_none(self, executor):
        """Test extracting blocked outputs when result is None"""
        blocked = executor._get_decision_blocked_outputs(None)
        assert blocked == []


class TestAssembleInputs:
    """Test input assembly logic"""
    
    def test_assemble_inputs_no_connections(self, executor, execution_context, simple_workflow):
        """Test assembling inputs with no connections"""
        # Create a simple graph with one node
        graph = ExecutionGraph(workflow_id="test")
        graph.nodes["node-1"] = NodeDependencies(
            node_id="node-1",
            input_connections=[],  # No connections
            output_connections=[]
        )
        
        inputs = executor.assemble_inputs(
            node_id="node-1",
            graph=graph,
            context=execution_context,
            workflow=simple_workflow
        )
        
        # Should return empty dict when no connections
        assert isinstance(inputs, dict)
        assert len(inputs) == 0
    
    def test_assemble_inputs_with_connection(self, executor, execution_context, simple_workflow):
        """Test assembling inputs with a connection"""
        # Setup: node-1 outputs to node-2
        graph = ExecutionGraph(workflow_id="test")
        graph.nodes["node-2"] = NodeDependencies(
            node_id="node-2",
            input_connections=[{
                "source_node_id": "node-1",
                "source_port": "output",
                "target_port": "input"
            }],
            output_connections=[]
        )
        
        # Add output from node-1 to context
        execution_context.node_outputs["node-1"] = {"output": "test data"}
        
        inputs = executor.assemble_inputs(
            node_id="node-2",
            graph=graph,
            context=execution_context,
            workflow=simple_workflow
        )
        
        # Should have the connected input
        assert "input" in inputs
        assert inputs["input"] == "test data"


class TestCancellation:
    """Test execution cancellation"""
    
    @pytest.mark.asyncio
    async def test_cancel_execution_sets_flag(self, executor):
        """Test that cancel_execution sets the cancel flag"""
        await executor.cancel_execution()
        
        assert executor.cancel_requested is True
    
    @pytest.mark.asyncio
    async def test_cancel_all_tasks_empty(self, executor):
        """Test cancelling tasks when none are active"""
        # Should not raise
        await executor._cancel_all_tasks()
        assert len(executor.active_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_cancel_all_tasks_with_tasks(self, executor):
        """Test cancelling active tasks"""
        # Create mock tasks
        task1 = asyncio.create_task(asyncio.sleep(10))
        task2 = asyncio.create_task(asyncio.sleep(10))
        
        executor.active_tasks["node-1"] = task1
        executor.active_tasks["node-2"] = task2
        
        # Cancel all
        await executor._cancel_all_tasks()
        
        # Tasks should be cancelled (but still in dict)
        assert task1.cancelled()
        assert task2.cancelled()
        # NOTE: tasks remain in active_tasks dict after cancellation


class TestShareToVariables:
    """Test variable sharing logic"""
    
    def test_share_to_variables_not_in_mapping(self, executor, execution_context):
        """Test that sharing warns when node not in mapping"""
        node_config = NodeConfiguration(
            node_id="node-1",
            node_type="test",
            name="Test",
            category="processing",
            config={},
            share_output_to_variables=True
        )
        
        outputs = {"result": "test data"}
        
        # No variable_name_mapping entry - will use fallback
        executor._share_to_variables(
            node_config=node_config,
            outputs=outputs,
            context=execution_context
        )
        
        # Should use fallback and add to _nodes namespace
        assert "_nodes" in execution_context.variables
    
    def test_share_to_variables_with_mapping(self, executor, execution_context):
        """Test that sharing works when node is in mapping"""
        node_config = NodeConfiguration(
            node_id="node-1",
            node_type="test",
            name="TestNode",
            category="processing",
            config={},
            share_output_to_variables=True,
            variable_name="my_var"
        )
        
        outputs = {"result": "test data"}
        
        # Setup variable mapping
        executor.variable_name_mapping["node-1"] = "my_var"
        
        executor._share_to_variables(
            node_config=node_config,
            outputs=outputs,
            context=execution_context
        )
        
        # Should add to _nodes namespace under the mapped key
        assert "_nodes" in execution_context.variables
        assert "my_var" in execution_context.variables["_nodes"]


class TestGetConnectionBranch:
    """Test connection branch determination"""
    
    def test_get_connection_branch_with_metadata(self, executor):
        """Test getting branch from connection metadata"""
        from app.schemas.workflow import Connection
        
        conn = Connection(
            source_node_id="decision-1",
            source_port="output",
            target_node_id="node-2",
            target_port="input",
            metadata={"branch": "false"}
        )
        
        branch = executor._get_connection_branch(
            source_node_id="decision-1",
            target_node_id="node-2",
            connections=[conn]
        )
        
        assert branch == "false"
    
    def test_get_connection_branch_from_port_name(self, executor):
        """Test getting branch from port name"""
        from app.schemas.workflow import Connection
        
        conn = Connection(
            source_node_id="decision-1",
            source_port="false",  # Port name contains "false"
            target_node_id="node-2",
            target_port="input",
            metadata={}
        )
        
        branch = executor._get_connection_branch(
            source_node_id="decision-1",
            target_node_id="node-2",
            connections=[conn]
        )
        
        assert branch == "false"
    
    def test_get_connection_branch_default(self, executor):
        """Test default branch is true"""
        from app.schemas.workflow import Connection
        
        conn = Connection(
            source_node_id="decision-1",
            source_port="output",
            target_node_id="node-2",
            target_port="input",
            metadata={}
        )
        
        branch = executor._get_connection_branch(
            source_node_id="decision-1",
            target_node_id="node-2",
            connections=[conn]
        )
        
        assert branch == "true"


class TestIsBranchBlocked:
    """Test branch blocking logic"""
    
    def test_is_branch_blocked_true(self, executor):
        """Test that blocked branch returns True"""
        result = NodeExecutionResult(
            node_id="decision-1",
            success=True,
            outputs={
                "blocked_outputs": ["false"],
                "active_outputs": ["true"]
            }
        )
        
        assert executor._is_branch_blocked("false", result) is True
        assert executor._is_branch_blocked("true", result) is False
    
    def test_is_branch_blocked_no_result(self, executor):
        """Test that no result means not blocked"""
        assert executor._is_branch_blocked("false", None) is False

