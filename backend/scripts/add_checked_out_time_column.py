#!/usr/bin/env python3
"""
Script to add checked_out_time column to the assets table.
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


def add_checked_out_time_column():
    """Add checked_out_time column to assets table"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Adding checked_out_time column to assets table...")

        # Add checked_out_time column
        cursor.execute(
            """
            ALTER TABLE assets ADD COLUMN IF NOT EXISTS checked_out_time TIMESTAMP;
        """
        )

        conn.commit()
        cursor.close()
        conn.close()

        print("checked_out_time column added successfully!")

    except Exception as e:
        print(f"Error adding column: {e}")


if __name__ == "__main__":
    add_checked_out_time_column()
