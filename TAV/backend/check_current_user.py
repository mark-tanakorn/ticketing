"""
Quick script to check current user in TAV (for dev mode)
"""
import sqlite3
import os

# Path to SQLite database
db_path = "data/tav_engine.db"

if not os.path.exists(db_path):
    print("❌ Database not found at:", db_path)
    print("   Backend server might not be running or database not initialized")
    exit(1)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all users
cursor.execute("""
    SELECT id, user_name, user_email, user_firstname, user_lastname, 
           user_is_deleted, user_is_disabled
    FROM users
    WHERE user_is_deleted = 0 OR user_is_deleted IS NULL
    ORDER BY id
""")

users = cursor.fetchall()

print("=" * 70)
print("Current Users in TAV Database")
print("=" * 70)

if not users:
    print("\n❌ No users found in database!")
    print("   You need to create a user first.")
    print("\n💡 Run: python scripts/create_test_user.py")
else:
    print(f"\n✓ Found {len(users)} user(s):\n")
    for user in users:
        user_id, username, email, firstname, lastname, is_deleted, is_disabled = user
        status = "🟢 Active"
        if is_disabled:
            status = "🔴 Disabled"
        elif is_deleted:
            status = "⚫ Deleted"
        
        print(f"  ID: {user_id}")
        print(f"  Username: {username}")
        print(f"  Email: {email or 'N/A'}")
        print(f"  Name: {firstname or ''} {lastname or ''}")
        print(f"  Status: {status}")
        print()
    
    # Check dev mode status
    cursor.execute("""
        SELECT value FROM settings 
        WHERE namespace = 'developer' AND key = 'enable_dev_mode'
    """)
    dev_mode_row = cursor.fetchone()
    
    if dev_mode_row:
        dev_mode = dev_mode_row[0].strip('"').lower() == 'true'
    else:
        dev_mode = True  # Default
    
    print("-" * 70)
    if dev_mode:
        first_user = users[0]
        print(f"🔓 DEV MODE ENABLED")
        print(f"   You are currently logged in as: {first_user[1]} (ID={first_user[0]})")
        print(f"   All API calls will use this user automatically.")
    else:
        print(f"🔒 PRODUCTION MODE")
        print(f"   You need a valid JWT token to access API.")

# Get workflow count per user
print("\n" + "=" * 70)
print("Workflows by User")
print("=" * 70)

cursor.execute("""
    SELECT author_id, COUNT(*) as workflow_count
    FROM workflows
    WHERE author_id IS NOT NULL
    GROUP BY author_id
""")

workflow_counts = cursor.fetchall()

if not workflow_counts:
    print("\n   No workflows found in database.")
else:
    for author_id, count in workflow_counts:
        # Get username
        cursor.execute("SELECT user_name FROM users WHERE id = ?", (author_id,))
        username_row = cursor.fetchone()
        username = username_row[0] if username_row else "Unknown"
        
        print(f"   User ID {author_id} ({username}): {count} workflow(s)")

conn.close()

print("\n" + "=" * 70)

