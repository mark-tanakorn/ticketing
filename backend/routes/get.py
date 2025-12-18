from fastapi import APIRouter
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from utils import (
    get_db_connection,
    trigger_sla_prebreached_workflow,
    trigger_sla_breached_workflow,
    SLA_HOURS_DICT,
    PRE_BREACH_SECONDS,
)

router = APIRouter()


# Get all tickets and check for SLA breaches and pre-breaches
@router.get("/tickets")
async def get_tickets():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM tickets ORDER BY date_created DESC")
        tickets = cursor.fetchall()
        cursor.close()
        conn.close()

        # Check and update SLA breaches and pre-breaches
        for ticket in tickets:
            if ticket.get("sla_start_time"):
                # Fetch phones
                approver_phone = None
                approver_email = None
                if ticket["approver"]:
                    conn_temp = get_db_connection()
                    cursor_temp = conn_temp.cursor()
                    cursor_temp.execute(
                        "SELECT phone, email FROM users WHERE name = %s LIMIT 1",
                        (ticket["approver"],),
                    )
                    result = cursor_temp.fetchone()
                    if result:
                        approver_phone = result[0]
                        approver_email = result[1]
                    cursor_temp.close()
                    conn_temp.close()

                fixer_phone = None
                fixer_email = None
                if ticket["fixer"]:
                    conn_temp = get_db_connection()
                    cursor_temp = conn_temp.cursor()
                    cursor_temp.execute(
                        "SELECT phone, email FROM fixers WHERE name = %s LIMIT 1",
                        (ticket["fixer"],),
                    )
                    result = cursor_temp.fetchone()
                    if result:
                        fixer_phone = result[0]
                        fixer_email = result[1]
                    cursor_temp.close()
                    conn_temp.close()

                sla_hours_value = SLA_HOURS_DICT.get(ticket["severity"].lower(), 72)
                breach_time = ticket["sla_start_time"] + timedelta(
                    hours=sla_hours_value
                )
                current_time = datetime.utcnow() + timedelta(hours=8)

                # Check pre-breach
                if (
                    not ticket.get("pre_breach_triggered", False)
                    and ticket["status"] not in ["closed", "sla_breached"]
                    and current_time >= breach_time - timedelta(seconds=PRE_BREACH_SECONDS)
                ):
                    sla_prebreached_payload = {
                        "ticket_id": ticket["id"],
                        "title": ticket["title"],
                        "description": ticket["description"],
                        "severity": ticket["severity"].capitalize(),
                        "breach_time": breach_time.strftime("%d/%m/%y %H:%M"),
                        "sla_hours": sla_hours_value,
                        "approver": ticket["approver"],
                        "approver_phone": approver_phone,
                        "fixer": ticket["fixer"],
                        "fixer_phone": fixer_phone,
                        "attachment_upload": ticket["attachment_upload"],
                    }
                    await trigger_sla_prebreached_workflow(sla_prebreached_payload)

                    # Update flag
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE tickets SET pre_breach_triggered = TRUE WHERE id = %s",
                        (ticket["id"],),
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    ticket["pre_breach_triggered"] = True

                # Check breach
                if (
                    not ticket.get("breach_triggered", False)
                    and ticket["status"] not in ["sla_breached", "closed"]
                    and current_time > breach_time
                ):
                    # Update status and flag
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE tickets SET status = 'sla_breached', breach_triggered = TRUE WHERE id = %s",
                        (ticket["id"],),
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    ticket["status"] = "sla_breached"
                    ticket["breach_triggered"] = True

                    # Trigger breach workflow
                    sla_breached_payload = {
                        "ticket_id": ticket["id"],
                        "title": ticket["title"],
                        "description": ticket["description"],
                        "severity": ticket["severity"].capitalize(),
                        "breach_time": breach_time.strftime("%d/%m/%y %H:%M"),
                        "sla_hours": sla_hours_value,
                        "approver": ticket["approver"],
                        "approver_phone": approver_phone,
                        "approver_email": approver_email,
                        "fixer": ticket["fixer"],
                        "fixer_phone": fixer_phone,
                        "fixer_email": fixer_email,
                        "attachment_upload": ticket["attachment_upload"],
                    }
                    await trigger_sla_breached_workflow(sla_breached_payload)

        return {"tickets": tickets}
    except Exception as e:
        return {"error": str(e)}


# Get all users
@router.get("/users")
async def get_all_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT id, name, phone, email, department, approval_tier FROM users ORDER BY id"
        )
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"users": users}
    except Exception as e:
        return {"error": str(e)}


# Get users by department, ordered by approval tier (create/edit ticket UI)
@router.get("/users/{department}")
async def get_users_by_department(department: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT id, name, department, approval_tier 
            FROM users 
            WHERE department = %s 
            ORDER BY approval_tier
        """,
            (department,),
        )
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"users": users}
    except Exception as e:
        return {"error": str(e)}


# Get all fixers
@router.get("/fixers")
async def get_all_fixers():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT id, name, email, phone, department FROM fixers ORDER BY id"
        )
        fixers = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"fixers": fixers}
    except Exception as e:
        return {"error": str(e)}
