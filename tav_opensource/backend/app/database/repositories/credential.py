"""
Credential Repository

CRUD operations for credentials with encryption support.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database.models.credential import Credential, AuthType
from app.utils.timezone import get_local_now

logger = logging.getLogger(__name__)


class CredentialRepository:
    """
    Repository for credential database operations.
    
    Provides CRUD operations for credentials. Encryption/decryption is
    handled by the CredentialManager service.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(
        self,
        user_id: int,
        name: str,
        service_type: str,
        auth_type: AuthType,
        encrypted_data: str,
        config_metadata: Optional[str] = None,
        description: Optional[str] = None
    ) -> Credential:
        """
        Create a new credential.
        
        Args:
            user_id: User ID who owns this credential
            name: User-friendly name
            service_type: Service identifier (e.g., 'slack', 'google')
            auth_type: Authentication type
            encrypted_data: Encrypted JSON string with credential data
            config_metadata: Optional metadata JSON string (not encrypted)
            description: Optional description
            
        Returns:
            Created Credential object
        """
        try:
            credential = Credential(
                user_id=user_id,
                name=name,
                service_type=service_type,
                auth_type=auth_type,
                encrypted_data=encrypted_data,
                config_metadata=config_metadata,
                description=description,
                is_active=True
            )
            
            self.db.add(credential)
            self.db.commit()
            self.db.refresh(credential)
            
            logger.info(f"Created credential {credential.id} for user {user_id}")
            return credential
            
        except Exception as e:
            logger.error(f"Error creating credential: {e}")
            self.db.rollback()
            raise
    
    def get_by_id(self, credential_id: int, user_id: int) -> Optional[Credential]:
        """
        Get a credential by ID.
        
        Args:
            credential_id: Credential ID
            user_id: User ID (for ownership check)
            
        Returns:
            Credential object or None if not found
        """
        try:
            credential = self.db.query(Credential).filter(
                and_(
                    Credential.id == credential_id,
                    Credential.user_id == user_id
                )
            ).first()
            
            return credential
            
        except Exception as e:
            logger.error(f"Error getting credential {credential_id}: {e}")
            return None
    
    def list_by_user(
        self,
        user_id: int,
        service_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Credential]:
        """
        List credentials for a user.
        
        Args:
            user_id: User ID
            service_type: Optional filter by service type
            is_active: Optional filter by active status
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of Credential objects
        """
        try:
            query = self.db.query(Credential).filter(Credential.user_id == user_id)
            
            if service_type:
                query = query.filter(Credential.service_type == service_type)
            
            if is_active is not None:
                query = query.filter(Credential.is_active == is_active)
            
            query = query.order_by(Credential.created_at.desc())
            query = query.limit(limit).offset(offset)
            
            credentials = query.all()
            return credentials
            
        except Exception as e:
            logger.error(f"Error listing credentials for user {user_id}: {e}")
            return []
    
    def count_by_user(
        self,
        user_id: int,
        service_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """
        Count credentials for a user.
        
        Args:
            user_id: User ID
            service_type: Optional filter by service type
            is_active: Optional filter by active status
            
        Returns:
            Number of credentials matching criteria
        """
        try:
            query = self.db.query(Credential).filter(Credential.user_id == user_id)
            
            if service_type:
                query = query.filter(Credential.service_type == service_type)
            
            if is_active is not None:
                query = query.filter(Credential.is_active == is_active)
            
            return query.count()
            
        except Exception as e:
            logger.error(f"Error counting credentials for user {user_id}: {e}")
            return 0
    
    def update(
        self,
        credential_id: int,
        user_id: int,
        name: Optional[str] = None,
        encrypted_data: Optional[str] = None,
        config_metadata: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Credential]:
        """
        Update a credential.
        
        Args:
            credential_id: Credential ID
            user_id: User ID (for ownership check)
            name: Optional new name
            encrypted_data: Optional new encrypted data
            config_metadata: Optional new metadata
            description: Optional new description
            is_active: Optional new active status
            
        Returns:
            Updated Credential object or None if not found
        """
        try:
            credential = self.get_by_id(credential_id, user_id)
            
            if not credential:
                logger.warning(f"Credential {credential_id} not found for user {user_id}")
                return None
            
            if name is not None:
                credential.name = name
            
            if encrypted_data is not None:
                credential.encrypted_data = encrypted_data
            
            if config_metadata is not None:
                credential.config_metadata = config_metadata
            
            if description is not None:
                credential.description = description
            
            if is_active is not None:
                credential.is_active = is_active
            
            credential.updated_at = get_local_now()
            
            self.db.commit()
            self.db.refresh(credential)
            
            logger.info(f"Updated credential {credential_id}")
            return credential
            
        except Exception as e:
            logger.error(f"Error updating credential {credential_id}: {e}")
            self.db.rollback()
            raise
    
    def delete(self, credential_id: int, user_id: int) -> bool:
        """
        Delete a credential.
        
        Args:
            credential_id: Credential ID
            user_id: User ID (for ownership check)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            credential = self.get_by_id(credential_id, user_id)
            
            if not credential:
                logger.warning(f"Credential {credential_id} not found for user {user_id}")
                return False
            
            self.db.delete(credential)
            self.db.commit()
            
            logger.info(f"Deleted credential {credential_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting credential {credential_id}: {e}")
            self.db.rollback()
            return False
    
    def update_last_used(self, credential_id: int) -> bool:
        """
        Update the last_used_at timestamp for a credential.
        
        Args:
            credential_id: Credential ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            credential = self.db.query(Credential).filter(
                Credential.id == credential_id
            ).first()
            
            if not credential:
                return False
            
            credential.last_used_at = get_local_now()
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating last_used for credential {credential_id}: {e}")
            self.db.rollback()
            return False
    
    def exists(
        self,
        user_id: int,
        name: Optional[str] = None,
        service_type: Optional[str] = None
    ) -> bool:
        """
        Check if a credential exists.
        
        Args:
            user_id: User ID
            name: Optional credential name
            service_type: Optional service type
            
        Returns:
            True if credential exists
        """
        try:
            query = self.db.query(Credential).filter(Credential.user_id == user_id)
            
            if name:
                query = query.filter(Credential.name == name)
            
            if service_type:
                query = query.filter(Credential.service_type == service_type)
            
            return query.count() > 0
            
        except Exception as e:
            logger.error(f"Error checking credential existence: {e}")
            return False
    
    def get_by_service_type(
        self,
        user_id: int,
        service_type: str,
        is_active: bool = True
    ) -> List[Credential]:
        """
        Get all credentials for a specific service type.
        
        Args:
            user_id: User ID
            service_type: Service type to filter by
            is_active: Whether to only return active credentials
            
        Returns:
            List of Credential objects
        """
        try:
            query = self.db.query(Credential).filter(
                and_(
                    Credential.user_id == user_id,
                    Credential.service_type == service_type
                )
            )
            
            if is_active:
                query = query.filter(Credential.is_active == True)
            
            return query.all()
            
        except Exception as e:
            logger.error(f"Error getting credentials by service type {service_type}: {e}")
            return []

