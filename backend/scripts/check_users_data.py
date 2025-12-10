#!/usr/bin/env python3
"""
Script to check what users are in the users table.
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

def check_users():
    """Check what users exist in the database."""

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        print("🔍 Checking users in database...")

        # Count total users
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()['count']
        print(f"📊 Total users in database: {count}")

        if count == 0:
            print("❌ No users found in database!")
        else:
            print("\n📋 Users found:")
            cursor.execute("SELECT * FROM users ORDER BY id")
            users = cursor.fetchall()
            for i, user in enumerate(users, 1):
                print(f"   {i}. {user['name']} - {user['email']}")
                print(f"      ID: {user['id']}")
                print(f"      Phone: {user['phone'] or 'N/A'}")
                print(f"      Department: {user['department'] or 'N/A'}")
                print(f"      Approval Tier: {user['approval_tier'] or 'N/A'}")
                print()

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error checking users: {e}")

if __name__ == "__main__":
    check_users()