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
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.base import Base
from app.database.session import engine
from app.database.models import User
from app.database.session import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db():
    """Initialize database with all tables."""
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


def create_system_user():
    """Create default system user for internal operations."""
    db = SessionLocal()
    try:
        # Check if system user already exists
        existing_user = db.query(User).filter(User.user_name == "system").first()
        if existing_user:
            logger.info("ℹ️  System user already exists")
            return
        
        # Create system user
        system_user = User(
            id=1,  # First user, system user
            user_name="system",
            user_email="system@tavengine.local",
            user_password="",  # No password - not for login
            user_firstname="System",
            user_lastname="User"
        )
        
        db.add(system_user)
        db.commit()
        
        logger.info("✅ Created default system user")
        logger.info(f"   ID: {system_user.id}")
        logger.info("   Username: system")
        
    except Exception as e:
        logger.error(f"❌ Error creating system user: {e}")
        db.rollback()
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
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("🚀 Initializing TAV Engine database...")
    init_db()
    logger.info("🎉 Database initialization complete!")

