"""
Create admin user for development
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.session import SessionLocal
from app.database.models.user import User
from app.utils.hashing import hash_password
import uuid

def check_existing_users():
    """Check if there are any existing users"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"\n✓ Found {len(users)} existing user(s) in database:")
        for user in users:
            print(f"  - ID: {user.id}, Username: {user.user_name}, Email: {user.user_email}")
        return users
    finally:
        db.close()

def create_admin_user(username, email, password, firstname=None, lastname=None):
    """Create an admin user"""
    db = SessionLocal()
    try:
        # Check if user already exists
        existing = db.query(User).filter(
            (User.user_name == username) | (User.user_email == email)
        ).first()
        
        if existing:
            print(f"\n❌ User already exists:")
            print(f"   Username: {existing.user_name}")
            print(f"   Email: {existing.user_email}")
            return existing
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Get the next ID manually (SQLite autoincrement workaround)
        max_id = db.query(User.id).order_by(User.id.desc()).first()
        next_id = (max_id[0] + 1) if max_id and max_id[0] else 1
        
        # Create new user
        new_user = User(
            id=next_id,  # Explicitly set the ID
            user_id=str(uuid.uuid4()),
            user_name=username,
            user_email=email,
            user_password=hashed_password,
            user_firstname=firstname or username.capitalize(),
            user_lastname=lastname or "User",
            user_is_deleted=False,
            user_is_disabled=False,
            is_show=True,
            user_is_firsttime_login=False,  # Skip first-time login for dev
            version_no=0,
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"\n✅ Successfully created admin user:")
        print(f"   ID: {new_user.id}")
        print(f"   UUID: {new_user.user_id}")
        print(f"   Username: {new_user.user_name}")
        print(f"   Email: {new_user.user_email}")
        print(f"   Password: {password} (please change this!)")
        
        return new_user
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error creating user: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Admin User Setup")
    print("=" * 60)
    
    # Check existing users first
    check_existing_users()
    
    print("\n" + "=" * 60)
    print("Please provide the following information:")
    print("=" * 60)
    
    # Get user input
    username = input("\nUsername (default: admin): ").strip() or "admin"
    email = input("Email (default: admin@tavengine.local): ").strip() or "admin@tavengine.local"
    password = input("Password (default: admin123): ").strip() or "admin123"
    firstname = input("First Name (optional, press Enter to skip): ").strip() or None
    lastname = input("Last Name (optional, press Enter to skip): ").strip() or None
    
    # Create user
    create_admin_user(username, email, password, firstname, lastname)
    
    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)

