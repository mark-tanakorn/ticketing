#!/usr/bin/env python3
"""
Test script to add sample data with variations of each field to the tickets database.
"""

import psycopg2
import random
from datetime import datetime, timedelta

def get_db_connection():
    """Get database connection - same as in main.py"""
    return psycopg2.connect(
        host="localhost",
        database="ticketing_db",
        user="ticketing_user",
        password="mysecretpassword",
        port=5432
    )

def add_sample_data():
    """Add sample tickets with variations of all fields"""

    # Sample data variations
    titles = [
        "Network connectivity issue",
        "Software installation failed",
        "Hardware malfunction - monitor not working",
        "Access denied to shared folder",
        "Security vulnerability found",
        "Database performance slow",
        "Mobile app crashes on startup",
        "Email system down",
        "Printer not responding",
        "User account locked",
        "Website loading slowly",
        "File upload error",
        "Login authentication failed",
        "System backup incomplete",
        "API endpoint timeout"
    ]

    descriptions = [
        "Users are experiencing intermittent connectivity issues in the main office. Network drops every few minutes.",
        "Attempting to install the latest software update results in error code 0x80070005. Multiple users affected.",
        "The monitor in conference room B suddenly stopped working. Display shows 'No Signal' message.",
        "Employees cannot access the shared drive containing important project documents. Permission error displayed.",
        "Security scan detected potential vulnerability in the web application firewall. Requires immediate attention.",
        "Database queries are taking 10+ seconds to complete, significantly impacting user experience.",
        "iOS users report the mobile application crashes immediately upon opening. Android version works fine.",
        "Company email system is completely down. No incoming or outgoing emails are being processed.",
        "Network printer on floor 3 is not responding to print jobs. Error message: 'Printer offline'.",
        "Multiple user accounts have been locked due to suspected security breach. Password reset required.",
        "The company website is loading extremely slowly, with page load times exceeding 30 seconds.",
        "Users cannot upload files larger than 5MB to the document management system.",
        "LDAP authentication is failing for all users. System shows 'Invalid credentials' error.",
        "Automated nightly backup failed to complete. Only 60% of data was backed up successfully.",
        "REST API endpoints are timing out after 30 seconds. Affects integration with partner systems."
    ]

    categories = ["Network", "Software", "Hardware", "Access", "Security"]
    severities = ["low", "medium", "high", "critical"]
    statuses = ["open", "in_progress", "awaiting_approval", "approval_denied", "closed", "sla_breached"]
    assigned_tos = [
        "network_team", "dev_team", "it_support", "security_team",
        "backend_team", "frontend_team", "qa_team", "ops_team",
        "helpdesk", "sysadmin", "db_admin", "ui_team"
    ]
    attachments = [
        "network_diagram.pdf", "error_log.txt", "screenshot.png",
        "system_report.docx", "config_backup.zip", "debug_trace.log",
        "user_manual.pdf", "troubleshooting_guide.docx", None, ""
    ]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Adding sample data to tickets table...")

        # Generate 50 sample tickets with variations
        for i in range(50):
            # Generate random ID
            ticket_id = random.randint(100000, 999999)

            # Random selections from each field
            title = random.choice(titles)
            description = random.choice(descriptions)
            category = random.choice(categories)
            severity = random.choice(severities)
            status = random.choice(statuses)
            assigned_to = random.choice(assigned_tos)
            attachment = random.choice(attachments)

            # Random date within last 90 days
            days_ago = random.randint(0, 90)
            date_created = datetime.now() - timedelta(days=days_ago)

            # Insert the ticket
            cursor.execute("""
                INSERT INTO tickets (id, title, description, category, severity, status, assigned_to, attachment_upload, date_created)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (ticket_id, title, description, category, severity, status, assigned_to, attachment, date_created))

            if (i + 1) % 10 == 0:
                print(f"Added {i + 1} tickets...")

        conn.commit()
        cursor.close()
        conn.close()

        print("✅ Successfully added 50 sample tickets with field variations!")
        print("Sample data includes:")
        print("- Random IDs (6-digit)")
        print("- Various titles and descriptions")
        print("- All category types: Network, Software, Hardware, Access, Security")
        print("- All severity levels: low, medium, high, critical")
        print("- All status types: open, in_progress, awaiting_approval, approval_denied, closed, sla_breached")
        print("- Different assigned teams")
        print("- Various attachment types (including null/empty)")
        print("- Random dates within last 90 days")

    except Exception as e:
        print(f"❌ Error adding sample data: {e}")

if __name__ == "__main__":
    add_sample_data()