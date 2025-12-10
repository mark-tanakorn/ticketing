#!/usr/bin/env python3
"""
Script to add sample data to the users table.
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

def add_sample_users():
    """Add sample users with different departments and approval tiers"""

    # Sample users data
    users = [
        {
            "name": "Kenji",
            "phone": "123",
            "email": "kenji@gmail.com",
            "department": "IT",
            "approval_tier": "1"
        },
        {
            "name": "Amos",
            "phone": "234",
            "email": "amos@gmail.com",
            "department": "IT",
            "approval_tier": "2"
        },
        {
            "name": "Bryan",
            "phone": "345",
            "email": "bryan@gmail.com",
            "department": "IT",
            "approval_tier": "3"
        },
    ]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Adding sample users to users table...")

        for i, user in enumerate(users, 1):
            cursor.execute("""
                INSERT INTO users (name, phone, email, department, approval_tier)
                VALUES (%s, %s, %s, %s, %s)
            """, (user['name'], user['phone'], user['email'], user['department'], user['approval_tier']))

            print(f"Added user {i}: {user['name']} ({user['department']} - Tier {user['approval_tier']})")

        conn.commit()
        cursor.close()
        conn.close()

        print("✅ Successfully added sample users!")


    except Exception as e:
        print(f"❌ Error adding sample users: {e}")

if __name__ == "__main__":
    add_sample_users()