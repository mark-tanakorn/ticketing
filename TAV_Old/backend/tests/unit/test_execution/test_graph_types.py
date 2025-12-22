"""
Unit tests for ExecutionGraph and NodeDependencies

Tests reactive execution logic:
- Dependency tracking
- State transitions (pending -> ready -> executing -> completed)
- Progress calculation
- Completion propagation
"""

import pytest
from app.core.execution.graph.types import ExecutionGraph, NodeDependencies, NodeExecutionPhase


@pytest.fixture
def simple_graph():
    """Create a simple linear graph: A -> B -> C"""
    graph = ExecutionGraph(workflow_id="test-workflow")
    
    # Node A: Source (no deps)
    node_a = NodeDependencies(node_id="node-a")
    node_a.dependents.add("node-b")
    
    # Node B: Depends on A
    node_b = NodeDependencies(node_id="node-b")
    node_b.dependencies.add("node-a")
    node_b.dependents.add("node-c")
    node_b.original_dep_count = 1
    node_b.remaining_deps = 1
    
    # Node C: Depends on B
    node_c = NodeDependencies(node_id="node-c")
    node_c.dependencies.add("node-b")
    node_c.original_dep_count = 1
    node_c.remaining_deps = 1
    
    graph.nodes = {
        "node-a": node_a,
        "node-b": node_b,
        "node-c": node_c
    }
    graph.source_nodes.add("node-a")
    graph.sink_nodes.add("node-c")
    
    return graph


class TestNodeDependencies:
    """Test NodeDependencies state logic"""
    
    def test_is_ready_logic(self):
        """Test is_ready logic based on dependencies and phase"""
        node = NodeDependencies(node_id="test")
        node.original_dep_count = 2
        node.remaining_deps = 2
        
        # Not ready initially
        assert not node.is_ready()
        
        # One dependency met
        node.mark_dependency_completed()
        assert node.remaining_deps == 1
        assert not node.is_ready()
        
        # All dependencies met
        node.mark_dependency_completed()
        assert node.remaining_deps == 0
        assert node.is_ready()
        
        # Not ready if already executed
        node.phase = NodeExecutionPhase.COMPLETED
        assert not node.is_ready()
    
    def test_is_source_node(self):
        """Test is_source_node logic"""
        # Source node (0 deps)
        source = NodeDependencies(node_id="source")
        assert source.is_source_node()
        
        # Dependent node (1 dep)
        dependent = NodeDependencies(node_id="dependent")
        dependent.original_dep_count = 1
        assert not dependent.is_source_node()
    
    def test_reset(self):
        """Test reset logic"""
        node = NodeDependencies(node_id="test")
        node.original_dep_count = 2
        node.remaining_deps = 0
        node.phase = NodeExecutionPhase.COMPLETED
        
        node.reset()
        
        assert node.remaining_deps == 2
        assert node.phase == NodeExecutionPhase.PENDING


class TestExecutionGraphState:
    """Test ExecutionGraph state transitions"""
    
    def test_get_ready_nodes_initially(self, simple_graph):
        """Test getting ready nodes at start"""
        ready_nodes = simple_graph.get_ready_nodes()
        
        assert len(ready_nodes) == 1
        assert "node-a" in ready_nodes
        assert "node-b" not in ready_nodes
    
    def test_mark_node_completed_propagates_readiness(self, simple_graph):
        """Test that completing a node updates dependents"""
        # Complete A
        newly_ready = simple_graph.mark_node_completed("node-a")
        
        # Check A status
        assert simple_graph.nodes["node-a"].phase == NodeExecutionPhase.COMPLETED
        assert "node-a" in simple_graph.completed_nodes
        
        # Check B status (should be ready now)
        assert "node-b" in newly_ready
        assert simple_graph.nodes["node-b"].remaining_deps == 0
        assert simple_graph.nodes["node-b"].is_ready()
        
        # Check C status (still not ready)
        assert simple_graph.nodes["node-c"].remaining_deps == 1
        assert not simple_graph.nodes["node-c"].is_ready()
    
    def test_full_execution_flow(self, simple_graph):
        """Test full execution flow A -> B -> C"""
        # 1. Start: A is ready
        assert simple_graph.get_ready_nodes() == ["node-a"]
        
        # 2. Complete A -> B becomes ready
        ready = simple_graph.mark_node_completed("node-a")
        assert ready == ["node-b"]
        
        # 3. Complete B -> C becomes ready
        ready = simple_graph.mark_node_completed("node-b")
        assert ready == ["node-c"]
        
        # 4. Complete C -> Nothing new ready, execution done
        ready = simple_graph.mark_node_completed("node-c")
        assert ready == []
        assert simple_graph.is_execution_complete()
    
    def test_mark_node_failed(self, simple_graph):
        """Test marking node as failed"""
        simple_graph.mark_node_failed("node-a")
        
        assert simple_graph.nodes["node-a"].phase == NodeExecutionPhase.FAILED
        assert "node-a" in simple_graph.failed_nodes
        
        # Execution technically complete (all active paths ended)
        # Note: In reality, the executor would handle stopping or skipping dependents
        # but purely from a graph state perspective:
        assert not simple_graph.is_execution_complete()  # B and C are still PENDING
    
    def test_mark_node_skipped_propagates(self, simple_graph):
        """Test that skipping a node skips its dependents recursively"""
        # Skip A
        skipped = simple_graph.mark_node_skipped("node-a")
        
        # Should skip A, B, and C
        assert "node-b" in skipped
        assert "node-c" in skipped
        
        assert simple_graph.nodes["node-a"].phase == NodeExecutionPhase.SKIPPED
        assert simple_graph.nodes["node-b"].phase == NodeExecutionPhase.SKIPPED
        assert simple_graph.nodes["node-c"].phase == NodeExecutionPhase.SKIPPED
        
        assert "node-a" in simple_graph.skipped_nodes
        assert "node-b" in simple_graph.skipped_nodes
        assert "node-c" in simple_graph.skipped_nodes
        
        assert simple_graph.is_execution_complete()


class TestExecutionProgress:
    """Test progress calculation logic"""
    
    def test_progress_calculation(self, simple_graph):
        """Test progress percentage calculation"""
        # Initial state
        stats = simple_graph.get_execution_progress()
        assert stats["total_nodes"] == 3
        assert stats["effective_total"] == 3  # No skipped nodes
        assert stats["completed"] == 0
        assert stats["progress_percent"] == 0.0
        
        # Complete 1/3
        simple_graph.mark_node_completed("node-a")
        stats = simple_graph.get_execution_progress()
        assert stats["completed"] == 1
        assert stats["progress_percent"] == pytest.approx(33.3, 0.1)
        
        # Complete 2/3
        simple_graph.mark_node_completed("node-b")
        stats = simple_graph.get_execution_progress()
        assert stats["completed"] == 2
        assert stats["progress_percent"] == pytest.approx(66.6, 0.1)
        
        # Complete 3/3
        simple_graph.mark_node_completed("node-c")
        stats = simple_graph.get_execution_progress()
        assert stats["completed"] == 3
        assert stats["progress_percent"] == 100.0
    
    def test_progress_with_skipped_nodes(self, simple_graph):
        """Test that skipped nodes are excluded from effective_total"""
        # Skip node-b (and its dependent node-c)
        simple_graph.mark_node_skipped("node-b")
        
        stats = simple_graph.get_execution_progress()
        assert stats["total_nodes"] == 3
        assert stats["skipped"] == 2  # node-b and node-c
        assert stats["effective_total"] == 1  # Only node-a will run
        
        # Complete node-a -> should be 100% (1 out of 1 effective)
        simple_graph.mark_node_completed("node-a")
        stats = simple_graph.get_execution_progress()
        assert stats["completed"] == 1
        assert stats["effective_total"] == 1
        assert stats["progress_percent"] == 100.0
    
    def test_progress_all_skipped(self, simple_graph):
        """Test progress when all nodes are skipped"""
        simple_graph.mark_node_skipped("node-a")
        # This recursively skips node-b and node-c too
        
        stats = simple_graph.get_execution_progress()
        assert stats["skipped"] == 3
        assert stats["effective_total"] == 0
        assert stats["progress_percent"] == 100.0  # All skipped = done


class TestGraphReset:
    """Test graph reset logic"""
    
    def test_reset_graph(self, simple_graph):
        """Test resetting graph to initial state"""
        # Run graph to completion
        simple_graph.mark_node_completed("node-a")
        simple_graph.mark_node_completed("node-b")
        simple_graph.mark_node_completed("node-c")
        
        assert simple_graph.is_execution_complete()
        
        # Reset
        simple_graph.reset()
        
        # Verify reset state
        assert not simple_graph.completed_nodes
        assert not simple_graph.failed_nodes
        assert not simple_graph.skipped_nodes
        
        # Check node states
        assert simple_graph.nodes["node-a"].phase == NodeExecutionPhase.PENDING
        assert simple_graph.nodes["node-b"].remaining_deps == 1
        assert simple_graph.nodes["node-c"].remaining_deps == 1
        
        # Check ready nodes
        assert simple_graph.get_ready_nodes() == ["node-a"]
    
    def test_reset_nodes_for_loop(self, simple_graph):
        """Test resetting specific nodes for loop iteration"""
        # Complete all nodes
        simple_graph.mark_node_completed("node-a")
        simple_graph.mark_node_completed("node-b")
        simple_graph.mark_node_completed("node-c")
        
        assert len(simple_graph.completed_nodes) == 3
        
        # Reset only node-b and node-c (as if they're in a loop)
        loop_nodes = {"node-b", "node-c"}
        simple_graph.reset_nodes_for_loop(loop_nodes)
        
        # node-a should still be completed
        assert "node-a" in simple_graph.completed_nodes
        assert simple_graph.nodes["node-a"].phase == NodeExecutionPhase.COMPLETED
        
        # node-b and node-c should be reset
        assert "node-b" not in simple_graph.completed_nodes
        assert "node-c" not in simple_graph.completed_nodes
        assert simple_graph.nodes["node-b"].phase == NodeExecutionPhase.PENDING
        assert simple_graph.nodes["node-c"].phase == NodeExecutionPhase.PENDING
        
        # Progress should reflect partial completion
        stats = simple_graph.get_execution_progress()
        assert stats["completed"] == 1
        assert stats["pending"] == 2
    
    def test_reset_nodes_for_loop_clears_all_sets(self, simple_graph):
        """Test that reset_nodes_for_loop clears completed, failed, and skipped sets"""
        # Mark nodes in different states
        simple_graph.mark_node_completed("node-a")
        simple_graph.mark_node_failed("node-b")
        simple_graph.mark_node_skipped("node-c")
        
        assert "node-a" in simple_graph.completed_nodes
        assert "node-b" in simple_graph.failed_nodes
        assert "node-c" in simple_graph.skipped_nodes
        
        # Reset all nodes
        all_nodes = {"node-a", "node-b", "node-c"}
        simple_graph.reset_nodes_for_loop(all_nodes)
        
        # All sets should be cleared
        assert not simple_graph.completed_nodes
        assert not simple_graph.failed_nodes
        assert not simple_graph.skipped_nodes
        
        # All nodes should be PENDING
        for node_id in all_nodes:
            assert simple_graph.nodes[node_id].phase == NodeExecutionPhase.PENDING

