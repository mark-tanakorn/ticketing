"""
Custom Nodes - user library endpoints (My Nodes).

Split out from endpoints/custom_nodes.py to keep modules small.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_smart, get_db
from app.api.v1.schemas.custom_nodes import (
    CustomNodeDetail,
    CustomNodeListResponse,
    CustomNodeSummary,
    DeleteCustomNodeResponse,
    NodeValidationResponse,
    RegisterCustomNodeResponse,
    UpdateCustomNodeCodeRequest,
    UpdateCustomNodeCodeResponse,
    ValidationError,
)
from app.database.models.conversation import CustomNode
from app.database.models.user import User
from app.utils.custom_node_metadata import extract_custom_node_metadata

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/library", response_model=CustomNodeListResponse)
async def list_my_custom_nodes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    """List custom nodes created by the current user."""
    try:
        nodes = (
            db.query(CustomNode)
            .filter(CustomNode.user_id == current_user.id)
            .order_by(CustomNode.updated_at.desc())
            .all()
        )

        summaries = [
            CustomNodeSummary(
                id=n.id,
                node_type=n.node_type,
                display_name=n.display_name,
                description=n.description,
                category=n.category,
                icon=n.icon,
                version=n.version,
                is_active=n.is_active,
                is_registered=n.is_registered,
                file_path=n.file_path,
                created_at=n.created_at,
                updated_at=n.updated_at,
            )
            for n in nodes
        ]

        return CustomNodeListResponse(success=True, nodes=summaries, total=len(summaries))
    except Exception as e:
        logger.error(f"❌ Failed to list custom nodes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list custom nodes: {str(e)}",
        )


@router.get("/library/{custom_node_id}", response_model=CustomNodeDetail)
async def get_my_custom_node(
    custom_node_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    """Get a single custom node created by the current user."""
    node = (
        db.query(CustomNode)
        .filter(CustomNode.id == custom_node_id, CustomNode.user_id == current_user.id)
        .first()
    )
    if not node:
        raise HTTPException(status_code=404, detail="Custom node not found")

    return CustomNodeDetail(
        id=node.id,
        node_type=node.node_type,
        display_name=node.display_name,
        description=node.description,
        category=node.category,
        icon=node.icon,
        version=node.version,
        is_active=node.is_active,
        is_registered=node.is_registered,
        file_path=node.file_path,
        created_at=node.created_at,
        updated_at=node.updated_at,
        code=node.code,
    )


@router.post("/library/{custom_node_id}/code", response_model=UpdateCustomNodeCodeResponse)
async def update_my_custom_node_code(
    custom_node_id: int,
    request: UpdateCustomNodeCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    """
    Update code for an existing custom node in the DB (does not write to filesystem).
    This allows web-based editing; user can register/reload separately.
    """
    node = (
        db.query(CustomNode)
        .filter(CustomNode.id == custom_node_id, CustomNode.user_id == current_user.id)
        .first()
    )
    if not node:
        raise HTTPException(status_code=404, detail="Custom node not found")

    code = (request.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Code cannot be empty")

    # Ensure node_type stays stable (mutable latest version, but same identity)
    from app.services.code_validator import NodeCodeValidator

    validator = NodeCodeValidator()
    validation = validator.validate(code)
    new_type = validation.get("node_type")
    if new_type and new_type != node.node_type:
        raise HTTPException(
            status_code=400,
            detail=f"node_type cannot be changed in-place (existing='{node.node_type}', new='{new_type}').",
        )

    node.code = code
    node.updated_at = datetime.utcnow()
    node.is_registered = False  # code changed; requires re-register/reload to take effect
    db.commit()

    detail = CustomNodeDetail(
        id=node.id,
        node_type=node.node_type,
        display_name=node.display_name,
        description=node.description,
        category=node.category,
        icon=node.icon,
        version=node.version,
        is_active=node.is_active,
        is_registered=node.is_registered,
        file_path=node.file_path,
        created_at=node.created_at,
        updated_at=node.updated_at,
        code=node.code,
    )
    return UpdateCustomNodeCodeResponse(success=True, node=detail)


@router.post("/library/{custom_node_id}/validate", response_model=NodeValidationResponse)
async def validate_my_custom_node(
    custom_node_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    """Validate the stored code for a custom node."""
    node = (
        db.query(CustomNode)
        .filter(CustomNode.id == custom_node_id, CustomNode.user_id == current_user.id)
        .first()
    )
    if not node:
        raise HTTPException(status_code=404, detail="Custom node not found")

    try:
        from app.services.code_validator import NodeCodeValidator

        validator = NodeCodeValidator()
        result = validator.validate(node.code or "")
        errors = [ValidationError(message=err, severity="error") for err in result.get("errors", [])]
        warnings = [ValidationError(message=warn, severity="warning") for warn in result.get("warnings", [])]
        return NodeValidationResponse(
            valid=result["valid"],
            errors=errors,
            warnings=warnings,
            node_type=result.get("node_type"),
            class_name=result.get("class_name"),
            message="Validation complete" if result["valid"] else "Validation failed",
        )
    except Exception as e:
        logger.error(f"❌ Validation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate node code: {str(e)}",
        )


@router.post("/library/{custom_node_id}/register", response_model=RegisterCustomNodeResponse)
async def register_my_custom_node(
    custom_node_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    """
    Save the node code to filesystem and hot-reload into registry.
    """
    node = (
        db.query(CustomNode)
        .filter(CustomNode.id == custom_node_id, CustomNode.user_id == current_user.id)
        .first()
    )
    if not node:
        raise HTTPException(status_code=404, detail="Custom node not found")

    from app.services.code_validator import NodeCodeValidator
    from app.services.node_saver import NodeSaver

    validator = NodeCodeValidator()
    validation = validator.validate(node.code or "")
    if not validation.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Code validation failed: {validation.get('errors')}",
        )

    detected_type = validation.get("node_type") or node.node_type
    if detected_type != node.node_type:
        raise HTTPException(
            status_code=400,
            detail=f"node_type mismatch (db='{node.node_type}', code='{detected_type}')",
        )

    saver = NodeSaver()
    save_result = saver.save_node(code=node.code, node_type=node.node_type, overwrite=True)
    node.file_path = save_result.get("file_path")

    # Sync display metadata from source code (source-of-truth)
    meta = extract_custom_node_metadata(node.code or "")
    if meta.category:
        node.category = meta.category
    if meta.name:
        node.display_name = meta.name
    if meta.description:
        node.description = meta.description
    if meta.icon:
        node.icon = meta.icon
    if meta.version:
        node.version = meta.version

    node.updated_at = datetime.utcnow()
    db.commit()

    registered = False
    try:
        from app.services.node_reloader import NodeReloader

        reloader = NodeReloader()
        await reloader.reload_custom_nodes()
        node.is_registered = True
        node.updated_at = datetime.utcnow()
        db.commit()
        registered = True
    except Exception as reload_error:
        logger.warning(f"⚠️ Hot-reload failed: {reload_error}")

    summary = CustomNodeSummary(
        id=node.id,
        node_type=node.node_type,
        display_name=node.display_name,
        description=node.description,
        category=node.category,
        icon=node.icon,
        version=node.version,
        is_active=node.is_active,
        is_registered=node.is_registered,
        file_path=node.file_path,
        created_at=node.created_at,
        updated_at=node.updated_at,
    )

    return RegisterCustomNodeResponse(
        success=registered,
        node=summary,
        message=save_result.get("message") or ("Registered" if registered else "Saved, but reload failed"),
    )


@router.delete("/library/{custom_node_id}", response_model=DeleteCustomNodeResponse)
async def delete_my_custom_node(
    custom_node_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart),
):
    """
    Delete a custom node (DB + filesystem) and hot-reload so it disappears from registry.
    """
    node = (
        db.query(CustomNode)
        .filter(CustomNode.id == custom_node_id, CustomNode.user_id == current_user.id)
        .first()
    )
    if not node:
        raise HTTPException(status_code=404, detail="Custom node not found")

    deleted_file_path = None
    try:
        from app.services.node_saver import NodeSaver

        saver = NodeSaver()
        try:
            deleted_file_path = saver.delete_node(node.node_type)
        except FileNotFoundError:
            # File might already be gone; still delete DB record.
            deleted_file_path = node.file_path
    except Exception as e:
        # We still allow DB deletion if filesystem deletion fails? For now: block and report.
        logger.error(f"❌ Failed to delete node file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete node file: {str(e)}")

    deleted_id = node.id
    deleted_type = node.node_type
    db.delete(node)
    db.commit()

    # Hot-reload so registry removes it
    try:
        from app.services.node_reloader import NodeReloader

        reloader = NodeReloader()
        await reloader.reload_custom_nodes()
    except Exception as reload_error:
        logger.warning(f"⚠️ Hot-reload after delete failed: {reload_error}")

    return DeleteCustomNodeResponse(
        success=True,
        deleted_id=deleted_id,
        deleted_node_type=deleted_type,
        deleted_file_path=deleted_file_path,
        message="Custom node deleted",
    )


