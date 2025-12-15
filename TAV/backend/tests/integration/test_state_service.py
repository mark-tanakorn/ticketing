"""
Integration tests for state management service.

Tests the complete state management flow including:
- Database operations
- CRUD operations
- State versioning
- Namespace isolation
"""
import pytest
import uuid
from app.core.services.state_service import StateService


class TestStateService:
    """Test state management service"""
    
    @pytest.fixture
    def workflow_id(self):
        """Generate a unique workflow ID for testing"""
        return str(uuid.uuid4())
    
    def test_set_and_get_state(self, workflow_id):
        """Test setting and retrieving state"""
        # Set state
        version = StateService.set_state(
            workflow_id=workflow_id,
            state_key="test_inventory",
            state_value={"coffee_beans": 100, "milk": 50},
            namespace="test"
        )
        
        assert version == 1, "First version should be 1"
        
        # Get state
        state = StateService.get_state(
            workflow_id=workflow_id,
            state_key="test_inventory",
            namespace="test"
        )
        
        assert state is not None
        assert state["coffee_beans"] == 100
        assert state["milk"] == 50
        
    def test_get_nonexistent_state_returns_default(self, workflow_id):
        """Test getting non-existent state returns default"""
        state = StateService.get_state(
            workflow_id=workflow_id,
            state_key="nonexistent",
            namespace="test",
            default={"default": True}
        )
        
        assert state == {"default": True}
        
    def test_update_state_merge(self, workflow_id):
        """Test updating state with merge operation"""
        # Set initial state
        StateService.set_state(
            workflow_id=workflow_id,
            state_key="test_merge",
            state_value={"a": 1, "b": 2},
            namespace="test"
        )
        
        # Update with merge
        new_value, version = StateService.update_state(
            workflow_id=workflow_id,
            state_key="test_merge",
            updates={"c": 3},
            namespace="test",
            operation="merge"
        )
        
        assert new_value == {"a": 1, "b": 2, "c": 3}
        assert version == 2, "Version should increment"
        
    def test_update_state_increment(self, workflow_id):
        """Test updating state with increment operation"""
        # Set initial numeric state
        StateService.set_state(
            workflow_id=workflow_id,
            state_key="test_cash",
            state_value=1000,
            namespace="test"
        )
        
        # Increment
        new_value, version = StateService.update_state(
            workflow_id=workflow_id,
            state_key="test_cash",
            updates=500,
            namespace="test",
            operation="increment"
        )
        
        assert new_value == 1500
        assert version == 2
        
    def test_state_versioning(self, workflow_id):
        """Test that state version increments on updates"""
        StateService.set_state(
            workflow_id=workflow_id,
            state_key="test_version",
            state_value={"count": 0},
            namespace="test"
        )
        
        # Update multiple times
        for i in range(3):
            version = StateService.set_state(
                workflow_id=workflow_id,
                state_key="test_version",
                state_value={"count": i + 1},
                namespace="test"
            )
            assert version == i + 2  # Version should increment
            
    def test_namespace_isolation(self, workflow_id):
        """Test that different namespaces are isolated"""
        # Set state in different namespaces
        StateService.set_state(
            workflow_id=workflow_id,
            state_key="shared_key",
            state_value={"namespace": "production"},
            namespace="production"
        )
        
        StateService.set_state(
            workflow_id=workflow_id,
            state_key="shared_key",
            state_value={"namespace": "simulation"},
            namespace="simulation"
        )
        
        # Retrieve from each namespace
        prod_state = StateService.get_state(
            workflow_id=workflow_id,
            state_key="shared_key",
            namespace="production"
        )
        
        sim_state = StateService.get_state(
            workflow_id=workflow_id,
            state_key="shared_key",
            namespace="simulation"
        )
        
        assert prod_state["namespace"] == "production"
        assert sim_state["namespace"] == "simulation"
        
    def test_list_states(self, workflow_id):
        """Test listing all states for a workflow"""
        # Create multiple states
        StateService.set_state(
            workflow_id=workflow_id,
            state_key="state_1",
            state_value={"data": 1},
            namespace="test"
        )
        
        StateService.set_state(
            workflow_id=workflow_id,
            state_key="state_2",
            state_value={"data": 2},
            namespace="test"
        )
        
        # List states
        states = StateService.list_states(
            workflow_id=workflow_id,
            namespace="test"
        )
        
        assert len(states) >= 2
        state_keys = [s['state_key'] for s in states]
        assert 'state_1' in state_keys
        assert 'state_2' in state_keys
        
    def test_delete_state(self, workflow_id):
        """Test deleting state"""
        # Create state
        StateService.set_state(
            workflow_id=workflow_id,
            state_key="to_delete",
            state_value={"data": "delete me"},
            namespace="test"
        )
        
        # Delete
        deleted = StateService.delete_state(
            workflow_id=workflow_id,
            state_key="to_delete",
            namespace="test"
        )
        
        assert deleted is True
        
        # Verify deleted
        state = StateService.get_state(
            workflow_id=workflow_id,
            state_key="to_delete",
            namespace="test"
        )
        
        assert state is None
        
    def test_state_expiration(self, workflow_id):
        """Test state with expiration time"""
        # Set state with expiration (1 second)
        version = StateService.set_state(
            workflow_id=workflow_id,
            state_key="expires",
            state_value={"temp": True},
            namespace="test",
            expires_in_seconds=1
        )
        
        assert version == 1
        
        # State should exist immediately
        state = StateService.get_state(
            workflow_id=workflow_id,
            state_key="expires",
            namespace="test"
        )
        assert state is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

