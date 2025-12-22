"""
Shared fixtures for Workflow tests
"""

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.base import Base
from app.database.repositories.users import UserRepository
from app.config import settings
from app.api.deps import get_db


@pytest.fixture(scope="function")
def test_engine():
    """Create in-memory test database engine with shared connection"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},  # Allow cross-thread access
        poolclass=StaticPool,  # Share connection across threads
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create test database session"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(test_db):
    """Create a test user for workflow tests"""
    user_repo = UserRepository(test_db)
    user = user_repo.create(
        user_name="testuser",
        user_password="testpass123",
        user_email="test@example.com",
        user_firstname="Test",
        user_lastname="User"
    )
    test_db.commit()
    
    # Generate a token for the user
    token_data = {
        "sub": user.user_name,
        "user_id": user.id,
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")
    user.token = token  # Attach token to user object for convenience
    
    return user

