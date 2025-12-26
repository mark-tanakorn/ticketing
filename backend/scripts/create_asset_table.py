#!/usr/bin/env python3
"""
Script to create the asset_history table for tracking asset actions.
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


def create_asset_history_table():
    """Create the asset_history table with the specified columns"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Creating asset_history table...")

        # Create assets table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS assets (
                id SERIAL PRIMARY KEY,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(255) NOT NULL,
                action VARCHAR(100) NOT NULL,
                item VARCHAR(255) NOT NULL,
                target VARCHAR(255)
            );
        """
        )

        # Create indexes for efficient querying
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_assets_date ON assets(date);
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_assets_created_by ON assets(created_by);
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_assets_action ON assets(action);
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_assets_item ON assets(item);
        """
        )

        conn.commit()
        print("Asset table created successfully!")

    except Exception as e:
        print(f"Error creating asset table: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    create_asset_history_table()
