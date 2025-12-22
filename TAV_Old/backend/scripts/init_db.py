"""
Database initialization script.

Creates all tables and sets up default data (system user).
For production, use Alembic migrations instead.

⚠️ IMPORTANT: If you have an existing database with old schema,
you should either:
1. Delete the database file and run this script (for development)
2. Run Alembic migrations (for production): `alembic upgrade head`
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.base import Base
from app.database.session import engine
from app.database.models import User
from app.database.session import SessionLocal
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_data_directory():
    """Ensure the data directory exists for SQLite databases."""
    if str(settings.DATABASE_URL).startswith("sqlite"):
        db_path = str(settings.DATABASE_URL).replace("sqlite:///", "")
        data_dir = Path(db_path).parent
        
        if not data_dir.exists():
            logger.info(f"📁 Creating data directory: {data_dir}")
            data_dir.mkdir(parents=True, exist_ok=True)
            logger.info("✅ Data directory created")
        else:
            logger.info(f"✓ Data directory exists: {data_dir}")


def init_db():
    """Initialize database with all tables."""
    logger.info("🚀 Initializing TAV Engine database...")
    logger.info(f"📍 Database URL: {settings.DATABASE_URL}")
    
    # Ensure data directory exists (for SQLite)
    ensure_data_directory()
    
    logger.info("🗄️  Creating database tables...")
    
    # Create all tables based on current models
    # Note: This will NOT modify existing tables, only create new ones
    # For schema changes, use Alembic migrations
    Base.metadata.create_all(bind=engine)
    
    logger.info("✅ Database tables created successfully")
    
    # Create default system user
    create_system_user()
    
    # Initialize default settings
    initialize_default_settings()
    
    logger.info("🎉 Database initialization complete!")


def create_system_user():
    """Create default system user for internal operations."""
    db = SessionLocal()
    try:
        # Check if any users exist
        user_count = db.query(User).count()
        
        if user_count > 0:
            logger.info(f"ℹ️  Found {user_count} existing user(s) in database")
            # Check specifically for system user
            system_user = db.query(User).filter(User.user_name == "system").first()
            if system_user:
                logger.info("   ✓ System user exists (ID=1)")
            return
        
        # Create system user (ID will be 1)
        logger.info("👤 Creating system user...")
        system_user = User(
            user_name="system",
            user_email="system@tavengine.local",
            user_password="",  # No password - not for login
            user_firstname="System",
            user_lastname="User",
            user_is_deleted=False,
            user_is_disabled=False,
            is_show=False,  # Hide from user lists
        )
        
        db.add(system_user)
        db.commit()
        db.refresh(system_user)
        
        logger.info("✅ Created system user")
        logger.info(f"   ID: {system_user.id}")
        logger.info(f"   Username: {system_user.user_name}")
        
    except Exception as e:
        logger.error(f"❌ Error creating system user: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def initialize_default_settings():
    """Initialize default application settings in database."""
    db = SessionLocal()
    try:
        from app.core.config.manager import init_settings_manager
        
        logger.info("⚙️  Initializing default settings...")
        settings_manager = init_settings_manager(db)
        logger.info("✅ Default settings initialized")
        
    except Exception as e:
        logger.error(f"❌ Error initializing settings: {e}")
        logger.warning("   Settings will use defaults")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()