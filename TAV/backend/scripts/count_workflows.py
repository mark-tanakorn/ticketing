#!/usr/bin/env python3
"""
Count workflows in the database.
"""

import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database.models.workflow import Workflow

def count_workflows():
    """Count all workflows in the database."""
    
    # Create database engine and session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        workflows = db.query(Workflow).all()
        count = len(workflows)
        
        print(f"📊 Total workflows in database: {count}")
        print("\nWorkflows:")
        for i, wf in enumerate(workflows, 1):
            print(f"{i}. {wf.name} - Status: {wf.status} - Author: {wf.author_id}")
        
    except Exception as e:
        print(f"❌ Error counting workflows: {e}")
        raise
    
    finally:
        db.close()

if __name__ == "__main__":
    count_workflows()
