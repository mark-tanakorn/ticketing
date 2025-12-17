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
        cursor.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS sla_start_time TIMESTAMP;")
        cursor.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS pre_breach_triggered BOOLEAN DEFAULT FALSE;")
        
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
        
        # Check and update SLA breaches and pre-breaches
        sla_hours_dict = {
            'low': 72,
            'medium': 48,
            'high': 24,
            'critical': 1/60  # 1 minute for testing
        }
        for ticket in tickets:
            if ticket.get('sla_start_time'):
                # Fetch phones
                approver_phone = None
                if ticket['approver']:
                    conn_temp = get_db_connection()
                    cursor_temp = conn_temp.cursor()
                    cursor_temp.execute("SELECT phone FROM users WHERE name = %s LIMIT 1", (ticket['approver'],))
                    result = cursor_temp.fetchone()
                    if result:
                        approver_phone = result[0]
                    cursor_temp.close()
                    conn_temp.close()
                
                fixer_phone = None
                if ticket['fixer']:
                    conn_temp = get_db_connection()
                    cursor_temp = conn_temp.cursor()
                    cursor_temp.execute("SELECT phone FROM fixers WHERE name = %s LIMIT 1", (ticket['fixer'],))
                    result = cursor_temp.fetchone()
                    if result:
                        fixer_phone = result[0]
                    cursor_temp.close()
                    conn_temp.close()
                
                sla_hours_value = sla_hours_dict.get(ticket['severity'].lower(), 72)
                breach_time = ticket['sla_start_time'] + timedelta(hours=sla_hours_value)
                current_time = datetime.utcnow() + timedelta(hours=8)
                
                # Check pre-breach (30 seconds before for testing)
                if not ticket.get('pre_breach_triggered', False) and ticket['status'] not in ['closed', 'sla_breached'] and current_time >= breach_time - timedelta(seconds=30):
                    payload = {
                        "ticket_id": ticket['id'],
                        "title": ticket['title'],
                        "description": ticket['description'],
                        "severity": ticket['severity'].capitalize(),
                        "breach_time": breach_time.strftime("%d/%m/%y %H:%M"),
                        "sla_hours": sla_hours_value,
                        "approver": ticket['approver'],
                        "approver_phone": approver_phone,
                        "fixer": ticket['fixer'],
                        "fixer_phone": fixer_phone,
                        "attachment_upload": ticket['attachment_upload'],
                    }
                    await trigger_tav_workflow_pre_breach(payload)
                    
                    # Update flag
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE tickets SET pre_breach_triggered = TRUE WHERE id = %s", (ticket['id'],))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    ticket['pre_breach_triggered'] = True
                
                # Check breach
                if ticket['status'] not in ['sla_breached', 'closed'] and current_time > breach_time:
                    # Update status
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE tickets SET status = 'sla_breached' WHERE id = %s", (ticket['id'],))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    ticket['status'] = 'sla_breached'
                    
                    # Trigger breach workflow
                    payload = {
                        "ticket_id": ticket['id'],
                        "title": ticket['title'],
                        "description": ticket['description'],
                        "severity": ticket['severity'].capitalize(),
                        "breach_time": breach_time.strftime("%d/%m/%y %H:%M"),
                        "sla_hours": sla_hours_value,
                        "approver": ticket['approver'],
                        "approver_phone": approver_phone,
                        "fixer": ticket['fixer'],
                        "fixer_phone": fixer_phone,
                        "attachment_upload": ticket['attachment_upload'],
                    }
                    await trigger_tav_workflow_sla_breached(payload)
        
        return {"tickets": tickets}
    except Exception as e:
        return {"error": str(e)}

# Add TAV constants and helper function
# For local dev, TAV typically runs at http://localhost:5000
# Override via env vars if you're targeting a remote TAV instance.
TAV_BASE_URL = os.getenv("TAV_BASE_URL", "http://localhost:5001")
TAV_WORKFLOW_ID = os.getenv("TAV_WORKFLOW_ID", "31220e0d-1a92-40ae-8cbc-400f3ec1b469")

async def trigger_tav_workflow(ticket_payload: dict) -> None:
    url = f"{TAV_BASE_URL}/api/v1/workflows/{TAV_WORKFLOW_ID}/execute"
    body = {"trigger_data": ticket_payload}

    async with httpx.AsyncClient(timeout=10) as client:
        # If TAV dev-mode is enabled, no Authorization header is needed.
        r = await client.post(url, json=body)
        r.raise_for_status()


async def trigger_tav_workflow_updated(ticket_payload: dict) -> None:
    # Use the new workflow ID for approved tickets
    updated_workflow_id = "69e99f3d-d527-49ff-9210-e1759696cda2"
    url = f"{TAV_BASE_URL}/api/v1/workflows/{updated_workflow_id}/execute"
    body = {"trigger_data": ticket_payload}

    async with httpx.AsyncClient(timeout=10) as client:
        # If TAV dev-mode is enabled, no Authorization header is needed.
        r = await client.post(url, json=body)
        r.raise_for_status()


async def trigger_tav_workflow_sla_breached(ticket_payload: dict) -> None:
    # Use the workflow ID for SLA breached tickets
    sla_breached_workflow_id = "004d3aaf-0914-4535-bc56-bd5fabc31dd5"
    url = f"{TAV_BASE_URL}/api/v1/workflows/{sla_breached_workflow_id}/execute"
    body = {"trigger_data": ticket_payload}

    print(f"Attempting to trigger SLA breached workflow for ticket {ticket_payload.get('Ticket ID')} at {url}")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # If TAV dev-mode is enabled, no Authorization header is needed.
            r = await client.post(url, json=body)
            r.raise_for_status()
            print(f"SLA breached workflow triggered successfully for ticket {ticket_payload.get('Ticket ID')}")
    except Exception as e:
        print(f"Failed to trigger SLA breached workflow: {e}")

async def trigger_tav_workflow_pre_breach(ticket_payload: dict) -> None:
    # Use the workflow ID for pre-breach notification (30 seconds before for testing)
    pre_breach_workflow_id = "1d25d573-3569-496f-91c5-0ad1d756026e"
    url = f"{TAV_BASE_URL}/api/v1/workflows/{pre_breach_workflow_id}/execute"
    body = {"trigger_data": ticket_payload}

    print(f"Attempting to trigger pre-breach workflow for ticket {ticket_payload.get('ticket_id')} at {url}")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # If TAV dev-mode is enabled, no Authorization header is needed.
            r = await client.post(url, json=body)
            r.raise_for_status()
            print(f"Pre-breach workflow triggered successfully for ticket {ticket_payload.get('ticket_id')}")
    except Exception as e:
        print(f"Failed to trigger pre-breach workflow: {e}")

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
                tav_execution_id = %s,
                sla_start_time = CASE WHEN %s THEN %s ELSE sla_start_time END,
                sla_breached_at = CASE WHEN %s THEN %s + INTERVAL '1 hour' * (CASE WHEN severity = 'critical' THEN 1.0/60 WHEN severity = 'high' THEN 24 WHEN severity = 'medium' THEN 48 ELSE 72 END) ELSE sla_breached_at END
            WHERE id = %s
            """,
            (
                new_status,
                payload.approved,
                payload.reply_text,
                decided_at,
                payload.execution_id,
                payload.approved,  # Only set sla_start_time if approved
                decided_at if payload.approved else None,
                payload.approved,  # Only set sla_breached_at if approved
                decided_at if payload.approved else None,
                ticket_id,
            ),
        )
        updated = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()

        if updated == 0:
            return {"error": f"Ticket {ticket_id} not found"}

        # If approved, trigger the updated workflow with correct SLA timing
        if payload.approved:
            # Fetch the complete ticket details
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
            ticket_data = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if ticket_data:
                # Calculate the correct breach_time based on sla_start_time
                sla_hours = {
                    'low': 72,
                    'medium': 48,
                    'high': 24,
                    'critical': 1/60  # 1 minute for testing
                }
                hours = sla_hours.get(ticket_data['severity'].lower(), 72)
                actual_breach_time = ticket_data['sla_start_time'] + timedelta(hours=hours)
                
                # Fetch approver phone
                approver_phone = None
                if ticket_data['approver']:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT phone FROM users WHERE name = %s LIMIT 1", (ticket_data['approver'],))
                    result = cursor.fetchone()
                    if result:
                        approver_phone = result[0]
                    cursor.close()
                    conn.close()
                
                # Fetch fixer phone
                fixer_phone = None
                if ticket_data['fixer']:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT phone FROM fixers WHERE name = %s LIMIT 1", (ticket_data['fixer'],))
                    result = cursor.fetchone()
                    if result:
                        fixer_phone = result[0]
                    cursor.close()
                    conn.close()
                
                # Create payload for the updated workflow
                updated_payload = {
                    "ticket_id": ticket_id,
                    "title": ticket_data["title"],
                    "description": ticket_data["description"],
                    "severity": ticket_data["severity"].capitalize(),
                    "breach_time": actual_breach_time.strftime("%d/%m/%y %H:%M"),
                    "sla_hours": hours,
                    "approver": ticket_data["approver"],
                    "fixer": ticket_data["fixer"],
                    "fixer_phone": fixer_phone,
                    "attachment_upload": ticket_data["attachment_upload"],
                }
                
                # Trigger the updated workflow
                await trigger_tav_workflow_updated(updated_payload)

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

        # Update
        cursor = conn.cursor()
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
            "severity": ticket.get("severity").capitalize() if ticket.get("severity") else ticket.get("severity"),
            "date_created": current_time.strftime("%d/%m/%y %H:%M"),
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
