"""
File Repository

Handles CRUD operations for file metadata.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database.models.file import File, FileType, FileCategory
from app.utils.timezone import get_local_now

logger = logging.getLogger(__name__)


class FileRepository:
    """Repository for file metadata operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        filename: str,
        storage_path: str,
        file_size_bytes: int,
        mime_type: str,
        file_hash: str,
        file_type: FileType = FileType.UPLOAD,
        file_category: FileCategory = FileCategory.OTHER,
        uploaded_by_id: Optional[int] = None,
        workflow_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        file_metadata: Optional[Dict[str, Any]] = None
    ) -> File:
        """
        Create a new file record.
        
        Args:
            filename: Original filename
            storage_path: Path where file is stored
            file_size_bytes: File size in bytes
            mime_type: MIME type
            file_hash: SHA256 hash
            file_type: File type (upload, artifact, temporary, permanent)
            file_category: File category (document, image, audio, video, etc.)
            uploaded_by_id: User ID who uploaded the file
            workflow_id: Associated workflow ID (optional)
            execution_id: Associated execution ID (optional)
            expires_at: Expiration datetime (optional)
            file_metadata: Additional metadata (optional)
            
        Returns:
            Created File object
        """
        file = File(
            filename=filename,
            storage_path=storage_path,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            file_hash=file_hash,
            file_type=file_type,
            file_category=file_category,
            uploaded_by_id=uploaded_by_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            expires_at=expires_at,
            file_metadata=file_metadata or {}
        )
        
        self.db.add(file)
        self.db.commit()
        self.db.refresh(file)
        
        logger.info(f"✅ Created file record: {file.id} ({file.filename}, type={file.file_type})")
        return file
    
    def get_by_id(self, file_id: str) -> Optional[File]:
        """Get file by ID."""
        return self.db.query(File).filter(File.id == file_id).first()
    
    def get_by_hash(self, file_hash: str) -> Optional[File]:
        """Get file by hash (for deduplication)."""
        return self.db.query(File).filter(File.file_hash == file_hash).first()
    
    def get_by_storage_path(self, storage_path: str) -> Optional[File]:
        """Get file by storage path."""
        return self.db.query(File).filter(File.storage_path == storage_path).first()
    
    def list_by_user(
        self,
        user_id: int,
        file_type: Optional[FileType] = None,
        file_category: Optional[FileCategory] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[File]:
        """List files uploaded by a user."""
        query = self.db.query(File).filter(File.uploaded_by_id == user_id)
        
        if file_type:
            query = query.filter(File.file_type == file_type)
        
        if file_category:
            query = query.filter(File.file_category == file_category)
        
        return query.order_by(File.uploaded_at.desc()).offset(offset).limit(limit).all()
    
    def list_by_workflow(self, workflow_id: str) -> List[File]:
        """List files associated with a workflow."""
        return self.db.query(File).filter(File.workflow_id == workflow_id).all()
    
    def list_expired(self, before: Optional[datetime] = None) -> List[File]:
        """
        List expired files.
        
        Args:
            before: Get files expired before this datetime (default: now)
            
        Returns:
            List of expired files
        """
        if before is None:
            before = get_local_now()
        
        return self.db.query(File).filter(
            and_(
                File.expires_at.isnot(None),
                File.expires_at < before,
                File.file_type != FileType.PERMANENT  # Never delete permanent files
            )
        ).all()
    
    def list_temporary_old(self, older_than_hours: int = 1) -> List[File]:
        """
        List old temporary files.
        
        Args:
            older_than_hours: Get temp files older than this many hours
            
        Returns:
            List of old temporary files
        """
        cutoff = get_local_now() - timedelta(hours=older_than_hours)
        
        return self.db.query(File).filter(
            and_(
                File.file_type == FileType.TEMPORARY,
                File.uploaded_at < cutoff
            )
        ).all()
    
    def update_access(self, file_id: str) -> None:
        """Update file access tracking."""
        file = self.get_by_id(file_id)
        if file:
            file.access_count += 1
            file.last_accessed_at = get_local_now()
            self.db.commit()
    
    def update_expiration(self, file_id: str, expires_at: Optional[datetime]) -> Optional[File]:
        """Update file expiration."""
        file = self.get_by_id(file_id)
        if file:
            file.expires_at = expires_at
            self.db.commit()
            self.db.refresh(file)
            logger.info(f"✅ Updated expiration for file {file_id}: {expires_at}")
        return file
    
    def mark_permanent(self, file_id: str) -> Optional[File]:
        """Mark file as permanent (never expires)."""
        file = self.get_by_id(file_id)
        if file:
            file.file_type = FileType.PERMANENT
            file.expires_at = None
            self.db.commit()
            self.db.refresh(file)
            logger.info(f"✅ Marked file {file_id} as permanent")
        return file
    
    def delete(self, file_id: str) -> bool:
        """
        Delete file record.
        
        Note: This only deletes the database record.
        The physical file must be deleted separately.
        
        Returns:
            True if deleted, False if not found
        """
        file = self.get_by_id(file_id)
        if file:
            self.db.delete(file)
            self.db.commit()
            logger.info(f"🗑️ Deleted file record: {file_id}")
            return True
        return False
    
    def delete_many(self, file_ids: List[str]) -> int:
        """
        Delete multiple file records.
        
        Returns:
            Number of records deleted
        """
        count = self.db.query(File).filter(File.id.in_(file_ids)).delete(synchronize_session=False)
        self.db.commit()
        logger.info(f"🗑️ Deleted {count} file records")
        return count
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        from sqlalchemy import func
        
        stats = self.db.query(
            File.file_type,
            func.count(File.id).label('count'),
            func.sum(File.file_size_bytes).label('total_bytes')
        ).group_by(File.file_type).all()
        
        result = {
            "by_type": {},
            "total_files": 0,
            "total_bytes": 0
        }
        
        for file_type, count, total_bytes in stats:
            result["by_type"][file_type.value] = {
                "count": count,
                "total_bytes": total_bytes or 0
            }
            result["total_files"] += count
            result["total_bytes"] += total_bytes or 0
        
        return result
