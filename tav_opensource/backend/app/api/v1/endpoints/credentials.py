"""
Credential Management API Endpoints

CRUD operations for secure credential storage.

Endpoints:
POST /credentials - Create new credential
GET /credentials - List user's credentials
GET /credentials/{id} - Get specific credential (with decrypted data)
PUT /credentials/{id} - Update credential
DELETE /credentials/{id} - Delete credential
GET /credentials/types - Get available credential types
POST /credentials/{id}/test - Test credential connection (future)
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user_smart
from app.database.models.user import User
from app.services.credential_manager import CredentialManager
from app.schemas.credential import (
    CredentialCreate,
    CredentialUpdate,
    CredentialResponse,
    CredentialWithData,
    CredentialListResponse,
    CredentialTypeResponse,
    CREDENTIAL_TYPE_DEFINITIONS
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=CredentialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new credential",
    description="Create a new credential with encrypted storage"
)
async def create_credential(
    credential: CredentialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Create a new credential.
    
    The credential data will be encrypted before storage.
    Sensitive fields (API keys, passwords, tokens) are automatically encrypted
    based on the credential type.
    
    Args:
        credential: Credential creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created credential (without sensitive data)
        
    Raises:
        HTTPException 400: If validation fails
        HTTPException 500: If creation fails
    """
    try:
        credential_manager = CredentialManager(db)
        
        result = credential_manager.create_credential(
            user_id=current_user.id,
            credential_data=credential
        )
        
        logger.info(f"User {current_user.id} created credential {result.id}")
        return result
        
    except ValueError as e:
        error_msg = str(e)
        logger.warning(f"Validation error creating credential: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_msg
        )
    except Exception as e:
        logger.error(f"Error creating credential: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create credential"
        )


@router.get(
    "/types/list",
    summary="Get credential types",
    description="Get available credential type definitions"
)
async def get_credential_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Get available credential type definitions.
    
    Returns information about supported credential types including:
    - Type name and description
    - Required and optional fields
    - Field types and labels
    
    This is useful for dynamically building credential creation forms in the UI.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dictionary of credential type definitions
    """
    try:
        credential_manager = CredentialManager(db)
        types = credential_manager.get_credential_types()
        
        return {
            "types": types,
            "count": len(types)
        }
        
    except Exception as e:
        logger.error(f"Error getting credential types: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get credential types"
        )


@router.get(
    "",
    response_model=CredentialListResponse,
    summary="List user credentials",
    description="Get list of all credentials for the current user"
)
async def list_credentials(
    service_type: Optional[str] = Query(None, description="Filter by service type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    List credentials for the current user.
    
    Returns credentials without sensitive data. Use GET /credentials/{id}
    to retrieve the decrypted credential data.
    
    Args:
        service_type: Optional filter by service type
        is_active: Optional filter by active status
        limit: Maximum results (default 100)
        offset: Pagination offset
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of credentials with total count
    """
    try:
        credential_manager = CredentialManager(db)
        
        credentials, total = credential_manager.list_credentials(
            user_id=current_user.id,
            service_type=service_type,
            is_active=is_active,
            limit=limit,
            offset=offset
        )
        
        return CredentialListResponse(
            credentials=credentials,
            total=total
        )
        
    except Exception as e:
        logger.error(f"Error listing credentials: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list credentials"
        )


@router.get(
    "/{credential_id}",
    response_model=CredentialWithData,
    summary="Get credential with data",
    description="Get specific credential with decrypted data"
)
async def get_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Get a credential with decrypted data.
    
    ⚠️ This endpoint returns sensitive data (API keys, passwords, tokens).
    Use with caution and ensure proper access controls.
    
    The last_used_at timestamp will be updated when this endpoint is called.
    
    Args:
        credential_id: Credential ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Credential with decrypted data
        
    Raises:
        HTTPException 404: If credential not found
        HTTPException 500: If retrieval fails
    """
    try:
        credential_manager = CredentialManager(db)
        
        credential = credential_manager.get_credential(
            credential_id=credential_id,
            user_id=current_user.id,
            include_data=True
        )
        
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credential {credential_id} not found"
            )
        
        return credential
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting credential {credential_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve credential"
        )


@router.put(
    "/{credential_id}",
    response_model=CredentialResponse,
    summary="Update credential",
    description="Update an existing credential"
)
async def update_credential(
    credential_id: int,
    credential_update: CredentialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Update a credential.
    
    You can update any combination of:
    - name: Display name
    - credential_data: Encrypted credential data (API keys, tokens, etc.)
    - metadata: Non-sensitive metadata
    - description: Description/notes
    - is_active: Active status
    
    Args:
        credential_id: Credential ID
        credential_update: Update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated credential (without sensitive data)
        
    Raises:
        HTTPException 404: If credential not found
        HTTPException 500: If update fails
    """
    try:
        credential_manager = CredentialManager(db)
        
        credential = credential_manager.update_credential(
            credential_id=credential_id,
            user_id=current_user.id,
            update_data=credential_update
        )
        
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credential {credential_id} not found"
            )
        
        logger.info(f"User {current_user.id} updated credential {credential_id}")
        return credential
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating credential {credential_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update credential"
        )


@router.delete(
    "/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete credential",
    description="Delete a credential"
)
async def delete_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Delete a credential.
    
    ⚠️ This action is permanent and cannot be undone.
    
    Args:
        credential_id: Credential ID
        db: Database session
        current_user: Current authenticated user
        
    Raises:
        HTTPException 404: If credential not found
        HTTPException 500: If deletion fails
    """
    try:
        credential_manager = CredentialManager(db)
        
        result = credential_manager.delete_credential(
            credential_id=credential_id,
            user_id=current_user.id
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credential {credential_id} not found"
            )
        
        logger.info(f"User {current_user.id} deleted credential {credential_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting credential {credential_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete credential"
        )


@router.post(
    "/{credential_id}/test",
    summary="Test credential",
    description="Test if credential works (future implementation)"
)
async def test_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Test a credential.
    
    This endpoint will make a test API call to verify the credential works.
    
    ⚠️ This is a placeholder for future implementation.
    
    Args:
        credential_id: Credential ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Test result
        
    Raises:
        HTTPException 404: If credential not found
        HTTPException 501: Not implemented
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Credential testing not yet implemented"
    )

