#!/usr/bin/env python3
"""
Delete all workflow data from the database.
WARNING: This will permanently delete all workflows!
"""

import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database.models.workflow import Workflow

def delete_all_workflows():
    """Delete all workflow data from the database."""
    
    # Create database engine and session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Get count before deletion
        count = db.query(Workflow).count()
        
        if count == 0:
            print("ℹ️  No workflows found in database.")
            return
        
        # Confirm deletion
        print(f"⚠️  WARNING: This will delete {count} workflow(s) from the database!")
        response = input("Are you sure you want to continue? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Deletion cancelled.")
            return
        
        print(f"🗑️  Deleting {count} workflow(s)...")
        
        # Delete all workflows
        deleted = db.query(Workflow).delete()
        db.commit()
        
        print(f"✅ Successfully deleted {deleted} workflow(s)!")
        print("🎉 Database is now empty.")
        
    except Exception as e:
        print(f"❌ Error deleting data: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()

if __name__ == "__main__":
    delete_all_workflows()
