#!/usr/bin/env python3
"""
Script to check what login entries are in the login table.
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
        port=5432,
    )


def check_login():
    """Check what login entries exist in the database."""

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        print("🔍 Checking login entries in database...")

        # Count total login entries
        cursor.execute("SELECT COUNT(*) FROM login")
        count = cursor.fetchone()["count"]
        print(f"📊 Total login entries in database: {count}")

        if count == 0:
            print("❌ No login entries found in database!")
        else:
            print("\n📋 Login entries found:")
            cursor.execute("SELECT * FROM login ORDER BY user_id")
            logins = cursor.fetchall()
            for i, login in enumerate(logins, 1):
                print(f"   {i}. {login['username']} - {login['email']}")
                print(f"      User ID: {login['user_id']}")
                print(
                    f"      Password: {'*' * len(login['password']) if login['password'] else 'N/A'}"
                )  # Mask password
                print(f"      Role: {login['role'] or 'N/A'}")
                print()

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error checking login entries: {e}")


if __name__ == "__main__":
    check_login()
