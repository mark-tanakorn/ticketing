#!/usr/bin/env python3
"""
Script to set checked_in = false for existing 'Checkout' assets.
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


def update_existing_check_ins():
    """Set checked_in = false for existing 'Checkout' assets"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Updating existing 'Checkout' assets to checked_in = false...")

        # Update existing Checkout assets
        cursor.execute(
            """
            UPDATE assets SET checked_in = false WHERE action = 'Checkout' AND checked_in IS NULL;
        """
        )

        conn.commit()
        cursor.close()
        conn.close()

        print("Existing 'Checkout' assets updated successfully!")

    except Exception as e:
        print(f"Error updating assets: {e}")


if __name__ == "__main__":
    update_existing_check_ins()
