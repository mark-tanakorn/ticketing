"""
Reset/Delete All Encrypted Credentials

This script deletes:
- All credentials from the credentials table
- All AI provider settings (which have encrypted API keys)

This does NOT delete:
- Workflows
- Executions
- Files
- Users
- Any other data

Use this when you've changed your ENCRYPTION_KEY and credentials can't be decrypted.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.session import SessionLocal, engine
from app.database.models import Credential, Setting
from sqlalchemy import delete


def reset_credentials():
    """Delete all credentials and AI provider settings."""
    db = SessionLocal()
    
    try:
        # Count before deletion
        credential_count = db.query(Credential).count()
        ai_settings_count = db.query(Setting).filter(
            Setting.category == 'ai',
            Setting.key == 'providers'
        ).count()
        
        print(f"Found {credential_count} credentials")
        print(f"Found {ai_settings_count} AI provider settings")
        print()
        
        if credential_count == 0 and ai_settings_count == 0:
            print("✅ No encrypted credentials to delete!")
            return
        
        # Ask for confirmation
        response = input("Delete all encrypted credentials? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled")
            return
        
        # Delete credentials
        if credential_count > 0:
            db.execute(delete(Credential))
            print(f"✅ Deleted {credential_count} credentials")
        
        # Delete AI provider settings (which contain encrypted API keys)
        if ai_settings_count > 0:
            db.execute(
                delete(Setting).where(
                    Setting.category == 'ai',
                    Setting.key == 'providers'
                )
            )
            print(f"✅ Deleted AI provider settings")
        
        db.commit()
        print()
        print("✅ All encrypted credentials deleted!")
        print()
        print("Next steps:")
        print("1. Restart your backend server")
        print("2. Go to Settings page in the UI")
        print("3. Re-add your AI providers and credentials")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Reset Encrypted Credentials")
    print("=" * 60)
    print()
    print("⚠️  This will delete:")
    print("   - All credentials from credentials table")
    print("   - AI provider settings (with encrypted API keys)")
    print()
    print("✅ This will NOT delete:")
    print("   - Workflows")
    print("   - Executions")
    print("   - Files")
    print("   - Users")
    print()
    
    reset_credentials()

