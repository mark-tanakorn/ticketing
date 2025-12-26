from fastapi import APIRouter, Depends
from utils import get_db_connection
from routes.auth import get_current_user

router = APIRouter()


# Delete a ticket
@router.delete("/tickets/{ticket_id}")
async def delete_ticket(ticket_id: int, current_user: dict = Depends(get_current_user)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if current_user["role"] in ["admin", "auditor"]:
            cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
        else:
            cursor.execute(
                "DELETE FROM tickets WHERE id = %s AND user_id = %s",
                (ticket_id, current_user["user_id"]),
            )
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Ticket deleted successfully"}
    except Exception as e:
        return {"error": str(e)}


# Delete a user
@router.delete("/users/{user_id}")
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


# Delete a fixer
@router.delete("/fixers/{fixer_id}")
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


# Delete a login user
@router.delete("/login/{user_id}")
async def delete_login_user(user_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get the role of the user being deleted
        cursor.execute("SELECT role FROM login WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        if not result:
            cursor.close()
            conn.close()
            return {"error": "User not found"}

        role = result[0]

        if role == "admin":
            # Count how many admins are left
            cursor.execute("SELECT COUNT(*) FROM login WHERE role = 'admin'")
            admin_count = cursor.fetchone()[0]
            print(
                f"Admin count: {admin_count}, deleting user ID: {user_id}, role: {role}"
            )
            if admin_count <= 1:
                print(f"Blocked attempt to delete the last admin user (ID: {user_id})")
                cursor.close()
                conn.close()
                return {"error": "Cannot delete the last admin user"}

        cursor.execute("DELETE FROM login WHERE user_id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "User deleted successfully"}
    except Exception as e:
        return {"error": str(e)}


# Delete an asset
@router.delete("/assets/{asset_id}")
async def delete_asset(asset_id: int, current_user: dict = Depends(get_current_user)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM assets WHERE id = %s", (asset_id,))
        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Asset deleted successfully"}
    except Exception as e:
        return {"error": str(e)}
