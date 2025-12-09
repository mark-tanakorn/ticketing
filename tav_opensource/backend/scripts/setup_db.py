"""
Complete database setup script with migration support.
 
This script provides a safe way to initialize or update the database.
It detects if Alembic is available and uses migrations when possible.
"""
 
import sys
import os
from pathlib import Path
 
# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))
 
import logging
from sqlalchemy import inspect, text
 
from app.database.base import Base
from app.database.session import engine, SessionLocal
from app.database.models import User
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
 
def check_table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()
 
 
def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    if not check_table_exists(table_name):
        return False
   
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns
 
 
def run_alembic_migrations():
    """Run Alembic migrations to update the database schema."""
    try:
        from alembic import command
        from alembic.config import Config
       
        # Get alembic.ini path
        alembic_ini = backend_path / "alembic.ini"
       
        if not alembic_ini.exists():
            logger.warning("⚠️  alembic.ini not found, skipping migrations")
            return False
       
        logger.info("📦 Running Alembic migrations...")
       
        # Create Alembic config
        alembic_cfg = Config(str(alembic_ini))
       
        # Run migrations
        command.upgrade(alembic_cfg, "head")
       
        logger.info("✅ Alembic migrations completed")
        return True
       
    except ImportError:
        logger.warning("⚠️  Alembic not installed, skipping migrations")
        return False
    except Exception as e:
        logger.error(f"❌ Error running Alembic migrations: {e}")
        return False
 
 
def create_tables_direct():
    """Create tables directly using SQLAlchemy metadata (for fresh databases)."""
    logger.info("🗄️  Creating database tables directly...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created")
 
 
def setup_database(force_recreate: bool = False, use_migrations: bool = True):
    """
    Setup database with proper handling of existing schemas.
   
    Args:
        force_recreate: If True, drop and recreate all tables (⚠️ DESTROYS DATA)
        use_migrations: If True, try to use Alembic migrations for schema updates
    """
    logger.info("🚀 Setting up TAV Engine database...")
   
    # Check if database is empty
    is_empty = not check_table_exists("users")
   
    if force_recreate:
        logger.warning("⚠️  FORCE RECREATE: Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        create_tables_direct()
    elif is_empty:
        logger.info("📝 Fresh database detected, creating tables...")
        create_tables_direct()
    else:
        logger.info("📚 Existing database detected")
       
        # Check for schema issues
        if not check_column_exists("files", "file_type"):
            logger.warning("⚠️  Schema mismatch detected: 'files' table missing 'file_type' column")
           
            if use_migrations:
                success = run_alembic_migrations()
                if not success:
                    logger.error("❌ Failed to run migrations. Options:")
                    logger.error("   1. Delete the database file and run this script again")
                    logger.error("   2. Run: python -m scripts.setup_db --force-recreate (⚠️ destroys data)")
                    logger.error("   3. Install Alembic: pip install alembic")
                    logger.error("   4. Manually fix the schema")
                    return False
            else:
                logger.error("❌ Schema mismatch and migrations disabled")
                logger.error("   Delete the database file or enable migrations")
                return False
        else:
            logger.info("✅ Schema is up to date")
   
    # Create default data
    create_system_user()
    initialize_default_settings()
   
    logger.info("🎉 Database setup complete!")
    return True
 
 
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
    import argparse
   
    parser = argparse.ArgumentParser(description="Setup TAV Engine database")
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Drop and recreate all tables (⚠️ DESTROYS ALL DATA)"
    )
    parser.add_argument(
        "--no-migrations",
        action="store_true",
        help="Disable Alembic migrations (use direct table creation)"
    )
   
    args = parser.parse_args()
   
    if args.force_recreate:
        confirm = input("⚠️  WARNING: This will DELETE ALL DATA. Type 'YES' to confirm: ")
        if confirm != "YES":
            logger.info("Aborted")
            sys.exit(0)
   
    success = setup_database(
        force_recreate=args.force_recreate,
        use_migrations=not args.no_migrations
    )
   
    sys.exit(0 if success else 1)