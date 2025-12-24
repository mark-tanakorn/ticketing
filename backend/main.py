from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from utils import init_database_tables
from routes.delete import router as delete_router
from routes.get import router as get_router
from routes.post import router as post_router
from routes.put import router as put_router
from routes.settings import router as settings_router
from routes.auth import router as auth_router
import os


app = FastAPI()

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "your-secret-key-change-this"),
    session_cookie="session_token",
    max_age=86400,  # 24 hours
    same_site="lax",
    https_only=False  # Set to True in production
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Allow both common Next.js ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(delete_router)
app.include_router(get_router)
app.include_router(post_router)
app.include_router(put_router)
app.include_router(settings_router)
app.include_router(auth_router, prefix="/auth", tags=["auth"])


# Create tables if they don't exist
@app.on_event("startup")
async def startup_event():
    init_database_tables()
