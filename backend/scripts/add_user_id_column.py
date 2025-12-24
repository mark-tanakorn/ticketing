#!/usr/bin/env python3
"""
Script to add user_id column to the existing tickets table.
"""

import psycopg2


def get_db_connection():
    """Get database connection - same as in main.py"""
    return psycopg2.connect(
        host="localhost",
        database="ticketing_db",
        user="ticketing_user",
        password="mysecretpassword",
        port=5432,
    )


def add_user_id_column():
    """Add user_id column to tickets table if it doesn't exist."""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("🔧 Adding user_id column to tickets table...")

        # Check if user_id column already exists
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tickets' AND column_name = 'user_id'
        """
        )

        if cursor.fetchone():
            print("✅ user_id column already exists in tickets table")
        else:
            # Add the user_id column
            cursor.execute(
                """
                ALTER TABLE tickets
                ADD COLUMN user_id INTEGER REFERENCES login(user_id)
            """
            )
            print("✅ Successfully added user_id column to tickets table")

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error adding user_id column: {e}")


if __name__ == "__main__":
    add_user_id_column()
