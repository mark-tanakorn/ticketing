#!/usr/bin/env python3
"""
Add sample workflow data to the database for testing the frontend dashboard.
"""

import sys
import os
from datetime import datetime, timedelta
import uuid

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database.models.workflow import Workflow
from app.database.base import Base

def create_sample_workflows():
    """Create sample workflow data for testing."""
    
    # Create database engine and session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("🎯 Adding sample workflow data...")
        
        # Sample workflow data
        sample_workflows = [
            {
                "id": str(uuid.uuid4()),
                "name": "Daily Email Report",
                "description": "Automated daily email report with key metrics and insights",
                "status": "stopped",
                "is_active": True,
                "is_template": False,
                "author_id": 1,
                "version": "1.2.0",
                "tags": ["email", "reporting", "daily"],
                "created_at": datetime.utcnow() - timedelta(days=5),
                "updated_at": datetime.utcnow() - timedelta(hours=2),
                "last_run_at": datetime.utcnow() - timedelta(minutes=15),
                "workflow_data": {
                    "workflow_id": str(uuid.uuid4()),
                    "name": "Daily Email Report",
                    "description": "Automated daily email report",
                    "format_version": "2.0.0",
                    "nodes": [
                        {
                            "node_id": "trigger_1",
                            "node_type": "schedule_trigger",
                            "name": "Daily Trigger",
                            "category": "triggers",
                            "config": {"schedule": "0 9 * * *"},
                            "position": {"x": 100, "y": 100}
                        },
                        {
                            "node_id": "report_1",
                            "node_type": "generate_report",
                            "name": "Generate Report",
                            "category": "processing",
                            "config": {"format": "html"},
                            "position": {"x": 300, "y": 100}
                        },
                        {
                            "node_id": "email_1",
                            "node_type": "send_email",
                            "name": "Send Email",
                            "category": "communication",
                            "config": {"recipients": ["team@company.com"]},
                            "position": {"x": 500, "y": 100}
                        }
                    ],
                    "connections": [
                        {
                            "connection_id": "conn_1",
                            "source_node_id": "trigger_1",
                            "source_port": "output",
                            "target_node_id": "report_1",
                            "target_port": "input"
                        },
                        {
                            "connection_id": "conn_2",
                            "source_node_id": "report_1",
                            "source_port": "output",
                            "target_node_id": "email_1",
                            "target_port": "input"
                        }
                    ],
                    "global_config": {},
                    "variables": {},
                    "metadata": {
                        "created_at": "2025-01-01T00:00:00",
                        "updated_at": "2025-01-01T00:00:00",
                        "created_by": "admin"
                    }
                }
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Data Processing Pipeline",
                "description": "Process incoming CSV files and update database records",
                "status": "stopped",
                "is_active": True,
                "is_template": False,
                "author_id": 2,
                "version": "2.1.3",
                "tags": ["data", "csv", "processing"],
                "created_at": datetime.utcnow() - timedelta(days=12),
                "updated_at": datetime.utcnow() - timedelta(minutes=30),
                "last_run_at": datetime.utcnow() - timedelta(minutes=5),
                "workflow_data": {
                    "workflow_id": str(uuid.uuid4()),
                    "name": "Data Processing Pipeline",
                    "description": "Process CSV files",
                    "format_version": "2.0.0",
                    "nodes": [
                        {
                            "node_id": "watch_1",
                            "node_type": "file_watcher",
                            "name": "Watch Folder",
                            "category": "triggers",
                            "config": {"path": "/data/incoming", "pattern": "*.csv"},
                            "position": {"x": 100, "y": 100}
                        }
                    ],
                    "connections": [],
                    "global_config": {},
                    "variables": {},
                    "metadata": {
                        "created_at": "2025-01-01T00:00:00",
                        "updated_at": "2025-01-01T00:00:00",
                        "created_by": "admin"
                    }
                }
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Web Scraping Job",
                "description": "Scrape product prices from competitor websites",
                "status": "stopped",
                "is_active": True,
                "is_template": False,
                "author_id": 3,
                "version": "1.0.5",
                "tags": ["scraping", "prices", "monitoring"],
                "created_at": datetime.utcnow() - timedelta(days=8),
                "updated_at": datetime.utcnow() - timedelta(hours=4),
                "last_run_at": datetime.utcnow() - timedelta(hours=1),
                "workflow_data": {
                    "workflow_id": str(uuid.uuid4()),
                    "name": "Web Scraping Job",
                    "description": "Scrape competitor prices",
                    "format_version": "2.0.0",
                    "nodes": [],
                    "connections": [],
                    "global_config": {},
                    "variables": {},
                    "metadata": {
                        "created_at": "2025-01-01T00:00:00",
                        "updated_at": "2025-01-01T00:00:00",
                        "created_by": "admin"
                    }
                }
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Backup Database",
                "description": "Weekly automated database backup to cloud storage",
                "status": "stopped",
                "is_active": True,
                "is_template": False,
                "author_id": 4,
                "version": "1.1.0",
                "tags": ["backup", "database", "weekly"],
                "created_at": datetime.utcnow() - timedelta(days=20),
                "updated_at": datetime.utcnow() - timedelta(days=1),
                "last_run_at": datetime.utcnow() - timedelta(days=7),
                "workflow_data": {
                    "workflow_id": str(uuid.uuid4()),
                    "name": "Backup Database",
                    "description": "Weekly database backup",
                    "format_version": "2.0.0",
                    "nodes": [],
                    "connections": [],
                    "global_config": {},
                    "variables": {},
                    "metadata": {
                        "created_at": "2025-01-01T00:00:00",
                        "updated_at": "2025-01-01T00:00:00",
                        "created_by": "admin"
                    }
                }
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Social Media Monitor",
                "description": "Monitor brand mentions across social media platforms",
                "status": "stopped",
                "is_active": True,
                "is_template": False,
                "author_id": 2,
                "version": "0.9.2",
                "tags": ["social", "monitoring", "brand"],
                "created_at": datetime.utcnow() - timedelta(days=30),
                "updated_at": datetime.utcnow() - timedelta(days=3),
                "last_run_at": datetime.utcnow() - timedelta(days=3),
                "workflow_data": {
                    "workflow_id": str(uuid.uuid4()),
                    "name": "Social Media Monitor",
                    "description": "Monitor social mentions",
                    "format_version": "2.0.0",
                    "nodes": [],
                    "connections": [],
                    "global_config": {},
                    "variables": {},
                    "metadata": {
                        "created_at": "2025-01-01T00:00:00",
                        "updated_at": "2025-01-01T00:00:00",
                        "created_by": "admin"
                    }
                }
            }
        ]
        
        # Insert workflows
        for workflow_data in sample_workflows:
            workflow = Workflow(**workflow_data)
            db.add(workflow)
        
        # Commit all changes
        db.commit()
        
        print(f"✅ Successfully added {len(sample_workflows)} sample workflows!")
        print("\nSample workflows:")
        for wf in sample_workflows:
            print(f"  - {wf['name']} ({wf['status']})")
        
        print(f"\n🎉 Sample data ready! Refresh your dashboard at http://localhost:3000")
        
    except Exception as e:
        print(f"❌ Error adding sample data: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_workflows()