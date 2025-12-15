"""Database session."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# Create engine based on database type
# SQLite doesn't support connection pooling parameters
if str(settings.DATABASE_URL).startswith("sqlite"):
    engine = create_engine(
        str(settings.DATABASE_URL),
        connect_args={"check_same_thread": False},  # SQLite specific
        echo=settings.LOG_LEVEL == "DEBUG",
    )
else:
    # PostgreSQL and other databases with connection pooling
    engine = create_engine(
        str(settings.DATABASE_URL),
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,  # Verify connections before using
        echo=settings.LOG_LEVEL == "DEBUG",
    )

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()