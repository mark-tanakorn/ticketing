#!/usr/bin/env python3
"""
Script to check the current schema of the tickets table.
"""

import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """Get database connection - same as in main.py"""
    return psycopg2.connect(
        host="localhost",
        database="ticketing_db",
        user="ticketing_user",
        password="mysecretpassword",
        port=5432
    )

def check_schema():
    """Check what columns exist in the tickets table"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        print("Checking tickets table schema...")

        # Get column information
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'tickets'
            ORDER BY ordinal_position;
        """)

        columns = cursor.fetchall()

        print("Current columns in tickets table:")
        for col in columns:
            print(f"  - {col['column_name']} ({col['data_type']}) - nullable: {col['is_nullable']}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error checking schema: {e}")

if __name__ == "__main__":
    check_schema()