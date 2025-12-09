"""
User Repository

Provides CRUD operations and business logic for User model.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.models.user import User
from app.utils.hashing import hash_password, verify_password


class UserRepository:
    """Repository for User model operations"""
    
    def __init__(self, db: Session):
        """Initialize repository with database session"""
        self.db = db
    
    # ========================================
    # CREATE Operations
    # ========================================
    
    def create(
        self,
        user_name: str,
        user_password: str,
        user_email: Optional[str] = None,
        created_by: Optional[str] = None,
        **kwargs
    ) -> User:
        """
        Create a new user with hashed password.
        
        Args:
            user_name: Username (required, unique)
            user_password: Plain text password (will be hashed)
            user_email: Email address (optional)
            created_by: Who created this user
            **kwargs: Additional user fields
        
        Returns:
            Created User object
        
        Raises:
            IntegrityError: If username or email already exists
        """
        # Hash the password
        hashed_password = hash_password(user_password)
        
        # Create user instance
        user = User(
            user_name=user_name,
            user_password=hashed_password,
            user_email=user_email,
            user_created_by=created_by,
            **kwargs
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    # ========================================
    # READ Operations
    # ========================================
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by primary key ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_user_id(self, user_id: str) -> Optional[User]:
        """Get user by UUID user_id"""
        return self.db.query(User).filter(User.user_id == user_id).first()
    
    def get_by_username(self, user_name: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.user_name == user_name).first()
    
    def get_by_email(self, user_email: str) -> Optional[User]:
        """Get user by email address"""
        return self.db.query(User).filter(User.user_email == user_email).first()
    
    def get_by_employee_id(self, employee_id: str) -> Optional[User]:
        """Get user by employee ID"""
        return self.db.query(User).filter(User.user_employee_id == employee_id).first()
    
    def get_by_staff_code(self, staff_code: str) -> Optional[User]:
        """Get user by staff code"""
        return self.db.query(User).filter(User.user_staffcode == staff_code).first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        include_disabled: bool = False
    ) -> List[User]:
        """
        Get all users with pagination.
        
        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            include_deleted: Include soft-deleted users
            include_disabled: Include disabled users
        
        Returns:
            List of User objects
        """
        query = self.db.query(User)
        
        # Filter out deleted/disabled users by default
        # Note: user_is_deleted can be None (nullable), so we check explicitly
        if not include_deleted:
            query = query.filter((User.user_is_deleted == False) | (User.user_is_deleted == None))
        
        if not include_disabled:
            query = query.filter((User.user_is_disabled == False) | (User.user_is_disabled == None))
        
        return query.offset(skip).limit(limit).all()
    
    def count(
        self,
        include_deleted: bool = False,
        include_disabled: bool = False
    ) -> int:
        """
        Count total users.
        
        Args:
            include_deleted: Include soft-deleted users
            include_disabled: Include disabled users
        
        Returns:
            Total count
        """
        query = self.db.query(func.count(User.id))
        
        if not include_deleted:
            query = query.filter((User.user_is_deleted == False) | (User.user_is_deleted == None))
        
        if not include_disabled:
            query = query.filter((User.user_is_disabled == False) | (User.user_is_disabled == None))
        
        return query.scalar()
    
    def search(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        include_disabled: bool = False
    ) -> List[User]:
        """
        Search users by name, email, or employee ID.
        
        Args:
            search_term: Search query
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Include soft-deleted users
            include_disabled: Include disabled users
        
        Returns:
            List of matching User objects
        """
        query = self.db.query(User).filter(
            or_(
                User.user_name.ilike(f"%{search_term}%"),
                User.user_email.ilike(f"%{search_term}%"),
                User.user_firstname.ilike(f"%{search_term}%"),
                User.user_lastname.ilike(f"%{search_term}%"),
                User.user_employee_id.ilike(f"%{search_term}%"),
                User.user_staffcode.ilike(f"%{search_term}%")
            )
        )
        
        if not include_deleted:
            query = query.filter((User.user_is_deleted == False) | (User.user_is_deleted == None))
        
        if not include_disabled:
            query = query.filter((User.user_is_disabled == False) | (User.user_is_disabled == None))
        
        return query.offset(skip).limit(limit).all()
    
    def get_by_department(
        self,
        department_id: int,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        include_disabled: bool = False
    ) -> List[User]:
        """Get users by department ID"""
        query = self.db.query(User).filter(User.user_department_id == department_id)
        
        if not include_deleted:
            query = query.filter((User.user_is_deleted == False) | (User.user_is_deleted == None))
        
        if not include_disabled:
            query = query.filter((User.user_is_disabled == False) | (User.user_is_disabled == None))
        
        return query.offset(skip).limit(limit).all()
    
    def get_by_supervisor(
        self,
        supervisor_user_id: int,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        include_disabled: bool = False
    ) -> List[User]:
        """Get users reporting to a specific supervisor"""
        query = self.db.query(User).filter(User.supervisor_user_id == supervisor_user_id)
        
        if not include_deleted:
            query = query.filter((User.user_is_deleted == False) | (User.user_is_deleted == None))
        
        if not include_disabled:
            query = query.filter((User.user_is_disabled == False) | (User.user_is_disabled == None))
        
        return query.offset(skip).limit(limit).all()
    
    # ========================================
    # UPDATE Operations
    # ========================================
    
    def update(
        self,
        user_id: int,
        modified_by: Optional[str] = None,
        **kwargs
    ) -> Optional[User]:
        """
        Update user fields.
        
        Args:
            user_id: User ID (primary key)
            modified_by: Who modified this user
            **kwargs: Fields to update
        
        Returns:
            Updated User object or None if not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        # Update modification tracking
        user.user_modified_by = modified_by
        user.user_modified_on = datetime.utcnow()
        user.version_no += 1
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def change_password(
        self,
        user_id: int,
        new_password: str,
        changed_by: Optional[str] = None
    ) -> Optional[User]:
        """
        Change user password.
        
        Args:
            user_id: User ID
            new_password: New plain text password (will be hashed)
            changed_by: Who changed the password
        
        Returns:
            Updated User object or None if not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        # Hash new password
        user.user_password = hash_password(new_password)
        
        # Update tracking
        user.user_change_password_by = changed_by
        user.user_change_password_on = datetime.utcnow()
        user.user_is_firsttime_login = False
        user.user_modified_by = changed_by
        user.user_modified_on = datetime.utcnow()
        user.version_no += 1
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def reset_password(
        self,
        user_id: int,
        new_password: str,
        reset_by: Optional[str] = None
    ) -> Optional[User]:
        """
        Reset user password (admin action).
        
        Args:
            user_id: User ID
            new_password: New plain text password (will be hashed)
            reset_by: Who reset the password
        
        Returns:
            Updated User object or None if not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        # Hash new password
        user.user_password = hash_password(new_password)
        
        # Update tracking
        user.user_reset_password_by = reset_by
        user.user_reset_password_on = datetime.utcnow()
        user.user_is_firsttime_login = True  # Force password change on next login
        user.user_modified_by = reset_by
        user.user_modified_on = datetime.utcnow()
        user.version_no += 1
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def disable_user(
        self,
        user_id: int,
        disabled_by: Optional[str] = None
    ) -> Optional[User]:
        """
        Disable a user account.
        
        Args:
            user_id: User ID
            disabled_by: Who disabled the user
        
        Returns:
            Updated User object or None if not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        user.user_is_disabled = True
        user.user_disabled_by = disabled_by
        user.user_disabled_on = datetime.utcnow()
        user.user_modified_by = disabled_by
        user.user_modified_on = datetime.utcnow()
        user.version_no += 1
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def enable_user(
        self,
        user_id: int,
        enabled_by: Optional[str] = None
    ) -> Optional[User]:
        """
        Enable a disabled user account.
        
        Args:
            user_id: User ID
            enabled_by: Who enabled the user
        
        Returns:
            Updated User object or None if not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        user.user_is_disabled = False
        user.user_enabled_by = enabled_by
        user.user_enabled_on = datetime.utcnow()
        user.user_modified_by = enabled_by
        user.user_modified_on = datetime.utcnow()
        user.version_no += 1
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    # ========================================
    # DELETE Operations (Soft Delete)
    # ========================================
    
    def soft_delete(
        self,
        user_id: int,
        deleted_by: Optional[str] = None
    ) -> Optional[User]:
        """
        Soft delete a user (set user_is_deleted flag).
        
        Args:
            user_id: User ID
            deleted_by: Who deleted the user
        
        Returns:
            Updated User object or None if not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        user.user_is_deleted = True
        user.user_deleted_by = deleted_by
        user.user_deleted_on = datetime.utcnow()
        user.user_modified_by = deleted_by
        user.user_modified_on = datetime.utcnow()
        user.version_no += 1
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def restore(
        self,
        user_id: int,
        restored_by: Optional[str] = None
    ) -> Optional[User]:
        """
        Restore a soft-deleted user.
        
        Args:
            user_id: User ID
            restored_by: Who restored the user
        
        Returns:
            Updated User object or None if not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        user.user_is_deleted = False
        user.user_deleted_by = None
        user.user_deleted_on = None
        user.user_modified_by = restored_by
        user.user_modified_on = datetime.utcnow()
        user.version_no += 1
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def hard_delete(self, user_id: int) -> bool:
        """
        Permanently delete a user from database.
        
        ⚠️ WARNING: This is irreversible! Use soft_delete() instead.
        
        Args:
            user_id: User ID
        
        Returns:
            True if deleted, False if not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        self.db.delete(user)
        self.db.commit()
        
        return True
    
    # ========================================
    # AUTHENTICATION Operations
    # ========================================
    
    def authenticate(
        self,
        user_name: str,
        password: str
    ) -> Optional[User]:
        """
        Authenticate a user by username and password.
        
        Args:
            user_name: Username
            password: Plain text password
        
        Returns:
            User object if authentication successful, None otherwise
        """
        user = self.get_by_username(user_name)
        
        if not user:
            return None
        
        # Check if user is deleted or disabled
        # Note: These fields are nullable, so we check explicitly for True
        if user.user_is_deleted is True or user.user_is_disabled is True:
            return None
        
        # Verify password
        if not user.user_password:
            return None
        
        if not verify_password(password, user.user_password):
            return None
        
        return user
    
    def is_active(self, user_id: int) -> bool:
        """
        Check if user is active (not deleted, not disabled).
        
        Args:
            user_id: User ID
        
        Returns:
            True if active, False otherwise
        """
        user = self.get_by_id(user_id)
        
        if not user:
            return False
        
        # Check explicitly for True since fields are nullable
        return user.user_is_deleted is not True and user.user_is_disabled is not True
    
    def requires_password_change(self, user_id: int) -> bool:
        """
        Check if user needs to change password on next login.
        
        Args:
            user_id: User ID
        
        Returns:
            True if password change required, False otherwise
        """
        user = self.get_by_id(user_id)
        
        if not user:
            return False
        
        return bool(user.user_is_firsttime_login)
    
    # ========================================
    # UTILITY Operations
    # ========================================
    
    def exists(self, user_id: int) -> bool:
        """Check if user exists by ID"""
        return self.db.query(User.id).filter(User.id == user_id).scalar() is not None
    
    def username_exists(self, user_name: str) -> bool:
        """Check if username already exists"""
        return self.db.query(User.id).filter(User.user_name == user_name).first() is not None
    
    def email_exists(self, user_email: str) -> bool:
        """Check if email already exists"""
        return self.db.query(User.id).filter(User.user_email == user_email).first() is not None

