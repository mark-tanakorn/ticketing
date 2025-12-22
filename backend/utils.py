import psycopg2
import httpx
import os
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# PostgreSQL connection
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_DATABASE", "ticketing_db"),
        user=os.getenv("DB_USER", "ticketing_user"),
        password=os.getenv("DB_PASSWORD", "mysecretpassword"),
        port=int(os.getenv("DB_PORT", 5432)),
    )


# TAV triggers
TAV_BASE_URL = os.getenv("TAV_BASE_URL", "http://localhost:5001")


# Trigger contact approver workflow
async def trigger_contact_approver_workflow(ticket_payload: dict) -> None:
    CONTACT_APPROVER_WORKFLOW_EMAIL = os.getenv(
        "CONTACT_APPROVER_WORKFLOW_EMAIL", "31220e0d-1a92-40ae-8cbc-400f3ec1b469"
    )
    url = f"{TAV_BASE_URL}/api/v1/workflows/{CONTACT_APPROVER_WORKFLOW_EMAIL}/execute"
    body = {"trigger_data": ticket_payload}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()


# Trigger contact fixer workflow
async def trigger_contact_fixer_workflow(ticket_payload: dict) -> None:
    CONTACT_FIXER_WORKFLOW_EMAIL = os.getenv(
        "CONTACT_FIXER_WORKFLOW_EMAIL", "69e99f3d-d527-49ff-9210-e1759696cda2"
    )
    url = f"{TAV_BASE_URL}/api/v1/workflows/{CONTACT_FIXER_WORKFLOW_EMAIL}/execute"
    body = {"trigger_data": ticket_payload}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()


# Trigger SLA breached workflow
async def trigger_sla_breached_workflow(ticket_payload: dict) -> None:
    SLA_BREACH_WORKFLOW_EMAIL = os.getenv(
        "SLA_BREACH_WORKFLOW_EMAIL", "004d3aaf-0914-4535-bc56-bd5fabc31dd5"
    )
    url = f"{TAV_BASE_URL}/api/v1/workflows/{SLA_BREACH_WORKFLOW_EMAIL}/execute"
    body = {"trigger_data": ticket_payload}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()


# Trigger SLA pre-breach workflow
async def trigger_sla_prebreached_workflow(ticket_payload: dict) -> None:
    SLA_PREBREACH_WORKFLOW_EMAIL = os.getenv(
        "SLA_PREBREACH_WORKFLOW_EMAIL", "1d25d573-3569-496f-91c5-0ad1d756026e"
    )
    url = f"{TAV_BASE_URL}/api/v1/workflows/{SLA_PREBREACH_WORKFLOW_EMAIL}/execute"
    body = {"trigger_data": ticket_payload}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()


# SLA hours dictionary - configurable via environment variables
SLA_HOURS_DICT = {
    "low": float(os.getenv("SLA_LOW_HOURS", 72)),
    "medium": float(os.getenv("SLA_MEDIUM_HOURS", 48)),
    "high": float(os.getenv("SLA_HIGH_HOURS", 24)),
    "critical": float(os.getenv("SLA_CRITICAL_HOURS", 4)),
}
# Pre-breach warning time (seconds before breach) - configurable via environment variables
PRE_BREACH_SECONDS = int(os.getenv("PRE_BREACH_SECONDS", 7200))


# Pydantic models for update_ticket_approval
class TicketApprovalPayload(BaseModel):
    approved: bool
    reply_text: str | None = None
    execution_id: str | None = None


# Pydantic models for update_ticket_status
class TicketStatusPayload(BaseModel):
    status: str | None = None
    fixer: str | None = None


# Database initialization
def init_database_tables():
    """Initialize database tables if they don't exist."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create tickets table only if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                category VARCHAR(50),
                severity VARCHAR(50),
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'open',
                attachment_upload TEXT,
                approver VARCHAR(255),
                fixer VARCHAR(255),
                approver_decision BOOLEAN,
                approver_reply_text TEXT,
                approver_decided_at TIMESTAMP,
                tav_execution_id TEXT,
                sla_start_time TIMESTAMP,
                pre_breach_triggered BOOLEAN DEFAULT FALSE,
                breach_triggered BOOLEAN DEFAULT FALSE
            );
        """
        )

        # Create users table only if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                email VARCHAR(255) UNIQUE NOT NULL,
                department VARCHAR(100),
                approval_tier INTEGER
            );
        """
        )

        # Create fixers table only if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fixers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                phone VARCHAR(50),
                department VARCHAR(255)
            );
        """
        )

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"DB setup error: {e}")
