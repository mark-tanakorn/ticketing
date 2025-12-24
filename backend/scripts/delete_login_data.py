#!/usr/bin/env python3
"""
Simple script to delete all rows from the login table.
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

def delete_all_login_data():
    """Delete all rows from login table"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM login")
        count_before = cursor.fetchone()[0]

        # Delete all rows
        cursor.execute("DELETE FROM login")

        # Reset auto-increment counter (optional)
        cursor.execute("ALTER SEQUENCE login_user_id_seq RESTART WITH 1")

        conn.commit()
        cursor.close()
        conn.close()

        print(f"✅ Successfully deleted {count_before} login entries from the database!")
        print("Auto-increment sequence has been reset to 1.")

    except Exception as e:
        print(f"❌ Error deleting login data: {e}")

if __name__ == "__main__":
    # Add confirmation prompt for safety
    confirm = input("⚠️  WARNING: This will delete ALL login entries from the database!\nAre you sure? (type 'yes' to confirm): ")

    if confirm.lower() == 'yes':
        delete_all_login_data()
    else:
        print("Operation cancelled.")