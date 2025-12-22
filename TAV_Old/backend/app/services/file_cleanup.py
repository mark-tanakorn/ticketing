"""
File Cleanup Service

Background service for cleaning up expired files based on storage settings.
"""

import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.database.repositories.file import FileRepository
from app.database.models.file import FileType
from app.core.config.manager import SettingsManager
from app.utils.timezone import get_local_now

logger = logging.getLogger(__name__)


class FileCleanupService:
    """
    Service for cleaning up expired files.
    
    Handles three types of cleanup:
    1. Temporary files - cleaned every hour (1-hour TTL)
    2. Upload files - cleaned daily (30-day TTL by default)
    3. Artifact files - cleaned every 6 hours (7-day TTL by default)
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.file_repo = FileRepository(db)
        self.settings_manager = SettingsManager(db)
        self.base_path = Path("data")
    
    def cleanup_expired_files(self) -> Dict[str, Any]:
        """
        Run cleanup for all expired files.
        
        Returns:
            Dict with cleanup statistics
        """
        logger.info("🧹 Starting file cleanup service...")
        
        # Check if cleanup is enabled
        storage_settings = self.settings_manager.get_storage_settings()
        
        if not storage_settings.auto_cleanup:
            logger.info("⏸️  Auto cleanup is disabled")
            return {
                "status": "disabled",
                "files_removed": 0,
                "space_freed_bytes": 0
            }
        
        stats = {
            "status": "completed",
            "files_removed": 0,
            "space_freed_bytes": 0,
            "by_type": {}
        }
        
        # Cleanup temporary files if enabled
        if storage_settings.temp_file_cleanup:
            temp_stats = self._cleanup_temporary_files(storage_settings)
            stats["by_type"]["temporary"] = temp_stats
            stats["files_removed"] += temp_stats["files_removed"]
            stats["space_freed_bytes"] += temp_stats["space_freed_bytes"]
        
        # Cleanup expired uploads and artifacts
        expired_stats = self._cleanup_expired()
        stats["by_type"]["expired"] = expired_stats
        stats["files_removed"] += expired_stats["files_removed"]
        stats["space_freed_bytes"] += expired_stats["space_freed_bytes"]
        
        logger.info(
            f"✅ Cleanup completed: {stats['files_removed']} files removed, "
            f"{stats['space_freed_bytes'] / (1024*1024):.2f} MB freed"
        )
        
        return stats
    
    def _cleanup_temporary_files(self, storage_settings) -> Dict[str, Any]:
        """Clean up old temporary files."""
        logger.info("🗑️  Cleaning up temporary files...")
        
        max_age_hours = storage_settings.temp_file_max_age_hours
        
        # Get old temporary files
        old_temp_files = self.file_repo.list_temporary_old(older_than_hours=max_age_hours)
        
        stats = {
            "files_removed": 0,
            "space_freed_bytes": 0,
            "files_failed": 0
        }
        
        for file_record in old_temp_files:
            try:
                # Delete physical file
                file_path = self.base_path / file_record.storage_path
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    os.remove(file_path)
                    stats["space_freed_bytes"] += file_size
                    logger.debug(f"🗑️  Deleted temp file: {file_path}")
                
                # Delete database record
                self.file_repo.delete(file_record.id)
                stats["files_removed"] += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to delete temp file {file_record.id}: {e}")
                stats["files_failed"] += 1
        
        if stats["files_removed"] > 0:
            logger.info(
                f"✅ Removed {stats['files_removed']} temporary files "
                f"({stats['space_freed_bytes'] / (1024*1024):.2f} MB)"
            )
        
        return stats
    
    def _cleanup_expired(self) -> Dict[str, Any]:
        """Clean up expired files (uploads and artifacts)."""
        logger.info("🗑️  Cleaning up expired files...")
        
        # Get expired files
        expired_files = self.file_repo.list_expired()
        
        stats = {
            "files_removed": 0,
            "space_freed_bytes": 0,
            "files_failed": 0,
            "by_file_type": {}
        }
        
        for file_record in expired_files:
            try:
                # Track by file type
                file_type = file_record.file_type.value
                if file_type not in stats["by_file_type"]:
                    stats["by_file_type"][file_type] = 0
                
                # Delete physical file
                file_path = self.base_path / file_record.storage_path
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    os.remove(file_path)
                    stats["space_freed_bytes"] += file_size
                    logger.debug(f"🗑️  Deleted expired file: {file_path}")
                
                # Delete database record
                self.file_repo.delete(file_record.id)
                stats["files_removed"] += 1
                stats["by_file_type"][file_type] += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to delete expired file {file_record.id}: {e}")
                stats["files_failed"] += 1
        
        if stats["files_removed"] > 0:
            logger.info(
                f"✅ Removed {stats['files_removed']} expired files "
                f"({stats['space_freed_bytes'] / (1024*1024):.2f} MB)"
            )
        
        return stats
    
    def cleanup_orphaned_files(self) -> Dict[str, Any]:
        """
        Clean up physical files that don't have database records.
        
        This handles cases where database cleanup succeeded but file deletion failed.
        """
        logger.info("🔍 Checking for orphaned files...")
        
        stats = {
            "files_removed": 0,
            "space_freed_bytes": 0,
            "directories_checked": 0
        }
        
        # Check each storage directory
        storage_dirs = [
            self.base_path / "uploads",
            self.base_path / "artifacts",
            self.base_path / "temp"
        ]
        
        for storage_dir in storage_dirs:
            if not storage_dir.exists():
                continue
            
            stats["directories_checked"] += 1
            
            # Recursively find all files
            for file_path in storage_dir.rglob("*"):
                if file_path.is_file():
                    # Get relative path
                    relative_path = str(file_path.relative_to(self.base_path))
                    
                    # Check if file exists in database
                    file_record = self.file_repo.get_by_storage_path(relative_path)
                    
                    if not file_record:
                        # Orphaned file - no database record
                        try:
                            file_size = file_path.stat().st_size
                            os.remove(file_path)
                            stats["files_removed"] += 1
                            stats["space_freed_bytes"] += file_size
                            logger.info(f"🗑️  Deleted orphaned file: {relative_path}")
                        except Exception as e:
                            logger.error(f"❌ Failed to delete orphaned file {relative_path}: {e}")
        
        if stats["files_removed"] > 0:
            logger.info(
                f"✅ Removed {stats['files_removed']} orphaned files "
                f"({stats['space_freed_bytes'] / (1024*1024):.2f} MB)"
            )
        else:
            logger.info("✅ No orphaned files found")
        
        return stats
    
    def cleanup_empty_directories(self):
        """Remove empty directories in storage paths."""
        logger.info("🗂️  Cleaning up empty directories...")
        
        removed_count = 0
        
        # Check each storage directory
        storage_dirs = [
            self.base_path / "uploads",
            self.base_path / "artifacts",
            self.base_path / "temp"
        ]
        
        for storage_dir in storage_dirs:
            if not storage_dir.exists():
                continue
            
            # Walk directory tree bottom-up
            for dirpath, dirnames, filenames in os.walk(storage_dir, topdown=False):
                current_dir = Path(dirpath)
                
                # Skip root storage directories
                if current_dir in storage_dirs:
                    continue
                
                # Check if directory is empty
                try:
                    if not any(current_dir.iterdir()):
                        current_dir.rmdir()
                        removed_count += 1
                        logger.debug(f"🗑️  Removed empty directory: {current_dir}")
                except Exception as e:
                    logger.debug(f"Could not remove directory {current_dir}: {e}")
        
        if removed_count > 0:
            logger.info(f"✅ Removed {removed_count} empty directories")
    
    def get_storage_usage(self) -> Dict[str, Any]:
        """
        Get current storage usage statistics.
        
        Returns:
            Dict with storage usage by type
        """
        stats = self.file_repo.get_storage_stats()
        
        # Add physical disk usage
        for storage_dir_name in ["uploads", "artifacts", "temp"]:
            storage_dir = self.base_path / storage_dir_name
            if storage_dir.exists():
                total_size = sum(
                    f.stat().st_size
                    for f in storage_dir.rglob("*")
                    if f.is_file()
                )
                stats[f"{storage_dir_name}_disk_bytes"] = total_size
        
        return stats


def run_cleanup_job(db: Session) -> Dict[str, Any]:
    """
    Run file cleanup job.
    
    This function can be called by:
    - Celery worker (scheduled task)
    - FastAPI background task
    - Manual admin endpoint
    
    Args:
        db: Database session
        
    Returns:
        Cleanup statistics
    """
    try:
        cleanup_service = FileCleanupService(db)
        
        # Run main cleanup
        stats = cleanup_service.cleanup_expired_files()
        
        # Also cleanup orphaned files (less frequently)
        orphaned_stats = cleanup_service.cleanup_orphaned_files()
        stats["orphaned_files_removed"] = orphaned_stats["files_removed"]
        
        # Cleanup empty directories
        cleanup_service.cleanup_empty_directories()
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Cleanup job failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "files_removed": 0,
            "space_freed_bytes": 0
        }

