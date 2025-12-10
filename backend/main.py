from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import random
from datetime import datetime, timedelta

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow Next.js dev server
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
                assigned_to VARCHAR(255),
                attachment_upload TEXT
            );
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database tables checked/created successfully")
    except Exception as e:
        print(f"DB setup error: {e}")

# Basic route
@app.get("/")
async def root():
    return {"message": "Backend is running!"}

@app.get("/tickets")
async def get_tickets():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM tickets ORDER BY date_created DESC;")
        tickets = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"tickets": tickets}
    except Exception as e:
        return {"error": str(e)}

@app.post("/tickets")
async def create_ticket(ticket: dict):
    try:
        # Generate random ID
        ticket_id = random.randint(100000, 999999)
        
        # Get current time in Singapore timezone (UTC+8)
        current_time = datetime.utcnow() + timedelta(hours=8)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tickets (id, title, description, category, severity, status, assigned_to, attachment_upload, date_created)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (ticket_id, ticket.get('title'), ticket.get('description'), ticket.get('category'), ticket.get('severity'), 'awaiting_approval', ticket.get('assigned_to'), ticket.get('attachment_upload'), current_time))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Ticket created successfully"}
    except Exception as e:
        return {"error": str(e)}
