#!/usr/bin/env python3
"""
Script to create the fixers table for the ticketing system.
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

def create_fixers_table():
    """Create the fixers table with the specified columns"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Creating fixers table...")

        # Create fixers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fixers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                phone VARCHAR(50),
                department VARCHAR(255)
            );
        """)

        # Create an index on email for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fixers_email ON fixers(email);
        """)

        # Create an index on department for filtering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fixers_department ON fixers(department);
        """)

        conn.commit()
        print("Fixers table created successfully!")

        # Add some sample fixers
        print("Adding sample fixers...")
        sample_fixers = [
            ("John Doe", "john.doe@example.com", "123-456-7890", "IT"),
            ("Jane Smith", "jane.smith@example.com", "098-765-4321", "HR"),
        ]

        for fixer in sample_fixers:
            cursor.execute("""
                INSERT INTO fixers (name, email, phone, department)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING;
            """, fixer)

        conn.commit()
        print(f"Added {len(sample_fixers)} sample fixers!")

    except Exception as e:
        print(f"Error creating fixers table: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_fixers_table()