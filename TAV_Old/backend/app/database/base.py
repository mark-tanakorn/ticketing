"""Database base."""

from sqlalchemy.orm import declarative_base
from app.utils.timezone import get_local_now

Base = declarative_base()


def get_current_timestamp():
    """Get current timestamp in local timezone for database defaults."""
    return get_local_now()