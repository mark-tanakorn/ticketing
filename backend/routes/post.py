from fastapi import APIRouter, HTTPException
from psycopg2.extras import RealDictCursor
import random
from datetime import datetime, timedelta
from utils import (
    get_db_connection,
    trigger_contact_approver_workflow,
    trigger_contact_fixer_workflow,
    SLA_HOURS_DICT,
    TicketApprovalPayload,
    TicketStatusPayload,
)

router = APIRouter()


# Create a new ticket
@router.post("/tickets")
async def create_ticket(ticket: dict):
    try:
        # Generate random ID
        ticket_id = random.randint(100000, 999999)

        # Get current time in Singapore timezone (UTC+8)
        current_time = datetime.utcnow() + timedelta(hours=8)

        # Find approver based on department and approval_tier
        approver_name = None
        department = ticket.get("department")
        approval_tier = ticket.get("approval_tier")

        if department and approval_tier:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT name FROM users 
                WHERE department = %s AND approval_tier = %s
                LIMIT 1
            """,
                (department, approval_tier),
            )
            result = cursor.fetchone()
            if result:
                approver_name = result[0]
            cursor.close()
            conn.close()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tickets (id, title, description, category, severity, status, attachment_upload, date_created, approver, fixer)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                ticket_id,
                ticket.get("title"),
                ticket.get("description"),
                ticket.get("category"),
                ticket.get("severity"),
                "awaiting_approval",
                ticket.get("attachment_upload"),
                current_time,
                approver_name,
                ticket.get("assigned_to"),
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Fetch approver phone number and email from users table
        approver_phone = None
        approver_email = None
        if approver_name:
            conn_temp = get_db_connection()
            cursor_temp = conn_temp.cursor()
            cursor_temp.execute(
                "SELECT phone, email FROM users WHERE name = %s LIMIT 1",
                (approver_name,),
            )
            result = cursor_temp.fetchone()
            if result:
                approver_phone = result[0]
                approver_email = result[1]
            cursor_temp.close()
            conn_temp.close()

        # Fetch fixer phone number from fixers table
        fixer_phone = None
        if ticket.get("assigned_to"):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT phone FROM fixers WHERE name = %s LIMIT 1
            """,
                (ticket.get("assigned_to"),),
            )
            result = cursor.fetchone()
            if result:
                fixer_phone = result[0]
            cursor.close()
            conn.close()

        # Craft the payload for TAV workflow
        contact_approver_payload = {
            "ticket_id": ticket_id,
            "title": ticket.get("title"),
            "description": ticket.get("description"),
            "severity": (
                ticket.get("severity").capitalize()
                if ticket.get("severity")
                else ticket.get("severity")
            ),
            "date_created": current_time.strftime("%d/%m/%y %H:%M"),
            "approver": approver_name,
            "approver_phone": approver_phone,
            "approver_email": approver_email,
            "fixer": ticket.get("assigned_to"),
            "fixer_phone": fixer_phone,
        }

        # Trigger TAV workflow
        await trigger_contact_approver_workflow(contact_approver_payload)

        return {"message": "Ticket created successfully"}
    except Exception as e:
        return {"error": str(e)}


# Create a new user
@router.post("/users")
async def create_user(user: dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if name already exists
        cursor.execute(
            "SELECT id FROM users WHERE LOWER(name) = LOWER(%s)", (user.get("name"),)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "User name already exists"}

        # Check if email already exists
        cursor.execute(
            "SELECT id FROM users WHERE LOWER(email) = LOWER(%s)", (user.get("email"),)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "User email already exists"}

        # Check if phone already exists
        cursor.execute("SELECT id FROM users WHERE phone = %s", (user.get("phone"),))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "User phone already exists"}

        # Get the next sequential ID (not auto-increment)
        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM users")
        next_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO users (id, name, phone, email, department, approval_tier)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (
                next_id,
                user.get("name"),
                user.get("phone"),
                user.get("email"),
                user.get("department"),
                user.get("approval_tier"),
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "User created successfully"}
    except Exception as e:
        return {"error": str(e)}


# Create a new fixer
@router.post("/fixers")
async def create_fixer(fixer: dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if name already exists
        cursor.execute(
            "SELECT id FROM fixers WHERE LOWER(name) = LOWER(%s)", (fixer.get("name"),)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "Fixer name already exists"}

        # Check if email already exists
        cursor.execute(
            "SELECT id FROM fixers WHERE LOWER(email) = LOWER(%s)",
            (fixer.get("email"),),
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "Fixer email already exists"}

        # Check if phone already exists
        cursor.execute("SELECT id FROM fixers WHERE phone = %s", (fixer.get("phone"),))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "Fixer phone already exists"}

        # Get the next sequential ID (not auto-increment)
        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM fixers")
        next_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO fixers (id, name, email, phone, department)
            VALUES (%s, %s, %s, %s, %s)
        """,
            (
                next_id,
                fixer.get("name"),
                fixer.get("email"),
                fixer.get("phone"),
                fixer.get("department"),
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Fixer created successfully"}
    except Exception as e:
        return {"error": str(e)}


# Update a ticket's status based on approver response
@router.post("/tickets/{ticket_id}/approval")
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
        if not payload.approved and (
            payload.reply_text is None or payload.reply_text.strip() == ""
        ):
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
                hours = SLA_HOURS_DICT.get(ticket_data["severity"].lower(), 72)
                actual_breach_time = ticket_data["sla_start_time"] + timedelta(
                    hours=hours
                )

                # Fetch approver email and phone
                approver_email = None
                approver_phone = None
                if ticket_data["approver"]:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT email, phone FROM users WHERE name = %s LIMIT 1",
                        (ticket_data["approver"],),
                    )
                    result = cursor.fetchone()
                    if result:
                        approver_email = result[0]
                        approver_phone = result[1]
                    cursor.close()
                    conn.close()

                # Fetch fixer email
                fixer_phone = None
                fixer_email = None
                if ticket_data["fixer"]:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT phone, email FROM fixers WHERE name = %s LIMIT 1",
                        (ticket_data["fixer"],),
                    )
                    result = cursor.fetchone()
                    if result:
                        fixer_phone = result[0]
                        fixer_email = result[1]
                    cursor.close()
                    conn.close()

                # Create payload for the updated workflow
                contact_fixer_payload = {
                    "ticket_id": ticket_id,
                    "title": ticket_data["title"],
                    "description": ticket_data["description"],
                    "severity": ticket_data["severity"].capitalize(),
                    "breach_time": actual_breach_time.strftime("%d/%m/%y %H:%M"),
                    "sla_hours": hours,
                    "approver": ticket_data["approver"],
                    "approver_email": approver_email,
                    "approver_phone": approver_phone,
                    "fixer": ticket_data["fixer"],
                    "fixer_phone": fixer_phone,
                    "fixer_email": fixer_email,
                    "attachment_upload": ticket_data["attachment_upload"],
                    "approver_decided_at": ticket_data["approver_decided_at"].strftime("%d/%m/%y %H:%M"),
                }

                # Trigger the updated workflow
                await trigger_contact_fixer_workflow(contact_fixer_payload)

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


# Update a ticket's status based on fixer response
@router.post("/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: int, payload: TicketStatusPayload | None = None
):
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
        cursor.execute(
            "SELECT id, status, fixer FROM tickets WHERE id = %s", (ticket_id,)
        )
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
        fixer_to_set = (
            requested_fixer if requested_fixer is not None else existing.get("fixer")
        )
        if new_status == "in_progress" and (
            fixer_to_set is None or str(fixer_to_set).strip() == ""
        ):
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

        return {
            "message": "Ticket status updated",
            "ticket_id": ticket_id,
            "status": new_status,
            "fixer": requested_fixer,
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e)}
