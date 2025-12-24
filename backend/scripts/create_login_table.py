#!/usr/bin/env python3
"""
Script to create the login table for the ticketing system.
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


def create_login_table():
    """Create the login table with the specified columns"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Creating login table...")

        # Create login table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS login (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'user'
            );
        """
        )

        # Create an index on username for faster lookups
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_login_username ON login(username);
        """
        )

        # Create an index on email for faster lookups
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_login_email ON login(email);
        """
        )

        conn.commit()
        print("Login table created successfully!")

    except Exception as e:
        print(f"Error creating login table: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    create_login_table()
