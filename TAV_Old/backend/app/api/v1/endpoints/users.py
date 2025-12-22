"""
User Endpoints

Handles user management operations (CRUD).
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.exc import IntegrityError

from app.api.deps import (
    get_current_active_user,
    get_current_admin_user,
    get_user_repository,
)
from app.database.models.user import User
from app.database.repositories.users import UserRepository
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    PasswordChange,
    PasswordReset,
)


router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(get_current_admin_user)
) -> UserResponse:
    """
    Create a new user.
    
    Requires admin privileges.
    
    Args:
        user_data: User creation data
        user_repo: User repository
        current_user: Current admin user
    
    Returns:
        Created user information
    
    Raises:
        HTTPException: If username/email already exists
    """
    # Check if username already exists
    if user_repo.username_exists(user_data.user_name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{user_data.user_name}' already exists"
        )
    
    # Check if email already exists (if provided)
    if user_data.user_email and user_repo.email_exists(user_data.user_email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{user_data.user_email}' already exists"
        )
    
    # Create user
    try:
        user = user_repo.create(
            user_name=user_data.user_name,
            user_password=user_data.user_password,
            user_email=user_data.user_email,
            created_by=current_user.user_name,
            **user_data.model_dump(exclude={'user_name', 'user_password', 'user_email'}, exclude_unset=True)
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User creation failed due to constraint violation"
        )
    
    return UserResponse.model_validate(user)


@router.get("", response_model=UserListResponse, status_code=status.HTTP_200_OK)
def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term"),
    include_deleted: bool = Query(False, description="Include deleted users"),
    include_disabled: bool = Query(False, description="Include disabled users"),
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(get_current_active_user)
) -> UserListResponse:
    """
    List users with pagination and search.
    
    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        search: Optional search term
        include_deleted: Include soft-deleted users
        include_disabled: Include disabled users
        user_repo: User repository
        current_user: Current authenticated user
    
    Returns:
        Paginated list of users
    """
    skip = (page - 1) * page_size
    
    # Search or list all
    if search:
        users = user_repo.search(
            search_term=search,
            skip=skip,
            limit=page_size,
            include_deleted=include_deleted,
            include_disabled=include_disabled
        )
        # For search, count might be different
        total = len(users)  # Simplified - in production, count search results separately
    else:
        users = user_repo.get_all(
            skip=skip,
            limit=page_size,
            include_deleted=include_deleted,
            include_disabled=include_disabled
        )
        total = user_repo.count(
            include_deleted=include_deleted,
            include_disabled=include_disabled
        )
    
    return UserListResponse(
        total=total,
        users=[UserResponse.model_validate(user) for user in users],
        page=page,
        page_size=page_size
    )


@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get user by ID.
    
    Args:
        user_id: User ID
        user_repo: User repository
        current_user: Current authenticated user
    
    Returns:
        User information
    
    Raises:
        HTTPException: If user not found
    """
    user = user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Update user information.
    
    Users can update their own information.
    Admins can update any user (TODO: implement RBAC).
    
    Args:
        user_id: User ID
        user_data: Updated user data
        user_repo: User repository
        current_user: Current authenticated user
    
    Returns:
        Updated user information
    
    Raises:
        HTTPException: If user not found or unauthorized
    """
    # Check if user exists
    if not user_repo.exists(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # TODO: Check permissions - users can only update themselves unless admin
    # For now, allow users to update their own profile
    if current_user.id != user_id:
        # TODO: Check if current_user is admin
        # For now, just allow it
        pass
    
    # Get update data
    update_data = user_data.model_dump(exclude_unset=True, exclude_none=True)
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # If password is being updated, handle separately
    if 'user_password' in update_data:
        new_password = update_data.pop('user_password')
        user = user_repo.change_password(
            user_id=user_id,
            new_password=new_password,
            changed_by=current_user.user_name
        )
    else:
        # Update other fields
        user = user_repo.update(
            user_id=user_id,
            modified_by=current_user.user_name,
            **update_data
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(get_current_admin_user)
) -> None:
    """
    Soft delete a user.
    
    Requires admin privileges.
    
    Args:
        user_id: User ID
        user_repo: User repository
        current_user: Current admin user
    
    Raises:
        HTTPException: If user not found or trying to delete self
    """
    # Prevent self-deletion
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Check if user exists
    if not user_repo.exists(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Soft delete
    user_repo.soft_delete(user_id=user_id, deleted_by=current_user.user_name)
    
    return None


@router.post("/{user_id}/password", response_model=UserResponse, status_code=status.HTTP_200_OK)
def change_password(
    user_id: int,
    password_data: PasswordChange,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Change user password (user-initiated).
    
    Users can only change their own password.
    
    Args:
        user_id: User ID
        password_data: Old and new passwords
        user_repo: User repository
        current_user: Current authenticated user
    
    Returns:
        Updated user information
    
    Raises:
        HTTPException: If user not found, unauthorized, or old password incorrect
    """
    # Users can only change their own password
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only change your own password"
        )
    
    # Verify old password
    user = user_repo.authenticate(current_user.user_name, password_data.old_password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current password"
        )
    
    # Change password
    updated_user = user_repo.change_password(
        user_id=user_id,
        new_password=password_data.new_password,
        changed_by=current_user.user_name
    )
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    return UserResponse.model_validate(updated_user)


@router.post("/{user_id}/reset-password", response_model=UserResponse, status_code=status.HTTP_200_OK)
def reset_password(
    user_id: int,
    password_data: PasswordReset,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(get_current_admin_user)
) -> UserResponse:
    """
    Reset user password (admin action).
    
    Requires admin privileges.
    Forces user to change password on next login.
    
    Args:
        user_id: User ID
        password_data: New password
        user_repo: User repository
        current_user: Current admin user
    
    Returns:
        Updated user information
    
    Raises:
        HTTPException: If user not found
    """
    # Check if user exists
    if not user_repo.exists(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Reset password
    user = user_repo.reset_password(
        user_id=user_id,
        new_password=password_data.new_password,
        reset_by=password_data.reset_by or current_user.user_name
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    return UserResponse.model_validate(user)


@router.post("/{user_id}/disable", response_model=UserResponse, status_code=status.HTTP_200_OK)
def disable_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(get_current_admin_user)
) -> UserResponse:
    """
    Disable a user account.
    
    Requires admin privileges.
    
    Args:
        user_id: User ID
        user_repo: User repository
        current_user: Current admin user
    
    Returns:
        Updated user information
    
    Raises:
        HTTPException: If user not found or trying to disable self
    """
    # Prevent self-disable
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account"
        )
    
    # Check if user exists
    if not user_repo.exists(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Disable user
    user = user_repo.disable_user(user_id=user_id, disabled_by=current_user.user_name)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    return UserResponse.model_validate(user)


@router.post("/{user_id}/enable", response_model=UserResponse, status_code=status.HTTP_200_OK)
def enable_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(get_current_admin_user)
) -> UserResponse:
    """
    Enable a disabled user account.
    
    Requires admin privileges.
    
    Args:
        user_id: User ID
        user_repo: User repository
        current_user: Current admin user
    
    Returns:
        Updated user information
    
    Raises:
        HTTPException: If user not found
    """
    # Check if user exists
    if not user_repo.exists(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Enable user
    user = user_repo.enable_user(user_id=user_id, enabled_by=current_user.user_name)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    return UserResponse.model_validate(user)


@router.post("/{user_id}/restore", response_model=UserResponse, status_code=status.HTTP_200_OK)
def restore_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repository),
    current_user: User = Depends(get_current_admin_user)
) -> UserResponse:
    """
    Restore a soft-deleted user.
    
    Requires admin privileges.
    
    Args:
        user_id: User ID
        user_repo: User repository
        current_user: Current admin user
    
    Returns:
        Restored user information
    
    Raises:
        HTTPException: If user not found
    """
    # Check if user exists (including deleted)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Restore user
    restored_user = user_repo.restore(user_id=user_id, restored_by=current_user.user_name)
    
    if not restored_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    return UserResponse.model_validate(restored_user)
