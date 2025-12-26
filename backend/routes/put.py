from fastapi import APIRouter, Depends
from utils import get_db_connection
from routes.auth import get_current_user

router = APIRouter()


# Update a ticket
@router.put("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: int, ticket: dict, current_user: dict = Depends(get_current_user)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if current_user["role"] in ["admin", "auditor"]:
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
        else:
            cursor.execute(
                """
                UPDATE tickets 
                SET title = %s, description = %s, category = %s, severity = %s, status = %s, attachment_upload = %s, approver = %s, fixer = %s
                WHERE id = %s AND user_id = %s
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
                    current_user["user_id"],
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


# Update a login user
@router.put("/login/{user_id}")
async def update_login_user(user_id: int, user: dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if username already exists for another user
        cursor.execute(
            "SELECT user_id FROM login WHERE LOWER(username) = LOWER(%s) AND user_id != %s",
            (user.get("name"), user_id),
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "Username already exists"}

        # Check if email already exists for another user
        cursor.execute(
            "SELECT user_id FROM login WHERE LOWER(email) = LOWER(%s) AND user_id != %s",
            (user.get("email"), user_id),
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"error": "Email already exists"}

        # If password is provided, hash it
        update_fields = "username = %s, email = %s, role = %s"
        values = [user.get("name"), user.get("email"), user.get("department")]
        if user.get("password"):
            from auth_utils import hash_password

            hashed_password = hash_password(user.get("password"))
            update_fields += ", password = %s"
            values.append(hashed_password)

        values.append(user_id)

        cursor.execute(
            f"""
            UPDATE login 
            SET {update_fields}
            WHERE user_id = %s
        """,
            values,
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "User updated successfully"}
    except Exception as e:
        return {"error": str(e)}


# Update an asset
@router.put("/assets/{asset_id}")
async def update_asset(
    asset_id: int, asset: dict, current_user: dict = Depends(get_current_user)
):
    try:
        from datetime import datetime, timedelta

        conn = get_db_connection()
        cursor = conn.cursor()

        # Build dynamic update query based on provided fields
        update_fields = []
        values = []

        if "action" in asset:
            update_fields.append("action = %s")
            values.append(asset["action"])
        if "item" in asset:
            update_fields.append("item = %s")
            values.append(asset["item"])
        if "serial_number" in asset:
            update_fields.append("serial_number = %s")
            values.append(asset["serial_number"])
        if "target" in asset:
            update_fields.append("target = %s")
            values.append(asset["target"])
        if "checked_out" in asset:
            update_fields.append("checked_out = %s")
            values.append(asset["checked_out"])
            # If setting checked_out to true, also set the timestamp
            if asset["checked_out"] == True:
                update_fields.append("checked_out_time = %s")
                values.append(datetime.utcnow() + timedelta(hours=8))

        if not update_fields:
            return {"error": "No fields to update"}

        query = f"UPDATE assets SET {', '.join(update_fields)} WHERE id = %s"
        values.append(asset_id)

        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Asset updated successfully"}
    except Exception as e:
        return {"error": str(e)}
