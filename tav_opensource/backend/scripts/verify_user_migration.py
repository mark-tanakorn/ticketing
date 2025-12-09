"""
Database Structure Verification Script

This script verifies the database structure and foreign key relationships
after the user table migration.
"""

import sqlite3
import sys
from pathlib import Path

def check_table_structure(cursor, table_name):
    """Check and display table structure."""
    print(f"\n{'='*60}")
    print(f"Table: {table_name}")
    print(f"{'='*60}")
    
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    if not columns:
        print(f"  ❌ Table '{table_name}' does not exist!")
        return False
    
    print("\nColumns:")
    print(f"{'CID':<5} {'Name':<30} {'Type':<15} {'NotNull':<8} {'Default':<10} {'PK':<5}")
    print("-" * 80)
    for col in columns:
        cid, name, col_type, notnull, default_val, pk = col
        print(f"{cid:<5} {name:<30} {col_type:<15} {notnull:<8} {str(default_val):<10} {pk:<5}")
    
    return True


def check_foreign_keys(cursor, table_name):
    """Check foreign key relationships."""
    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
    fks = cursor.fetchall()
    
    if fks:
        print(f"\nForeign Keys:")
        print(f"{'ID':<5} {'Seq':<5} {'Table':<20} {'From':<20} {'To':<20} {'OnUpdate':<15} {'OnDelete':<15}")
        print("-" * 100)
        for fk in fks:
            fk_id, seq, table, from_col, to_col, on_update, on_delete, match = fk
            print(f"{fk_id:<5} {seq:<5} {table:<20} {from_col:<20} {to_col:<20} {on_update:<15} {on_delete:<15}")
    else:
        print(f"\nForeign Keys: None")
    
    return fks


def check_indexes(cursor, table_name):
    """Check table indexes."""
    cursor.execute(f"PRAGMA index_list({table_name})")
    indexes = cursor.fetchall()
    
    if indexes:
        print(f"\nIndexes:")
        print(f"{'Seq':<5} {'Name':<40} {'Unique':<8} {'Origin':<10}")
        print("-" * 70)
        for idx in indexes:
            seq, name, unique, origin, partial = idx
            print(f"{seq:<5} {name:<40} {unique:<8} {origin:<10}")
    else:
        print(f"\nIndexes: None")
    
    return indexes


def verify_database(db_path):
    """Main verification function."""
    print(f"\n🔍 Verifying Database Structure")
    print(f"Database: {db_path}")
    
    if not Path(db_path).exists():
        print(f"\n❌ Database file not found: {db_path}")
        print(f"The migrations have not been run yet.")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Check users table
        users_exists = check_table_structure(cursor, "users")
        if users_exists:
            check_indexes(cursor, "users")
            
            # Count users
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            print(f"\n📊 Total users: {count}")
        
        # Check if backup table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users_backup'")
        if cursor.fetchone():
            print(f"\n✅ Backup table 'users_backup' exists")
            cursor.execute("SELECT COUNT(*) FROM users_backup")
            backup_count = cursor.fetchone()[0]
            print(f"📊 Backup users count: {backup_count}")
        
        # Check related tables
        related_tables = ['audit_logs', 'api_keys', 'workflows', 'files', 'executions']
        
        print(f"\n\n{'='*60}")
        print("RELATED TABLES WITH FOREIGN KEYS")
        print(f"{'='*60}")
        
        for table in related_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                print(f"\n{'='*60}")
                print(f"Table: {table}")
                print(f"{'='*60}")
                fks = check_foreign_keys(cursor, table)
                
                # Check if foreign key references users table
                user_fk_found = False
                for fk in fks:
                    if fk[2] == 'users':  # fk[2] is the referenced table
                        user_fk_found = True
                        break
                
                if user_fk_found:
                    print(f"✅ Foreign key to 'users' table found")
                else:
                    print(f"⚠️  No foreign key to 'users' table")
            else:
                print(f"\n⚠️  Table '{table}' does not exist yet")
        
        conn.close()
        
        print(f"\n\n{'='*60}")
        print("✅ Verification Complete")
        print(f"{'='*60}\n")
        
        return True
        
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    # Check if database path is provided
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # Default SQLite database path
        db_path = "tav_engine.db"
        print(f"No database path provided, using default: {db_path}")
    
    success = verify_database(db_path)
    sys.exit(0 if success else 1)

