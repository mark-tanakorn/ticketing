"""Settings API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_db, get_current_user_smart, get_current_user_always_dev, get_user_identifier
from app.database.models.user import User
from app.core.config.manager import SettingsManager
from app.schemas.settings import (
    AllSettings,
    ExecutionSettings,
    AISettings,
    UISettings,
    StorageSettings,
    SecuritySettings,
    NetworkSettings,
    IntegrationsSettings,
    DeveloperSettings,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# RESPONSE MODELS
# ==============================================================================

class SettingsResponse(BaseModel):
    """Response model for settings operations."""
    success: bool
    message: str
    data: dict | None = None


# ==============================================================================
# GET ALL SETTINGS
# ==============================================================================

@router.get(
    "",
    response_model=AllSettings,
    summary="Get all settings",
    description="Retrieve all application settings"
)
async def get_all_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Get all application settings."""
    try:
        manager = SettingsManager(db)
        settings = manager.get_all_settings()
        return settings
    except Exception as e:
        logger.error(f"Failed to get all settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve settings: {str(e)}"
        )


# ==============================================================================
# UI SETTINGS
# ==============================================================================

@router.get(
    "/ui",
    response_model=UISettings,
    summary="Get UI settings",
    description="Retrieve user interface settings"
)
async def get_ui_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Get UI settings."""
    try:
        manager = SettingsManager(db)
        settings = manager.get_ui_settings()
        return settings
    except Exception as e:
        logger.error(f"Failed to get UI settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve UI settings: {str(e)}"
        )


@router.put(
    "/ui",
    response_model=UISettings,
    summary="Update UI settings",
    description="Update user interface settings"
)
async def update_ui_settings(
    settings: UISettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Update UI settings."""
    try:
        user_id = get_user_identifier(current_user)
        manager = SettingsManager(db)
        updated_settings = manager.update_ui_settings(
            settings, 
            updated_by=user_id
        )
        logger.info(f"UI settings updated by {user_id}")
        return updated_settings
    except Exception as e:
        logger.error(f"Failed to update UI settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update UI settings: {str(e)}"
        )


# ==============================================================================
# EXECUTION SETTINGS
# ==============================================================================

@router.get(
    "/execution",
    response_model=ExecutionSettings,
    summary="Get execution settings",
    description="Retrieve workflow execution settings"
)
async def get_execution_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Get execution settings."""
    try:
        manager = SettingsManager(db)
        return manager.get_execution_settings()
    except Exception as e:
        logger.error(f"Failed to get execution settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve execution settings: {str(e)}"
        )


@router.put(
    "/execution",
    response_model=ExecutionSettings,
    summary="Update execution settings",
    description="Update workflow execution settings"
)
async def update_execution_settings(
    settings: ExecutionSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Update execution settings."""
    try:
        manager = SettingsManager(db)
        updated_settings = manager.update_execution_settings(
            settings,
            updated_by=get_user_identifier(current_user)
        )
        logger.info(f"Execution settings updated by {get_user_identifier(current_user)}")
        return updated_settings
    except Exception as e:
        logger.error(f"Failed to update execution settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update execution settings: {str(e)}"
        )


# ==============================================================================
# AI SETTINGS
# ==============================================================================

@router.get(
    "/ai",
    response_model=AISettings,
    summary="Get AI settings",
    description="Retrieve AI provider settings"
)
async def get_ai_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Get AI settings."""
    try:
        manager = SettingsManager(db)
        return manager.get_ai_settings()
    except Exception as e:
        logger.error(f"Failed to get AI settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve AI settings: {str(e)}"
        )


@router.put(
    "/ai",
    response_model=AISettings,
    summary="Update AI settings",
    description="Update AI provider settings"
)
async def update_ai_settings(
    settings: AISettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Update AI settings."""
    try:
        manager = SettingsManager(db)
        updated_settings = manager.update_ai_settings(
            settings,
            updated_by=get_user_identifier(current_user)
        )
        logger.info(f"AI settings updated by {get_user_identifier(current_user)}")
        return updated_settings
    except Exception as e:
        logger.error(f"Failed to update AI settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update AI settings: {str(e)}"
        )


# ==============================================================================
# SECURITY SETTINGS
# ==============================================================================

@router.get(
    "/security",
    response_model=SecuritySettings,
    summary="Get security settings",
    description="Retrieve security settings"
)
async def get_security_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Get security settings."""
    try:
        manager = SettingsManager(db)
        return manager.get_security_settings()
    except Exception as e:
        logger.error(f"Failed to get security settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve security settings: {str(e)}"
        )


@router.put(
    "/security",
    response_model=SecuritySettings,
    summary="Update security settings",
    description="Update security settings"
)
async def update_security_settings(
    settings: SecuritySettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Update security settings."""
    try:
        manager = SettingsManager(db)
        updated_settings = manager.update_security_settings(
            settings,
            updated_by=get_user_identifier(current_user)
        )
        logger.info(f"Security settings updated by {get_user_identifier(current_user)}")
        return updated_settings
    except Exception as e:
        logger.error(f"Failed to update security settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update security settings: {str(e)}"
        )


# ==============================================================================
# DEVELOPER SETTINGS
# ==============================================================================

@router.get(
    "/developer",
    response_model=DeveloperSettings,
    summary="Get developer settings",
    description="Retrieve developer settings (always bypasses authentication to prevent lockouts)"
)
async def get_developer_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_always_dev)
):
    """
    Get developer settings.
    
    This endpoint ALWAYS bypasses authentication to prevent lockouts.
    Users can always access this to toggle dev mode back on.
    """
    try:
        manager = SettingsManager(db)
        return manager.get_developer_settings()
    except Exception as e:
        logger.error(f"Failed to get developer settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve developer settings: {str(e)}"
        )


@router.put(
    "/developer",
    response_model=DeveloperSettings,
    summary="Update developer settings",
    description="Update developer settings (always bypasses authentication to prevent lockouts)"
)
async def update_developer_settings(
    settings: DeveloperSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_always_dev)
):
    """
    Update developer settings.
    
    This endpoint ALWAYS bypasses authentication to prevent lockouts.
    This allows users to toggle dev mode back on even if they accidentally
    turned it off and don't have valid credentials.
    """
    try:
        manager = SettingsManager(db)
        updated_settings = manager.update_developer_settings(
            settings,
            updated_by=get_user_identifier(current_user)
        )
        logger.info(f"Developer settings updated by {get_user_identifier(current_user)}")
        return updated_settings
    except Exception as e:
        logger.error(f"Failed to update developer settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update developer settings: {str(e)}"
        )


# ==============================================================================
# STORAGE SETTINGS
# ==============================================================================

@router.get(
    "/storage",
    response_model=StorageSettings,
    summary="Get storage settings",
    description="Retrieve storage and cleanup settings"
)
async def get_storage_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Get storage settings."""
    try:
        manager = SettingsManager(db)
        return manager.get_storage_settings()
    except Exception as e:
        logger.error(f"Failed to get storage settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve storage settings: {str(e)}"
        )


@router.put(
    "/storage",
    response_model=StorageSettings,
    summary="Update storage settings",
    description="Update storage and cleanup settings"
)
async def update_storage_settings(
    settings: StorageSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Update storage settings."""
    try:
        manager = SettingsManager(db)
        updated_settings = manager.update_storage_settings(
            settings,
            updated_by=get_user_identifier(current_user)
        )
        logger.info(f"Storage settings updated by {get_user_identifier(current_user)}")
        return updated_settings
    except Exception as e:
        logger.error(f"Failed to update storage settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update storage settings: {str(e)}"
        )


# ==============================================================================
# INTEGRATIONS SETTINGS
# ==============================================================================

@router.get(
    "/integrations",
    response_model=IntegrationsSettings,
    summary="Get integrations settings",
    description="Retrieve third-party integration API keys (decrypted)"
)
async def get_integrations_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Get integrations settings with decrypted API keys."""
    try:
        manager = SettingsManager(db)
        return manager.get_integrations_settings()
    except Exception as e:
        logger.error(f"Failed to get integrations settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve integrations settings: {str(e)}"
        )


@router.put(
    "/integrations",
    response_model=IntegrationsSettings,
    summary="Update integrations settings",
    description="Update third-party integration API keys (auto-encrypted)"
)
async def update_integrations_settings(
    settings: IntegrationsSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Update integrations settings with automatic encryption of API keys."""
    try:
        manager = SettingsManager(db)
        updated_settings = manager.update_integrations_settings(
            settings,
            updated_by=get_user_identifier(current_user)
        )
        logger.info(f"Integrations settings updated by {get_user_identifier(current_user)}")
        return updated_settings
    except Exception as e:
        logger.error(f"Failed to update integrations settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update integrations settings: {str(e)}"
        )