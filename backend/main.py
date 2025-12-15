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
        
        # Helper function to check SLA breach
        def is_sla_breached(date_created, severity):
            sla_hours = {
                'low': 72,
                'medium': 48,
                'high': 24,
                'critical': 4
            }
            hours = sla_hours.get(severity.lower(), 72)
            breach_time = date_created + timedelta(hours=hours)
            current_time = datetime.utcnow() + timedelta(hours=8)  # Singapore timezone
            return current_time > breach_time
        
        # Check and update SLA breaches
        for ticket in tickets:
            if ticket['status'] != 'sla_breached' and is_sla_breached(ticket['date_created'], ticket['severity']):
                # Update status in database
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE tickets SET status = 'sla_breached' WHERE id = %s", (ticket['id'],))
                conn.commit()
                cursor.close()
                conn.close()
                ticket['status'] = 'sla_breached'  # Update in memory
        
        return {"tickets": tickets}
    except Exception as e:
        return {"error": str(e)}

# Add TAV constants and helper function
# For local dev, TAV typically runs at http://localhost:5000
# Override via env vars if you're targeting a remote TAV instance.
TAV_BASE_URL = os.getenv("TAV_BASE_URL", "http://localhost:5000")
TAV_WORKFLOW_ID = os.getenv("TAV_WORKFLOW_ID", "de51f0d2-31fb-448a-acfd-409586920ad8")

async def trigger_tav_workflow(ticket_payload: dict) -> None:
    url = f"{TAV_BASE_URL}/api/v1/workflows/{TAV_WORKFLOW_ID}/execute"
    body = {"trigger_data": ticket_payload}

    async with httpx.AsyncClient(timeout=10) as client:
        # If TAV dev-mode is enabled, no Authorization header is needed.
        r = await client.post(url, json=body)
        r.raise_for_status()


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
