"""
Create test user with ID=1 for testing SSO integration

This script creates a hardcoded user with:
- ID: 1
- Username: mark.tanakorn
- Email: mark.tanakorn@company.com

This user represents a BizProj user accessing TAV via SSO.
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

def create_test_user():
    """Create test user with ID=1"""
    db = SessionLocal()
    try:
        # Check if user with ID=1 already exists
        existing = db.query(User).filter(User.id == 1).first()
        
        if existing:
            print(f"\n✓ User with ID=1 already exists:")
            print(f"   ID: {existing.id}")
            print(f"   Username: {existing.user_name}")
            print(f"   Email: {existing.user_email}")
            return existing
        
        # Create user with ID=1
        test_user = User(
            id=1,
            user_id=str(uuid.uuid4()),
            user_name="mark.tanakorn",
            user_email="mark.tanakorn@company.com",
            user_password=hash_password("test123"),  # Not used for SSO, but required
            user_firstname="Mark",
            user_lastname="Tanakorn",
            user_is_deleted=False,
            user_is_disabled=False,
            is_show=True,
            user_is_firsttime_login=False,
            version_no=0,
        )
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        print(f"\n✅ Successfully created test user:")
        print(f"   ID: {test_user.id}")
        print(f"   UUID: {test_user.user_id}")
        print(f"   Username: {test_user.user_name}")
        print(f"   Email: {test_user.user_email}")
        print(f"\n📝 This user will have workflows associated with author_id=1")
        
        return test_user
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error creating test user: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Creating Test User (ID=1)")
    print("=" * 60)
    
    create_test_user()
    
    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print("\n💡 Next steps:")
    print("   1. Create workflows as this user (they'll have author_id=1)")
    print("   2. Log in with a different SSO user")
    print("   3. Verify the new user sees no workflows")
    print("=" * 60)

