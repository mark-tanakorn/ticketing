"""
Unit tests for Execution & Status API endpoints.

Tests:
- POST /workflows/{id}/pause - Pause execution
- POST /workflows/{id}/resume - Resume execution  
- POST /workflows/{id}/stop - Stop execution
- GET /workflows/{id}/status - Get workflow status
- GET /executions/{id} - Get execution status
- GET /workflows/{id}/executions - Get execution history
- GET /executions/{id}/detailed - Get detailed execution info

NOTE: These tests are currently skipped as they test workflow execution control
endpoints that require a fully integrated system. They should be run as
integration tests, not unit tests.
"""

import pytest

pytestmark = pytest.mark.skip(reason="These are integration tests, not unit tests. Skipping for now.")

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.models.workflow import Workflow
from app.database.models.execution import Execution
from app.database.models.user import User


class TestPauseExecution:
    """Test POST /workflows/{id}/pause - Pause execution."""
    
    def test_pause_running_execution(self, client: TestClient, test_db: Session, test_user: User):
        """Test pausing a running execution."""
        # Create workflow
        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        test_db.refresh(workflow)  # Ensure ID is populated
        
        # Create running execution
        execution = Execution(
            workflow_id=workflow.id,
            status="running",
            execution_source="manual",
            execution_mode="oneshot"
        )
        test_db.add(execution)
        test_db.commit()
        test_db.refresh(execution)  # Ensure ID is populated
        
        response = client.post(
            f"/api/v1/workflows/{workflow.id}/pause",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["status"] == "paused"
        assert execution.id in data["execution_ids"]
        assert "Paused" in data["message"]
        
        # Verify execution status in DB
        test_db.refresh(execution)
        assert execution.status == "paused"
    
    def test_pause_no_running_execution(self, client: TestClient, test_db: Session, test_user: User):
        """Test pausing when no execution is running."""
        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        response = client.post(
            f"/api/v1/workflows/{workflow.id}/pause",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 404
        assert "No running execution" in response.json()["detail"]
    
    def test_pause_nonexistent_workflow(self, client: TestClient, test_db: Session, test_user: User):
        """Test pausing non-existent workflow."""
        response = client.post(
            "/api/v1/workflows/non-existent-id/pause",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_pause_multiple_executions(self, client: TestClient, test_db: Session, test_user: User):
        """Test pausing multiple running executions."""
        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        # Create multiple running executions
        exec1 = Execution(
            workflow_id=workflow.id,
            status="running",
            execution_source="manual",
            execution_mode="oneshot"
        )
        exec2 = Execution(
            workflow_id=workflow.id,
            status="running",
            execution_source="manual",
            execution_mode="oneshot"
        )
        test_db.add_all([exec1, exec2])
        test_db.commit()
        
        response = client.post(
            f"/api/v1/workflows/{workflow.id}/pause",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "Paused 2" in data["message"]
        assert len(data["execution_ids"]) == 2


class TestResumeExecution:
    """Test POST /workflows/{id}/resume - Resume execution."""
    
    def test_resume_paused_execution(self, client: TestClient, test_db: Session, test_user: User):
        """Test resuming a paused execution."""
        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        # Create paused execution
        execution = Execution(
            workflow_id=workflow.id,
            status="paused",
            execution_source="manual",
            execution_mode="oneshot"
        )
        test_db.add(execution)
        test_db.commit()
        
        response = client.post(
            f"/api/v1/workflows/{workflow.id}/resume",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["status"] == "running"
        assert execution.id in data["execution_ids"]
        assert "Resumed" in data["message"]
        
        # Verify execution status in DB
        test_db.refresh(execution)
        assert execution.status == "running"
    
    def test_resume_no_paused_execution(self, client: TestClient, test_db: Session, test_user: User):
        """Test resuming when no execution is paused."""
        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        response = client.post(
            f"/api/v1/workflows/{workflow.id}/resume",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 404
        assert "No paused execution" in response.json()["detail"]


class TestStopExecution:
    """Test POST /workflows/{id}/stop - Stop execution."""
    
    def test_stop_running_execution(self, client: TestClient, test_db: Session, test_user: User):
        """Test stopping a running execution."""
        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            status="na",
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        # Create running execution
        execution = Execution(
            workflow_id=workflow.id,
            status="running",
            execution_source="manual",
            execution_mode="oneshot"
        )
        test_db.add(execution)
        test_db.commit()
        
        response = client.post(
            f"/api/v1/workflows/{workflow.id}/stop",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "stopped"
        assert "Stopped" in data["message"]
    
    def test_stop_idle_workflow(self, client: TestClient, test_db: Session, test_user: User):
        """Test stopping idle workflow (nothing to stop)."""
        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            status="na",
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        response = client.post(
            f"/api/v1/workflows/{workflow.id}/stop",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["mode"] == "idle"
        assert "already stopped" in data["message"].lower()


class TestWorkflowStatus:
    """Test GET /workflows/{id}/status - Get workflow status."""
    
    def test_get_workflow_status_with_execution(self, client: TestClient, test_db: Session, test_user: User):
        """Test getting workflow status with active execution."""
        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            status="running",
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        # Create execution
        execution = Execution(
            workflow_id=workflow.id,
            status="running",
            execution_source="manual",
            execution_mode="oneshot"
        )
        test_db.add(execution)
        test_db.commit()
        
        response = client.get(
            f"/api/v1/workflows/{workflow.id}/status",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["workflow_id"] == workflow.id
        assert data["status"] == "running"
        assert data["running_executions"] == 1
        assert data["last_execution"] is not None
        assert data["last_execution"]["execution_id"] == execution.id
    
    def test_get_workflow_status_idle(self, client: TestClient, test_db: Session, test_user: User):
        """Test getting status of idle workflow."""
        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            status="na",
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        response = client.get(
            f"/api/v1/workflows/{workflow.id}/status",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["workflow_id"] == workflow.id
        assert data["status"] == "na"
        assert data["running_executions"] == 0
        assert data["last_execution"] is None

    def test_execute_sets_workflow_status_running(self, client: TestClient, test_db: Session, test_user: User):
        """Starting execution should set workflow.status to 'running' in DB"""
        import time
        from app.database.models.execution import Execution

        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            status="na",
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()

        # Trigger execution via API (async background)
        response = client.post(
            f"/api/v1/workflows/{workflow.id}/execute",
            headers={"Authorization": f"Bearer {test_user.token}"},
            json={}
        )

        assert response.status_code == 202

        # Give background task a moment to update DB
        time.sleep(0.5)

        # Refresh workflow and assert status updated
        test_db.refresh(workflow)
        assert workflow.status == "running"


class TestExecutionHistory:
    """Test GET /workflows/{id}/executions - Get execution history."""
    
    def test_get_execution_history(self, client: TestClient, test_db: Session, test_user: User):
        """Test getting execution history."""
        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        # Create multiple executions
        for i in range(5):
            execution = Execution(
                workflow_id=workflow.id,
                status="completed" if i % 2 == 0 else "failed",
                execution_source="manual",
                execution_mode="oneshot"
            )
            test_db.add(execution)
        test_db.commit()
        
        response = client.get(
            f"/api/v1/workflows/{workflow.id}/executions",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["workflow_id"] == workflow.id
        assert data["total_count"] == 5
        assert len(data["executions"]) == 5
        assert data["has_more"] is False
    
    def test_get_execution_history_with_status_filter(self, client: TestClient, test_db: Session, test_user: User):
        """Test getting execution history with status filter."""
        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        # Create mixed status executions
        for status in ["completed", "failed", "completed", "stopped"]:
            execution = Execution(
                workflow_id=workflow.id,
                status=status,
                execution_source="manual",
                execution_mode="oneshot"
            )
            test_db.add(execution)
        test_db.commit()
        
        response = client.get(
            f"/api/v1/workflows/{workflow.id}/executions?status=completed",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_count"] == 2
        assert len(data["executions"]) == 2
        assert all(exec["status"] == "completed" for exec in data["executions"])
    
    def test_get_execution_history_pagination(self, client: TestClient, test_db: Session, test_user: User):
        """Test execution history pagination."""
        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        # Create many executions
        for i in range(30):
            execution = Execution(
                workflow_id=workflow.id,
                status="completed",
                execution_source="manual",
                execution_mode="oneshot"
            )
            test_db.add(execution)
        test_db.commit()
        
        # Get first page
        response = client.get(
            f"/api/v1/workflows/{workflow.id}/executions?limit=10&offset=0",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_count"] == 30
        assert len(data["executions"]) == 10
        assert data["has_more"] is True
        assert data["limit"] == 10
        assert data["offset"] == 0
        
        # Get second page
        response = client.get(
            f"/api/v1/workflows/{workflow.id}/executions?limit=10&offset=10",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["executions"]) == 10
        assert data["has_more"] is True


class TestDetailedExecutionStatus:
    """Test GET /executions/{id}/detailed - Get detailed execution info."""
    
    def test_get_detailed_execution_status(self, client: TestClient, test_db: Session, test_user: User):
        """Test getting detailed execution status."""
        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        # Create execution with detailed results
        execution = Execution(
            workflow_id=workflow.id,
            status="completed",
            execution_source="manual",
            execution_mode="oneshot",
            node_results={
                "node-1": {
                    "status": "completed",
                    "output": {"result": "success"},
                    "duration_ms": 150
                }
            },
            execution_log=[
                {"timestamp": "2024-01-01T00:00:00Z", "message": "Started"},
                {"timestamp": "2024-01-01T00:00:01Z", "message": "Completed"}
            ],
            final_outputs={"final_result": "success"},
            execution_metadata={"custom_field": "value"}
        )
        test_db.add(execution)
        test_db.commit()
        
        response = client.get(
            f"/api/v1/executions/{execution.id}/detailed",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["execution_id"] == execution.id
        assert data["workflow_id"] == workflow.id
        assert data["status"] == "completed"
        
        # Check progress info
        assert data["progress"]["total_nodes"] == 1
        assert data["progress"]["completed_nodes"] == 1
        assert data["progress"]["failed_nodes"] == 0
        assert data["progress"]["progress_percentage"] == 100.0
        
        # Check node results
        assert "node-1" in data["node_results"]
        assert data["node_results"]["node-1"]["status"] == "completed"
        
        # Check execution log
        assert len(data["execution_log"]) == 2
        assert data["execution_log"][0]["message"] == "Started"
        
        # Check outputs
        assert data["final_outputs"]["final_result"] == "success"
        
        # Check metadata
        assert data["execution_metadata"]["custom_field"] == "value"
    
    def test_get_detailed_execution_not_found(self, client: TestClient, test_db: Session, test_user: User):
        """Test getting detailed status for non-existent execution."""
        response = client.get(
            "/api/v1/executions/non-existent-id/detailed",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_detailed_status_with_failed_nodes(self, client: TestClient, test_db: Session, test_user: User):
        """Test detailed status with failed nodes."""
        workflow = Workflow(
            name="Test Workflow",
            workflow_data={
                "nodes": [
                    {"id": "node-1", "type": "test", "config": {}},
                    {"id": "node-2", "type": "test", "config": {}}
                ],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        # Create execution with mixed results
        execution = Execution(
            workflow_id=workflow.id,
            status="failed",
            execution_source="manual",
            execution_mode="oneshot",
            node_results={
                "node-1": {"status": "completed"},
                "node-2": {"status": "failed", "error": "Node failed"}
            },
            error_message="Workflow failed: node-2 failed"
        )
        test_db.add(execution)
        test_db.commit()
        
        response = client.get(
            f"/api/v1/executions/{execution.id}/detailed",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "failed"
        assert data["progress"]["total_nodes"] == 2
        assert data["progress"]["completed_nodes"] == 1
        assert data["progress"]["failed_nodes"] == 1
        assert data["progress"]["progress_percentage"] == 50.0
        assert data["error_message"] == "Workflow failed: node-2 failed"

