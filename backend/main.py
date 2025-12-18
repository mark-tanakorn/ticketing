from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor
import random
from datetime import datetime, timedelta
from utils import (
    get_db_connection,
    SLA_HOURS_DICT,
    trigger_tav_workflow,
    trigger_tav_workflow_updated
)
from routes.delete import router as delete_router
from routes.get import router as get_router


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],  # Allow Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(delete_router)
app.include_router(get_router)

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
                decided_at,
                payload.approved,  # Only set sla_breached_at if approved
                decided_at,
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
                hours = SLA_HOURS_DICT.get(ticket_data['severity'].lower(), 72)
                actual_breach_time = ticket_data['sla_start_time'] + timedelta(hours=hours)
                
                # Fetch approver email
                approver_email = None
                if ticket_data['approver']:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT email FROM users WHERE name = %s LIMIT 1", (ticket_data['approver'],))
                    result = cursor.fetchone()
                    if result:
                        approver_email = result[0]
                    cursor.close()
                    conn.close()
                
                # Fetch fixer email
                fixer_phone = None
                fixer_email = None
                if ticket_data['fixer']:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT phone, email FROM fixers WHERE name = %s LIMIT 1", (ticket_data['fixer'],))
                    result = cursor.fetchone()
                    if result:
                        fixer_phone = result[0]
                        fixer_email = result[1]
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
                    'approver_email': approver_email,
                    "fixer": ticket_data["fixer"],
                    "fixer_phone": fixer_phone,
                    "fixer_email": fixer_email,
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

        # Fetch approver phone number and email from users table
        approver_phone = None
        approver_email = None
        if approver_name:
            conn_temp = get_db_connection()
            cursor_temp = conn_temp.cursor()
            cursor_temp.execute("SELECT phone, email FROM users WHERE name = %s LIMIT 1", (approver_name,))
            result = cursor_temp.fetchone()
            if result:
                approver_phone = result[0]
                approver_email = result[1]
            cursor_temp.close()
            conn_temp.close()

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
            "approver_email": approver_email,
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


