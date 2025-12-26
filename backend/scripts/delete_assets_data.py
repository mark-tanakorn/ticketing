#!/usr/bin/env python3
"""
Simple script to delete all rows from the assets table.
"""

import psycopg2

def get_db_connection():
    """Get database connection - same as in main.py"""
    return psycopg2.connect(
        host="localhost",
        database="ticketing_db",
        user="ticketing_user",
        password="mysecretpassword",
        port=5432
    )

def delete_all_assets():
    """Delete all rows from assets table"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM assets")
        count_before = cursor.fetchone()[0]

        # Delete all rows
        cursor.execute("DELETE FROM assets")

        # Reset auto-increment counter (optional)
        cursor.execute("ALTER SEQUENCE assets_id_seq RESTART WITH 1")

        conn.commit()
        cursor.close()
        conn.close()

        print(f"✅ Successfully deleted {count_before} assets from the database!")
        print("Auto-increment sequence has been reset to 1.")

    except Exception as e:
        print(f"❌ Error deleting data: {e}")

if __name__ == "__main__":
    # Add confirmation prompt for safety
    confirm = input("⚠️  WARNING: This will delete ALL assets from the database!\nAre you sure? (type 'yes' to confirm): ")

    if confirm.lower() == 'yes':
        delete_all_assets()
    else:
        print("Operation cancelled.")