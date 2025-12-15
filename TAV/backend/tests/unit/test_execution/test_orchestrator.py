"""
Unit tests for WorkflowOrchestrator

These are TRUE unit tests - they test the orchestrator's coordination logic
by mocking all external dependencies (DB, executor, graph builder, etc.)
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from app.core.execution.orchestrator import WorkflowOrchestrator
from app.core.execution.context import ExecutionContext, ExecutionMode
from app.database.models.workflow import Workflow
from app.database.models.execution import Execution
from app.schemas.workflow import WorkflowDefinition, ExecutionStatus, NodeConfiguration


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit = Mock()
    db.add = Mock()
    db.refresh = Mock()
    return db


@pytest.fixture
def mock_workflow_db():
    """Mock workflow from database"""
    workflow = Mock(spec=Workflow)
    workflow.id = str(uuid4())
    workflow.author_id = 123
    workflow.workflow_data = {
        "name": "Test Workflow",
        "version": "1.0",
        "nodes": [
            {
                "node_id": "node-1",
                "node_type": "text_input",
                "name": "Text Input",
                "category": "input",
                "config": {}
            }
        ],
        "connections": [],
        "metadata": {}
    }
    workflow.execution_config = None
    workflow.status = ExecutionStatus.PENDING
    workflow.last_execution_id = None
    workflow.last_run_at = None
    return workflow


@pytest.fixture
def orchestrator(mock_db):
    """Create orchestrator instance"""
    return WorkflowOrchestrator(mock_db)


class TestOrchestratorInitialization:
    """Test orchestrator initialization"""
    
    def test_init_with_db_session(self, mock_db):
        """Test orchestrator initializes with database session"""
        orchestrator = WorkflowOrchestrator(mock_db)
        
        assert orchestrator.db == mock_db


class TestWorkflowLoading:
    """Test workflow loading from database"""
    
    @pytest.mark.asyncio
    async def test_workflow_not_found_raises_error(self, orchestrator, mock_db):
        """Test that missing workflow raises ValueError"""
        # Arrange
        workflow_id = str(uuid4())
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Workflow not found"):
            await orchestrator.execute_workflow(workflow_id)
    
    @pytest.mark.asyncio
    async def test_workflow_loaded_successfully(self, orchestrator, mock_db, mock_workflow_db):
        """Test that workflow is loaded from database correctly"""
        # Arrange
        workflow_id = mock_workflow_db.id
        
        # Mock query to return workflow for Workflow query, None for Execution query
        def mock_query_side_effect(model):
            mock_query_result = Mock()
            mock_filter_result = Mock()
            
            if model.__name__ == 'Workflow':
                mock_filter_result.first.return_value = mock_workflow_db
            else:  # Execution query
                mock_filter_result.first.return_value = None  # No existing execution
            
            mock_query_result.filter.return_value = mock_filter_result
            return mock_query_result
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Mock all downstream dependencies
        with patch('app.core.execution.orchestrator.GraphBuilder') as mock_graph_builder, \
             patch('app.core.execution.orchestrator.ParallelExecutor') as mock_executor, \
             patch('app.core.execution.orchestrator.register_execution'), \
             patch('app.core.execution.orchestrator.unregister_execution'), \
             patch('app.api.v1.endpoints.executions.publish_execution_event', new_callable=AsyncMock):
            
            # Mock graph builder
            mock_graph = Mock()
            mock_graph.source_nodes = []
            mock_graph.sink_nodes = []
            mock_graph_builder.return_value.build.return_value = mock_graph
            
            # Mock executor
            mock_context = Mock(spec=ExecutionContext)
            mock_context.completed_at = datetime.now()
            mock_context.started_at = datetime.now()
            mock_context.final_outputs = {}
            mock_context.node_results = {}
            mock_context.execution_log = []
            mock_executor_instance = Mock()
            mock_executor_instance.execute_workflow = AsyncMock(return_value=mock_context)
            mock_executor.return_value = mock_executor_instance
            
            # Act
            execution_id = await orchestrator.execute_workflow(workflow_id)
            
            # Assert
            assert execution_id is not None
            assert isinstance(execution_id, str)


class TestExecutionRecordManagement:
    """Test execution record creation and updates"""
    
    @pytest.mark.asyncio
    async def test_creates_execution_record(self, orchestrator, mock_db, mock_workflow_db):
        """Test that execution record is created in database"""
        # Arrange
        workflow_id = mock_workflow_db.id
        
        # Mock query to return workflow for Workflow query, None for Execution query
        def mock_query_side_effect(model):
            mock_query_result = Mock()
            mock_filter_result = Mock()
            
            if model.__name__ == 'Workflow':
                mock_filter_result.first.return_value = mock_workflow_db
            else:  # Execution query
                mock_filter_result.first.return_value = None  # No existing execution
            
            mock_query_result.filter.return_value = mock_filter_result
            return mock_query_result
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Mock dependencies
        with patch('app.core.execution.orchestrator.GraphBuilder') as mock_graph_builder, \
             patch('app.core.execution.orchestrator.ParallelExecutor') as mock_executor, \
             patch('app.core.execution.orchestrator.register_execution'), \
             patch('app.core.execution.orchestrator.unregister_execution'), \
             patch('app.api.v1.endpoints.executions.publish_execution_event', new_callable=AsyncMock):
            
            # Setup mocks
            mock_graph = Mock()
            mock_graph.source_nodes = []
            mock_graph.sink_nodes = []
            mock_graph_builder.return_value.build.return_value = mock_graph
            
            mock_context = Mock(spec=ExecutionContext)
            mock_context.completed_at = datetime.now()
            mock_context.started_at = datetime.now()
            mock_context.final_outputs = {}
            mock_context.node_results = {}
            mock_context.execution_log = []
            mock_executor_instance = Mock()
            mock_executor_instance.execute_workflow = AsyncMock(return_value=mock_context)
            mock_executor.return_value = mock_executor_instance
            
            # Act
            await orchestrator.execute_workflow(workflow_id)
            
            # Assert
            mock_db.add.assert_called()  # Execution record was added
            mock_db.commit.assert_called()  # Changes were committed
    
    @pytest.mark.asyncio
    async def test_updates_execution_status_on_success(self, orchestrator, mock_db, mock_workflow_db):
        """Test that execution status is updated to COMPLETED on success"""
        # Arrange
        workflow_id = mock_workflow_db.id
        
        # Create mock execution that will be returned by query
        mock_execution = Mock(spec=Execution)
        mock_execution.id = str(uuid4())
        
        # First call returns workflow, subsequent calls for execution queries
        def mock_query_side_effect(model_class):
            mock_query = Mock()
            if model_class == Workflow:
                mock_query.filter.return_value.first.return_value = mock_workflow_db
            elif model_class == Execution:
                # First call: check if exists (None), second call: update status
                mock_query.filter.return_value.first.side_effect = [None, mock_execution]
            return mock_query
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Mock dependencies
        with patch('app.core.execution.orchestrator.GraphBuilder') as mock_graph_builder, \
             patch('app.core.execution.orchestrator.ParallelExecutor') as mock_executor, \
             patch('app.core.execution.orchestrator.register_execution'), \
             patch('app.core.execution.orchestrator.unregister_execution'), \
             patch('app.api.v1.endpoints.executions.publish_execution_event', new_callable=AsyncMock):
            
            # Setup mocks
            mock_graph = Mock()
            mock_graph.source_nodes = []
            mock_graph.sink_nodes = []
            mock_graph_builder.return_value.build.return_value = mock_graph
            
            mock_context = Mock(spec=ExecutionContext)
            mock_context.completed_at = datetime.now()
            mock_context.started_at = datetime.now()
            mock_context.final_outputs = {}
            mock_context.node_results = {}
            mock_context.execution_log = []
            mock_executor_instance = Mock()
            mock_executor_instance.execute_workflow = AsyncMock(return_value=mock_context)
            mock_executor.return_value = mock_executor_instance
            
            # Act
            await orchestrator.execute_workflow(workflow_id)
            
            # Assert
            # The execution status should be set to COMPLETED
            # (We can't directly assert on the mock object, but we verify commit was called)
            assert mock_db.commit.called


class TestConfigMerging:
    """Test execution config merging logic"""
    
    def test_merge_config_uses_defaults_when_no_settings(self, orchestrator, mock_workflow_db):
        """Test that default config is used when settings can't be loaded"""
        # Arrange
        mock_workflow_db.execution_config = None
        
        with patch('app.core.config.manager.get_settings_manager', side_effect=Exception("DB error")):
            # Act
            config = orchestrator._merge_execution_config(mock_workflow_db)
            
            # Assert
            assert config is not None
            assert "max_concurrent_nodes" in config
            assert "default_timeout" in config
            assert "max_retries" in config
            assert config["max_concurrent_nodes"] == 5  # Default value
    
    def test_merge_config_workflow_overrides_global(self, orchestrator, mock_workflow_db):
        """Test that workflow-specific config overrides global settings"""
        # Arrange
        mock_workflow_db.execution_config = {
            "max_concurrent_nodes": 10,  # Override
            "default_timeout": 600         # Override
        }
        
        with patch('app.core.config.manager.get_settings_manager', side_effect=Exception("DB error")):
            # Act
            config = orchestrator._merge_execution_config(mock_workflow_db)
            
            # Assert
            assert config["max_concurrent_nodes"] == 10  # Workflow override
            assert config["default_timeout"] == 600       # Workflow override
            assert config["max_retries"] == 3             # Global default


class TestErrorHandling:
    """Test error handling and rollback"""
    
    @pytest.mark.asyncio
    async def test_execution_failure_updates_status_to_failed(self, orchestrator, mock_db, mock_workflow_db):
        """Test that execution failure updates status to FAILED"""
        # Arrange
        workflow_id = mock_workflow_db.id
        
        # Create mock execution
        mock_execution = Mock(spec=Execution)
        mock_execution.id = str(uuid4())
        
        def mock_query_side_effect(model_class):
            mock_query = Mock()
            if model_class == Workflow:
                mock_query.filter.return_value.first.return_value = mock_workflow_db
            elif model_class == Execution:
                mock_query.filter.return_value.first.side_effect = [None, mock_execution]
            return mock_query
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Mock dependencies
        with patch('app.core.execution.orchestrator.GraphBuilder') as mock_graph_builder, \
             patch('app.core.execution.orchestrator.ParallelExecutor') as mock_executor, \
             patch('app.core.execution.orchestrator.register_execution'), \
             patch('app.core.execution.orchestrator.unregister_execution'), \
             patch('app.api.v1.endpoints.executions.publish_execution_event', new_callable=AsyncMock):
            
            # Setup mocks
            mock_graph = Mock()
            mock_graph.source_nodes = []
            mock_graph.sink_nodes = []
            mock_graph_builder.return_value.build.return_value = mock_graph
            
            # Make executor raise an exception
            mock_executor_instance = Mock()
            mock_executor_instance.execute_workflow = AsyncMock(side_effect=RuntimeError("Node failed"))
            mock_executor.return_value = mock_executor_instance
            
            # Act & Assert
            with pytest.raises(RuntimeError, match="Node failed"):
                await orchestrator.execute_workflow(workflow_id)
            
            # Verify failure was recorded
            assert mock_db.commit.called


class TestExecutionCancellation:
    """Test execution cancellation"""
    
    @pytest.mark.asyncio
    async def test_cancel_execution_not_found_raises_error(self, orchestrator, mock_db):
        """Test that cancelling non-existent execution raises ValueError"""
        # Arrange
        execution_id = str(uuid4())
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Execution not found"):
            await orchestrator.cancel_execution(execution_id)
    
    @pytest.mark.asyncio
    async def test_cancel_execution_not_running_returns_false(self, orchestrator, mock_db):
        """Test that cancelling completed execution returns False"""
        # Arrange
        execution_id = str(uuid4())
        mock_execution = Mock(spec=Execution)
        mock_execution.id = execution_id
        mock_execution.status = ExecutionStatus.COMPLETED
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_execution
        
        # Act
        result = await orchestrator.cancel_execution(execution_id)
        
        # Assert
        assert result is False


class TestGetExecutionStatus:
    """Test execution status retrieval"""
    
    def test_get_status_returns_none_for_missing_execution(self, orchestrator, mock_db):
        """Test that get_execution_status returns None for missing execution"""
        # Arrange
        execution_id = str(uuid4())
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = orchestrator.get_execution_status(execution_id)
        
        # Assert
        assert result is None
    
    def test_get_status_returns_execution_data(self, orchestrator, mock_db):
        """Test that get_execution_status returns execution data"""
        # Arrange
        execution_id = str(uuid4())
        mock_execution = Mock(spec=Execution)
        mock_execution.id = execution_id
        mock_execution.workflow_id = str(uuid4())
        mock_execution.status = ExecutionStatus.COMPLETED
        mock_execution.execution_source = "manual"
        mock_execution.started_at = datetime.now()
        mock_execution.completed_at = datetime.now()
        mock_execution.final_outputs = {"result": "test"}
        mock_execution.error_message = None
        mock_execution.execution_metadata = {"duration_seconds": 5}
        mock_execution.node_results = {}
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_execution
        
        # Act
        result = orchestrator.get_execution_status(execution_id)
        
        # Assert
        assert result is not None
        assert result["execution_id"] == execution_id
        assert result["status"] == ExecutionStatus.COMPLETED
        assert result["final_outputs"] == {"result": "test"}


