"""
Test Current User via API

Makes a simple API call to check who you're currently logged in as in dev mode.
"""
import requests
import sys

# Configuration
BACKEND_URL = "http://localhost:5000"

def check_current_user():
    """Check current user in dev mode"""
    print("=" * 70)
    print("Checking Current User (Dev Mode)")
    print("=" * 70)
    print()
    
    try:
        # Try to access a protected endpoint in dev mode
        # In dev mode, it should return the first active user automatically
        response = requests.get(f"{BACKEND_URL}/api/v1/users", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            users = data.get("users", [])
            
            if users:
                print("✅ Backend is running and accessible!")
                print()
                print(f"📊 Total users in database: {data.get('total', len(users))}")
                print()
                print("Current users:")
                for user in users:
                    print(f"  • ID: {user['id']}")
                    print(f"    Username: {user['user_name']}")
                    print(f"    Email: {user.get('user_email', 'N/A')}")
                    print(f"    Name: {user.get('user_firstname', '')} {user.get('user_lastname', '')}")
                    print()
                
                print("=" * 70)
                print("🔓 DEV MODE Status")
                print("=" * 70)
                print("If you're in dev mode, you're automatically logged in as the first user.")
                print(f"Current user should be: {users[0]['user_name']} (ID={users[0]['id']})")
                print()
                
                return users
            else:
                print("❌ No users found in database")
                print("   Run: python backend/scripts/create_test_user.py")
                return []
        
        elif response.status_code == 401:
            print("🔒 Backend requires authentication (Production Mode)")
            print("   Dev mode is disabled. You need a JWT token to access.")
            print()
            print("To enable dev mode, update database settings:")
            print("   UPDATE settings SET value='true' WHERE namespace='developer' AND key='enable_dev_mode';")
            return None
        
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"   {response.text}")
            return None
            
    except requests.ConnectionError:
        print("❌ Cannot connect to backend server")
        print(f"   Is the backend running at {BACKEND_URL}?")
        print()
        print("To start the backend:")
        print("   python scripts/native/start_native.py")
        return None
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def check_workflow_count():
    """Check workflow count per user"""
    print()
    print("=" * 70)
    print("Workflows by User")
    print("=" * 70)
    print()
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/workflows", timeout=5)
        
        if response.status_code == 200:
            workflows = response.json()
            
            if not workflows:
                print("   No workflows found in database.")
                print()
                print("💡 Create a workflow in the UI to test user isolation!")
                return
            
            # Count by author_id
            by_author = {}
            for wf in workflows:
                author_id = wf.get('author_id')
                if author_id:
                    by_author[author_id] = by_author.get(author_id, 0) + 1
            
            if by_author:
                for author_id, count in by_author.items():
                    print(f"   User ID {author_id}: {count} workflow(s)")
            else:
                print("   Workflows exist but have no author_id assigned")
            
            print()
            print(f"   Total: {len(workflows)} workflow(s)")
            
        else:
            print(f"   Could not fetch workflows: {response.status_code}")
    
    except Exception as e:
        print(f"   Error fetching workflows: {e}")


if __name__ == "__main__":
    users = check_current_user()
    
    if users:
        check_workflow_count()
        
        print()
        print("=" * 70)
        print("Next Steps for Testing SSO")
        print("=" * 70)
        print()
        print("1. Create some workflows as current user (ID={})".format(users[0]['id']))
        print("2. Generate a JWT token for a DIFFERENT user (e.g., user ID=2)")
        print("3. Access SSO endpoint with that token:")
        print("   GET http://localhost:5000/api/v1/sso/?token=<JWT_TOKEN>")
        print("4. Verify the new user sees NO workflows (isolation working!)")
        print()

