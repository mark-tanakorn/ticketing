"""
Database connection utilities.
Separated from utils.py to avoid circular imports.
"""

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_db_connection():
    """Get a PostgreSQL database connection."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_DATABASE", "ticketing_db"),
        user=os.getenv("DB_USER", "ticketing_user"),
        password=os.getenv("DB_PASSWORD", "mysecretpassword"),
        port=int(os.getenv("DB_PORT", 5432)),
    )
