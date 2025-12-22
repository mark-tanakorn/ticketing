"""
Unit tests for GraphBuilder

Tests graph construction logic including:
- Dependency resolution
- Source/sink node identification
- Special node handling (tools/memory/ui)
- Graph validation
"""

import pytest
from unittest.mock import Mock

from app.core.execution.graph.builder import GraphBuilder, build_execution_graph
from app.core.execution.graph.types import ExecutionGraph, NodeExecutionPhase
from app.schemas.workflow import WorkflowDefinition, NodeConfiguration, Connection


def create_test_node(node_id: str, category: str = "processing", node_type: str = "test") -> NodeConfiguration:
    """Helper to create test node configuration"""
    return NodeConfiguration(
        node_id=node_id,
        node_type=node_type,
        name=f"Node {node_id}",
        category=category,
        config={}
    )


def create_test_connection(
    source_id: str,
    target_id: str,
    source_port: str = "output",
    target_port: str = "input"
) -> Connection:
    """Helper to create test connection"""
    return Connection(
        connection_id=f"{source_id}-{target_id}",
        source_node_id=source_id,
        source_port=source_port,
        target_node_id=target_id,
        target_port=target_port
    )


class TestGraphBuilderInitialization:
    """Test GraphBuilder initialization"""
    
    def test_init_stores_workflow(self):
        """Test that builder stores workflow definition"""
        # Arrange
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=[create_test_node("node-1")],
            connections=[]
        )
        
        # Act
        builder = GraphBuilder(workflow)
        
        # Assert
        assert builder.workflow == workflow
        assert "node-1" in builder.nodes_by_id
    
    def test_init_indexes_nodes_by_id(self):
        """Test that nodes are indexed by ID for quick lookup"""
        # Arrange
        nodes = [
            create_test_node("node-1"),
            create_test_node("node-2"),
            create_test_node("node-3")
        ]
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=nodes,
            connections=[]
        )
        
        # Act
        builder = GraphBuilder(workflow)
        
        # Assert
        assert len(builder.nodes_by_id) == 3
        assert all(node_id in builder.nodes_by_id for node_id in ["node-1", "node-2", "node-3"])


class TestSimpleGraphBuilding:
    """Test building simple graphs"""
    
    def test_build_single_node_graph(self):
        """Test building graph with single node"""
        # Arrange
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=[create_test_node("node-1")],
            connections=[]
        )
        builder = GraphBuilder(workflow)
        
        # Act
        graph = builder.build()
        
        # Assert
        assert isinstance(graph, ExecutionGraph)
        assert len(graph.nodes) == 1
        assert "node-1" in graph.nodes
        assert "node-1" in graph.source_nodes  # No dependencies = source
        assert "node-1" in graph.sink_nodes    # No dependents = sink
    
    def test_build_linear_graph(self):
        """Test building simple linear A -> B -> C graph"""
        # Arrange
        nodes = [
            create_test_node("node-a"),
            create_test_node("node-b"),
            create_test_node("node-c")
        ]
        connections = [
            create_test_connection("node-a", "node-b"),
            create_test_connection("node-b", "node-c")
        ]
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=nodes,
            connections=connections
        )
        builder = GraphBuilder(workflow)
        
        # Act
        graph = builder.build()
        
        # Assert
        assert len(graph.nodes) == 3
        
        # Check source/sink
        assert "node-a" in graph.source_nodes
        assert "node-c" in graph.sink_nodes
        assert len(graph.source_nodes) == 1
        assert len(graph.sink_nodes) == 1
        
        # Check dependencies
        assert len(graph.nodes["node-a"].dependencies) == 0
        assert len(graph.nodes["node-b"].dependencies) == 1
        assert "node-a" in graph.nodes["node-b"].dependencies
        assert len(graph.nodes["node-c"].dependencies) == 1
        assert "node-b" in graph.nodes["node-c"].dependencies
        
        # Check dependents
        assert "node-b" in graph.nodes["node-a"].dependents
        assert "node-c" in graph.nodes["node-b"].dependents
        assert len(graph.nodes["node-c"].dependents) == 0


class TestDependencyResolution:
    """Test dependency resolution logic"""
    
    def test_parallel_branches(self):
        """Test graph with parallel branches (A -> B, A -> C)"""
        # Arrange
        nodes = [
            create_test_node("node-a"),  # Source
            create_test_node("node-b"),  # Branch 1
            create_test_node("node-c")   # Branch 2
        ]
        connections = [
            create_test_connection("node-a", "node-b"),
            create_test_connection("node-a", "node-c")
        ]
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=nodes,
            connections=connections
        )
        builder = GraphBuilder(workflow)
        
        # Act
        graph = builder.build()
        
        # Assert
        assert "node-a" in graph.source_nodes
        assert len(graph.source_nodes) == 1
        
        # Both B and C depend on A
        assert "node-a" in graph.nodes["node-b"].dependencies
        assert "node-a" in graph.nodes["node-c"].dependencies
        
        # A has two dependents
        assert len(graph.nodes["node-a"].dependents) == 2
        assert "node-b" in graph.nodes["node-a"].dependents
        assert "node-c" in graph.nodes["node-a"].dependents
    
    def test_merge_branches(self):
        """Test graph with merging branches (A -> C, B -> C)"""
        # Arrange
        nodes = [
            create_test_node("node-a"),  # Source 1
            create_test_node("node-b"),  # Source 2
            create_test_node("node-c")   # Merge point
        ]
        connections = [
            create_test_connection("node-a", "node-c"),
            create_test_connection("node-b", "node-c")
        ]
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=nodes,
            connections=connections
        )
        builder = GraphBuilder(workflow)
        
        # Act
        graph = builder.build()
        
        # Assert
        # Two source nodes
        assert len(graph.source_nodes) == 2
        assert "node-a" in graph.source_nodes
        assert "node-b" in graph.source_nodes
        
        # C depends on both A and B
        assert len(graph.nodes["node-c"].dependencies) == 2
        assert "node-a" in graph.nodes["node-c"].dependencies
        assert "node-b" in graph.nodes["node-c"].dependencies
        
        # C has 2 remaining dependencies initially
        assert graph.nodes["node-c"].remaining_deps == 2
        assert graph.nodes["node-c"].original_dep_count == 2


class TestSpecialNodeHandling:
    """Test special node handling (tools/memory/ui)"""
    
    def test_tools_connection_does_not_create_dependency(self):
        """Test that tools connections don't create execution dependencies"""
        # Arrange
        nodes = [
            create_test_node("node-a", category="processing"),  # Tool provider
            create_test_node("node-b", category="ai")           # Agent with tools
        ]
        connections = [
            create_test_connection("node-a", "node-b", target_port="tools")
        ]
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=nodes,
            connections=connections
        )
        builder = GraphBuilder(workflow)
        
        # Act
        graph = builder.build()
        
        # Assert
        # B should NOT depend on A (tools connection)
        assert len(graph.nodes["node-b"].dependencies) == 0
        
        # Both should be source nodes (no regular dependencies)
        # UPDATE: Node A is a tool-only node, so it is EXCLUDED from source_nodes
        # Node B is a source node because it has no incoming regular dependencies
        assert "node-a" not in graph.source_nodes
        assert "node-b" in graph.source_nodes
        
        # Node A is correctly identified as tool-only
        assert "node-a" in graph.tools_memory_only_nodes
        
        # But connection should still be tracked
        assert len(graph.nodes["node-b"].input_connections) == 1
        assert graph.nodes["node-b"].input_connections[0]["target_port"] == "tools"
    
    def test_tools_only_node_identification(self):
        """Test that nodes with ONLY tools/memory outputs are identified"""
        # Arrange
        nodes = [
            create_test_node("node-a", category="processing"),  # Tool provider
            create_test_node("node-b", category="ai")           # Agent
        ]
        connections = [
            create_test_connection("node-a", "node-b", target_port="tools")
        ]
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=nodes,
            connections=connections
        )
        builder = GraphBuilder(workflow)
        
        # Act
        graph = builder.build()
        
        # Assert
        # Node A has only special outputs, should be marked as tools-only
        assert "node-a" in graph.tools_memory_only_nodes
        # Node B has no outputs, should NOT be marked
        assert "node-b" not in graph.tools_memory_only_nodes
    
    def test_ui_node_identification(self):
        """Test that UI nodes are identified by category"""
        # Arrange
        nodes = [
            create_test_node("node-a", category="input"),
            create_test_node("node-b", category="ui")
        ]
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=nodes,
            connections=[]
        )
        builder = GraphBuilder(workflow)
        
        # Act
        graph = builder.build()
        
        # Assert
        assert "node-b" in graph.ui_nodes
        assert "node-a" not in graph.ui_nodes
    
    def test_mixed_connections(self):
        """Test node with both regular and special connections"""
        # Arrange
        nodes = [
            create_test_node("node-a"),  # Source
            create_test_node("node-b"),  # Has regular + tools output
            create_test_node("node-c"),  # Regular dependent
            create_test_node("node-d")   # Tools dependent
        ]
        connections = [
            create_test_connection("node-a", "node-b"),  # Regular
            create_test_connection("node-b", "node-c"),  # Regular
            create_test_connection("node-b", "node-d", target_port="tools")  # Special
        ]
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=nodes,
            connections=connections
        )
        builder = GraphBuilder(workflow)
        
        # Act
        graph = builder.build()
        
        # Assert
        # Node B should NOT be tools-only (has regular output)
        assert "node-b" not in graph.tools_memory_only_nodes
        
        # C depends on B (regular connection)
        assert "node-b" in graph.nodes["node-c"].dependencies
        
        # D does NOT depend on B (tools connection)
        assert "node-b" not in graph.nodes["node-d"].dependencies


class TestGraphValidation:
    """Test graph validation logic"""
    
    def test_no_source_nodes_warning(self, caplog):
        """Test that warning is logged when no source nodes found"""
        # Arrange - circular dependency (shouldn't happen but tests validation)
        nodes = [
            create_test_node("node-a"),
            create_test_node("node-b")
        ]
        connections = [
            create_test_connection("node-a", "node-b"),
            create_test_connection("node-b", "node-a")  # Circular!
        ]
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=nodes,
            connections=connections
        )
        builder = GraphBuilder(workflow)
        
        # Act
        with caplog.at_level("WARNING"):
            graph = builder.build()
        
        # Assert
        assert len(graph.source_nodes) == 0
        assert "No source nodes found" in caplog.text


class TestDependencyCounters:
    """Test dependency counter initialization"""
    
    def test_remaining_deps_initialized_correctly(self):
        """Test that remaining_deps is set to match dependency count"""
        # Arrange
        nodes = [
            create_test_node("node-a"),
            create_test_node("node-b"),
            create_test_node("node-c")
        ]
        connections = [
            create_test_connection("node-a", "node-c"),
            create_test_connection("node-b", "node-c")
        ]
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=nodes,
            connections=connections
        )
        builder = GraphBuilder(workflow)
        
        # Act
        graph = builder.build()
        
        # Assert
        node_c = graph.nodes["node-c"]
        assert node_c.original_dep_count == 2
        assert node_c.remaining_deps == 2
        assert node_c.remaining_deps == node_c.original_dep_count


class TestConvenienceFunction:
    """Test convenience function"""
    
    def test_build_execution_graph_function(self):
        """Test that convenience function works correctly"""
        # Arrange
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=[create_test_node("node-1")],
            connections=[]
        )
        
        # Act
        graph = build_execution_graph(workflow)
        
        # Assert
        assert isinstance(graph, ExecutionGraph)
        assert len(graph.nodes) == 1


class TestConnectionTracking:
    """Test that connections are tracked for data flow"""
    
    def test_input_connections_tracked(self):
        """Test that input connections are tracked on target node"""
        # Arrange
        nodes = [
            create_test_node("node-a"),
            create_test_node("node-b")
        ]
        connections = [
            create_test_connection("node-a", "node-b")
        ]
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=nodes,
            connections=connections
        )
        builder = GraphBuilder(workflow)
        
        # Act
        graph = builder.build()
        
        # Assert
        assert len(graph.nodes["node-b"].input_connections) == 1
        conn = graph.nodes["node-b"].input_connections[0]
        assert conn["source_node_id"] == "node-a"
        assert conn["target_node_id"] == "node-b"
    
    def test_output_connections_tracked(self):
        """Test that output connections are tracked on source node"""
        # Arrange
        nodes = [
            create_test_node("node-a"),
            create_test_node("node-b")
        ]
        connections = [
            create_test_connection("node-a", "node-b")
        ]
        workflow = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test",
            nodes=nodes,
            connections=connections
        )
        builder = GraphBuilder(workflow)
        
        # Act
        graph = builder.build()
        
        # Assert
        assert len(graph.nodes["node-a"].output_connections) == 1
        conn = graph.nodes["node-a"].output_connections[0]
        assert conn["source_node_id"] == "node-a"
        assert conn["target_node_id"] == "node-b"
