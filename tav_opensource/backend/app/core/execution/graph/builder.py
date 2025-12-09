"""
Execution Graph Builder

Constructs dependency graphs from workflow definitions.
"""

import logging
from typing import Dict, List, Set
from collections import defaultdict

from app.schemas.workflow import WorkflowDefinition, Connection, NodeConfiguration
from app.core.execution.graph.types import (
    ExecutionGraph,
    NodeDependencies,
    ConnectionInfo,
    NodeExecutionPhase,
)

logger = logging.getLogger(__name__)


class GraphBuilder:
    """
    Builds execution dependency graphs from workflow definitions.
    
    This is responsible for:
    1. Analyzing connections to determine dependencies
    2. Identifying source nodes (no dependencies)
    3. Handling special ports (tools/memory/ui)
    4. Building the reactive dependency structure
    """
    
    def __init__(self, workflow: WorkflowDefinition):
        """
        Initialize graph builder.
        
        Args:
            workflow: Workflow definition to build graph from
        """
        self.workflow = workflow
        self.nodes_by_id: Dict[str, NodeConfiguration] = {
            node.node_id: node for node in workflow.nodes
        }
    
    def build(self) -> ExecutionGraph:
        """
        Build execution graph from workflow.
        
        Returns:
            ExecutionGraph ready for reactive execution
        """
        logger.info(f"🔨 Building execution graph for workflow: {self.workflow.workflow_id}")
        logger.info(f"📊 Workflow has {len(self.workflow.nodes)} nodes, {len(self.workflow.connections)} connections")
        
        # Initialize graph
        graph = ExecutionGraph(workflow_id=self.workflow.workflow_id)
        
        # Initialize node dependencies
        for node in self.workflow.nodes:
            graph.nodes[node.node_id] = NodeDependencies(
                node_id=node.node_id,
                dependencies=set(),
                dependents=set(),
                original_dep_count=0,
                remaining_deps=0,
                phase=NodeExecutionPhase.PENDING,
                input_connections=[],
                output_connections=[],
            )
        
        # Build dependency relationships from connections
        self._build_dependencies(graph)
        
        # Identify special nodes FIRST (must happen before source/sink identification)
        self._identify_special_nodes(graph)
        
        # Then identify source and sink nodes (can now use special node info)
        self._identify_source_nodes(graph)
        self._identify_sink_nodes(graph)
        
        # Validate graph
        self._validate_graph(graph)
        
        logger.info(
            f"✅ Graph built: {len(graph.source_nodes)} sources, "
            f"{len(graph.sink_nodes)} sinks, "
            f"{len(graph.tools_memory_only_nodes)} tool-only nodes"
        )
        if graph.tools_memory_only_nodes:
            logger.info(f"🤖 Tool-only nodes (will not auto-execute): {graph.tools_memory_only_nodes}")
        
        return graph
    
    def _build_dependencies(self, graph: ExecutionGraph) -> None:
        """
        Build dependency relationships from connections.
        
        This is the core logic that determines execution order:
        - Regular connections (signal/universal) create dependencies
        - Special connections (tools/memory/ui) do NOT create dependencies
        """
        # Track regular vs special connections
        regular_connections = []
        special_connections = []
        
        for conn in self.workflow.connections:
            conn_info = ConnectionInfo(
                connection_id=conn.connection_id,
                source_node_id=conn.source_node_id,
                source_port=conn.source_port,
                target_node_id=conn.target_node_id,
                target_port=conn.target_port,
                metadata=conn.metadata,
            )
            
            if conn_info.is_special_port():
                special_connections.append(conn_info)
            else:
                regular_connections.append(conn_info)
        
        logger.info(
            f"📡 Connections: {len(regular_connections)} regular, "
            f"{len(special_connections)} special (tools/memory/ui)"
        )
        
        # Process regular connections (create dependencies)
        for conn_info in regular_connections:
            source_id = conn_info.source_node_id
            target_id = conn_info.target_node_id
            
            # Add dependency: target depends on source
            graph.nodes[target_id].dependencies.add(source_id)
            graph.nodes[source_id].dependents.add(target_id)
            
            # Track connections for data flow
            graph.nodes[target_id].input_connections.append(conn_info.__dict__)
            graph.nodes[source_id].output_connections.append(conn_info.__dict__)
        
        # Process special connections (no dependencies, but track for data flow)
        for conn_info in special_connections:
            target_id = conn_info.target_node_id
            source_id = conn_info.source_node_id
            
            # Track connections but DON'T create dependencies
            graph.nodes[target_id].input_connections.append(conn_info.__dict__)
            graph.nodes[source_id].output_connections.append(conn_info.__dict__)
            
            logger.debug(
                f"🔌 Special connection: {source_id} → {target_id} "
                f"({conn_info.target_port}) - no dependency created"
            )
        
        # Set dependency counts
        for node_id, node_deps in graph.nodes.items():
            dep_count = len(node_deps.dependencies)
            node_deps.original_dep_count = dep_count
            node_deps.remaining_deps = dep_count
            
            if dep_count > 0:
                logger.debug(
                    f"📌 Node {node_id} depends on: {node_deps.dependencies}"
                )
    
    def _identify_source_nodes(self, graph: ExecutionGraph) -> None:
        """
        Identify source nodes (nodes with no dependencies).
        
        These are the nodes that can execute immediately when workflow starts.
        Typically trigger nodes.
        """
        for node_id, node_deps in graph.nodes.items():
            if node_deps.is_source_node():
                # Exclude special nodes from initial sources
                if node_id in graph.tools_memory_only_nodes:
                    logger.debug(f"🚫 Excluding tool node from sources: {node_id}")
                    continue
                    
                if node_id not in graph.ui_nodes:
                    graph.source_nodes.add(node_id)
                    logger.debug(f"🎯 Source node: {node_id}")
    
    def _identify_sink_nodes(self, graph: ExecutionGraph) -> None:
        """
        Identify sink nodes (nodes with no dependents).
        
        These are the final nodes in the workflow (e.g., export, response).
        """
        for node_id, node_deps in graph.nodes.items():
            if len(node_deps.dependents) == 0:
                graph.sink_nodes.add(node_id)
                logger.debug(f"🎬 Sink node: {node_id}")
    
    def _identify_special_nodes(self, graph: ExecutionGraph) -> None:
        """
        Identify special nodes that need special handling.
        
        1. Tools/Memory-only nodes: Nodes that ONLY have tools/memory connections
           - Should not be treated as source nodes
           - Execute reactively when their dependent needs them
        
        2. UI nodes: Human-in-the-loop nodes
           - Need special handling for pausing/resuming
        """
        # Identify tools/memory-only nodes
        for node_id, node_deps in graph.nodes.items():
            # Check if this node has ANY regular output connections
            has_regular_output = any(
                conn['target_port'] not in ('tools', 'memory', 'ui')
                for conn in node_deps.output_connections
            )
            
            # If only special outputs, mark as tools/memory-only
            # A node is considered a "Tool Node" if:
            # 1. It has NO regular outputs (it's not driving downstream nodes)
            # 2. It HAS at least one special output (it's attached to an agent/memory)
            if not has_regular_output and len(node_deps.output_connections) > 0:
                graph.tools_memory_only_nodes.add(node_id)
                logger.debug(f"🤖 Tools/memory-only node: {node_id}")
        
        # Identify UI nodes by category
        for node_id in graph.nodes:
            node_config = self.nodes_by_id.get(node_id)
            if node_config and node_config.category == "ui":
                graph.ui_nodes.add(node_id)
                logger.debug(f"🎨 UI node: {node_id}")
    
    def _validate_graph(self, graph: ExecutionGraph) -> None:
        """
        Validate graph structure.
        
        Checks:
        - At least one source node exists OR detects loop structures
        - Detect circular dependencies (loops)
        - All nodes are reachable from sources
        """
        # Detect cycles/loops
        cycles = self._detect_cycles(graph)
        
        if cycles:
            logger.info(f"🔁 Detected {len(cycles)} loop structure(s) in workflow")
            graph.has_loops = True
            graph.loop_back_edges = cycles
            
            # For workflows with loops, identify the loop entry point
            # Strategy: Find the node that triggered the loop (typically has 'trigger' input)
            # and is being triggered BY a decision node or loop control node
            for cycle in cycles:
                loop_nodes = set(cycle)
                
                # Find the "natural" entry point - look for nodes that:
                # 1. Are in the loop
                # 2. Have a 'trigger' input port
                # 3. Are connected FROM a decision/control node
                entry_point = None
                
                # First, try to find a node with node_type containing "loop" or "while"
                for node_id in loop_nodes:
                    node_config = self.nodes_by_id.get(node_id)
                    if node_config and ('loop' in node_config.node_type.lower() or 'while' in node_config.node_type.lower()):
                        entry_point = node_id
                        logger.info(f"🎯 Found loop control node as entry: {node_id} ({node_config.node_type})")
                        break
                
                # If no loop control node found, use the first node in the cycle
                if not entry_point:
                    entry_point = cycle[0]
                    logger.warning(f"⚠️ No loop control node found, using first node in cycle: {entry_point}")
                
                # Add ONLY the entry point as a source
                graph.source_nodes.add(entry_point)
                
                # CRITICAL: For the first iteration, the entry point needs to execute
                # even though it has dependencies (from the loop back edge).
                # We identify which dependency is the "loop back" dependency and
                # temporarily remove it for the first iteration.
                entry_deps = graph.nodes[entry_point].dependencies
                loop_back_deps = entry_deps & loop_nodes  # Dependencies that are in the loop
                
                if loop_back_deps:
                    logger.info(f"🔄 Entry point has {len(loop_back_deps)} loop-back dependencies, will ignore for first iteration")
                    # Store original dependencies for loop reset
                    graph.nodes[entry_point].loop_back_dependencies = loop_back_deps
                    # Remove loop-back dependencies for first iteration
                    graph.nodes[entry_point].dependencies = entry_deps - loop_back_deps
                    graph.nodes[entry_point].original_dep_count = len(graph.nodes[entry_point].dependencies)
                    graph.nodes[entry_point].remaining_deps = len(graph.nodes[entry_point].dependencies)
                    logger.info(f"   Adjusted entry point to have {graph.nodes[entry_point].original_dep_count} external dependencies")
        
        if not graph.source_nodes:
            logger.warning(
                "⚠️ No source nodes found! Workflow may not execute properly. "
                "Check if all nodes have dependencies."
            )
    
    def _detect_cycles(self, graph: ExecutionGraph) -> List[List[str]]:
        """
        Detect cycles in the dependency graph using DFS.
        
        Returns:
            List of cycles, where each cycle is a list of node IDs
        """
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node_id: str, path: List[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            # Visit all dependents (nodes that depend on this node)
            for dependent in graph.nodes[node_id].dependents:
                if dependent not in visited:
                    dfs(dependent, path.copy())
                elif dependent in rec_stack:
                    # Found a cycle!
                    cycle_start_idx = path.index(dependent)
                    cycle = path[cycle_start_idx:] + [dependent]
                    cycles.append(cycle)
            
            rec_stack.remove(node_id)
        
        # Run DFS from each node
        for node_id in graph.nodes:
            if node_id not in visited:
                dfs(node_id, [])
        
        return cycles


def build_execution_graph(workflow: WorkflowDefinition) -> ExecutionGraph:
    """
    Convenience function to build execution graph.
    
    Args:
        workflow: Workflow definition
    
    Returns:
        ExecutionGraph ready for execution
    """
    builder = GraphBuilder(workflow)
    return builder.build()
