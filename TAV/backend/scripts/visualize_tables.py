"""
Quick Database Table Visualizer

Shows all tables with their columns, types, and sample row counts.
"""

import sys
import sqlite3
from pathlib import Path
from tabulate import tabulate

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Database path
db_path = backend_dir / "data" / "tav_engine.db"

if not db_path.exists():
    print(f"❌ Database not found at: {db_path}")
    print("\nRun: python scripts/init_db.py to create it")
    sys.exit(1)

print(f"📊 Connecting to: {db_path}")
print("="*100)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\n✅ Found {len(tables)} tables in TAV database\n")
    
    # For each table, show structure and count
    for i, table_name in enumerate(tables, 1):
        print(f"\n{'='*100}")
        print(f"{i}. TABLE: {table_name}")
        print('='*100)
        
        # Get table info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Format columns as table
        headers = ["#", "Column Name", "Type", "Not Null", "Default", "Primary Key"]
        rows = []
        for col in columns:
            cid, name, col_type, not_null, default_val, pk = col
            rows.append([
                cid + 1,
                name,
                col_type,
                "✓" if not_null else "",
                default_val if default_val else "",
                "🔑" if pk else ""
            ])
        
        print(tabulate(rows, headers=headers, tablefmt="grid"))
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"\n📊 Row count: {count} records")
        
        # Get indexes
        cursor.execute(f"PRAGMA index_list({table_name})")
        indexes = cursor.fetchall()
        if indexes:
            print(f"📇 Indexes: {len(indexes)}")
            for idx in indexes[:3]:  # Show first 3
                print(f"   - {idx[1]}" + (" (UNIQUE)" if idx[2] else ""))
    
    print("\n" + "="*100)
    print("✅ Database visualization complete!")
    print("="*100)
    
    # Summary
    print("\n📋 QUICK SUMMARY:")
    print("-" * 100)
    summary_data = []
    for table_name in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        col_count = len(cursor.fetchall())
        summary_data.append([table_name, col_count, count])
    
    print(tabulate(
        summary_data,
        headers=["Table Name", "Columns", "Records"],
        tablefmt="pretty"
    ))
    
    conn.close()
    
    print("\n💡 TIP: For a visual interface, use DB Browser for SQLite:")
    print("   Download: https://sqlitebrowser.org/dl/")
    print(f"   Open file: {db_path}")
    
except sqlite3.Error as e:
    print(f"❌ Database error: {e}")
    sys.exit(1)
except ImportError:
    print("❌ Missing 'tabulate' library. Install with: pip install tabulate")
    sys.exit(1)

