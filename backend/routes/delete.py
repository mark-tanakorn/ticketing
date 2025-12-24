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
        cursor.execute("DELETE FROM tickets WHERE id = %s AND user_id = %s", (ticket_id, current_user["user_id"]))
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
