#!/usr/bin/env python3
"""
Simple script to delete all rows from the tickets table.
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

def delete_all_data():
    """Delete all rows from tickets table"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM tickets")
        count_before = cursor.fetchone()[0]

        # Delete all rows
        cursor.execute("DELETE FROM tickets")

        # Reset auto-increment counter (optional)
        cursor.execute("ALTER SEQUENCE tickets_id_seq RESTART WITH 1")

        conn.commit()
        cursor.close()
        conn.close()

        print(f"✅ Successfully deleted {count_before} tickets from the database!")
        print("Auto-increment sequence has been reset to 1.")

    except Exception as e:
        print(f"❌ Error deleting data: {e}")

if __name__ == "__main__":
    # Add confirmation prompt for safety
    confirm = input("⚠️  WARNING: This will delete ALL tickets from the database!\nAre you sure? (type 'yes' to confirm): ")

    if confirm.lower() == 'yes':
        delete_all_data()
    else:
        print("Operation cancelled.")