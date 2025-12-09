"""
Database Schema Checker

Detects schema issues and missing columns in the database.
Useful for diagnosing migration problems.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from sqlalchemy import inspect, text
from app.database.session import engine, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def get_table_columns(table_name: str) -> list:
    """Get list of columns in a table."""
    if not check_table_exists(table_name):
        return []
    
    inspector = inspect(engine)
    return [col['name'] for col in inspector.get_columns(table_name)]


def check_schema():
    """Check database schema for common issues."""
    logger.info("🔍 Checking database schema...")
    
    issues = []
    warnings = []
    
    # Check if database exists
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"✅ Database connected. Found {len(tables)} tables: {', '.join(tables)}")
    except Exception as e:
        logger.error(f"❌ Cannot connect to database: {e}")
        return False
    
    # Check critical tables
    critical_tables = ["users", "workflows", "executions", "files"]
    for table in critical_tables:
        if not check_table_exists(table):
            issues.append(f"Missing critical table: {table}")
            logger.error(f"❌ Missing table: {table}")
        else:
            logger.info(f"✅ Table exists: {table}")
    
    # Check files table schema (common issue)
    if check_table_exists("files"):
        columns = get_table_columns("files")
        logger.info(f"📋 Files table columns: {', '.join(columns)}")
        
        required_columns = {
            'id': 'Primary key',
            'filename': 'Original filename',
            'storage_path': 'Storage location',
            'file_size_bytes': 'File size',
            'mime_type': 'MIME type',
            'file_hash': 'SHA256 hash for deduplication',
            'file_type': 'File type (upload/artifact/temporary/permanent)',
            'file_category': 'Category (document/image/audio/video/etc)',
            'uploaded_by_id': 'User who uploaded',
            'workflow_id': 'Associated workflow (optional)',
            'execution_id': 'Associated execution (optional)',
            'uploaded_at': 'Upload timestamp',
            'expires_at': 'Expiration timestamp',
        }
        
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            logger.error("❌ FILES TABLE SCHEMA ISSUE DETECTED!")
            logger.error(f"   Missing columns: {', '.join(missing_columns)}")
            for col in missing_columns:
                logger.error(f"   - {col}: {required_columns[col]}")
            issues.append(f"Files table missing columns: {', '.join(missing_columns)}")
        else:
            logger.info("✅ Files table schema is complete")
    
    # Check users table
    if check_table_exists("users"):
        columns = get_table_columns("users")
        logger.info(f"📋 Users table columns: {', '.join(columns)}")
        
        if 'user_name' not in columns:
            issues.append("Users table missing 'user_name' column")
            logger.error("❌ Users table missing 'user_name' column")
    
    # Check workflows table
    if check_table_exists("workflows"):
        columns = get_table_columns("workflows")
        logger.info(f"📋 Workflows table columns: {', '.join(columns)}")
        
        if 'recommended_await_completion' not in columns:
            warnings.append("Workflows table missing 'recommended_await_completion' column (recent addition)")
            logger.warning("⚠️  Workflows table missing 'recommended_await_completion' column")
    
    # Check credentials table
    if check_table_exists("credentials"):
        columns = get_table_columns("credentials")
        logger.info(f"📋 Credentials table columns: {', '.join(columns)}")
    else:
        warnings.append("Credentials table does not exist (may be normal for older versions)")
    
    # Summary
    print("\n" + "="*80)
    if issues:
        logger.error(f"\n❌ FOUND {len(issues)} CRITICAL ISSUE(S):")
        for i, issue in enumerate(issues, 1):
            logger.error(f"   {i}. {issue}")
        
        print("\n" + "="*80)
        print("💡 HOW TO FIX:")
        print("="*80)
        print("\nOption 1: Delete and recreate database (⚠️ DESTROYS ALL DATA)")
        print("  1. Stop the backend server")
        print("  2. Delete the database file (usually data/tav_engine.db)")
        print("  3. Run: python scripts/init_db.py")
        print("\nOption 2: Run database migrations (preserves data)")
        print("  1. Make sure Alembic is installed: pip install alembic")
        print("  2. Run: cd backend && alembic upgrade head")
        print("\nOption 3: Use the setup script")
        print("  - Fresh database: python scripts/setup_db.py")
        print("  - Force recreate: python scripts/setup_db.py --force-recreate")
        print("="*80)
        
        return False
    
    if warnings:
        logger.warning(f"\n⚠️  Found {len(warnings)} warning(s):")
        for i, warning in enumerate(warnings, 1):
            logger.warning(f"   {i}. {warning}")
    
    if not issues:
        logger.info("\n✅ Database schema looks good!")
        return True
    
    return True


def test_file_query():
    """Test if we can query the files table (common failure point)."""
    if not check_table_exists("files"):
        logger.warning("⚠️  Files table does not exist, skipping query test")
        return False
    
    try:
        from app.database.models.file import File
        db = SessionLocal()
        
        logger.info("🧪 Testing file query...")
        count = db.query(File).count()
        logger.info(f"✅ Successfully queried files table: {count} file(s) found")
        db.close()
        return True
    except Exception as e:
        logger.error(f"❌ Failed to query files table: {e}")
        logger.error("   This usually means the database schema doesn't match the model definition")
        return False


if __name__ == "__main__":
    logger.info("🚀 TAV Engine Database Schema Checker")
    logger.info("="*80)
    
    schema_ok = check_schema()
    
    print("\n" + "="*80)
    logger.info("🧪 Testing database queries...")
    print("="*80)
    
    query_ok = test_file_query()
    
    print("\n" + "="*80)
    if schema_ok and query_ok:
        logger.info("✅ All checks passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some checks failed. Please review the issues above.")
        sys.exit(1)

