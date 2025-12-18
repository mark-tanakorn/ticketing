
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