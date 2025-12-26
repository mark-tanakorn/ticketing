#!/usr/bin/env python3
"""
Script to add serial_number column to the assets table.
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


def add_serial_number_column():
    """Add serial_number column to assets table"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Adding serial_number column to assets table...")

        # Add serial_number column
        cursor.execute(
            """
            ALTER TABLE assets ADD COLUMN IF NOT EXISTS serial_number VARCHAR(255);
        """
        )

        conn.commit()
        cursor.close()
        conn.close()

        print("serial_number column added successfully!")

    except Exception as e:
        print(f"Error adding column: {e}")


if __name__ == "__main__":
    add_serial_number_column()
