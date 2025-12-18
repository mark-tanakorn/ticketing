#!/usr/bin/env python3
"""
Script to add breach_triggered column to tickets table.
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

def add_breach_triggered_column():
    """Add breach_triggered column to tickets table"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Adding breach_triggered column to tickets table...")

        # Add the column if it doesn't exist
        cursor.execute("""
            ALTER TABLE tickets
            ADD COLUMN IF NOT EXISTS breach_triggered BOOLEAN DEFAULT FALSE;
        """)

        conn.commit()
        print("Column added successfully!")

    except Exception as e:
        print(f"❌ Error adding column: {e}")

if __name__ == "__main__":
    add_breach_triggered_column()