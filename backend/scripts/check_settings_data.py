#!/usr/bin/env python3
"""
Script to check and display all settings data from the database.
"""

import sys
import os
from datetime import datetime

# Add the parent directory to the path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_db_connection

def check_settings_data():
    """Query and display all settings from the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query all settings
        cursor.execute("""
            SELECT id, key, value, description, category, data_type, created_at, updated_at
            FROM settings
            ORDER BY category, key
        """)

        settings = cursor.fetchall()

        if not settings:
            print("No settings found in the database.")
            return

        print(f"Found {len(settings)} settings in the database:\n")
        print("-" * 100)

        # Group by category
        current_category = None
        for setting in settings:
            setting_id, key, value, description, category, data_type, created_at, updated_at = setting

            if category != current_category:
                if current_category is not None:
                    print()  # Add spacing between categories
                print(f"📁 Category: {category}")
                print("-" * 50)
                current_category = category

            print(f"🔑 Key: {key}")
            print(f"   Value: {value} (type: {data_type})")
            print(f"   Description: {description}")
            print(f"   Created: {created_at}")
            print(f"   Updated: {updated_at}")
            print()

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error checking settings data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_settings_data()