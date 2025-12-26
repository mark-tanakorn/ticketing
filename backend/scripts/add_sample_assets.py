#!/usr/bin/env python3
"""
Script to add sample data to the assets table.
"""

import psycopg2
import random
import string
from datetime import datetime, timedelta


def get_db_connection():
    """Get database connection - same as in main.py"""
    return psycopg2.connect(
        host="localhost",
        database="ticketing_db",
        user="ticketing_user",
        password="mysecretpassword",
        port=5432,
    )


def generate_random_string(length=8):
    """Generate a random string of specified length"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def generate_random_item():
    """Generate a random item name"""
    items = [
        "Laptop", "Monitor", "Keyboard", "Mouse", "Headphones",
        "Tablet", "Phone", "Printer", "Scanner", "Projector",
        "Router", "Switch", "Cable", "Adapter", "Charger"
    ]
    return random.choice(items) + " " + generate_random_string(4)


def generate_random_serial():
    """Generate a random serial number"""
    return "SN-" + generate_random_string(10)


def generate_random_target():
    """Generate a random target from 3 predefined names"""
    targets = ["John Doe", "Jane Smith", "Bob Johnson"]
    return random.choice(targets)


def generate_random_action():
    """Generate a random action from checkout, transfer, maintenance"""
    actions = ["Checkout", "Transfer", "Maintenance"]
    return random.choice(actions)


def add_sample_assets():
    """Add 10 sample assets with random actions and checked_in = false"""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Adding sample assets to assets table...")

        # Generate 10 sample assets
        for i in range(50):
            asset_data = {
                "created_by": "System Admin",
                "action": generate_random_action(),
                "item": generate_random_item(),
                "serial_number": generate_random_serial(),
                "target": generate_random_target(),
                "checked_in": False
            }

            cursor.execute("""
                INSERT INTO assets (created_by, action, item, serial_number, target, checked_in)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                asset_data['created_by'],
                asset_data['action'],
                asset_data['item'],
                asset_data['serial_number'],
                asset_data['target'],
                asset_data['checked_in']
            ))

            print(f"Added asset {i+1}: {asset_data['item']} (SN: {asset_data['serial_number']}) - Target: {asset_data['target']}")

        conn.commit()
        cursor.close()
        conn.close()

        print("✅ Successfully added 10 sample assets!")

    except Exception as e:
        print(f"❌ Error adding sample assets: {e}")


if __name__ == "__main__":
    add_sample_assets()