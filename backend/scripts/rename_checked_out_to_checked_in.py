#!/usr/bin/env python3
"""
Script to rename checked_out columns to checked_in in the assets table.
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


def rename_checked_out_columns():
    """Rename checked_out and checked_out_time columns to checked_in and checked_in_time"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Renaming checked_out columns to checked_in...")

        # Rename checked_out_time to checked_in_time
        cursor.execute(
            """
            ALTER TABLE assets RENAME COLUMN checked_out_time TO checked_in_time;
        """
        )

        # Rename checked_out to checked_in
        cursor.execute(
            """
            ALTER TABLE assets RENAME COLUMN checked_out TO checked_in;
        """
        )

        conn.commit()
        cursor.close()
        conn.close()

        print("Columns renamed successfully!")
    except Exception as e:
        print(f"Error renaming columns: {e}")


if __name__ == "__main__":
    rename_checked_out_columns()