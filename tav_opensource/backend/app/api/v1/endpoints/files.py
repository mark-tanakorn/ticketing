"""
File Upload and Management API Endpoints

Handles file uploads, downloads, listing, and deletion.
"""

import logging
import hashlib
import mimetypes
import os
import shutil
from datetime import timedelta
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user_smart, get_user_identifier
from app.database.models.user import User
from app.database.models.file import File, FileType, FileCategory
from app.database.repositories.file import FileRepository
from app.core.config.manager import SettingsManager
from app.utils.timezone import get_local_now

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class FileUploadRequest(BaseModel):
    """File upload configuration."""
    file_type: FileType = Field(default=FileType.UPLOAD, description="File type for lifecycle management")
    file_category: Optional[FileCategory] = Field(default=None, description="File content category (auto-detected if None)")
    workflow_id: Optional[str] = Field(default=None, description="Associated workflow ID")
    execution_id: Optional[str] = Field(default=None, description="Associated execution ID")
    make_permanent: bool = Field(default=False, description="Mark file as permanent (never expires)")


class FileMetadataResponse(BaseModel):
    """File metadata response."""
    id: str
    filename: str
    file_size_bytes: int
    mime_type: str
    file_type: str
    file_category: str
    storage_path: str
    uploaded_at: str
    expires_at: Optional[str]
    access_count: int
    workflow_id: Optional[str]
    download_url: str


class FileListResponse(BaseModel):
    """File list response."""
    files: List[FileMetadataResponse]
    total: int


class StorageStatsResponse(BaseModel):
    """Storage statistics response."""
    by_type: dict
    total_files: int
    total_bytes: int
    total_mb: float
    total_gb: float


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_storage_base_path() -> Path:
    """Get base storage path."""
    base_path = Path("data")
    base_path.mkdir(exist_ok=True)
    return base_path


def detect_file_category(mime_type: str, filename: str) -> FileCategory:
    """Auto-detect file category from MIME type and filename."""
    if mime_type.startswith("image/"):
        return FileCategory.IMAGE
    elif mime_type.startswith("audio/"):
        return FileCategory.AUDIO
    elif mime_type.startswith("video/"):
        return FileCategory.VIDEO
    elif mime_type in ["application/pdf", "application/msword", 
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "application/vnd.ms-excel.sheet.macroenabled.12",
                        "application/vnd.ms-excel",
                        "text/plain", "text/markdown", "application/json", "text/csv"]:
        return FileCategory.DOCUMENT
    elif mime_type in ["application/zip", "application/x-tar", 
                        "application/x-gzip", "application/x-rar-compressed"]:
        return FileCategory.ARCHIVE
    else:
        return FileCategory.OTHER


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def calculate_expiration(
    file_type: FileType,
    storage_settings
) -> Optional[str]:
    """Calculate expiration datetime based on file type and settings."""
    if file_type == FileType.PERMANENT:
        return None
    
    now = get_local_now()
    
    if file_type == FileType.TEMPORARY:
        # Temp files expire in 1 hour
        expires_at = now + timedelta(hours=storage_settings.temp_file_max_age_hours)
    elif file_type == FileType.UPLOAD:
        # Uploads expire based on settings (default 30 days)
        expires_at = now + timedelta(days=storage_settings.upload_storage_days)
    elif file_type == FileType.ARTIFACT:
        # Artifacts expire based on settings (default 7 days)
        expires_at = now + timedelta(days=storage_settings.artifact_ttl_days)
    else:
        # Default to upload TTL
        expires_at = now + timedelta(days=storage_settings.upload_storage_days)
    
    return expires_at.isoformat()


def get_category_directory(file_category: FileCategory, file_type: FileType) -> str:
    """Get storage directory for file category."""
    if file_type == FileType.TEMPORARY:
        return "temp"
    elif file_type == FileType.ARTIFACT:
        return "artifacts"
    else:
        # Upload files organized by category
        return f"uploads/{file_category.value}"


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/upload",
    response_model=FileMetadataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
    description="Upload a file with optional metadata and lifecycle configuration"
)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    file_type: FileType = Query(default=FileType.UPLOAD),
    file_category: Optional[FileCategory] = Query(default=None),
    workflow_id: Optional[str] = Query(default=None),
    execution_id: Optional[str] = Query(default=None),
    make_permanent: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Upload a file.
    
    - **file**: File to upload
    - **file_type**: Lifecycle type (upload, artifact, temporary, permanent)
    - **file_category**: Content category (auto-detected if not provided)
    - **workflow_id**: Optional workflow association
    - **execution_id**: Optional execution association
    - **make_permanent**: If true, file never expires
    
    Returns file metadata including download URL.
    """
    try:
        # Get settings
        settings_manager = SettingsManager(db)
        storage_settings = settings_manager.get_storage_settings()
        security_settings = settings_manager.get_security_settings()
        
        # Validate file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > security_settings.max_content_length:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size} bytes) exceeds maximum allowed ({security_settings.max_content_length} bytes)"
            )
        
        # Detect MIME type
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
        
        # Auto-detect category if not provided
        if file_category is None:
            file_category = detect_file_category(mime_type, file.filename)
        
        # Override to permanent if requested
        if make_permanent:
            file_type = FileType.PERMANENT
        
        # Determine storage directory
        category_dir = get_category_directory(file_category, file_type)
        storage_dir = get_storage_base_path() / category_dir
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_id = str(uuid4())
        safe_filename = file.filename.replace("/", "_").replace("\\", "_")
        storage_filename = f"{file_id}_{safe_filename}"
        storage_path = storage_dir / storage_filename
        
        # Save file to disk
        with open(storage_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"📁 Saved file to: {storage_path}")
        
        # Calculate file hash
        file_hash = calculate_file_hash(storage_path)
        
        # Check for duplicate (optional - deduplication)
        file_repo = FileRepository(db)
        existing_file = file_repo.get_by_hash(file_hash)
        
        if existing_file and existing_file.file_type != FileType.TEMPORARY:
            # File already exists, return existing record
            logger.info(f"♻️ File already exists (hash match): {existing_file.id}")
            return FileMetadataResponse(
                id=existing_file.id,
                filename=existing_file.filename,
                file_size_bytes=existing_file.file_size_bytes,
                mime_type=existing_file.mime_type,
                file_type=existing_file.file_type.value,
                file_category=existing_file.file_category.value,
                storage_path=existing_file.storage_path,
                uploaded_at=existing_file.uploaded_at.isoformat(),
                expires_at=existing_file.expires_at.isoformat() if existing_file.expires_at else None,
                access_count=existing_file.access_count,
                workflow_id=existing_file.workflow_id,
                download_url=f"/api/v1/files/{existing_file.id}/download"
            )
        
        # Calculate expiration
        expires_at_str = calculate_expiration(file_type, storage_settings)
        expires_at_dt = None
        if expires_at_str:
            from dateutil.parser import parse
            expires_at_dt = parse(expires_at_str)
        
        # Get user ID
        user_id = current_user.id if hasattr(current_user, 'id') else None
        
        # Create file record
        file_record = file_repo.create(
            filename=file.filename,
            storage_path=str(storage_path.relative_to(get_storage_base_path())),
            file_size_bytes=file_size,
            mime_type=mime_type,
            file_hash=file_hash,
            file_type=file_type,
            file_category=file_category,
            uploaded_by_id=user_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            expires_at=expires_at_dt,
            file_metadata={
                "original_filename": file.filename,
                "upload_method": "api"
            }
        )
        
        logger.info(f"✅ File uploaded successfully: {file_record.id} ({file.filename})")
        
        return FileMetadataResponse(
            id=file_record.id,
            filename=file_record.filename,
            file_size_bytes=file_record.file_size_bytes,
            mime_type=file_record.mime_type,
            file_type=file_record.file_type.value,
            file_category=file_record.file_category.value,
            storage_path=file_record.storage_path,
            uploaded_at=file_record.uploaded_at.isoformat(),
            expires_at=file_record.expires_at.isoformat() if file_record.expires_at else None,
            access_count=file_record.access_count,
            workflow_id=file_record.workflow_id,
            download_url=f"/api/v1/files/{file_record.id}/download"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ File upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )


@router.get(
    "/{file_id}/download",
    summary="Download a file",
    description="Download a file by ID",
    response_class=FileResponse
)
async def download_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Download a file by ID."""
    file_repo = FileRepository(db)
    file_record = file_repo.get_by_id(file_id)
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_id}"
        )
    
    # Build full path
    file_path = get_storage_base_path() / file_record.storage_path
    
    if not file_path.exists():
        logger.error(f"❌ File record exists but file missing: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )
    
    # Update access tracking
    file_repo.update_access(file_id)
    
    logger.info(f"📥 Downloading file: {file_id} ({file_record.filename})")
    
    return FileResponse(
        path=str(file_path),
        filename=file_record.filename,
        media_type=file_record.mime_type
    )


@router.options(
    "/{file_id}/view",
    summary="CORS preflight for file viewing"
)
async def view_file_options(file_id: str):
    """Handle CORS preflight requests."""
    from fastapi.responses import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.get(
    "/{file_id}/view",
    summary="View a file inline",
    description="View a file inline (for PDFs, images, etc.)",
    response_class=StreamingResponse
)
async def view_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """View a file inline (without forcing download)."""
    file_repo = FileRepository(db)
    file_record = file_repo.get_by_id(file_id)
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_id}"
        )
    
    # Build full path
    file_path = get_storage_base_path() / file_record.storage_path
    
    if not file_path.exists():
        logger.error(f"❌ File record exists but file missing: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )
    
    # Update access tracking
    file_repo.update_access(file_id)
    
    logger.info(f"👁️  Viewing file inline: {file_id} ({file_record.filename})")
    
    def file_iterator():
        with open(file_path, "rb") as f:
            yield from f
    
    return StreamingResponse(
        file_iterator(),
        media_type=file_record.mime_type,
        headers={
            "Content-Disposition": f"inline; filename={file_record.filename}",
            "Access-Control-Allow-Origin": "*",  # Allow CORS for Fabric.js
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@router.get(
    "/temp/download/{temp_filename}",
    summary="Download temporary export file",
    description="Download a temporary file generated by export nodes",
    response_class=FileResponse
)
async def download_temp_file(
    temp_filename: str,
    mode: Optional[str] = Query(default="download", description="Download mode: 'download' or 'save_as'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Download a temporary export file.
    
    This endpoint handles files generated by export nodes (CSV, PDF, etc.)
    stored in the temp directory.
    
    Args:
        temp_filename: Temporary filename (with timestamp prefix)
        mode: 'download' for quick download, 'save_as' for browser Save As dialog
    
    Returns:
        File download response with appropriate headers
    """
    # Build temp file path
    temp_dir = get_storage_base_path() / "temp"
    file_path = temp_dir / temp_filename
    
    if not file_path.exists():
        logger.error(f"❌ Temp file not found: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Temporary file not found: {temp_filename}"
        )
    
    # Validate file is actually in temp directory (security check)
    try:
        file_path.resolve().relative_to(temp_dir.resolve())
    except ValueError:
        logger.error(f"🚨 Security: Attempted path traversal: {temp_filename}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid file path"
        )
    
    # Extract original filename (remove timestamp prefix)
    # Format: 20231113_143022_originalname.csv
    parts = temp_filename.split("_", 2)
    original_filename = parts[2] if len(parts) >= 3 else temp_filename
    
    # Detect MIME type
    mime_type = mimetypes.guess_type(original_filename)[0] or "application/octet-stream"
    
    logger.info(f"📥 Downloading temp file: {temp_filename} (mode={mode})")
    
    # Return FileResponse
    # The frontend will handle the download attribute based on mode
    return FileResponse(
        path=str(file_path),
        filename=original_filename,
        media_type=mime_type,
        headers={
            "X-Download-Mode": mode  # Pass mode to frontend for handling
        }
    )



@router.get(
    "/{file_id}",
    response_model=FileMetadataResponse,
    summary="Get file metadata",
    description="Get file metadata without downloading"
)
async def get_file_metadata(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Get file metadata."""
    file_repo = FileRepository(db)
    file_record = file_repo.get_by_id(file_id)
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_id}"
        )
    
    return FileMetadataResponse(
        id=file_record.id,
        filename=file_record.filename,
        file_size_bytes=file_record.file_size_bytes,
        mime_type=file_record.mime_type,
        file_type=file_record.file_type.value,
        file_category=file_record.file_category.value,
        storage_path=file_record.storage_path,
        uploaded_at=file_record.uploaded_at.isoformat(),
        expires_at=file_record.expires_at.isoformat() if file_record.expires_at else None,
        access_count=file_record.access_count,
        workflow_id=file_record.workflow_id,
        download_url=f"/api/v1/files/{file_record.id}/download"
    )


@router.get(
    "",
    response_model=FileListResponse,
    summary="List files",
    description="List uploaded files with optional filtering"
)
async def list_files(
    file_type: Optional[FileType] = Query(default=None),
    file_category: Optional[FileCategory] = Query(default=None),
    workflow_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """List files."""
    file_repo = FileRepository(db)
    
    # Get user ID
    user_id = current_user.id if hasattr(current_user, 'id') else None
    
    if workflow_id:
        files = file_repo.list_by_workflow(workflow_id)
    elif user_id:
        files = file_repo.list_by_user(user_id, file_type, file_category, limit, offset)
    else:
        files = []
    
    file_responses = [
        FileMetadataResponse(
            id=f.id,
            filename=f.filename,
            file_size_bytes=f.file_size_bytes,
            mime_type=f.mime_type,
            file_type=f.file_type.value,
            file_category=f.file_category.value,
            storage_path=f.storage_path,
            uploaded_at=f.uploaded_at.isoformat(),
            expires_at=f.expires_at.isoformat() if f.expires_at else None,
            access_count=f.access_count,
            workflow_id=f.workflow_id,
            download_url=f"/api/v1/files/{f.id}/download"
        )
        for f in files
    ]
    
    return FileListResponse(
        files=file_responses,
        total=len(file_responses)
    )


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
    description="Delete a file and its metadata"
)
async def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Delete a file."""
    file_repo = FileRepository(db)
    file_record = file_repo.get_by_id(file_id)
    
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_id}"
        )
    
    # Delete physical file
    file_path = get_storage_base_path() / file_record.storage_path
    if file_path.exists():
        try:
            os.remove(file_path)
            logger.info(f"🗑️ Deleted physical file: {file_path}")
        except Exception as e:
            logger.error(f"❌ Failed to delete physical file: {e}")
    
    # Delete database record
    file_repo.delete(file_id)
    
    logger.info(f"✅ File deleted: {file_id}")


@router.get(
    "/stats/storage",
    response_model=StorageStatsResponse,
    summary="Get storage statistics",
    description="Get storage usage statistics"
)
async def get_storage_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Get storage statistics."""
    file_repo = FileRepository(db)
    stats = file_repo.get_storage_stats()
    
    total_bytes = stats["total_bytes"]
    
    return StorageStatsResponse(
        by_type=stats["by_type"],
        total_files=stats["total_files"],
        total_bytes=total_bytes,
        total_mb=round(total_bytes / (1024 * 1024), 2),
        total_gb=round(total_bytes / (1024 * 1024 * 1024), 2)
    )


@router.post(
    "/cleanup",
    summary="Run file cleanup",
    description="Manually trigger file cleanup job (admin only)"
)
async def trigger_cleanup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """Manually trigger file cleanup."""
    from app.services.file_cleanup import run_cleanup_job
    
    logger.info(f"🧹 Manual cleanup triggered by user")
    
    stats = run_cleanup_job(db)
    
    return {
        "success": True,
        "message": "Cleanup completed",
        "stats": stats
    }
