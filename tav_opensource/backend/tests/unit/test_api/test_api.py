#!/usr/bin/env python3
"""
Test the workflows API endpoint directly.
"""

import sys
import os
import requests
import json

def test_api():
    """Test the workflows API endpoint."""
    
    try:
        print("🌐 Testing API endpoint...")
        
        # Test the API endpoint
        url = "http://localhost:5000/api/v1/workflows"
        print(f"📡 Making request to: {url}")
        
        response = requests.get(url, timeout=10)
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📄 Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Response successful!")
            print(f"📋 Number of workflows returned: {len(data)}")
            
            if len(data) > 0:
                print("\n📝 First workflow:")
                print(json.dumps(data[0], indent=2, default=str))
            else:
                print("❌ API returned empty list!")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"💬 Error message: {response.text}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is your FastAPI server running on port 5000?")
    except Exception as e:
        print(f"❌ Error testing API: {e}")

if __name__ == "__main__":
    test_api()