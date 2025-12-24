#!/usr/bin/env python3
"""
Script to check what ticket entries are in the tickets table.
"""

import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """Get database connection - same as in main.py"""
    return psycopg2.connect(
        host="localhost",
        database="ticketing_db",
        user="ticketing_user",
        password="mysecretpassword",
        port=5432,
    )


def check_tickets():
    """Check what ticket entries exist in the database."""

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        print("🔍 Checking ticket entries in database...")

        # Count total ticket entries
        cursor.execute("SELECT COUNT(*) FROM tickets")
        count = cursor.fetchone()["count"]
        print(f"📊 Total ticket entries in database: {count}")

        if count == 0:
            print("❌ No ticket entries found in database!")
        else:
            print("\n📋 Ticket entries found:")
            cursor.execute("SELECT * FROM tickets ORDER BY id")
            tickets = cursor.fetchall()
            for i, ticket in enumerate(tickets, 1):
                print(f"   {i}. Ticket ID: {ticket['id']} - {ticket['title']}")
                print(f"      User ID: {ticket['user_id'] or 'N/A'}")
                print(f"      Description: {ticket['description'] or 'N/A'}")
                print(f"      Category: {ticket['category'] or 'N/A'}")
                print(f"      Severity: {ticket['severity'] or 'N/A'}")
                print(f"      Status: {ticket['status'] or 'N/A'}")
                print(f"      Date Created: {ticket['date_created'] or 'N/A'}")
                print(f"      Approver: {ticket['approver'] or 'N/A'}")
                print(f"      Fixer: {ticket['fixer'] or 'N/A'}")
                print(f"      Attachment: {ticket['attachment_upload'] or 'N/A'}")
                if ticket['approver_decision'] is not None:
                    print(f"      Approved: {ticket['approver_decision']}")
                if ticket['approver_reply_text']:
                    print(f"      Approver Reply: {ticket['approver_reply_text']}")
                if ticket['tav_execution_id']:
                    print(f"      TAV Execution ID: {ticket['tav_execution_id']}")
                print()

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error checking tickets: {e}")


if __name__ == "__main__":
    check_tickets()