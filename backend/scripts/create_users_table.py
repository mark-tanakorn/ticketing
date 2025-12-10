#!/usr/bin/env python3
"""
Script to create the users table for the ticketing system.
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

def create_users_table():
    """Create the users table with the specified columns"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Creating users table...")

        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                email VARCHAR(255) UNIQUE NOT NULL,
                department VARCHAR(100),
                approval_tier INTEGER,
            );
        """)

        # Create an index on email for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """)

        # Create an index on department for filtering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_department ON users(department);
        """)

        conn.commit()
        print("Users table created successfully!")

        # Add some sample users
        print("Adding sample users...")
        sample_users = [
            ("John Smith", "+1-555-0101", "john.smith@company.com", "IT", 1),
            ("Sarah Johnson", "+1-555-0102", "sarah.johnson@company.com", "HR", 2),
            ("Mike Davis", "+1-555-0103", "mike.davis@company.com", "Finance", 1),
            ("Emily Chen", "+1-555-0104", "emily.chen@company.com", "IT", 3),
            ("David Wilson", "+1-555-0105", "david.wilson@company.com", "Operations", 2),
            ("Lisa Brown", "+1-555-0106", "lisa.brown@company.com", "Legal", None),
            ("Tom Anderson", "+1-555-0107", "tom.anderson@company.com", "IT", 1),
            ("Jennifer Lee", "+1-555-0108", "jennifer.lee@company.com", "Marketing", 2),
        ]

        for user in sample_users:
            cursor.execute("""
                INSERT INTO users (name, phone, email, department, approval_tier)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING;
            """, user)

        conn.commit()
        print(f"Added {len(sample_users)} sample users!")

    except Exception as e:
        print(f"Error creating users table: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_users_table()