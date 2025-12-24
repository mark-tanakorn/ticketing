#!/usr/bin/env python3
"""
Script to check the login table schema.
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

def check_login_schema():
    """Check the schema of the login table."""

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        print("🔍 Checking login table schema...")

        # Get table schema
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'login'
            ORDER BY ordinal_position;
        """)

        columns = cursor.fetchall()

        if not columns:
            print("❌ Login table does not exist!")
        else:
            print("📋 Login table columns:")
            for col in columns:
                nullable = "NOT NULL" if col['is_nullable'] == 'NO' else "NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"   - {col['column_name']} {col['data_type']} {nullable}{default}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error checking schema: {e}")

if __name__ == "__main__":
    check_login_schema()