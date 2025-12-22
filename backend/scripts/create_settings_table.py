#!/usr/bin/env python3
"""
Initialize settings table with default values.
Run this script to populate the settings table with initial configuration values.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_db_connection

def init_settings():
    """Initialize the settings table with default values."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert initial settings values
        settings_data = [
            ('SLA_LOW_HOURS', '72', 'SLA timeframe for low priority tickets (hours)', 'sla', 'number'),
            ('SLA_MEDIUM_HOURS', '48', 'SLA timeframe for medium priority tickets (hours)', 'sla', 'number'),
            ('SLA_HIGH_HOURS', '24', 'SLA timeframe for high priority tickets (hours)', 'sla', 'number'),
            ('SLA_CRITICAL_HOURS', '0.1', 'SLA timeframe for critical priority tickets (hours)', 'sla', 'number'),
            ('PRE_BREACH_SECONDS', '300', 'Seconds before SLA breach to send warnings', 'sla', 'number'),
            ('COMMUNICATION_MODE', 'EMAIL', 'Communication method: EMAIL or WHATSAPP', 'communication', 'string'),
        ]

        for key, value, description, category, data_type in settings_data:
            # Use INSERT ... ON CONFLICT to avoid duplicates
            cursor.execute(
                """
                INSERT INTO settings (key, value, description, category, data_type)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (key) DO NOTHING
                """,
                (key, value, description, category, data_type)
            )

        conn.commit()
        cursor.close()
        conn.close()

        print("✅ Settings table initialized successfully!")
        print("Inserted settings:")
        for key, value, description, category, data_type in settings_data:
            print(f"  - {key}: {value} ({description})")

    except Exception as e:
        print(f"❌ Error initializing settings: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_settings()