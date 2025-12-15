"""
Integration tests for node auto-discovery system.

Tests the complete node discovery flow including:
- Module scanning
- Node class detection
- Automatic registration
- Registry integration
"""
import pytest
from app.core.nodes.loader import discover_and_register_nodes
from app.core.nodes.registry import NodeRegistry


class TestNodeDiscovery:
    """Test node auto-discovery system"""
    
    def test_node_discovery_runs_successfully(self):
        """Test that node discovery completes without errors"""
        # Clear registry first
        NodeRegistry.clear()
        
        # Run discovery
        stats = discover_and_register_nodes()
        
        assert stats is not None
        assert 'modules_scanned' in stats
        assert 'nodes_found' in stats
        assert 'nodes_registered' in stats
        assert 'errors' in stats
        
    def test_discovers_builtin_nodes(self):
        """Test that built-in nodes are discovered"""
        # Clear and rediscover
        NodeRegistry.clear()
        stats = discover_and_register_nodes()
        
        # Should find a reasonable number of nodes
        assert stats['nodes_registered'] > 10, "Should discover at least 10 built-in nodes"
        
    def test_new_business_nodes_registered(self):
        """Test that new business simulation nodes are discovered"""
        # Ensure discovery has run
        if NodeRegistry.list_types() == []:
            discover_and_register_nodes()
        
        # Check our new nodes
        new_nodes = [
            'state_get', 'state_set', 'state_update',
            'loop_orchestrator',
            'metric_tracker', 'anomaly_detector', 'event_logger'
        ]
        
        registered = NodeRegistry.list_types()
        
        for node_type in new_nodes:
            assert node_type in registered, f"Node {node_type} should be registered"
            
            # Verify node class can be retrieved
            node_class = NodeRegistry.get(node_type)
            assert node_class is not None, f"Should be able to get {node_type} class"
            
            # Verify metadata exists
            metadata = NodeRegistry.get_metadata(node_type)
            assert metadata is not None, f"Should have metadata for {node_type}"
            assert 'display_name' in metadata
            assert 'category' in metadata
            
    def test_node_has_required_attributes(self):
        """Test that discovered nodes have required attributes"""
        if NodeRegistry.list_types() == []:
            discover_and_register_nodes()
        
        # Test state_get node as example
        node_class = NodeRegistry.get('state_get')
        
        assert hasattr(node_class, 'type')
        assert hasattr(node_class, 'display_name')
        assert hasattr(node_class, 'category')
        assert hasattr(node_class, 'description')
        assert hasattr(node_class, 'get_input_ports')
        assert hasattr(node_class, 'get_output_ports')
        assert hasattr(node_class, 'execute')
        
    def test_nodes_grouped_by_category(self):
        """Test that nodes can be grouped by category"""
        if NodeRegistry.list_types() == []:
            discover_and_register_nodes()
        
        all_nodes = NodeRegistry.list_all()
        
        # Group by category
        by_category = {}
        for node_type, metadata in all_nodes.items():
            category = metadata.get('category', 'uncategorized')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(node_type)
        
        # Should have multiple categories
        assert len(by_category) > 3, "Should have multiple node categories"
        
        # New categories should exist
        assert 'business' in by_category, "Should have business category"
        assert 'analytics' in by_category, "Should have analytics category"
        
    def test_discovery_handles_errors_gracefully(self):
        """Test that discovery continues even if some modules fail"""
        NodeRegistry.clear()
        stats = discover_and_register_nodes()
        
        # Should complete even with potential errors
        assert stats['nodes_registered'] > 0, "Should register some nodes even with errors"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

