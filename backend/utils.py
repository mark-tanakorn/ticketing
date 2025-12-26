import httpx
import os
from pydantic import BaseModel
from dotenv import load_dotenv
from routes.settings import get_setting
from database import get_db_connection

# Load environment variables from .env file
load_dotenv()


# TAV triggers
TAV_BASE_URL = os.getenv("TAV_BASE_URL", "http://localhost:5001")


# Trigger contact approver workflow
async def trigger_contact_approver_workflow(ticket_payload: dict) -> None:
    # Get communication mode from settings (defaults to EMAIL)
    comm_mode = get_setting("COMMUNICATION_MODE", "EMAIL")

    if comm_mode == "WHATSAPP":
        CONTACT_APPROVER_WORKFLOW = os.getenv(
            "CONTACT_APPROVER_WORKFLOW", "79947809-4d2a-48ab-9592-d40be4232193"
        )
        workflow_id = CONTACT_APPROVER_WORKFLOW
    else:  # EMAIL mode (default)
        CONTACT_APPROVER_WORKFLOW_EMAIL = os.getenv(
            "CONTACT_APPROVER_WORKFLOW_EMAIL", "a5f8998d-32d2-4a2f-ae7e-5edffb8ba283"
        )
        workflow_id = CONTACT_APPROVER_WORKFLOW_EMAIL

    url = f"{TAV_BASE_URL}/api/v1/workflows/{workflow_id}/execute"
    body = {"trigger_data": ticket_payload}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()


# Trigger contact fixer workflow
async def trigger_contact_fixer_workflow(ticket_payload: dict) -> None:
    # Get communication mode from settings (defaults to EMAIL)
    comm_mode = get_setting("COMMUNICATION_MODE", "EMAIL")

    if comm_mode == "WHATSAPP":
        CONTACT_FIXER_WORKFLOW = os.getenv(
            "CONTACT_FIXER_WORKFLOW", "eaf126b2-43e5-41e4-9fd0-05edb9116000"
        )
        workflow_id = CONTACT_FIXER_WORKFLOW
    else:  # EMAIL mode (default)
        CONTACT_FIXER_WORKFLOW_EMAIL = os.getenv(
            "CONTACT_FIXER_WORKFLOW_EMAIL", "1e93a7fa-88c3-4f11-91a7-52dbf9a80c65"
        )
        workflow_id = CONTACT_FIXER_WORKFLOW_EMAIL

    url = f"{TAV_BASE_URL}/api/v1/workflows/{workflow_id}/execute"
    body = {"trigger_data": ticket_payload}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()


# Trigger SLA breached workflow
async def trigger_sla_breached_workflow(ticket_payload: dict) -> None:
    # Get communication mode from settings (defaults to EMAIL)
    comm_mode = get_setting("COMMUNICATION_MODE", "EMAIL")

    if comm_mode == "WHATSAPP":
        SLA_BREACH_WORKFLOW = os.getenv(
            "SLA_BREACH_WORKFLOW", "1119013f-1058-410e-bc93-cb9ec03b5832"
        )
        workflow_id = SLA_BREACH_WORKFLOW
    else:  # EMAIL mode (default)
        SLA_BREACH_WORKFLOW_EMAIL = os.getenv(
            "SLA_BREACH_WORKFLOW_EMAIL", "bf26936d-2e10-4aba-b74e-a6b3e52fe491"
        )
        workflow_id = SLA_BREACH_WORKFLOW_EMAIL

    url = f"{TAV_BASE_URL}/api/v1/workflows/{workflow_id}/execute"
    body = {"trigger_data": ticket_payload}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()


# Trigger SLA pre-breach workflow
async def trigger_sla_prebreached_workflow(ticket_payload: dict) -> None:
    # Get communication mode from settings (defaults to EMAIL)
    comm_mode = get_setting("COMMUNICATION_MODE", "EMAIL")

    if comm_mode == "WHATSAPP":
        SLA_PREBREACH_WORKFLOW = os.getenv(
            "SLA_PREBREACH_WORKFLOW", "b3e2eaab-3ae8-4b7e-94d1-199b234586b7"
        )
        workflow_id = SLA_PREBREACH_WORKFLOW
    else:  # EMAIL mode (default)
        SLA_PREBREACH_WORKFLOW_EMAIL = os.getenv(
            "SLA_PREBREACH_WORKFLOW_EMAIL", "b244cbae-02fe-4e90-9241-686e3453c7a2"
        )
        workflow_id = SLA_PREBREACH_WORKFLOW_EMAIL

    url = f"{TAV_BASE_URL}/api/v1/workflows/{workflow_id}/execute"
    body = {"trigger_data": ticket_payload}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()


# SLA hours dictionary - configurable via database settings
SLA_HOURS_DICT = {
    "low": float(get_setting("SLA_LOW_HOURS", 72)),
    "medium": float(get_setting("SLA_MEDIUM_HOURS", 48)),
    "high": float(get_setting("SLA_HIGH_HOURS", 24)),
    "critical": float(get_setting("SLA_CRITICAL_HOURS", 4)),
}
# Pre-breach warning time (seconds before breach) - configurable via database settings
PRE_BREACH_SECONDS = int(get_setting("PRE_BREACH_SECONDS", 7200))


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
                user_id INTEGER REFERENCES login(user_id),
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

        # Create settings table only if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                id SERIAL PRIMARY KEY,
                key VARCHAR(100) UNIQUE NOT NULL,
                value TEXT NOT NULL,
                description TEXT,
                category VARCHAR(50) DEFAULT 'general',
                data_type VARCHAR(20) DEFAULT 'string',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Create login table only if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS login (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'user'
            );
        """
        )

        # Create assets table only if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS assets (
                id SERIAL PRIMARY KEY,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(255) NOT NULL,
                action VARCHAR(100) NOT NULL,
                item VARCHAR(255) NOT NULL,
                serial_number VARCHAR(255),
                target VARCHAR(255),
                checked_out BOOLEAN DEFAULT NULL,
                checked_out_time TIMESTAMP
            );
        """
        )

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"DB setup error: {e}")
