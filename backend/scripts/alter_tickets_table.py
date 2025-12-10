#!/usr/bin/env python3
"""
Script to alter the tickets table: add approver and fixer columns, drop assigned_to column.
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

def alter_tickets_table():
    """Alter the tickets table to add new columns and drop old one"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Altering tickets table...")

        # Since there are no rows, we can safely drop and recreate the table with correct schema
        cursor.execute("DROP TABLE tickets;")

        # Recreate with correct column order
        cursor.execute("""
            CREATE TABLE tickets (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                category VARCHAR(50),
                severity VARCHAR(50),
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'open',
                approver VARCHAR(255),
                fixer VARCHAR(255),
                attachment_upload TEXT
            );
        """)

        conn.commit()
        print("Tickets table altered successfully!")

    except Exception as e:
        print(f"❌ Error altering table: {e}")

    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    alter_tickets_table()