"""
Clean up partially created conversation tables from failed migration.

Run from backend directory:
    cd backend
    python scripts/cleanup_conversation_tables.py
"""
import sys
import os

# Add backend directory to path (parent of scripts)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.database.session import SessionLocal
from sqlalchemy import text

def cleanup_tables():
    """Drop partially created tables"""
    db = SessionLocal()
    
    try:
        print("🧹 Cleaning up partial tables...")
        
        # Drop in reverse order (children first)
        tables = ['conversation_messages', 'custom_nodes', 'conversations']
        
        for table in tables:
            try:
                db.execute(text(f'DROP TABLE IF EXISTS {table}'))
                print(f"  ✅ Dropped {table}")
            except Exception as e:
                print(f"  ⚠️  Could not drop {table}: {e}")
        
        db.commit()
        print("✅ Cleanup complete!")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        db.rollback()
        return False
    
    finally:
        db.close()
    
    return True

if __name__ == "__main__":
    success = cleanup_tables()
    sys.exit(0 if success else 1)

