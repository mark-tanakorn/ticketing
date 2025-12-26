#!/usr/bin/env python3
"""
Script to add checked_out column to the assets table.
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


def add_checked_out_column():
    """Add checked_out column to assets table"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Adding checked_out column to assets table...")

        # Add checked_out column
        cursor.execute(
            """
            ALTER TABLE assets ADD COLUMN IF NOT EXISTS checked_out BOOLEAN DEFAULT NULL;
        """
        )

        conn.commit()
        cursor.close()
        conn.close()

        print("checked_out column added successfully!")

    except Exception as e:
        print(f"Error adding column: {e}")


if __name__ == "__main__":
    add_checked_out_column()
