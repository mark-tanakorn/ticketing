from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils import (
    get_db_connection,
)
from routes.delete import router as delete_router
from routes.get import router as get_router
from routes.post import router as post_router
from routes.put import router as put_router


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
app.include_router(post_router)
app.include_router(put_router)


# Create tables if they don't exist
@app.on_event("startup")
async def startup_event():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create tickets table only if it doesn't exist
        cursor.execute(
            """
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
                fixer VARCHAR(255),
                approver_decision BOOLEAN,
                approver_reply_text TEXT,
                approver_decided_at TIMESTAMP,
                tav_execution_id TEXT,
                sla_start_time TIMESTAMP,
                pre_breach_triggered BOOLEAN DEFAULT FALSE
            );
        """
        )

        # Create users table only if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                email VARCHAR(255) UNIQUE NOT NULL,
                department VARCHAR(100),
                approval_tier INTEGER
            );
        """
        )

        # Create fixers table only if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fixers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                phone VARCHAR(50),
                department VARCHAR(255)
            );
        """
        )

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"DB setup error: {e}")
