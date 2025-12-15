#!/usr/bin/env python
"""
Local Development Startup Script

Automatically runs migrations and starts the backend server.
This mimics what Docker does automatically.
"""

import sys
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    """Run migrations and start server."""
    
    # Ensure we're in the backend directory
    backend_dir = Path(__file__).parent.parent
    
    logger.info("="*60)
    logger.info("🚀 TAV Engine - Local Development Startup")
    logger.info("="*60)
    
    # Step 1: Run migrations
    logger.info("\n🔧 Step 1: Running database migrations...")
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("✅ Migrations completed successfully")
        if result.stdout:
            for line in result.stdout.splitlines():
                logger.info(f"   {line}")
    except subprocess.CalledProcessError as e:
        logger.error("❌ Migration failed!")
        logger.error(f"   {e.stderr}")
        logger.info("\n💡 Tip: If migrations fail, you can:")
        logger.info("   1. Delete data/tav_engine.db and try again")
        logger.info("   2. Run manually: cd backend && alembic upgrade head")
        logger.info("   3. Or use: python scripts/migrate_files_table.py")
        sys.exit(1)
    except FileNotFoundError:
        logger.error("❌ Alembic not found!")
        logger.error("   Install it with: pip install alembic")
        sys.exit(1)
    
    # Step 2: Start server
    logger.info("\n🚀 Step 2: Starting backend server...")
    logger.info("="*60)
    logger.info("Server will be available at: http://localhost:5000")
    logger.info("API docs at: http://localhost:5000/docs")
    logger.info("Press Ctrl+C to stop")
    logger.info("="*60)
    logger.info("")
    
    try:
        subprocess.run(
            ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"],
            cwd=backend_dir,
            check=True
        )
    except KeyboardInterrupt:
        logger.info("\n\n👋 Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

