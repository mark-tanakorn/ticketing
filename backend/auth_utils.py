from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
import os
from database import get_db_connection
from typing import Optional

# Password hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Session signing
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")
serializer = URLSafeTimedSerializer(SECRET_KEY)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_session_token(user_id: int) -> str:
    """Create a signed session token containing the user_id."""
    return serializer.dumps({"user_id": user_id})


def verify_session_token(token: str) -> Optional[int]:
    """Verify a session token and return the user_id if valid."""
    try:
        data = serializer.loads(token, max_age=86400)  # 24 hours
        return data["user_id"]
    except:
        return None


def get_user_by_credentials(username_or_email: str, password: str) -> Optional[dict]:
    """Get user from login table by username/email and password."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if input is email or username
        if "@" in username_or_email:
            query = "SELECT user_id, username, email, password, role FROM login WHERE email = %s"
        else:
            query = "SELECT user_id, username, email, password, role FROM login WHERE username = %s"

        cursor.execute(query, (username_or_email,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and verify_password(password, user[3]):  # user[3] is password
            return {
                "user_id": user[0],
                "username": user[1],
                "email": user[2],
                "role": user[4],
            }
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user info by user_id."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id, username, email, role FROM login WHERE user_id = %s",
            (user_id,),
        )
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            return {
                "user_id": user[0],
                "username": user[1],
                "email": user[2],
                "role": user[3],
            }
        return None
    except Exception as e:
        print(f"Error getting user by id: {e}")
        return None
