#!/usr/bin/env python3
"""
Quick test script for JwtTokenManager
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.jwt_manager import JwtTokenManager
from jose import jwt

def test_jwt_manager():
    # print("Testing JwtTokenManager...")

    # Test generate token
    username = "testuser"
    user_id = 123
    department = "IT"
    role = "Admin"

    token = JwtTokenManager.generate_token(username, user_id, department, role)
    print(f"")
    print(token) # Full token for copy-paste

    # Check config
    secret = JwtTokenManager._get_secret_key()
    issuer = JwtTokenManager._get_issuer()
    audience = JwtTokenManager._get_audience()
    # print(f"Config - Secret: {secret[:10]}..., Issuer: {issuer}, Audience: {audience}")

    # Manual decode with audience
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], audience=audience)
        # print(f"Manual decode with audience successful: {payload}")
    except Exception as e:
        print(f"Manual decode with audience failed: {e}")
        return False

    # Test validate token
    claims = JwtTokenManager.validate_token(token)
    if not claims:
        print("Token validation failed!")
        return False
    # if claims:
    #     print("Token validated successfully!")
    #     print(f"Claims: {claims}")
    # else:
    #     print("Token validation failed!")
    #     return False

    # Test extract user ID
    extracted_user_id = JwtTokenManager.get_user_id_from_token(token)
    if extracted_user_id != user_id:
        print(f"User ID extraction failed: got {extracted_user_id}, expected {user_id}")
        return False
    # if extracted_user_id == user_id:
    #     print(f"User ID extracted correctly: {extracted_user_id}")
    # else:
    #     print(f"User ID extraction failed: got {extracted_user_id}, expected {user_id}")
    #     return False

    # Test extract username
    extracted_username = JwtTokenManager.get_username_from_token(token)
    if extracted_username != username:
        print(f"Username extraction failed: got {extracted_username}, expected {username}")
        return False
    # if extracted_username == username:
    #     print(f"Username extracted correctly: {extracted_username}")
    # else:
    #     print(f"Username extraction failed: got {extracted_username}, expected {username}")
    #     return False

    # Test invalid token
    invalid_claims = JwtTokenManager.validate_token("invalid.token.here")
    if invalid_claims is not None:
        print("Invalid token was incorrectly accepted!")
        return False
    # if invalid_claims is None:
    #     print("Invalid token correctly rejected!")
    # else:
    #     print("Invalid token was incorrectly accepted!")
    #     return False

    # print("All tests passed!")
    return True

if __name__ == "__main__":
    success = test_jwt_manager()
    sys.exit(0 if success else 1)