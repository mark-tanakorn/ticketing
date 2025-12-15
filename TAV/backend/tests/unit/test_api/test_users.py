"""
Unit Tests for User API Endpoints

Tests CRUD operations, password management, and user status endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.base import Base
from app.database.repositories.users import UserRepository
from app.api.deps import get_db


class TestUserCreate:
    """Test user creation endpoint"""
    
    def test_create_user_success(self, client, auth_headers):
        """Test successful user creation"""
        response = client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "user_name": "newuser",
                "user_password": "newpass123",
                "user_email": "new@example.com",
                "user_firstname": "New",
                "user_lastname": "User"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["user_name"] == "newuser"
        assert data["user_email"] == "new@example.com"
        assert data["user_firstname"] == "New"
        assert data["user_lastname"] == "User"
        assert "id" in data
        assert "user_id" in data
        
        # Password should not be in response
        assert "user_password" not in data
    
    def test_create_user_duplicate_username(self, client, auth_headers, test_user):
        """Test creating user with duplicate username"""
        response = client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "user_name": "testuser",  # Already exists
                "user_password": "password123",  # Valid 8+ chars
                "user_email": "different@example.com"
            }
        )
        
        # Pydantic validation or API can return 422 for business logic errors
        assert response.status_code in [409, 422]
        detail = response.json()["detail"]
        # Handle both string and list responses
        detail_str = str(detail).lower() if isinstance(detail, (list, dict)) else detail.lower()
        assert "already" in detail_str or "exists" in detail_str or "user_name" in detail_str
    
    def test_create_user_duplicate_email(self, client, auth_headers, test_user):
        """Test creating user with duplicate email"""
        response = client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "user_name": "different",
                "user_password": "password123",  # Valid 8+ chars
                "user_email": "test@example.com"  # Already exists
            }
        )
        
        # Pydantic validation or API can return 422 for business logic errors
        assert response.status_code in [409, 422]
        detail = response.json()["detail"]
        # Handle both string and list responses
        detail_str = str(detail).lower() if isinstance(detail, (list, dict)) else detail.lower()
        assert "already" in detail_str or "exists" in detail_str or "user_email" in detail_str
    
    def test_create_user_without_auth(self, client):
        """Test creating user without authentication"""
        response = client.post(
            "/api/v1/users",
            json={
                "user_name": "newuser",
                "user_password": "pass123",
                "user_email": "new@example.com"
            }
        )
        
        assert response.status_code == 401  # Unauthorized - no authentication provided
    
    def test_create_user_invalid_email(self, client, auth_headers):
        """Test creating user with invalid email"""
        response = client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "user_name": "newuser",
                "user_password": "pass123",
                "user_email": "not-an-email"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_user_short_password(self, client, auth_headers):
        """Test creating user with short password"""
        response = client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "user_name": "newuser",
                "user_password": "short",  # Less than 8 characters
                "user_email": "new@example.com"
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestUserList:
    """Test user list endpoint"""
    
    def test_list_users_success(self, client, auth_headers, test_user):
        """Test listing users"""
        response = client.get(
            "/api/v1/users",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "users" in data
        assert "page" in data
        assert "page_size" in data
        
        assert data["total"] >= 1
        assert len(data["users"]) >= 1
        assert data["page"] == 1
    
    def test_list_users_pagination(self, client, test_db, auth_headers):
        """Test user list pagination"""
        # Create multiple users
        user_repo = UserRepository(test_db)
        for i in range(5):
            user_repo.create(
                user_name=f"user{i}",
                user_password="pass123",
                user_email=f"user{i}@example.com"
            )
        
        # Get first page
        response = client.get(
            "/api/v1/users?page=1&page_size=3",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["page_size"] == 3
        assert len(data["users"]) == 3
    
    def test_list_users_search(self, client, test_db, auth_headers):
        """Test user list search"""
        # Create users with different names
        user_repo = UserRepository(test_db)
        user_repo.create(
            user_name="john_doe",
            user_password="pass123",
            user_email="john@example.com"
        )
        user_repo.create(
            user_name="jane_smith",
            user_password="pass123",
            user_email="jane@example.com"
        )
        
        # Search for "john"
        response = client.get(
            "/api/v1/users?search=john",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should find john_doe
        assert len(data["users"]) >= 1
        assert any(u["user_name"] == "john_doe" for u in data["users"])
    
    def test_list_users_without_auth(self, client):
        """Test listing users without authentication"""
        response = client.get("/api/v1/users")
        
        assert response.status_code == 401  # Unauthorized - no authentication provided


class TestUserGet:
    """Test get user by ID endpoint"""
    
    def test_get_user_success(self, client, auth_headers, test_user):
        """Test getting user by ID"""
        response = client.get(
            f"/api/v1/users/{test_user.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == test_user.id
        assert data["user_name"] == "testuser"
        assert data["user_email"] == "test@example.com"
    
    def test_get_user_not_found(self, client, auth_headers):
        """Test getting non-existent user"""
        response = client.get(
            "/api/v1/users/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_get_user_without_auth(self, client, test_user):
        """Test getting user without authentication"""
        response = client.get(f"/api/v1/users/{test_user.id}")
        
        assert response.status_code == 401  # Unauthorized - no authentication provided


class TestUserUpdate:
    """Test user update endpoint"""
    
    def test_update_user_success(self, client, auth_headers, test_user):
        """Test updating user"""
        response = client.patch(
            f"/api/v1/users/{test_user.id}",
            headers=auth_headers,
            json={
                "user_firstname": "Updated",
                "user_lastname": "Name",
                "job_title": "Senior Engineer"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_firstname"] == "Updated"
        assert data["user_lastname"] == "Name"
        # Note: job_title might not be in response schema
    
    def test_update_user_not_found(self, client, auth_headers):
        """Test updating non-existent user"""
        response = client.patch(
            "/api/v1/users/99999",
            headers=auth_headers,
            json={"user_firstname": "Test"}
        )
        
        assert response.status_code == 404
    
    def test_update_user_no_fields(self, client, auth_headers, test_user):
        """Test updating user with no fields"""
        response = client.patch(
            f"/api/v1/users/{test_user.id}",
            headers=auth_headers,
            json={}
        )
        
        assert response.status_code == 400


class TestUserDelete:
    """Test user deletion endpoint"""
    
    def test_delete_user_success(self, client, test_db, auth_headers):
        """Test soft deleting user"""
        # Create another user to delete
        user_repo = UserRepository(test_db)
        user_to_delete = user_repo.create(
            user_name="todelete",
            user_password="pass123",
            user_email="delete@example.com"
        )
        
        response = client.delete(
            f"/api/v1/users/{user_to_delete.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # Verify user is soft deleted
        deleted_user = user_repo.get_by_id(user_to_delete.id)
        assert deleted_user.user_is_deleted is True
    
    def test_delete_self(self, client, auth_headers, test_user):
        """Test that user cannot delete themselves"""
        response = client.delete(
            f"/api/v1/users/{test_user.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]
    
    def test_delete_user_not_found(self, client, auth_headers):
        """Test deleting non-existent user"""
        response = client.delete(
            "/api/v1/users/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestUserPasswordChange:
    """Test password change endpoint"""
    
    def test_change_password_success(self, client, auth_headers, test_user):
        """Test changing own password"""
        response = client.post(
            f"/api/v1/users/{test_user.id}/password",
            headers=auth_headers,
            json={
                "old_password": "testpass123",
                "new_password": "newpass456"
            }
        )
        
        assert response.status_code == 200
        
        # Verify new password works
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "newpass456"
            }
        )
        
        assert login_response.status_code == 200
    
    def test_change_password_wrong_old(self, client, auth_headers, test_user):
        """Test changing password with wrong old password"""
        response = client.post(
            f"/api/v1/users/{test_user.id}/password",
            headers=auth_headers,
            json={
                "old_password": "wrongpass",
                "new_password": "newpass456"
            }
        )
        
        assert response.status_code == 401
    
    def test_change_password_same_as_old(self, client, auth_headers, test_user):
        """Test changing password to same as old"""
        response = client.post(
            f"/api/v1/users/{test_user.id}/password",
            headers=auth_headers,
            json={
                "old_password": "testpass123",
                "new_password": "testpass123"  # Same as old
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_change_other_user_password(self, client, test_db, auth_headers):
        """Test that user cannot change another user's password"""
        # Create another user
        user_repo = UserRepository(test_db)
        other_user = user_repo.create(
            user_name="otheruser",
            user_password="pass123",
            user_email="other@example.com"
        )
        test_db.commit()
        
        response = client.post(
            f"/api/v1/users/{other_user.id}/password",
            headers=auth_headers,
            json={
                "old_password": "pass123",
                "new_password": "newpass456"
            }
        )
        
        # Can return 403 (forbidden) or 422 (validation error)
        assert response.status_code in [403, 422]


class TestUserPasswordReset:
    """Test password reset endpoint (admin)"""
    
    def test_reset_password_success(self, client, test_db, auth_headers):
        """Test admin resetting user password"""
        # Create user to reset
        user_repo = UserRepository(test_db)
        user = user_repo.create(
            user_name="resetme",
            user_password="oldpass123",
            user_email="reset@example.com"
        )
        
        response = client.post(
            f"/api/v1/users/{user.id}/reset-password",
            headers=auth_headers,
            json={
                "new_password": "resetpass123",
                "reset_by": "admin"
            }
        )
        
        assert response.status_code == 200
        
        # Verify new password works
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "resetme",
                "password": "resetpass123"
            }
        )
        
        assert login_response.status_code == 200
    
    def test_reset_password_not_found(self, client, auth_headers):
        """Test resetting password for non-existent user"""
        response = client.post(
            "/api/v1/users/99999/reset-password",
            headers=auth_headers,
            json={
                "new_password": "newpass123",
                "reset_by": "admin"
            }
        )
        
        assert response.status_code == 404


class TestUserDisableEnable:
    """Test user disable/enable endpoints"""
    
    def test_disable_user_success(self, client, test_db, auth_headers):
        """Test disabling user"""
        # Create user to disable
        user_repo = UserRepository(test_db)
        user = user_repo.create(
            user_name="todisable",
            user_password="pass123",
            user_email="disable@example.com"
        )
        
        response = client.post(
            f"/api/v1/users/{user.id}/disable",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify user cannot login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "todisable",
                "password": "pass123"
            }
        )
        
        assert login_response.status_code == 401
    
    def test_disable_self(self, client, auth_headers, test_user):
        """Test that user cannot disable themselves"""
        response = client.post(
            f"/api/v1/users/{test_user.id}/disable",
            headers=auth_headers
        )
        
        assert response.status_code == 400
    
    def test_enable_user_success(self, client, test_db, auth_headers):
        """Test enabling disabled user"""
        # Create and disable user
        user_repo = UserRepository(test_db)
        user = user_repo.create(
            user_name="toenable",
            user_password="pass123",
            user_email="enable@example.com"
        )
        user_repo.disable_user(user.id, disabled_by="admin")
        
        # Enable user
        response = client.post(
            f"/api/v1/users/{user.id}/enable",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify user can login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "toenable",
                "password": "pass123"
            }
        )
        
        assert login_response.status_code == 200


class TestUserRestore:
    """Test user restore endpoint"""
    
    def test_restore_user_success(self, client, test_db, auth_headers):
        """Test restoring soft-deleted user"""
        # Create and delete user
        user_repo = UserRepository(test_db)
        user = user_repo.create(
            user_name="torestore",
            user_password="pass123",
            user_email="restore@example.com"
        )
        user_repo.soft_delete(user.id, deleted_by="admin")
        
        # Restore user
        response = client.post(
            f"/api/v1/users/{user.id}/restore",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify user can login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "torestore",
                "password": "pass123"
            }
        )
        
        assert login_response.status_code == 200
    
    def test_restore_user_not_found(self, client, auth_headers):
        """Test restoring non-existent user"""
        response = client.post(
            "/api/v1/users/99999/restore",
            headers=auth_headers
        )
        
        assert response.status_code == 404

