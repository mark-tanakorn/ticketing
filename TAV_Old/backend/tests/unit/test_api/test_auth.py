"""
Unit Tests for Authentication API Endpoints

Tests login, logout, token refresh, and get current user endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch

from app.main import app
from app.database.base import Base
from app.database.repositories.users import UserRepository
from app.api.deps import get_db


class TestAuthLogin:
    """Test login endpoint"""
    
    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_id"] == test_user.id
        assert data["username"] == "testuser"
        
        # Verify tokens are not empty
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0
    
    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "password123"
            }
        )
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_disabled_user(self, client, test_db, test_user):
        """Test login with disabled user"""
        # Disable user
        user_repo = UserRepository(test_db)
        user_repo.disable_user(test_user.id, disabled_by="admin")
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_deleted_user(self, client, test_db, test_user):
        """Test login with soft-deleted user"""
        # Soft delete user
        user_repo = UserRepository(test_db)
        user_repo.soft_delete(test_user.id, deleted_by="admin")
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_missing_fields(self, client):
        """Test login with missing fields"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser"}
        )
        
        assert response.status_code == 422  # Validation error


class TestAuthRefresh:
    """Test token refresh endpoint"""
    
    def test_refresh_token_success(self, client, test_user):
        """Test successful token refresh"""
        # First login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh the token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
    
    def test_refresh_with_access_token(self, client, test_user):
        """Test refresh with access token (should fail)"""
        # Login to get access token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        access_token = login_response.json()["access_token"]
        
        # Try to refresh with access token (should fail)
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token}
        )
        
        assert response.status_code == 401
        assert "Invalid token type" in response.json()["detail"]
    
    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token"""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )
        
        assert response.status_code == 401


class TestAuthLogout:
    """Test logout endpoint"""
    
    def test_logout_success(self, client, test_user):
        """Test successful logout"""
        # Login first
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        access_token = login_response.json()["access_token"]
        
        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        assert "logged out successfully" in response.json()["message"]
    
    def test_logout_without_token(self, client):
        """Test logout without authentication token"""
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401  # Unauthorized - no credentials provided


class TestAuthGetCurrentUser:
    """Test get current user endpoint"""
    
    def test_get_current_user_success(self, client, test_user):
        """Test getting current user info"""
        # Login first
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        access_token = login_response.json()["access_token"]
        
        # Get current user
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == test_user.id
        assert data["user_name"] == "testuser"
        assert data["user_email"] == "test@example.com"
        assert data["user_firstname"] == "Test"
        assert data["user_lastname"] == "User"
        
        # Verify sensitive fields are not included
        assert "user_password" not in data
    
    def test_get_current_user_without_token(self, client):
        """Test getting current user without token"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401  # Unauthorized - no credentials provided
    
    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401
    
    def test_get_current_user_disabled(self, client, test_db, test_user):
        """Test getting current user when account is disabled"""
        # Login first
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        access_token = login_response.json()["access_token"]
        
        # Disable user
        user_repo = UserRepository(test_db)
        user_repo.disable_user(test_user.id, disabled_by="admin")
        
        # Try to get current user (should fail)
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()


class TestAuthTokenValidation:
    """Test JWT token validation"""
    
    def test_token_contains_user_id(self, client, test_user):
        """Test that token contains user ID in payload"""
        from jose import jwt
        from app.config import settings
        
        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        access_token = login_response.json()["access_token"]
        
        # Decode token (without verification for testing)
        payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])
        
        assert "sub" in payload
        assert payload["sub"] == str(test_user.id)
        assert payload["type"] == "access"
    
    def test_refresh_token_type(self, client, test_user):
        """Test that refresh token has correct type"""
        from jose import jwt
        from app.config import settings
        
        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        
        refresh_token = login_response.json()["refresh_token"]
        
        # Decode token
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
        
        assert payload["type"] == "refresh"

