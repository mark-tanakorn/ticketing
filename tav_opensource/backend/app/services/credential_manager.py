"""
Credential Manager Service

High-level credential management with encryption/decryption support.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.models.credential import Credential, AuthType
from app.database.repositories.credential import CredentialRepository
from app.security.encryption import encrypt_value, decrypt_value, encrypt_dict, decrypt_dict
from app.schemas.credential import (
    CredentialCreate,
    CredentialUpdate,
    CredentialResponse,
    CredentialWithData,
    CredentialInDB,
    CREDENTIAL_TYPE_DEFINITIONS
)

logger = logging.getLogger(__name__)


class CredentialManager:
    """
    High-level credential management service.
    
    Handles encryption/decryption of credential data and provides
    a clean interface for credential operations.
    """
    
    def __init__(self, db: Session):
        """
        Initialize credential manager.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.repository = CredentialRepository(db)
    
    def create_credential(
        self,
        user_id: int,
        credential_data: CredentialCreate
    ) -> CredentialResponse:
        """
        Create a new credential with encryption.
        
        Args:
            user_id: User ID who owns this credential
            credential_data: Credential creation data
            
        Returns:
            CredentialResponse object (without sensitive data)
            
        Raises:
            ValueError: If credential data is invalid
            Exception: If database operation fails
        """
        try:
            # Validate credential data against type definition if available
            auth_type_str = credential_data.auth_type.value
            if auth_type_str in CREDENTIAL_TYPE_DEFINITIONS:
                type_def = CREDENTIAL_TYPE_DEFINITIONS[auth_type_str]
                required_fields = [f.name for f in type_def.fields if f.required]
                
                # Check for required fields
                for field in required_fields:
                    if field not in credential_data.credential_data:
                        raise ValueError(f"Required field '{field}' missing for {type_def.name}")
            
            # Determine which fields to encrypt based on type definition
            fields_to_encrypt = []
            if auth_type_str in CREDENTIAL_TYPE_DEFINITIONS:
                type_def = CREDENTIAL_TYPE_DEFINITIONS[auth_type_str]
                fields_to_encrypt = [f.name for f in type_def.fields if f.encrypted]
            else:
                # For custom types, encrypt all fields by default
                fields_to_encrypt = list(credential_data.credential_data.keys())
            
            # Encrypt sensitive fields
            encrypted_data_dict = encrypt_dict(
                credential_data.credential_data,
                fields_to_encrypt
            )
            encrypted_data_json = json.dumps(encrypted_data_dict)
            
            # Prepare metadata (not encrypted)
            config_metadata_json = None
            if credential_data.metadata:
                config_metadata_json = json.dumps(credential_data.metadata)
            
            # Create credential in database
            credential = self.repository.create(
                user_id=user_id,
                name=credential_data.name,
                service_type=credential_data.service_type,
                auth_type=credential_data.auth_type,
                encrypted_data=encrypted_data_json,
                config_metadata=config_metadata_json,
                description=credential_data.description
            )
            
            logger.info(f"Created credential {credential.id} for user {user_id}")
            
            # Return response without sensitive data
            return self._to_response(credential)
            
        except ValueError as e:
            logger.warning(f"Validation error creating credential: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating credential: {e}")
            raise
    
    def get_credential(
        self,
        credential_id: int,
        user_id: int,
        include_data: bool = False
    ) -> Optional[CredentialResponse | CredentialWithData]:
        """
        Get a credential by ID.
        
        Args:
            credential_id: Credential ID
            user_id: User ID (for ownership check)
            include_data: Whether to include decrypted credential data
            
        Returns:
            CredentialResponse or CredentialWithData, or None if not found
        """
        try:
            credential = self.repository.get_by_id(credential_id, user_id)
            
            if not credential:
                return None
            
            if include_data:
                # Update last_used timestamp
                self.repository.update_last_used(credential_id)
                return self._to_response_with_data(credential)
            else:
                return self._to_response(credential)
                
        except Exception as e:
            logger.error(f"Error getting credential {credential_id}: {e}")
            return None
    
    def list_credentials(
        self,
        user_id: int,
        service_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[CredentialResponse], int]:
        """
        List credentials for a user.
        
        Args:
            user_id: User ID
            service_type: Optional filter by service type
            is_active: Optional filter by active status
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            Tuple of (list of CredentialResponse, total count)
        """
        try:
            credentials = self.repository.list_by_user(
                user_id=user_id,
                service_type=service_type,
                is_active=is_active,
                limit=limit,
                offset=offset
            )
            
            total = self.repository.count_by_user(
                user_id=user_id,
                service_type=service_type,
                is_active=is_active
            )
            
            responses = [self._to_response(c) for c in credentials]
            return responses, total
            
        except Exception as e:
            logger.error(f"Error listing credentials for user {user_id}: {e}")
            return [], 0
    
    def update_credential(
        self,
        credential_id: int,
        user_id: int,
        update_data: CredentialUpdate
    ) -> Optional[CredentialResponse]:
        """
        Update a credential.
        
        Args:
            credential_id: Credential ID
            user_id: User ID (for ownership check)
            update_data: Update data
            
        Returns:
            Updated CredentialResponse or None if not found
        """
        try:
            # Get existing credential to determine auth_type
            existing = self.repository.get_by_id(credential_id, user_id)
            if not existing:
                return None
            
            # Prepare update parameters
            update_params = {}
            
            if update_data.name is not None:
                update_params['name'] = update_data.name
            
            if update_data.credential_data is not None:
                # Determine which fields to encrypt
                auth_type_str = existing.auth_type.value
                fields_to_encrypt = []
                
                if auth_type_str in CREDENTIAL_TYPE_DEFINITIONS:
                    type_def = CREDENTIAL_TYPE_DEFINITIONS[auth_type_str]
                    fields_to_encrypt = [f.name for f in type_def.fields if f.encrypted]
                else:
                    fields_to_encrypt = list(update_data.credential_data.keys())
                
                # Encrypt and serialize
                encrypted_data_dict = encrypt_dict(
                    update_data.credential_data,
                    fields_to_encrypt
                )
                update_params['encrypted_data'] = json.dumps(encrypted_data_dict)
            
            if update_data.metadata is not None:
                update_params['config_metadata'] = json.dumps(update_data.metadata)
            
            if update_data.description is not None:
                update_params['description'] = update_data.description
            
            if update_data.is_active is not None:
                update_params['is_active'] = update_data.is_active
            
            # Update credential
            credential = self.repository.update(
                credential_id=credential_id,
                user_id=user_id,
                **update_params
            )
            
            if not credential:
                return None
            
            logger.info(f"Updated credential {credential_id}")
            return self._to_response(credential)
            
        except Exception as e:
            logger.error(f"Error updating credential {credential_id}: {e}")
            raise
    
    def delete_credential(self, credential_id: int, user_id: int) -> bool:
        """
        Delete a credential.
        
        Args:
            credential_id: Credential ID
            user_id: User ID (for ownership check)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.repository.delete(credential_id, user_id)
            
            if result:
                logger.info(f"Deleted credential {credential_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error deleting credential {credential_id}: {e}")
            return False
    
    def get_credential_data(
        self,
        credential_id: int,
        user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get decrypted credential data.
        
        This method is used by the executor to inject credentials into nodes.
        
        Args:
            credential_id: Credential ID
            user_id: Optional user ID for ownership check (skip for system use)
            
        Returns:
            Decrypted credential data dictionary or None
        """
        try:
            if user_id:
                credential = self.repository.get_by_id(credential_id, user_id)
            else:
                # System access (e.g., from executor)
                credential = self.db.query(Credential).filter(
                    Credential.id == credential_id
                ).first()
            
            if not credential or not credential.is_active:
                return None
            
            # Update last_used timestamp
            self.repository.update_last_used(credential_id)
            
            # Decrypt data
            return self._decrypt_credential_data(credential)
            
        except Exception as e:
            logger.error(f"Error getting credential data {credential_id}: {e}")
            return None
    
    def test_credential(
        self,
        credential_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Test a credential (placeholder for future implementation).
        
        Args:
            credential_id: Credential ID
            user_id: User ID (for ownership check)
            
        Returns:
            Test result dictionary
        """
        # TODO: Implement credential testing logic
        # This would make actual API calls to verify credentials work
        return {
            "success": True,
            "message": "Credential test not implemented yet"
        }
    
    def get_credential_types(self) -> Dict[str, Any]:
        """
        Get available credential type definitions.
        
        Returns:
            Dictionary of credential type definitions
        """
        return {
            type_id: {
                "name": type_def.name,
                "auth_type": type_def.auth_type.value,
                "description": type_def.description,
                "fields": [
                    {
                        "name": field.name,
                        "type": field.type,
                        "required": field.required,
                        "label": field.label,
                        "description": field.description,
                        # Don't expose which fields are encrypted (security)
                    }
                    for field in type_def.fields
                ]
            }
            for type_id, type_def in CREDENTIAL_TYPE_DEFINITIONS.items()
        }
    
    # Private helper methods
    
    def _to_response(self, credential: Credential) -> CredentialResponse:
        """Convert Credential model to CredentialResponse."""
        metadata_dict = None
        if credential.config_metadata:
            try:
                metadata_dict = json.loads(credential.config_metadata)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse metadata for credential {credential.id}")
        
        return CredentialResponse(
            id=credential.id,
            user_id=credential.user_id,
            name=credential.name,
            service_type=credential.service_type,
            auth_type=credential.auth_type,
            description=credential.description,
            metadata=metadata_dict,
            is_active=credential.is_active,
            created_at=credential.created_at,
            updated_at=credential.updated_at,
            last_used_at=credential.last_used_at
        )
    
    def _to_response_with_data(self, credential: Credential) -> CredentialWithData:
        """Convert Credential model to CredentialWithData (with decrypted data)."""
        base_response = self._to_response(credential)
        decrypted_data = self._decrypt_credential_data(credential)
        
        return CredentialWithData(
            **base_response.model_dump(),
            credential_data=decrypted_data
        )
    
    def _decrypt_credential_data(self, credential: Credential) -> Dict[str, Any]:
        """Decrypt credential data."""
        try:
            # Parse encrypted JSON
            encrypted_data = json.loads(credential.encrypted_data)
            
            # Determine which fields to decrypt
            auth_type_str = credential.auth_type.value
            fields_to_decrypt = []
            
            if auth_type_str in CREDENTIAL_TYPE_DEFINITIONS:
                type_def = CREDENTIAL_TYPE_DEFINITIONS[auth_type_str]
                fields_to_decrypt = [f.name for f in type_def.fields if f.encrypted]
            else:
                # For custom types, try to decrypt all string fields
                fields_to_decrypt = list(encrypted_data.keys())
            
            # Decrypt sensitive fields
            decrypted_data = decrypt_dict(encrypted_data, fields_to_decrypt)
            
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Error decrypting credential {credential.id}: {e}")
            raise ValueError("Failed to decrypt credential data")

