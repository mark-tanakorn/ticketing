from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import random
from datetime import datetime, timedelta
import httpx
import os

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],  # Allow Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PostgreSQL connection
def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="ticketing_db",
        user="ticketing_user",
        password="mysecretpassword",
        port=5432
    )

# Create tables if they don't exist (don't drop existing data)
@app.on_event("startup")
async def startup_event():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create tickets table only if it doesn't exist
        cursor.execute("""
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
                fixer VARCHAR(255)
            );
        """)

        # Add approval tracking columns (safe for existing DBs)
        cursor.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS approver_decision BOOLEAN;")
        cursor.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS approver_reply_text TEXT;")
        cursor.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS approver_decided_at TIMESTAMP;")
        cursor.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS tav_execution_id TEXT;")

        # Add SLA tracking columns (safe for existing DBs)
        cursor.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS sla_reminder_sent_at TIMESTAMP;")
        cursor.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS sla_breached_at TIMESTAMP;")
        cursor.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS sla_started_at TIMESTAMP;")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database tables checked/created successfully")
    except Exception as e:
        print(f"DB setup error: {e}")

# Create fixers table if it doesn't exist
@app.on_event("startup")
async def create_fixers_table():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fixers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                phone VARCHAR(50),
                department VARCHAR(255)
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("Fixers table checked/created successfully")
    except Exception as e:
        print(f"DB setup error for fixers table: {e}")

# Basic route
@app.get("/")
async def root():
    return {"message": "Backend is running!"}

@app.get("/users/{department}")
async def get_users_by_department(department: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, name, department, approval_tier 
            FROM users 
            WHERE department = %s 
            ORDER BY approval_tier
        """, (department,))
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"users": users}
    except Exception as e:
        return {"error": str(e)}

@app.get("/users")
async def get_all_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, name, phone, email, department, approval_tier FROM users ORDER BY id")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"users": users}
    except Exception as e:
        return {"error": str(e)}

@app.post("/users")
async def create_user(user: dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if name already exists
        cursor.execute("SELECT id FROM users WHERE LOWER(name) = LOWER(%s)", (user.get('name'),))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "User name already exists"}

        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(%s)", (user.get('email'),))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "User email already exists"}

        # Check if phone already exists
        cursor.execute("SELECT id FROM users WHERE phone = %s", (user.get('phone'),))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "User phone already exists"}

        # Get the next sequential ID (not auto-increment)
        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM users")
        next_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO users (id, name, phone, email, department, approval_tier)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (next_id, user.get('name'), user.get('phone'), user.get('email'), user.get('department'), user.get('approval_tier')))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "User created successfully"}
    except Exception as e:
        return {"error": str(e)}

@app.put("/users/{user_id}")
async def update_user(user_id: int, user: dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if name already exists for another user
        cursor.execute("SELECT id FROM users WHERE LOWER(name) = LOWER(%s) AND id != %s", (user.get('name'), user_id))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "User name already exists"}

        # Check if email already exists for another user
        cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(%s) AND id != %s", (user.get('email'), user_id))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "User email already exists"}

        # Check if phone already exists for another user
        cursor.execute("SELECT id FROM users WHERE phone = %s AND id != %s", (user.get('phone'), user_id))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "User phone already exists"}

        cursor.execute("""
            UPDATE users 
            SET name = %s, phone = %s, email = %s, department = %s, approval_tier = %s
            WHERE id = %s
        """, (user.get('name'), user.get('phone'), user.get('email'), user.get('department'), user.get('approval_tier'), user_id))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "User updated successfully"}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "User deleted successfully"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/tickets")
async def get_tickets():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM tickets ORDER BY date_created DESC")
        tickets = cursor.fetchall()
        cursor.close()
        conn.close()

        # Check and update SLA breaches (and trigger SLA breach workflow on first transition)
        for ticket in tickets:
            # 1 hour before breach reminder
            await _handle_sla_reminder_for_ticket_if_needed(ticket)
            transitioned = await _handle_sla_breach_for_ticket_if_needed(ticket)
            if transitioned:
                ticket["status"] = "sla_breached"  # Update in memory
        
        return {"tickets": tickets}
    except Exception as e:
        return {"error": str(e)}

# Add TAV constants and helper function
# For local dev, TAV typically runs at http://localhost:5000
# Override via env vars if you're targeting a remote TAV instance.
TAV_BASE_URL = os.getenv("TAV_BASE_URL", "http://localhost:5000")
TAV_WORKFLOW_ID = os.getenv("TAV_WORKFLOW_ID", "de51f0d2-31fb-448a-acfd-409586920ad8")
# SLA workflows
# - Reminder workflow default: b632cbb0-5543-408d-a086-4f0dcae48fc5
# - Breach indicator workflow default: d01e23c4-82de-45a8-afad-5d30c30ca4ec
# Backward compat: if older env var TAV_SLA_WORKFLOW_ID is set, it will be used as the reminder workflow.
TAV_SLA_REMINDER_WORKFLOW_ID = os.getenv(
    "TAV_SLA_REMINDER_WORKFLOW_ID",
    os.getenv("TAV_SLA_WORKFLOW_ID", "b632cbb0-5543-408d-a086-4f0dcae48fc5"),
)
TAV_SLA_BREACH_WORKFLOW_ID = os.getenv(
    "TAV_SLA_BREACH_WORKFLOW_ID",
    "d01e23c4-82de-45a8-afad-5d30c30ca4ec",
)

async def trigger_tav_workflow(ticket_payload: dict) -> None:
    url = f"{TAV_BASE_URL}/api/v1/workflows/{TAV_WORKFLOW_ID}/execute"
    body = {"trigger_data": ticket_payload}

    async with httpx.AsyncClient(timeout=10) as client:
        # If TAV dev-mode is enabled, no Authorization header is needed.
        r = await client.post(url, json=body)
        r.raise_for_status()

async def trigger_tav_sla_reminder_workflow(ticket_payload: dict) -> None:
    """
    Trigger the SLA reminder workflow in TAV (separate workflow ID from ticket creation).
    """
    url = f"{TAV_BASE_URL}/api/v1/workflows/{TAV_SLA_REMINDER_WORKFLOW_ID}/execute"
    body = {"trigger_data": ticket_payload}

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()

async def trigger_tav_sla_breach_indicator_workflow(ticket_payload: dict) -> None:
    """
    Trigger the SLA breach indicator workflow in TAV.
    """
    url = f"{TAV_BASE_URL}/api/v1/workflows/{TAV_SLA_BREACH_WORKFLOW_ID}/execute"
    body = {"trigger_data": ticket_payload}

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()


def is_sla_breached(date_created, severity: str) -> bool:
    """
    Returns True if current time is past SLA breach time.
    IMPORTANT: Uses get_sla_breach_time() so reminder + breach logic stay consistent
    (including our CRITICAL test override).
    """
    breach_time = get_sla_breach_time(date_created, severity)
    current_time = datetime.utcnow() + timedelta(hours=8)  # Singapore timezone
    return current_time > breach_time


def get_sla_breach_time(start_time, severity: str):
    """
    Compute SLA breach time.
    """
    sev = (severity or "").lower()

    sla_hours = {
        "low": 72,
        "medium": 48,
        "high": 24,
        "critical": 4,
    }
    hours = sla_hours.get(sev, 72)
    return start_time + timedelta(hours=hours)


async def _handle_sla_reminder_for_ticket_if_needed(ticket: dict) -> bool:
    """
    If ticket is within 1 hour of SLA breach (but not yet breached), trigger TAV reminder once.
    Returns True if it triggered during this call.
    """
    try:
        if ticket.get("status") == "sla_breached":
            return False

        # If reminder already sent, do nothing.
        if ticket.get("sla_reminder_sent_at"):
            return False

        # SLA should start counting once the ticket is in progress (sla_started_at).
        # Fallback to date_created for older rows.
        date_created = ticket.get("date_created")
        sla_started_at = ticket.get("sla_started_at") or date_created
        severity = ticket.get("severity")
        if not sla_started_at:
            return False

        now = datetime.utcnow() + timedelta(hours=8)  # Singapore timezone
        breach_time = get_sla_breach_time(sla_started_at, severity)
        seconds_left = (breach_time - now).total_seconds()

        # Trigger window: 1 hour before breach (3600s)
        reminder_window_seconds = 3600

        # Trigger only when breach is in the future and within the window.
        if seconds_left <= 0 or seconds_left > reminder_window_seconds:
            return False

        reminder_sent_at = now

        # Atomically mark reminder as sent to avoid duplicates.
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE tickets
            SET sla_reminder_sent_at = %s
            WHERE id = %s
              AND status != 'sla_breached'
              AND sla_reminder_sent_at IS NULL
            """,
            (reminder_sent_at, ticket.get("id")),
        )
        updated = cursor.rowcount
        conn.commit()

        if updated == 0:
            cursor.close()
            conn.close()
            return False

        # Enrich payload similarly to create_ticket
        approver_name = ticket.get("approver")
        fixer_name = ticket.get("fixer")

        approver_phone = None
        if approver_name:
            cursor.execute("SELECT phone FROM users WHERE name = %s LIMIT 1", (approver_name,))
            r = cursor.fetchone()
            if r:
                approver_phone = r[0]

        fixer_phone = None
        if fixer_name:
            cursor.execute("SELECT phone FROM fixers WHERE name = %s LIMIT 1", (fixer_name,))
            r = cursor.fetchone()
            if r:
                fixer_phone = r[0]

        cursor.close()
        conn.close()

        dc = ticket.get("date_created")
        date_created_iso = dc.isoformat() if hasattr(dc, "isoformat") else str(dc)

        payload = {
            "event": "sla_reminder",
            "reminder_sent_at": reminder_sent_at.isoformat(),
            "breach_time": breach_time.isoformat() if hasattr(breach_time, "isoformat") else str(breach_time),
            "seconds_left": int(seconds_left),
            "ticket_id": ticket.get("id"),
            "title": ticket.get("title"),
            "description": ticket.get("description"),
            "severity": ticket.get("severity"),
            "date_created": date_created_iso,
            "sla_started_at": (
                sla_started_at.isoformat() if hasattr(sla_started_at, "isoformat") else str(sla_started_at)
            ),
            "approver": approver_name,
            "approver_phone": approver_phone,
            "fixer": fixer_name,
            "fixer_phone": fixer_phone,
            "status": ticket.get("status"),
        }

        await trigger_tav_sla_reminder_workflow(payload)
        return True
    except Exception:
        # Don't block /tickets if the workflow call fails; marking reminder sent prevents spam.
        return True


async def _handle_sla_breach_for_ticket_if_needed(ticket: dict) -> bool:
    """
    If ticket just breached SLA, atomically flip status to 'sla_breached' and trigger TAV workflow.
    Returns True if it transitioned to 'sla_breached' during this call.
    """
    try:
        if ticket.get("status") == "sla_breached":
            return False

        date_created = ticket.get("date_created")
        sla_started_at = ticket.get("sla_started_at") or date_created
        severity = ticket.get("severity")
        if not sla_started_at or not is_sla_breached(sla_started_at, severity):
            return False

        breached_at = datetime.utcnow() + timedelta(hours=8)  # Singapore timezone

        # Atomically transition to sla_breached to avoid duplicate workflow triggers.
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE tickets
            SET status = 'sla_breached',
                sla_breached_at = %s
            WHERE id = %s
              AND status != 'sla_breached'
            """,
            (breached_at, ticket.get("id")),
        )
        updated = cursor.rowcount
        conn.commit()

        if updated == 0:
            cursor.close()
            conn.close()
            return False

        # Enrich payload similarly to create_ticket
        approver_name = ticket.get("approver")
        fixer_name = ticket.get("fixer")

        approver_phone = None
        if approver_name:
            cursor.execute("SELECT phone FROM users WHERE name = %s LIMIT 1", (approver_name,))
            r = cursor.fetchone()
            if r:
                approver_phone = r[0]

        fixer_phone = None
        if fixer_name:
            cursor.execute("SELECT phone FROM fixers WHERE name = %s LIMIT 1", (fixer_name,))
            r = cursor.fetchone()
            if r:
                fixer_phone = r[0]

        cursor.close()
        conn.close()

        dc = ticket.get("date_created")
        date_created_iso = dc.isoformat() if hasattr(dc, "isoformat") else str(dc)
        breach_time = get_sla_breach_time(sla_started_at, severity)

        payload = {
            "event": "sla_breached",
            "breached_at": breached_at.isoformat(),
            "breach_time": breach_time.isoformat() if hasattr(breach_time, "isoformat") else str(breach_time),
            "ticket_id": ticket.get("id"),
            "title": ticket.get("title"),
            "description": ticket.get("description"),
            "severity": ticket.get("severity"),
            "date_created": date_created_iso,
            "sla_started_at": (
                sla_started_at.isoformat() if hasattr(sla_started_at, "isoformat") else str(sla_started_at)
            ),
            "approver": approver_name,
            "approver_phone": approver_phone,
            "fixer": fixer_name,
            "fixer_phone": fixer_phone,
            "status": "sla_breached",
        }

        await trigger_tav_sla_breach_indicator_workflow(payload)
        return True
    except Exception:
        # Don't block /tickets if the workflow call fails; status flip is already persisted.
        return True


class TicketApprovalPayload(BaseModel):
    approved: bool
    reply_text: str | None = None
    execution_id: str | None = None


@app.post("/tickets/{ticket_id}/approval")
async def update_ticket_approval(ticket_id: int, payload: TicketApprovalPayload):
    """
    Callback endpoint for TAV to report approver decision (yes/no + optional message).

    Expected body:
      { "approved": true|false, "reply_text": "...", "execution_id": "..." }
    """
    try:
        # If approved, move ticket back to the normal "open" flow (not a terminal "approved" state)
        new_status = "open" if payload.approved else "approval_denied"
        decided_at = datetime.utcnow() + timedelta(hours=8)  # Singapore timezone

        # If approval is denied, we require a remark / reason.
        if not payload.approved and (payload.reply_text is None or payload.reply_text.strip() == ""):
            raise HTTPException(
                status_code=400,
                detail="reply_text is required when approved=false",
            )

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE tickets
            SET status = %s,
                approver_decision = %s,
                approver_reply_text = %s,
                approver_decided_at = %s,
                tav_execution_id = %s
            WHERE id = %s
            """,
            (
                new_status,
                payload.approved,
                payload.reply_text,
                decided_at,
                payload.execution_id,
                ticket_id,
            ),
        )
        updated = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()

        if updated == 0:
            return {"error": f"Ticket {ticket_id} not found"}

        return {
            "message": "Approval decision recorded",
            "ticket_id": ticket_id,
            "status": new_status,
            "approved": payload.approved,
            "reply_text": payload.reply_text,
            "execution_id": payload.execution_id,
        }
    except Exception as e:
        return {"error": str(e)}


class TicketStatusPayload(BaseModel):
    status: str | None = None
    fixer: str | None = None


@app.post("/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: int, payload: TicketStatusPayload | None = None):
    """
    Update ticket status (separate from approval callback).

    Expected body:
      { "status": "in_progress", "fixer": "Nick" }
    """
    try:
        allowed_statuses = {
            "open",
            "in_progress",
            "closed",
            "awaiting_approval",
            "approval_denied",
            "sla_breached",
        }
        # If caller sends no body (common from some workflow tools), default to in_progress.
        requested_status = payload.status if payload else None
        new_status = (requested_status or "in_progress").strip().lower()
        if new_status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{requested_status}'. Allowed: {sorted(allowed_statuses)}",
            )

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Ensure ticket exists and check current status for basic transition safety
        cursor.execute("SELECT id, status, fixer FROM tickets WHERE id = %s", (ticket_id,))
        existing = cursor.fetchone()
        if not existing:
            cursor.close()
            conn.close()
            return {"error": f"Ticket {ticket_id} not found"}

        # Do not allow moving a denied ticket into progress without re-opening
        if existing.get("status") == "approval_denied" and new_status == "in_progress":
            cursor.close()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail="Cannot move a denied ticket to in_progress. Re-open it first.",
            )

        # If marking in progress, ensure there's a fixer assigned (either existing or provided)
        requested_fixer = payload.fixer if payload else None
        fixer_to_set = requested_fixer if requested_fixer is not None else existing.get("fixer")
        if new_status == "in_progress" and (fixer_to_set is None or str(fixer_to_set).strip() == ""):
            cursor.close()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail="fixer is required to set status=in_progress",
            )

        # If moving into progress from a different state, start SLA timer now.
        now = datetime.utcnow() + timedelta(hours=8)  # Singapore timezone
        should_start_sla = existing.get("status") != "in_progress" and new_status == "in_progress"

        cursor = conn.cursor()
        if should_start_sla:
            cursor.execute(
                """
                UPDATE tickets
                SET status = %s,
                    fixer = COALESCE(%s, fixer),
                    sla_started_at = %s,
                    sla_reminder_sent_at = NULL,
                    sla_breached_at = NULL
                WHERE id = %s
                """,
                (new_status, requested_fixer, now, ticket_id),
            )
        else:
            cursor.execute(
                """
                UPDATE tickets
                SET status = %s,
                    fixer = COALESCE(%s, fixer)
                WHERE id = %s
                """,
                (new_status, requested_fixer, ticket_id),
            )
        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Ticket status updated", "ticket_id": ticket_id, "status": new_status, "fixer": requested_fixer}
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e)}

@app.post("/tickets")
async def create_ticket(ticket: dict):
    try:
        # Generate random ID
        ticket_id = random.randint(100000, 999999)
        
        # Get current time in Singapore timezone (UTC+8)
        current_time = datetime.utcnow() + timedelta(hours=8)
        
        # Find approver based on department and approval_tier
        approver_name = None
        department = ticket.get('department')
        approval_tier = ticket.get('approval_tier')
        
        if department and approval_tier:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM users 
                WHERE department = %s AND approval_tier = %s
                LIMIT 1
            """, (department, approval_tier))
            result = cursor.fetchone()
            if result:
                approver_name = result[0]
            cursor.close()
            conn.close()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tickets (id, title, description, category, severity, status, attachment_upload, date_created, approver, fixer)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (ticket_id, ticket.get('title'), ticket.get('description'), ticket.get('category'), ticket.get('severity'), 'awaiting_approval', ticket.get('attachment_upload'), current_time, approver_name, ticket.get('assigned_to')))
        conn.commit()
        cursor.close()
        conn.close()

        # Fetch approver phone number from users table
        approver_phone = None
        if approver_name:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT phone FROM users WHERE name = %s LIMIT 1
            """, (approver_name,))
            result = cursor.fetchone()
            if result:
                approver_phone = result[0]
            cursor.close()
            conn.close()

        # Fetch fixer phone number from fixers table
        fixer_phone = None
        if ticket.get('assigned_to'):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT phone FROM fixers WHERE name = %s LIMIT 1
            """, (ticket.get('assigned_to'),))
            result = cursor.fetchone()
            if result:
                fixer_phone = result[0]
            cursor.close()
            conn.close()

        # Craft the payload for TAV workflow
        ticket_payload = {
            "ticket_id": ticket_id,
            "title": ticket.get("title"),
            "description": ticket.get("description"),
            "severity": ticket.get("severity"),
            "date_created": current_time.isoformat(),
            "approver": approver_name,
            "approver_phone": approver_phone,
            'fixer': ticket.get('assigned_to'),
            'fixer_phone': fixer_phone
        }

        # Trigger TAV workflow
        await trigger_tav_workflow(ticket_payload)

        return {"message": "Ticket created successfully"}
    except Exception as e:
        return {"error": str(e)}

@app.put("/tickets/{ticket_id}")
async def update_ticket(ticket_id: int, ticket: dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tickets 
            SET title = %s, description = %s, category = %s, severity = %s, status = %s, attachment_upload = %s, approver = %s, fixer = %s
            WHERE id = %s
        """, (ticket.get('title'), ticket.get('description'), ticket.get('category'), ticket.get('severity'), ticket.get('status'), ticket.get('attachment_upload'), ticket.get('approver'), ticket.get('fixer'), ticket_id))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Ticket updated successfully"}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/tickets/{ticket_id}")
async def delete_ticket(ticket_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Ticket deleted successfully"}
    except Exception as e:
        return {"error": str(e)}

# Get all fixers
@app.get("/fixers")
async def get_all_fixers():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, name, email, phone, department FROM fixers ORDER BY id")
        fixers = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"fixers": fixers}
    except Exception as e:
        return {"error": str(e)}

# Create a new fixer
@app.post("/fixers")
async def create_fixer(fixer: dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if name already exists
        cursor.execute("SELECT id FROM fixers WHERE LOWER(name) = LOWER(%s)", (fixer.get('name'),))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "Fixer name already exists"}

        # Check if email already exists
        cursor.execute("SELECT id FROM fixers WHERE LOWER(email) = LOWER(%s)", (fixer.get('email'),))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "Fixer email already exists"}

        # Check if phone already exists
        cursor.execute("SELECT id FROM fixers WHERE phone = %s", (fixer.get('phone'),))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "Fixer phone already exists"}

        # Get the next sequential ID (not auto-increment)
        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM fixers")
        next_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO fixers (id, name, email, phone, department)
            VALUES (%s, %s, %s, %s, %s)
        """, (next_id, fixer.get('name'), fixer.get('email'), fixer.get('phone'), fixer.get('department')))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Fixer created successfully"}
    except Exception as e:
        return {"error": str(e)}

# Update a fixer
@app.put("/fixers/{fixer_id}")
async def update_fixer(fixer_id: int, fixer: dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if name already exists for another fixer
        cursor.execute("SELECT id FROM fixers WHERE LOWER(name) = LOWER(%s) AND id != %s", (fixer.get('name'), fixer_id))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "Fixer name already exists"}

        # Check if email already exists for another fixer
        cursor.execute("SELECT id FROM fixers WHERE LOWER(email) = LOWER(%s) AND id != %s", (fixer.get('email'), fixer_id))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "Fixer email already exists"}

        # Check if phone already exists for another fixer
        cursor.execute("SELECT id FROM fixers WHERE phone = %s AND id != %s", (fixer.get('phone'), fixer_id))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "Fixer phone already exists"}

        cursor.execute("""
            UPDATE fixers 
            SET name = %s, email = %s, phone = %s, department = %s
            WHERE id = %s
        """, (fixer.get('name'), fixer.get('email'), fixer.get('phone'), fixer.get('department'), fixer_id))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Fixer updated successfully"}
    except Exception as e:
        return {"error": str(e)}

# Delete a fixer
@app.delete("/fixers/{fixer_id}")
async def delete_fixer(fixer_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fixers WHERE id = %s", (fixer_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Fixer deleted successfully"}
    except Exception as e:
        return {"error": str(e)}
