"""
Direct SQLite cleanup - drops conversation tables
"""
import sqlite3
import os

# Database path (adjust if needed)
db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'tav_engine.db')

print(f"🔍 Database path: {db_path}")
print(f"📁 Exists: {os.path.exists(db_path)}")

if not os.path.exists(db_path):
    print("❌ Database file not found!")
    print("Looking for database files...")
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    if os.path.exists(data_dir):
        files = os.listdir(data_dir)
        print(f"Files in data/: {files}")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n🧹 Dropping tables...")
        
        # Drop in reverse order
        tables = ['conversation_messages', 'custom_nodes', 'conversations']
        
        for table in tables:
            try:
                cursor.execute(f'DROP TABLE IF EXISTS {table}')
                print(f"  ✅ Dropped {table}")
            except Exception as e:
                print(f"  ⚠️  {table}: {e}")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Cleanup complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

