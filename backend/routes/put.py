from fastapi import APIRouter
from utils import get_db_connection

router = APIRouter()


# Update a ticket
@router.put("/tickets/{ticket_id}")
async def update_ticket(ticket_id: int, ticket: dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE tickets 
            SET title = %s, description = %s, category = %s, severity = %s, status = %s, attachment_upload = %s, approver = %s, fixer = %s
            WHERE id = %s
        """,
            (
                ticket.get("title"),
                ticket.get("description"),
                ticket.get("category"),
                ticket.get("severity"),
                ticket.get("status"),
                ticket.get("attachment_upload"),
                ticket.get("approver"),
                ticket.get("fixer"),
                ticket_id,
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Ticket updated successfully"}
    except Exception as e:
        return {"error": str(e)}


# Update a user
@router.put("/users/{user_id}")
async def update_user(user_id: int, user: dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if name already exists for another user
        cursor.execute(
            "SELECT id FROM users WHERE LOWER(name) = LOWER(%s) AND id != %s",
            (user.get("name"), user_id),
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "User name already exists"}

        # Check if email already exists for another user
        cursor.execute(
            "SELECT id FROM users WHERE LOWER(email) = LOWER(%s) AND id != %s",
            (user.get("email"), user_id),
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "User email already exists"}

        # Check if phone already exists for another user
        cursor.execute(
            "SELECT id FROM users WHERE phone = %s AND id != %s",
            (user.get("phone"), user_id),
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "User phone already exists"}

        cursor.execute(
            """
            UPDATE users 
            SET name = %s, phone = %s, email = %s, department = %s, approval_tier = %s
            WHERE id = %s
        """,
            (
                user.get("name"),
                user.get("phone"),
                user.get("email"),
                user.get("department"),
                user.get("approval_tier"),
                user_id,
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "User updated successfully"}
    except Exception as e:
        return {"error": str(e)}


# Update a fixer
@router.put("/fixers/{fixer_id}")
async def update_fixer(fixer_id: int, fixer: dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if name already exists for another fixer
        cursor.execute(
            "SELECT id FROM fixers WHERE LOWER(name) = LOWER(%s) AND id != %s",
            (fixer.get("name"), fixer_id),
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "Fixer name already exists"}

        # Check if email already exists for another fixer
        cursor.execute(
            "SELECT id FROM fixers WHERE LOWER(email) = LOWER(%s) AND id != %s",
            (fixer.get("email"), fixer_id),
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "Fixer email already exists"}

        # Check if phone already exists for another fixer
        cursor.execute(
            "SELECT id FROM fixers WHERE phone = %s AND id != %s",
            (fixer.get("phone"), fixer_id),
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "Fixer phone already exists"}

        cursor.execute(
            """
            UPDATE fixers 
            SET name = %s, email = %s, phone = %s, department = %s
            WHERE id = %s
        """,
            (
                fixer.get("name"),
                fixer.get("email"),
                fixer.get("phone"),
                fixer.get("department"),
                fixer_id,
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Fixer updated successfully"}
    except Exception as e:
        return {"error": str(e)}
