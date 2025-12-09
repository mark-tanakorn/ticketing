"""
Unit Tests for User Repository

Tests CRUD operations, authentication, and business logic.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.database.models.user import User
from app.database.repositories.users import UserRepository
from app.utils.hashing import hash_password, verify_password


@pytest.fixture(scope="module")
def test_engine():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create a new database session for each test"""
    # Clear all tables before each test
    from app.database.base import Base
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def user_repo(test_db):
    """Create UserRepository instance"""
    return UserRepository(test_db)


class TestUserRepositoryCreate:
    """Test user creation operations"""
    
    def test_create_user_basic(self, user_repo):
        """Test creating a basic user"""
        user = user_repo.create(
            user_name="testuser",
            user_password="password123",
            user_email="test@example.com"
        )
        
        assert user.id is not None
        assert user.user_id is not None  # UUID should be generated
        assert user.user_name == "testuser"
        assert user.user_email == "test@example.com"
        assert user.user_password != "password123"  # Should be hashed
        assert verify_password("password123", user.user_password)
    
    def test_create_user_with_details(self, user_repo):
        """Test creating a user with full details"""
        user = user_repo.create(
            user_name="john.doe",
            user_password="secret123",
            user_email="john.doe@company.com",
            user_firstname="John",
            user_lastname="Doe",
            user_employee_id="EMP001",
            user_staffcode="SC001",
            job_title="Senior Software Engineer",
            user_department_id=10,
            created_by="admin"
        )
        
        assert user.user_name == "john.doe"
        assert user.user_firstname == "John"
        assert user.user_lastname == "Doe"
        assert user.user_employee_id == "EMP001"
        assert user.job_title == "Senior Software Engineer"
        assert user.user_created_by == "admin"
    
    def test_create_user_without_email(self, user_repo):
        """Test creating a user without email (nullable)"""
        user = user_repo.create(
            user_name="noemail_user",
            user_password="password123"
        )
        
        assert user.user_name == "noemail_user"
        assert user.user_email is None
    
    def test_create_duplicate_username(self, user_repo):
        """Test that duplicate usernames raise IntegrityError"""
        from sqlalchemy.exc import IntegrityError
        
        user_repo.create(user_name="duplicate", user_password="pass123")
        
        with pytest.raises(IntegrityError):
            user_repo.create(user_name="duplicate", user_password="pass456")


class TestUserRepositoryRead:
    """Test user read operations"""
    
    @pytest.fixture(autouse=True)
    def setup_users(self, user_repo):
        """Create test users before each test"""
        self.user1 = user_repo.create(
            user_name="user1",
            user_password="pass1",
            user_email="user1@test.com",
            user_firstname="User",
            user_lastname="One",
            user_employee_id="EMP001",
            user_staffcode="SC001",
            user_department_id=10
        )
        
        self.user2 = user_repo.create(
            user_name="user2",
            user_password="pass2",
            user_email="user2@test.com",
            user_department_id=10
        )
        
        self.user3 = user_repo.create(
            user_name="user3",
            user_password="pass3",
            user_email="user3@test.com",
            user_department_id=20
        )
    
    def test_get_by_id(self, user_repo):
        """Test getting user by primary key ID"""
        user = user_repo.get_by_id(self.user1.id)
        
        assert user is not None
        assert user.user_name == "user1"
    
    def test_get_by_user_id(self, user_repo):
        """Test getting user by UUID user_id"""
        user = user_repo.get_by_user_id(self.user1.user_id)
        
        assert user is not None
        assert user.user_name == "user1"
    
    def test_get_by_username(self, user_repo):
        """Test getting user by username"""
        user = user_repo.get_by_username("user1")
        
        assert user is not None
        assert user.user_email == "user1@test.com"
    
    def test_get_by_email(self, user_repo):
        """Test getting user by email"""
        user = user_repo.get_by_email("user1@test.com")
        
        assert user is not None
        assert user.user_name == "user1"
    
    def test_get_by_employee_id(self, user_repo):
        """Test getting user by employee ID"""
        user = user_repo.get_by_employee_id("EMP001")
        
        assert user is not None
        assert user.user_name == "user1"
    
    def test_get_by_staff_code(self, user_repo):
        """Test getting user by staff code"""
        user = user_repo.get_by_staff_code("SC001")
        
        assert user is not None
        assert user.user_name == "user1"
    
    def test_get_all(self, user_repo):
        """Test getting all users"""
        users = user_repo.get_all()
        
        assert len(users) == 3
    
    def test_get_all_with_pagination(self, user_repo):
        """Test pagination"""
        users = user_repo.get_all(skip=1, limit=2)
        
        assert len(users) == 2
    
    def test_count(self, user_repo):
        """Test counting users"""
        count = user_repo.count()
        
        assert count == 3
    
    def test_search(self, user_repo):
        """Test searching users"""
        results = user_repo.search("user1")
        
        assert len(results) >= 1
        assert any(u.user_name == "user1" for u in results)
    
    def test_search_by_employee_id(self, user_repo):
        """Test searching by employee ID"""
        results = user_repo.search("EMP001")
        
        assert len(results) >= 1
        assert any(u.user_employee_id == "EMP001" for u in results)
    
    def test_get_by_department(self, user_repo):
        """Test getting users by department"""
        users = user_repo.get_by_department(10)
        
        assert len(users) == 2
        assert all(u.user_department_id == 10 for u in users)


class TestUserRepositoryUpdate:
    """Test user update operations"""
    
    @pytest.fixture(autouse=True)
    def setup_user(self, user_repo):
        """Create test user before each test"""
        self.user = user_repo.create(
            user_name="testuser",
            user_password="password123",
            user_email="test@example.com"
        )
    
    def test_update_user(self, user_repo):
        """Test updating user fields"""
        updated = user_repo.update(
            self.user.id,
            user_firstname="John",
            user_lastname="Doe",
            modified_by="admin"
        )
        
        assert updated.user_firstname == "John"
        assert updated.user_lastname == "Doe"
        assert updated.user_modified_by == "admin"
        assert updated.version_no == 1  # Version incremented
    
    def test_change_password(self, user_repo):
        """Test changing password"""
        updated = user_repo.change_password(
            self.user.id,
            "newpassword456",
            changed_by="testuser"
        )
        
        assert verify_password("newpassword456", updated.user_password)
        assert updated.user_change_password_by == "testuser"
        assert updated.user_change_password_on is not None
        assert updated.user_is_firsttime_login == False
    
    def test_reset_password(self, user_repo):
        """Test resetting password (admin action)"""
        updated = user_repo.reset_password(
            self.user.id,
            "resetpassword",
            reset_by="admin"
        )
        
        assert verify_password("resetpassword", updated.user_password)
        assert updated.user_reset_password_by == "admin"
        assert updated.user_reset_password_on is not None
        assert updated.user_is_firsttime_login == True  # Force password change
    
    def test_disable_user(self, user_repo):
        """Test disabling a user"""
        updated = user_repo.disable_user(self.user.id, disabled_by="admin")
        
        assert updated.user_is_disabled == True
        assert updated.user_disabled_by == "admin"
        assert updated.user_disabled_on is not None
    
    def test_enable_user(self, user_repo):
        """Test enabling a disabled user"""
        # First disable
        user_repo.disable_user(self.user.id, disabled_by="admin")
        
        # Then enable
        updated = user_repo.enable_user(self.user.id, enabled_by="admin")
        
        assert updated.user_is_disabled == False
        assert updated.user_enabled_by == "admin"
        assert updated.user_enabled_on is not None


class TestUserRepositoryDelete:
    """Test user delete operations"""
    
    @pytest.fixture(autouse=True)
    def setup_user(self, user_repo):
        """Create test user before each test"""
        self.user = user_repo.create(
            user_name="testuser",
            user_password="password123"
        )
    
    def test_soft_delete(self, user_repo):
        """Test soft deleting a user"""
        deleted = user_repo.soft_delete(self.user.id, deleted_by="admin")
        
        assert deleted.user_is_deleted == True
        assert deleted.user_deleted_by == "admin"
        assert deleted.user_deleted_on is not None
    
    def test_soft_delete_filters_from_get_all(self, user_repo):
        """Test that soft-deleted users are filtered from get_all()"""
        user_repo.soft_delete(self.user.id, deleted_by="admin")
        
        users = user_repo.get_all()
        
        assert len(users) == 0
    
    def test_soft_delete_included_with_flag(self, user_repo):
        """Test that soft-deleted users can be included"""
        user_repo.soft_delete(self.user.id, deleted_by="admin")
        
        users = user_repo.get_all(include_deleted=True)
        
        assert len(users) == 1
    
    def test_restore(self, user_repo):
        """Test restoring a soft-deleted user"""
        user_repo.soft_delete(self.user.id, deleted_by="admin")
        
        restored = user_repo.restore(self.user.id, restored_by="admin")
        
        assert restored.user_is_deleted == False
        assert restored.user_deleted_by is None
        assert restored.user_deleted_on is None
    
    def test_hard_delete(self, user_repo, test_db):
        """Test permanently deleting a user"""
        user_id = self.user.id
        
        result = user_repo.hard_delete(user_id)
        
        assert result == True
        assert user_repo.get_by_id(user_id) is None


class TestUserRepositoryAuthentication:
    """Test authentication operations"""
    
    @pytest.fixture(autouse=True)
    def setup_user(self, user_repo):
        """Create test user before each test"""
        self.user = user_repo.create(
            user_name="authuser",
            user_password="password123",
            user_email="auth@test.com"
        )
    
    def test_authenticate_success(self, user_repo):
        """Test successful authentication"""
        user = user_repo.authenticate("authuser", "password123")
        
        assert user is not None
        assert user.user_name == "authuser"
    
    def test_authenticate_wrong_password(self, user_repo):
        """Test authentication with wrong password"""
        user = user_repo.authenticate("authuser", "wrongpassword")
        
        assert user is None
    
    def test_authenticate_nonexistent_user(self, user_repo):
        """Test authentication with non-existent user"""
        user = user_repo.authenticate("nonexistent", "password")
        
        assert user is None
    
    def test_authenticate_disabled_user(self, user_repo):
        """Test that disabled users cannot authenticate"""
        user_repo.disable_user(self.user.id, disabled_by="admin")
        
        user = user_repo.authenticate("authuser", "password123")
        
        assert user is None
    
    def test_authenticate_deleted_user(self, user_repo):
        """Test that deleted users cannot authenticate"""
        user_repo.soft_delete(self.user.id, deleted_by="admin")
        
        user = user_repo.authenticate("authuser", "password123")
        
        assert user is None
    
    def test_is_active(self, user_repo):
        """Test checking if user is active"""
        assert user_repo.is_active(self.user.id) == True
    
    def test_is_active_disabled(self, user_repo):
        """Test that disabled users are not active"""
        user_repo.disable_user(self.user.id, disabled_by="admin")
        
        assert user_repo.is_active(self.user.id) == False
    
    def test_requires_password_change(self, user_repo):
        """Test checking if password change required"""
        # New users should require password change by default
        assert user_repo.requires_password_change(self.user.id) == True
    
    def test_requires_password_change_after_change(self, user_repo):
        """Test that flag is cleared after password change"""
        user_repo.change_password(self.user.id, "newpassword", changed_by="authuser")
        
        assert user_repo.requires_password_change(self.user.id) == False
    
    def test_requires_password_change_after_reset(self, user_repo):
        """Test that flag is set after admin reset"""
        user_repo.reset_password(self.user.id, "resetpass", reset_by="admin")
        
        assert user_repo.requires_password_change(self.user.id) == True


class TestUserRepositoryUtility:
    """Test utility operations"""
    
    @pytest.fixture(autouse=True)
    def setup_user(self, user_repo):
        """Create test user before each test"""
        self.user = user_repo.create(
            user_name="utiluser",
            user_password="password123",
            user_email="util@test.com"
        )
    
    def test_exists(self, user_repo):
        """Test checking if user exists"""
        assert user_repo.exists(self.user.id) == True
        assert user_repo.exists(99999) == False
    
    def test_username_exists(self, user_repo):
        """Test checking if username exists"""
        assert user_repo.username_exists("utiluser") == True
        assert user_repo.username_exists("nonexistent") == False
    
    def test_email_exists(self, user_repo):
        """Test checking if email exists"""
        assert user_repo.email_exists("util@test.com") == True
        assert user_repo.email_exists("nonexistent@test.com") == False


class TestUserRepositoryHierarchy:
    """Test organizational hierarchy operations"""
    
    @pytest.fixture(autouse=True)
    def setup_hierarchy(self, user_repo):
        """Create hierarchical users"""
        self.manager = user_repo.create(
            user_name="manager",
            user_password="pass123"
        )
        
        self.employee1 = user_repo.create(
            user_name="employee1",
            user_password="pass123",
            supervisor_user_id=self.manager.id
        )
        
        self.employee2 = user_repo.create(
            user_name="employee2",
            user_password="pass123",
            supervisor_user_id=self.manager.id
        )
    
    def test_get_by_supervisor(self, user_repo):
        """Test getting employees by supervisor"""
        employees = user_repo.get_by_supervisor(self.manager.id)
        
        assert len(employees) == 2
        assert all(e.supervisor_user_id == self.manager.id for e in employees)

