"""
Startup Cleanup Service

Wipes all files on server restart to ensure clean state.
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def wipe_all_files_on_startup():
    """
    Wipe all uploaded files, artifacts, and temporary files on startup.
    
    This ensures a clean slate on every server restart and prevents
    accumulation of orphaned files from previous sessions.
    
    Directories wiped:
    - data/uploads/
    - data/artifacts/
    - data/temp/
    """
    logger.info("🗑️  Starting file wipe on server startup...")
    
    base_path = Path("data")
    directories_to_wipe = [
        base_path / "uploads",
        base_path / "artifacts",
        base_path / "temp",
    ]
    
    total_deleted = 0
    total_size = 0
    
    for directory in directories_to_wipe:
        if not directory.exists():
            logger.info(f"   📁 {directory} doesn't exist, skipping...")
            continue
        
        try:
            # Calculate total size before deletion
            dir_size = sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())
            file_count = sum(1 for f in directory.rglob('*') if f.is_file())
            
            if file_count == 0:
                logger.info(f"   📁 {directory} is already empty")
                continue
            
            # Delete all contents
            shutil.rmtree(directory)
            directory.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories for file categories
            if directory.name == "uploads":
                (directory / "document").mkdir(exist_ok=True)
                (directory / "image").mkdir(exist_ok=True)
                (directory / "audio").mkdir(exist_ok=True)
                (directory / "video").mkdir(exist_ok=True)
                (directory / "archive").mkdir(exist_ok=True)
                (directory / "other").mkdir(exist_ok=True)
            
            total_deleted += file_count
            total_size += dir_size
            
            logger.info(
                f"   ✅ Wiped {directory}: {file_count} files "
                f"({dir_size / 1024 / 1024:.2f} MB)"
            )
            
        except Exception as e:
            logger.error(f"   ❌ Failed to wipe {directory}: {e}", exc_info=True)
    
    if total_deleted > 0:
        logger.info(
            f"✅ Startup file wipe complete: {total_deleted} files deleted "
            f"({total_size / 1024 / 1024:.2f} MB freed)"
        )
    else:
        logger.info("✅ Startup file wipe complete: No files to delete")


def clear_database_file_records():
    """
    Clear all file records from the database on startup.
    
    This should be called after wiping files to keep database in sync.
    """
    logger.info("🗄️  Clearing file records from database...")
    
    try:
        from app.database.session import SessionLocal
        from app.database.models.file import File
        
        db = SessionLocal()
        try:
            # Count files before deletion
            file_count = db.query(File).count()
            
            if file_count == 0:
                logger.info("   ✅ No file records to clear")
                return
            
            # Delete all file records
            db.query(File).delete()
            db.commit()
            
            logger.info(f"   ✅ Cleared {file_count} file records from database")
            
        except Exception as e:
            db.rollback()
            logger.error(f"   ❌ Failed to clear file records: {e}", exc_info=True)
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Failed to clear database file records: {e}", exc_info=True)


def startup_cleanup():
    """
    Complete startup cleanup: wipe files and clear database records.
    """
    wipe_all_files_on_startup()
    clear_database_file_records()

