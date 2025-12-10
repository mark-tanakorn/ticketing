from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import random

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

# Create tables and sample data on startup
@app.on_event("startup")
async def startup_event():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create tickets table
        cursor.execute("DROP TABLE IF EXISTS tickets;")
        cursor.execute("""
            CREATE TABLE tickets (
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
        
        # Insert sample data (always reset on startup)
        cursor.execute("TRUNCATE TABLE tickets;")
        
        # Sample data
        data_list = [
            ("Fix login bug", "Users can't log in on mobile devices", "Software", "critical", "open", "dev_team", "2025-08-01 10:00:00"),
            ("Add dark mode", "Implement dark theme for better UX", "Hardware", "medium", "in_progress", "ui_team", "2025-08-15 14:30:00"),
            ("Update docs", "Refresh the user guide with new features", "Network", "low", "closed", "docs_team", "2025-08-20 09:15:00"),
            ("Database optimization", "Improve query performance", "Access", "high", "awaiting_approval", "backend_team", "2025-06-05 16:45:00"),
            ("Mobile app crash", "App crashes on startup for iOS users", "Security", "critical", "in_progress", "mobile_team", "2025-11-28 11:20:00"),
            ("Email notifications", "Add email alerts for ticket updates", "Software", "medium", "awaiting_approval", "dev_team", "2025-06-03 08:00:00"),
            ("Security audit", "Conduct security review", "Hardware", "high", "closed", "security_team", "2025-09-10 13:00:00"),
            ("UI redesign", "Redesign dashboard interface", "Network", "medium", "in_progress", "ui_team", "2025-06-22 15:10:00"),
            ("API rate limiting", "Implement rate limiting for APIs", "Access", "low", "approval_denied", "backend_team", "2025-06-07 12:30:00"),
            ("User feedback", "Analyze user survey responses", "Security", "low", "closed", "product_team", "2025-10-05 17:00:00"),
            ("Payment integration", "Integrate Stripe for payments", "Software", "high", "awaiting_approval", "dev_team", "2025-11-30 10:45:00"),
            ("Bug in reports", "Reports page shows incorrect data", "Hardware", "medium", "open", "qa_team", "2025-06-02 14:20:00"),
            ("Feature request", "Add export to CSV", "Network", "low", "closed", "dev_team", "2025-09-25 16:00:00"),
            ("Server downtime", "Investigate recent server outage", "Access", "critical", "in_progress", "ops_team", "2025-11-18 07:30:00"),
            ("Code review", "Review pull requests", "Security", "medium", "awaiting_approval", "dev_team", "2025-12-04 09:00:00"),
            ("Implement user authentication", "Add OAuth login options", "Software", "high", "open", "backend_team", "2025-12-08 09:00:00"),
            ("Fix memory leak", "App consumes too much memory on Android", "Hardware", "high", "in_progress", "mobile_team", "2025-08-25 11:00:00"),
            ("Add search functionality", "Implement search in ticket list", "Network", "medium", "open", "ui_team", "2025-12-06 13:00:00"),
            ("Database backup", "Set up automated backups", "Access", "medium", "closed", "ops_team", "2025-10-15 10:00:00"),
            ("Code refactoring", "Clean up legacy code", "Security", "low", "in_progress", "dev_team", "2025-08-20 15:00:00"),
            ("User onboarding", "Improve new user experience", "Software", "medium", "open", "product_team", "2025-06-07 14:00:00"),
            ("API documentation", "Update API docs", "Hardware", "low", "closed", "docs_team", "2025-09-30 12:00:00"),
            ("Performance monitoring", "Add monitoring tools", "Network", "high", "open", "backend_team", "2025-12-09 08:00:00"),
            ("Bug fix: UI glitch", "Fix button alignment issue", "Access", "low", "closed", "ui_team", "2025-11-10 16:00:00"),
            ("Feature: Notifications", "Add push notifications", "Security", "medium", "in_progress", "dev_team", "2025-08-27 10:00:00"),
        ]
        
        num_tickets = len(data_list)
        ids = set()
        while len(ids) < num_tickets:
            ids.add(random.randint(100000, 999999))
        ids_list = list(ids)
        
        new_data = []
        for i, item in enumerate(data_list):
            new_data.append((ids_list[i], item[0], item[1], item[2], item[3], item[4], item[5], item[6], None))
        
        cursor.executemany("""
            INSERT INTO tickets (id, title, description, category, severity, status, assigned_to, date_created, attachment_upload) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, new_data)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database tables created and sample data inserted")
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
