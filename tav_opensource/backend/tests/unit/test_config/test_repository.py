"""
Unit tests for Settings Repository
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.database.base import Base
from app.database.models.setting import Setting, SettingHistory
from app.database.repositories.settings import SettingsRepository


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def repo(db_session):
    """Create a settings repository."""
    return SettingsRepository(db_session)


class TestSettingsRepository:
    """Test settings repository CRUD operations."""
    
    def test_set_and_get_setting(self, repo):
        """Test setting and getting a value."""
        # Set a setting
        result = repo.set("test", "key1", "value1", updated_by="test_user")
        assert result is True
        
        # Get the setting
        value = repo.get("test", "key1")
        assert value == "value1"
    
    def test_get_nonexistent_setting(self, repo):
        """Test getting a non-existent setting returns default."""
        value = repo.get("test", "nonexistent", default="default_value")
        assert value == "default_value"
    
    def test_set_complex_value(self, repo):
        """Test setting complex JSON values."""
        complex_value = {
            "nested": {
                "key": "value",
                "number": 42,
                "list": [1, 2, 3]
            }
        }
        
        repo.set("test", "complex", complex_value)
        result = repo.get("test", "complex")
        
        assert result == complex_value
        assert result["nested"]["number"] == 42
    
    def test_update_existing_setting(self, repo):
        """Test updating an existing setting."""
        repo.set("test", "key1", "value1")
        repo.set("test", "key1", "value2")
        
        value = repo.get("test", "key1")
        assert value == "value2"
    
    def test_unchanged_value_skipped(self, repo):
        """Test that unchanged values don't create duplicate entries."""
        repo.set("test", "key1", "value1")
        
        # Set same value again
        result = repo.set("test", "key1", "value1")
        assert result is True
        
        # Value should still be the same
        value = repo.get("test", "key1")
        assert value == "value1"
    
    def test_delete_setting(self, repo):
        """Test deleting a setting."""
        repo.set("test", "key1", "value1")
        
        result = repo.delete("test", "key1", deleted_by="test_user")
        assert result is True
        
        value = repo.get("test", "key1", default=None)
        assert value is None
    
    def test_delete_nonexistent_setting(self, repo):
        """Test deleting a non-existent setting."""
        result = repo.delete("test", "nonexistent")
        assert result is False
    
    def test_get_all_settings(self, repo):
        """Test getting all settings."""
        repo.set("namespace1", "key1", "value1")
        repo.set("namespace1", "key2", "value2")
        repo.set("namespace2", "key1", "value3")
        
        all_settings = repo.get_all()
        
        assert "namespace1" in all_settings
        assert "namespace2" in all_settings
        assert all_settings["namespace1"]["key1"] == "value1"
        assert all_settings["namespace1"]["key2"] == "value2"
        assert all_settings["namespace2"]["key1"] == "value3"
    
    def test_get_namespace(self, repo):
        """Test getting all settings in a namespace."""
        repo.set("test", "key1", "value1")
        repo.set("test", "key2", "value2")
        repo.set("other", "key1", "value3")
        
        test_settings = repo.get_namespace("test")
        
        assert len(test_settings) == 2
        assert test_settings["key1"] == "value1"
        assert test_settings["key2"] == "value2"
        assert "key3" not in test_settings
    
    def test_clear_namespace(self, repo):
        """Test clearing all settings in a namespace."""
        repo.set("test", "key1", "value1")
        repo.set("test", "key2", "value2")
        repo.set("other", "key1", "value3")
        
        result = repo.clear_namespace("test", deleted_by="test_user")
        assert result is True
        
        test_settings = repo.get_namespace("test")
        assert len(test_settings) == 0
        
        # Other namespace should be unaffected
        other_settings = repo.get_namespace("other")
        assert len(other_settings) == 1
    
    def test_bulk_set(self, repo):
        """Test bulk setting multiple values."""
        settings = {
            "namespace1": {
                "key1": "value1",
                "key2": "value2"
            },
            "namespace2": {
                "key1": "value3"
            }
        }
        
        changed_count = repo.bulk_set(settings, updated_by="test_user")
        assert changed_count == 3
        
        assert repo.get("namespace1", "key1") == "value1"
        assert repo.get("namespace1", "key2") == "value2"
        assert repo.get("namespace2", "key1") == "value3"
    
    def test_exists(self, repo):
        """Test checking if a setting exists."""
        repo.set("test", "key1", "value1")
        
        assert repo.exists("test", "key1") is True
        assert repo.exists("test", "nonexistent") is False
    
    def test_audit_trail_on_set(self, repo, db_session):
        """Test that setting a value creates audit trail entry."""
        repo.set("test", "key1", "value1", updated_by="user1")
        
        history = db_session.query(SettingHistory).filter(
            SettingHistory.namespace == "test",
            SettingHistory.key == "key1"
        ).all()
        
        assert len(history) == 1
        assert history[0].changed_by == "user1"
        assert history[0].new_value is not None
    
    def test_audit_trail_on_update(self, repo, db_session):
        """Test that updating a value creates audit trail entry."""
        repo.set("test", "key1", "value1")
        repo.set("test", "key1", "value2", updated_by="user2")
        
        history = db_session.query(SettingHistory).filter(
            SettingHistory.namespace == "test",
            SettingHistory.key == "key1"
        ).order_by(SettingHistory.changed_at).all()
        
        assert len(history) == 2
        # Second entry should have old value
        assert '"value1"' in history[1].old_value
        assert '"value2"' in history[1].new_value
    
    def test_audit_trail_on_delete(self, repo, db_session):
        """Test that deleting a value creates audit trail entry."""
        repo.set("test", "key1", "value1")
        repo.delete("test", "key1", deleted_by="user3")
        
        history = db_session.query(SettingHistory).filter(
            SettingHistory.namespace == "test",
            SettingHistory.key == "key1"
        ).order_by(SettingHistory.changed_at).all()
        
        # Should have 2 entries: one for set, one for delete
        assert len(history) == 2
        assert history[1].changed_by == "user3"
        assert history[1].new_value is None  # Deletion
    
    def test_get_history(self, repo):
        """Test getting setting change history."""
        import time
        repo.set("test", "key1", "value1", updated_by="user1")
        time.sleep(0.01)  # Ensure different timestamps
        repo.set("test", "key1", "value2", updated_by="user2")
        time.sleep(0.01)  # Ensure different timestamps
        repo.set("test", "key1", "value3", updated_by="user3")
        
        history = repo.get_history("test", "key1")
        
        assert len(history) == 3
        # Should be in reverse chronological order
        assert history[0]["changed_by"] == "user3"
        assert history[1]["changed_by"] == "user2"
        assert history[2]["changed_by"] == "user1"
    
    def test_get_history_with_limit(self, repo):
        """Test getting history with limit."""
        for i in range(10):
            repo.set("test", "key1", f"value{i}")
        
        history = repo.get_history("test", "key1", limit=5)
        assert len(history) == 5
    
    def test_get_history_by_namespace(self, repo):
        """Test getting history for entire namespace."""
        repo.set("test", "key1", "value1")
        repo.set("test", "key2", "value2")
        repo.set("other", "key1", "value3")
        
        history = repo.get_history(namespace="test")
        
        assert len(history) == 2
        namespaces = [h["namespace"] for h in history]
        assert all(ns == "test" for ns in namespaces)


