"""Pytest fixtures and configuration."""

import os
import sys
from pathlib import Path

# Set up test environment variables BEFORE any app imports
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-not-production")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-32-characters!")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

# Add backend directory to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine for the session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create a test database session for each test."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def clean_db(test_engine):
    """Provide a clean database for each test."""
    # Drop all tables
    Base.metadata.drop_all(test_engine)
    # Recreate all tables
    Base.metadata.create_all(test_engine)
    
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()