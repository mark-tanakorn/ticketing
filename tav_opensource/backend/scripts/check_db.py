#!/usr/bin/env python3
"""
Check workflow data in the database.
"""

import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database.models.workflow import Workflow

def check_workflows():
    """Check what workflows exist in the database."""
    
    # Create database engine and session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("🔍 Checking workflows in database...")
        
        # Count total workflows
        count = db.query(Workflow).count()
        print(f"📊 Total workflows in database: {count}")
        
        if count == 0:
            print("❌ No workflows found in database!")
            print("   Try running: python scripts/add_sample_data.py")
        else:
            print("\n📋 Workflows found:")
            workflows = db.query(Workflow).all()
            for i, workflow in enumerate(workflows, 1):
                print(f"   {i}. {workflow.name} - Status: {workflow.status}")
                print(f"      ID: {workflow.id}")
                print(f"      Created: {workflow.created_at}")
                print(f"      Active: {workflow.is_active}")
                print()
        
        # Also check database file exists
        if settings.DATABASE_URL.startswith("sqlite:///"):
            db_path = settings.DATABASE_URL.replace("sqlite:///", "")
            if os.path.exists(db_path):
                file_size = os.path.getsize(db_path)
                print(f"💾 Database file: {db_path} ({file_size} bytes)")
            else:
                print(f"❌ Database file not found: {db_path}")
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        raise
    
    finally:
        db.close()

if __name__ == "__main__":
    check_workflows()