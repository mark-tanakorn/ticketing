"""
Manual Database Migration Script
Adds file_type and file_category columns to files table
"""

import sqlite3
import sys
from pathlib import Path

# Path to database
db_path = Path("data/tav_engine.db")

if not db_path.exists():
    print(f"❌ Database not found: {db_path}")
    print("Make sure you're running this from the backend directory")
    sys.exit(1)

print(f"📦 Migrating database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(files)")
    columns = [row[1] for row in cursor.fetchall()]
    
    needs_migration = False
    
    if 'file_type' not in columns:
        print("➕ Adding file_type column...")
        cursor.execute("ALTER TABLE files ADD COLUMN file_type TEXT")
        cursor.execute("UPDATE files SET file_type = 'upload' WHERE file_type IS NULL")
        needs_migration = True
    else:
        print("✅ file_type column already exists")
    
    if 'file_category' not in columns:
        print("➕ Adding file_category column...")
        cursor.execute("ALTER TABLE files ADD COLUMN file_category TEXT")
        cursor.execute("UPDATE files SET file_category = 'other' WHERE file_category IS NULL")
        needs_migration = True
    else:
        print("✅ file_category column already exists")
    
    if 'workflow_id' not in columns:
        print("➕ Adding workflow_id column...")
        cursor.execute("ALTER TABLE files ADD COLUMN workflow_id TEXT")
        needs_migration = True
    else:
        print("✅ workflow_id column already exists")
    
    if 'execution_id' not in columns:
        print("➕ Adding execution_id column...")
        cursor.execute("ALTER TABLE files ADD COLUMN execution_id TEXT")
        needs_migration = True
    else:
        print("✅ execution_id column already exists")
    
    # Create indexes (SQLite will ignore if they exist)
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_file_type ON files(file_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_file_category ON files(file_category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_workflow_id ON files(workflow_id)")
        print("✅ Indexes created/verified")
    except Exception as e:
        print(f"⚠️  Index creation warning: {e}")
    
    conn.commit()
    
    if needs_migration:
        print("\n✅ Migration completed successfully!")
    else:
        print("\n✅ Database already up to date!")
    
    print("\n📊 Current files table schema:")
    cursor.execute("PRAGMA table_info(files)")
    for row in cursor.fetchall():
        print(f"  - {row[1]} ({row[2]})")
    
    conn.close()
    
except Exception as e:
    print(f"\n❌ Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

