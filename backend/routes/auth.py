from fastapi import APIRouter, HTTPException, Depends, Response, Cookie
from pydantic import BaseModel
from typing import Optional
from auth_utils import (
    hash_password,
    get_user_by_credentials,
    create_session_token,
    verify_session_token,
    get_user_by_id
)
from database import get_db_connection

router = APIRouter()

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    role: str

# Dependency to get current user from session
def get_current_user(session_token: Optional[str] = Cookie(None)) -> dict:
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_session_token(session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

@router.post("/login", response_model=UserResponse)
def login(request: LoginRequest, response: Response):
    """Login with username/email and password."""
    user = get_user_by_credentials(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create session token
    session_token = create_session_token(user["user_id"])

    # Set session cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=86400,  # 24 hours
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )

    return UserResponse(**user)

@router.post("/register", response_model=UserResponse)
def register(request: RegisterRequest):
    """Register a new user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if username or email already exists
        cursor.execute("SELECT user_id FROM login WHERE username = %s OR email = %s",
                      (request.username, request.email))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username or email already exists")

        # Hash password
        hashed_password = hash_password(request.password)

        # Insert new user
        cursor.execute(
            "INSERT INTO login (username, email, password) VALUES (%s, %s, %s) RETURNING user_id",
            (request.username, request.email, hashed_password)
        )
        user_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()

        return UserResponse(
            user_id=user_id,
            username=request.username,
            email=request.email,
            role="user"
        )

    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/logout")
def logout(response: Response):
    """Logout by clearing the session cookie."""
    response.delete_cookie(key="session_token")
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(**current_user)