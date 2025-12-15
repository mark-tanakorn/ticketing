"""
Unit tests for Workflow CRUD API endpoints.

Tests:
- POST /workflows - Create workflow
- GET /workflows - List workflows
- GET /workflows/{id} - Load single workflow
- PUT /workflows/{id} - Update workflow
- DELETE /workflows/{id} - Delete workflow
- PATCH /workflows/{id}/name - Rename workflow
- POST /workflows/{id}/duplicate - Duplicate workflow
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.models.workflow import Workflow
from app.database.models.user import User


class TestWorkflowCreate:
    """Test POST /workflows - Create workflow."""
    
    def test_create_minimal_workflow(self, client: TestClient, test_db: Session, test_user: User):
        """Test creating a workflow with minimal data."""
        workflow_data = {
            "name": "Test Workflow",
            "nodes": [
                {
                    "id": "node-1",
                    "type": "manual_trigger",
                    "config": {}
                }
            ],
            "connections": []
        }
        
        response = client.post(
            "/api/v1/workflows",
            json=workflow_data,
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["name"] == "Test Workflow"
        assert data["version"] == "1.0"
        assert data["status"] == "na"
        assert data["is_active"] is True
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["id"] == "node-1"
    
    def test_create_full_workflow(self, client: TestClient, test_db: Session, test_user: User):
        """Test creating a workflow with all fields."""
        workflow_data = {
            "name": "Full Workflow",
            "description": "Test description",
            "version": "2.0",
            "nodes": [
                {
                    "id": "node-1",
                    "type": "manual_trigger",
                    "config": {}
                },
                {
                    "id": "node-2",
                    "type": "http_request",
                    "config": {
                        "url": "https://api.example.com",
                        "method": "GET"
                    }
                }
            ],
            "connections": [
                {
                    "sourceNodeId": "node-1",
                    "sourcePortId": "output",
                    "targetNodeId": "node-2",
                    "targetPortId": "input"
                }
            ],
            "tags": ["test", "demo"],
            "execution_config": {
                "max_parallel_executions": 5
            },
            "metadata": {
                "author": "Test User",
                "category": "demo"
            }
        }
        
        response = client.post(
            "/api/v1/workflows",
            json=workflow_data,
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["name"] == "Full Workflow"
        assert data["description"] == "Test description"
        assert data["version"] == "2.0"
        assert len(data["nodes"]) == 2
        assert len(data["connections"]) == 1
        assert data["tags"] == ["test", "demo"]
        assert data["execution_config"]["max_parallel_executions"] == 5
        assert data["metadata"]["category"] == "demo"
    
    def test_create_workflow_encrypts_sensitive_fields(self, client: TestClient, test_db: Session, test_user: User):
        """Test that sensitive fields are encrypted on creation."""
        workflow_data = {
            "name": "Secure Workflow",
            "nodes": [
                {
                    "id": "node-1",
                    "type": "http_request",
                    "config": {
                        "url": "https://api.example.com",
                        "api_key": "my-secret-key-12345",
                        "password": "super-secret-password"
                    }
                }
            ],
            "connections": []
        }
        
        response = client.post(
            "/api/v1/workflows",
            json=workflow_data,
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Response should contain decrypted values
        node_config = data["nodes"][0]["config"]
        assert node_config["api_key"] == "my-secret-key-12345"
        assert node_config["password"] == "super-secret-password"
        
        # Database should contain encrypted values
        workflow = test_db.query(Workflow).filter_by(id=data["id"]).first()
        stored_config = workflow.workflow_data["nodes"][0]["config"]
        
        # Encrypted values start with 'gAAAAA' (Fernet format)
        assert stored_config["api_key"].startswith("gAAAAA")
        assert stored_config["password"].startswith("gAAAAA")
        assert stored_config["api_key"] != "my-secret-key-12345"
        assert stored_config["password"] != "super-secret-password"
    
    def test_create_workflow_validates_structure(self, client: TestClient, test_db: Session, test_user: User):
        """Test that workflow structure is validated."""
        # Empty nodes
        response = client.post(
            "/api/v1/workflows",
            json={"name": "Invalid", "nodes": [], "connections": []},
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        assert response.status_code == 400
        assert "at least one node" in response.json()["detail"].lower()
        
        # Duplicate node IDs
        response = client.post(
            "/api/v1/workflows",
            json={
                "name": "Invalid",
                "nodes": [
                    {"id": "node-1", "type": "test"},
                    {"id": "node-1", "type": "test"}
                ],
                "connections": []
            },
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        assert response.status_code == 400
        assert "duplicate" in response.json()["detail"].lower()
        
        # Invalid connection (non-existent source)
        response = client.post(
            "/api/v1/workflows",
            json={
                "name": "Invalid",
                "nodes": [{"id": "node-1", "type": "test"}],
                "connections": [
                    {"sourceNodeId": "non-existent", "targetNodeId": "node-1"}
                ]
            },
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        assert response.status_code == 400
        assert "non-existent" in response.json()["detail"].lower()


class TestWorkflowLoad:
    """Test GET /workflows/{id} - Load single workflow."""
    
    def test_load_workflow_success(self, client: TestClient, test_db: Session, test_user: User):
        """Test loading an existing workflow."""
        # Create workflow directly in DB
        workflow = Workflow(
            name="Test Workflow",
            description="Test description",
            version="1.0",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        response = client.get(
            f"/api/v1/workflows/{workflow.id}",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == workflow.id
        assert data["name"] == "Test Workflow"
        assert data["description"] == "Test description"
        assert len(data["nodes"]) == 1
    
    def test_load_workflow_decrypts_secrets(self, client: TestClient, test_db: Session, test_user: User):
        """Test that encrypted fields are decrypted when loading."""
        from app.security.encryption import encrypt_value
        
        # Create workflow with encrypted field
        workflow = Workflow(
            name="Secure Workflow",
            workflow_data={
                "nodes": [{
                    "id": "node-1",
                    "type": "test",
                    "config": {
                        "api_key": encrypt_value("secret-key-12345")
                    }
                }],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        response = client.get(
            f"/api/v1/workflows/{workflow.id}",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be decrypted
        assert data["nodes"][0]["config"]["api_key"] == "secret-key-12345"
    
    def test_load_workflow_not_found(self, client: TestClient, test_db: Session, test_user: User):
        """Test loading non-existent workflow."""
        response = client.get(
            "/api/v1/workflows/non-existent-id",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestWorkflowUpdate:
    """Test PUT /workflows/{id} - Update workflow."""
    
    def test_update_workflow_name(self, client: TestClient, test_db: Session, test_user: User):
        """Test updating workflow name only."""
        workflow = Workflow(
            name="Original Name",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        response = client.put(
            f"/api/v1/workflows/{workflow.id}",
            json={"name": "Updated Name"},
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Updated Name"
        # Nodes should remain unchanged
        assert len(data["nodes"]) == 1
    
    def test_update_workflow_nodes(self, client: TestClient, test_db: Session, test_user: User):
        """Test updating workflow nodes."""
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
        
        response = client.put(
            f"/api/v1/workflows/{workflow.id}",
            json={
                "nodes": [
                    {"id": "node-1", "type": "test", "config": {}},
                    {"id": "node-2", "type": "test", "config": {}}
                ],
                "connections": []
            },
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["nodes"]) == 2
    
    def test_update_workflow_validates_structure(self, client: TestClient, test_db: Session, test_user: User):
        """Test that updates are validated."""
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
        
        # Try to update with invalid structure (empty nodes)
        response = client.put(
            f"/api/v1/workflows/{workflow.id}",
            json={"nodes": [], "connections": []},
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 400
        assert "at least one node" in response.json()["detail"].lower()


class TestWorkflowDelete:
    """Test DELETE /workflows/{id} - Delete workflow."""
    
    def test_delete_workflow_success(self, client: TestClient, test_db: Session, test_user: User):
        """Test deleting an existing workflow."""
        workflow = Workflow(
            name="To Delete",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        workflow_id = workflow.id
        
        response = client.delete(
            f"/api/v1/workflows/{workflow_id}",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 204
        
        # Verify it's deleted
        deleted = test_db.query(Workflow).filter_by(id=workflow_id).first()
        assert deleted is None
    
    def test_delete_workflow_not_found(self, client: TestClient, test_db: Session, test_user: User):
        """Test deleting non-existent workflow."""
        response = client.delete(
            "/api/v1/workflows/non-existent-id",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 404


class TestWorkflowRename:
    """Test PATCH /workflows/{id}/name - Quick rename."""
    
    def test_rename_workflow(self, client: TestClient, test_db: Session, test_user: User):
        """Test quick rename endpoint."""
        workflow = Workflow(
            name="Original Name",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {}}],
                "connections": [],
                "metadata": {}
            },
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        
        response = client.patch(
            f"/api/v1/workflows/{workflow.id}/name",
            json={"name": "New Name"},
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "New Name"
        assert len(data["nodes"]) == 1  # Other data unchanged


class TestWorkflowDuplicate:
    """Test POST /workflows/{id}/duplicate - Duplicate workflow."""
    
    def test_duplicate_workflow(self, client: TestClient, test_db: Session, test_user: User):
        """Test duplicating a workflow."""
        workflow = Workflow(
            name="Original Workflow",
            description="Original description",
            version="1.0",
            workflow_data={
                "nodes": [{"id": "node-1", "type": "test", "config": {"key": "value"}}],
                "connections": [{"sourceNodeId": "node-1", "targetNodeId": "node-2"}],
                "metadata": {"custom": "data"}
            },
            tags=["tag1", "tag2"],
            author_id=test_user.id
        )
        test_db.add(workflow)
        test_db.commit()
        original_id = workflow.id
        
        response = client.post(
            f"/api/v1/workflows/{original_id}/duplicate",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # New workflow with different ID
        assert data["id"] != original_id
        assert data["name"] == "Original Workflow (Copy)"
        assert data["description"] == "Original description"
        assert data["version"] == "1.0"
        
        # Data should be copied
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["config"]["key"] == "value"
        assert len(data["connections"]) == 1
        assert data["metadata"]["custom"] == "data"
        assert data["tags"] == ["tag1", "tag2"]
        
        # Status should be reset
        assert data["status"] == "na"
        assert data["last_run_at"] is None
    
    def test_duplicate_workflow_not_found(self, client: TestClient, test_db: Session, test_user: User):
        """Test duplicating non-existent workflow."""
        response = client.post(
            "/api/v1/workflows/non-existent-id/duplicate",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 404


class TestWorkflowList:
    """Test GET /workflows - List workflows."""
    
    def test_list_workflows(self, client: TestClient, test_db: Session, test_user: User):
        """Test listing all workflows."""
        # Create multiple workflows
        for i in range(3):
            workflow = Workflow(
                name=f"Workflow {i}",
                workflow_data={
                    "nodes": [{"id": f"node-{i}", "type": "test", "config": {}}],
                    "connections": [],
                    "metadata": {}
                },
                author_id=test_user.id
            )
            test_db.add(workflow)
        test_db.commit()
        
        response = client.get(
            "/api/v1/workflows",
            headers={"Authorization": f"Bearer {test_user.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) >= 3
        assert all("name" in wf for wf in data)
        assert all("id" in wf for wf in data)

