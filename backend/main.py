from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor

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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                severity VARCHAR(50),
                date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'open',
                assigned_to VARCHAR(255)
            );
        """)
        
        # Insert sample data (always reset on startup)
        cursor.execute("TRUNCATE TABLE tickets;")
        cursor.executemany("""
            INSERT INTO tickets (title, description, severity, status, assigned_to, date_created) VALUES (%s, %s, %s, %s, %s, %s);
        """, [
            ("Fix login bug", "Users can't log in on mobile devices", "high", "open", "dev_team", "2025-12-01 10:00:00"),
            ("Add dark mode", "Implement dark theme for better UX", "medium", "in_progress", "ui_team", "2025-11-15 14:30:00"),
            ("Update docs", "Refresh the user guide with new features", "low", "closed", "docs_team", "2025-10-20 09:15:00"),
            ("Database optimization", "Improve query performance", "high", "open", "backend_team", "2025-12-05 16:45:00"),
            ("Mobile app crash", "App crashes on startup for iOS users", "high", "in_progress", "mobile_team", "2025-11-28 11:20:00"),
            ("Email notifications", "Add email alerts for ticket updates", "medium", "open", "dev_team", "2025-12-03 08:00:00"),
            ("Security audit", "Conduct security review", "high", "closed", "security_team", "2025-09-10 13:00:00"),
            ("UI redesign", "Redesign dashboard interface", "medium", "in_progress", "ui_team", "2025-11-22 15:10:00"),
            ("API rate limiting", "Implement rate limiting for APIs", "low", "open", "backend_team", "2025-12-07 12:30:00"),
            ("User feedback", "Analyze user survey responses", "low", "closed", "product_team", "2025-10-05 17:00:00"),
            ("Payment integration", "Integrate Stripe for payments", "high", "in_progress", "dev_team", "2025-11-30 10:45:00"),
            ("Bug in reports", "Reports page shows incorrect data", "medium", "open", "qa_team", "2025-12-02 14:20:00"),
            ("Feature request", "Add export to CSV", "low", "closed", "dev_team", "2025-09-25 16:00:00"),
            ("Server downtime", "Investigate recent server outage", "high", "in_progress", "ops_team", "2025-11-18 07:30:00"),
            ("Code review", "Review pull requests", "medium", "open", "dev_team", "2025-12-04 09:00:00"),
            ("Implement user authentication", "Add OAuth login options", "high", "open", "backend_team", "2025-12-08 09:00:00"),
            ("Fix memory leak", "App consumes too much memory on Android", "high", "in_progress", "mobile_team", "2025-11-25 11:00:00"),
            ("Add search functionality", "Implement search in ticket list", "medium", "open", "ui_team", "2025-12-06 13:00:00"),
            ("Database backup", "Set up automated backups", "medium", "closed", "ops_team", "2025-10-15 10:00:00"),
            ("Code refactoring", "Clean up legacy code", "low", "in_progress", "dev_team", "2025-11-20 15:00:00"),
            ("User onboarding", "Improve new user experience", "medium", "open", "product_team", "2025-12-07 14:00:00"),
            ("API documentation", "Update API docs", "low", "closed", "docs_team", "2025-09-30 12:00:00"),
            ("Performance monitoring", "Add monitoring tools", "high", "open", "backend_team", "2025-12-09 08:00:00"),
            ("Bug fix: UI glitch", "Fix button alignment issue", "low", "closed", "ui_team", "2025-11-10 16:00:00"),
            ("Feature: Notifications", "Add push notifications", "medium", "in_progress", "dev_team", "2025-11-27 10:00:00"),
            ("Fix login bug", "Users can't log in on mobile devices", "high", "open", "dev_team", "2025-12-01 10:00:00"),
            ("Add dark mode", "Implement dark theme for better UX", "medium", "in_progress", "ui_team", "2025-11-15 14:30:00"),
            ("Update docs", "Refresh the user guide with new features", "low", "closed", "docs_team", "2025-10-20 09:15:00"),
            ("Database optimization", "Improve query performance", "high", "open", "backend_team", "2025-12-05 16:45:00"),
            ("Mobile app crash", "App crashes on startup for iOS users", "high", "in_progress", "mobile_team", "2025-11-28 11:20:00"),
            ("Email notifications", "Add email alerts for ticket updates", "medium", "open", "dev_team", "2025-12-03 08:00:00"),
            ("Security audit", "Conduct security review", "high", "closed", "security_team", "2025-09-10 13:00:00"),
            ("UI redesign", "Redesign dashboard interface", "medium", "in_progress", "ui_team", "2025-11-22 15:10:00"),
            ("API rate limiting", "Implement rate limiting for APIs", "low", "open", "backend_team", "2025-12-07 12:30:00"),
            ("User feedback", "Analyze user survey responses", "low", "closed", "product_team", "2025-10-05 17:00:00"),
            ("Payment integration", "Integrate Stripe for payments", "high", "in_progress", "dev_team", "2025-11-30 10:45:00"),
            ("Bug in reports", "Reports page shows incorrect data", "medium", "open", "qa_team", "2025-12-02 14:20:00"),
            ("Feature request", "Add export to CSV", "low", "closed", "dev_team", "2025-09-25 16:00:00"),
            ("Server downtime", "Investigate recent server outage", "high", "in_progress", "ops_team", "2025-11-18 07:30:00"),
            ("Code review", "Review pull requests", "medium", "open", "dev_team", "2025-12-04 09:00:00"),
            ("Implement user authentication", "Add OAuth login options", "high", "open", "backend_team", "2025-12-08 09:00:00"),
            ("Fix memory leak", "App consumes too much memory on Android", "high", "in_progress", "mobile_team", "2025-11-25 11:00:00"),
            ("Add search functionality", "Implement search in ticket list", "medium", "open", "ui_team", "2025-12-06 13:00:00"),
            ("Database backup", "Set up automated backups", "medium", "closed", "ops_team", "2025-10-15 10:00:00"),
            ("Code refactoring", "Clean up legacy code", "low", "in_progress", "dev_team", "2025-11-20 15:00:00"),
            ("User onboarding", "Improve new user experience", "medium", "open", "product_team", "2025-12-07 14:00:00"),
            ("API documentation", "Update API docs", "low", "closed", "docs_team", "2025-09-30 12:00:00"),
            ("Performance monitoring", "Add monitoring tools", "high", "open", "backend_team", "2025-12-09 08:00:00"),
            ("Bug fix: UI glitch", "Fix button alignment issue", "low", "closed", "ui_team", "2025-11-10 16:00:00"),
            ("Feature: Notifications", "Add push notifications", "medium", "in_progress", "dev_team", "2025-11-27 10:00:00"),
            ("Fix login bug", "Users can't log in on mobile devices", "high", "open", "dev_team", "2025-12-01 10:00:00"),
            ("Add dark mode", "Implement dark theme for better UX", "medium", "in_progress", "ui_team", "2025-11-15 14:30:00"),
            ("Update docs", "Refresh the user guide with new features", "low", "closed", "docs_team", "2025-10-20 09:15:00"),
            ("Database optimization", "Improve query performance", "high", "open", "backend_team", "2025-12-05 16:45:00"),
            ("Mobile app crash", "App crashes on startup for iOS users", "high", "in_progress", "mobile_team", "2025-11-28 11:20:00"),
            ("Email notifications", "Add email alerts for ticket updates", "medium", "open", "dev_team", "2025-12-03 08:00:00"),
            ("Security audit", "Conduct security review", "high", "closed", "security_team", "2025-09-10 13:00:00"),
            ("UI redesign", "Redesign dashboard interface", "medium", "in_progress", "ui_team", "2025-11-22 15:10:00"),
            ("API rate limiting", "Implement rate limiting for APIs", "low", "open", "backend_team", "2025-12-07 12:30:00"),
            ("User feedback", "Analyze user survey responses", "low", "closed", "product_team", "2025-10-05 17:00:00"),
            ("Payment integration", "Integrate Stripe for payments", "high", "in_progress", "dev_team", "2025-11-30 10:45:00"),
            ("Bug in reports", "Reports page shows incorrect data", "medium", "open", "qa_team", "2025-12-02 14:20:00"),
            ("Feature request", "Add export to CSV", "low", "closed", "dev_team", "2025-09-25 16:00:00"),
            ("Server downtime", "Investigate recent server outage", "high", "in_progress", "ops_team", "2025-11-18 07:30:00"),
            ("Code review", "Review pull requests", "medium", "open", "dev_team", "2025-12-04 09:00:00"),
            ("Implement user authentication", "Add OAuth login options", "high", "open", "backend_team", "2025-12-08 09:00:00"),
            ("Fix memory leak", "App consumes too much memory on Android", "high", "in_progress", "mobile_team", "2025-11-25 11:00:00"),
            ("Add search functionality", "Implement search in ticket list", "medium", "open", "ui_team", "2025-12-06 13:00:00"),
            ("Database backup", "Set up automated backups", "medium", "closed", "ops_team", "2025-10-15 10:00:00"),
            ("Code refactoring", "Clean up legacy code", "low", "in_progress", "dev_team", "2025-11-20 15:00:00"),
            ("User onboarding", "Improve new user experience", "medium", "open", "product_team", "2025-12-07 14:00:00"),
            ("API documentation", "Update API docs", "low", "closed", "docs_team", "2025-09-30 12:00:00"),
            ("Performance monitoring", "Add monitoring tools", "high", "open", "backend_team", "2025-12-09 08:00:00"),
            ("Bug fix: UI glitch", "Fix button alignment issue", "low", "closed", "ui_team", "2025-11-10 16:00:00"),
            ("Feature: Notifications", "Add push notifications", "medium", "in_progress", "dev_team", "2025-11-27 10:00:00"),
            ("Fix login bug", "Users can't log in on mobile devices", "high", "open", "dev_team", "2025-12-01 10:00:00"),
            ("Add dark mode", "Implement dark theme for better UX", "medium", "in_progress", "ui_team", "2025-11-15 14:30:00"),
            ("Update docs", "Refresh the user guide with new features", "low", "closed", "docs_team", "2025-10-20 09:15:00"),
            ("Database optimization", "Improve query performance", "high", "open", "backend_team", "2025-12-05 16:45:00"),
            ("Mobile app crash", "App crashes on startup for iOS users", "high", "in_progress", "mobile_team", "2025-11-28 11:20:00"),
            ("Email notifications", "Add email alerts for ticket updates", "medium", "open", "dev_team", "2025-12-03 08:00:00"),
            ("Security audit", "Conduct security review", "high", "closed", "security_team", "2025-09-10 13:00:00"),
            ("UI redesign", "Redesign dashboard interface", "medium", "in_progress", "ui_team", "2025-11-22 15:10:00"),
            ("API rate limiting", "Implement rate limiting for APIs", "low", "open", "backend_team", "2025-12-07 12:30:00"),
            ("User feedback", "Analyze user survey responses", "low", "closed", "product_team", "2025-10-05 17:00:00"),
            ("Payment integration", "Integrate Stripe for payments", "high", "in_progress", "dev_team", "2025-11-30 10:45:00"),
            ("Bug in reports", "Reports page shows incorrect data", "medium", "open", "qa_team", "2025-12-02 14:20:00"),
            ("Feature request", "Add export to CSV", "low", "closed", "dev_team", "2025-09-25 16:00:00"),
            ("Server downtime", "Investigate recent server outage", "high", "in_progress", "ops_team", "2025-11-18 07:30:00"),
            ("Code review", "Review pull requests", "medium", "open", "dev_team", "2025-12-04 09:00:00"),
            ("Implement user authentication", "Add OAuth login options", "high", "open", "backend_team", "2025-12-08 09:00:00"),
            ("Fix memory leak", "App consumes too much memory on Android", "high", "in_progress", "mobile_team", "2025-11-25 11:00:00"),
            ("Add search functionality", "Implement search in ticket list", "medium", "open", "ui_team", "2025-12-06 13:00:00"),
            ("Database backup", "Set up automated backups", "medium", "closed", "ops_team", "2025-10-15 10:00:00"),
            ("Code refactoring", "Clean up legacy code", "low", "in_progress", "dev_team", "2025-11-20 15:00:00"),
            ("User onboarding", "Improve new user experience", "medium", "open", "product_team", "2025-12-07 14:00:00"),
            ("API documentation", "Update API docs", "low", "closed", "docs_team", "2025-09-30 12:00:00"),
            ("Performance monitoring", "Add monitoring tools", "high", "open", "backend_team", "2025-12-09 08:00:00"),
            ("Bug fix: UI glitch", "Fix button alignment issue", "low", "closed", "ui_team", "2025-11-10 16:00:00"),
            ("Feature: Notifications", "Add push notifications", "medium", "in_progress", "dev_team", "2025-11-27 10:00:00"),
            ("Fix login bug", "Users can't log in on mobile devices", "high", "open", "dev_team", "2025-12-01 10:00:00"),
            ("Add dark mode", "Implement dark theme for better UX", "medium", "in_progress", "ui_team", "2025-11-15 14:30:00"),
            ("Update docs", "Refresh the user guide with new features", "low", "closed", "docs_team", "2025-10-20 09:15:00"),
            ("Database optimization", "Improve query performance", "high", "open", "backend_team", "2025-12-05 16:45:00"),
            ("Mobile app crash", "App crashes on startup for iOS users", "high", "in_progress", "mobile_team", "2025-11-28 11:20:00"),
            ("Email notifications", "Add email alerts for ticket updates", "medium", "open", "dev_team", "2025-12-03 08:00:00"),
            ("Security audit", "Conduct security review", "high", "closed", "security_team", "2025-09-10 13:00:00"),
            ("UI redesign", "Redesign dashboard interface", "medium", "in_progress", "ui_team", "2025-11-22 15:10:00"),
            ("API rate limiting", "Implement rate limiting for APIs", "low", "open", "backend_team", "2025-12-07 12:30:00"),
            ("User feedback", "Analyze user survey responses", "low", "closed", "product_team", "2025-10-05 17:00:00"),
            ("Payment integration", "Integrate Stripe for payments", "high", "in_progress", "dev_team", "2025-11-30 10:45:00"),
            ("Bug in reports", "Reports page shows incorrect data", "medium", "open", "qa_team", "2025-12-02 14:20:00"),
            ("Feature request", "Add export to CSV", "low", "closed", "dev_team", "2025-09-25 16:00:00"),
            ("Server downtime", "Investigate recent server outage", "high", "in_progress", "ops_team", "2025-11-18 07:30:00"),
            ("Code review", "Review pull requests", "medium", "open", "dev_team", "2025-12-04 09:00:00"),
            ("Implement user authentication", "Add OAuth login options", "high", "open", "backend_team", "2025-12-08 09:00:00"),
            ("Fix memory leak", "App consumes too much memory on Android", "high", "in_progress", "mobile_team", "2025-11-25 11:00:00"),
            ("Add search functionality", "Implement search in ticket list", "medium", "open", "ui_team", "2025-12-06 13:00:00"),
            ("Database backup", "Set up automated backups", "medium", "closed", "ops_team", "2025-10-15 10:00:00"),
            ("Code refactoring", "Clean up legacy code", "low", "in_progress", "dev_team", "2025-11-20 15:00:00"),
            ("User onboarding", "Improve new user experience", "medium", "open", "product_team", "2025-12-07 14:00:00"),
            ("API documentation", "Update API docs", "low", "closed", "docs_team", "2025-09-30 12:00:00"),
            ("Performance monitoring", "Add monitoring tools", "high", "open", "backend_team", "2025-12-09 08:00:00"),
            ("Bug fix: UI glitch", "Fix button alignment issue", "low", "closed", "ui_team", "2025-11-10 16:00:00"),
            ("Feature: Notifications", "Add push notifications", "medium", "in_progress", "dev_team", "2025-11-27 10:00:00"),
            ("Fix login bug", "Users can't log in on mobile devices", "high", "open", "dev_team", "2025-12-01 10:00:00"),
            ("Add dark mode", "Implement dark theme for better UX", "medium", "in_progress", "ui_team", "2025-11-15 14:30:00"),
            ("Update docs", "Refresh the user guide with new features", "low", "closed", "docs_team", "2025-10-20 09:15:00"),
            ("Database optimization", "Improve query performance", "high", "open", "backend_team", "2025-12-05 16:45:00"),
            ("Mobile app crash", "App crashes on startup for iOS users", "high", "in_progress", "mobile_team", "2025-11-28 11:20:00"),
            ("Email notifications", "Add email alerts for ticket updates", "medium", "open", "dev_team", "2025-12-03 08:00:00"),
            ("Security audit", "Conduct security review", "high", "closed", "security_team", "2025-09-10 13:00:00"),
            ("UI redesign", "Redesign dashboard interface", "medium", "in_progress", "ui_team", "2025-11-22 15:10:00"),
            ("API rate limiting", "Implement rate limiting for APIs", "low", "open", "backend_team", "2025-12-07 12:30:00"),
            ("User feedback", "Analyze user survey responses", "low", "closed", "product_team", "2025-10-05 17:00:00"),
            ("Payment integration", "Integrate Stripe for payments", "high", "in_progress", "dev_team", "2025-11-30 10:45:00"),
            ("Bug in reports", "Reports page shows incorrect data", "medium", "open", "qa_team", "2025-12-02 14:20:00"),
            ("Feature request", "Add export to CSV", "low", "closed", "dev_team", "2025-09-25 16:00:00"),
            ("Server downtime", "Investigate recent server outage", "high", "in_progress", "ops_team", "2025-11-18 07:30:00"),
            ("Code review", "Review pull requests", "medium", "open", "dev_team", "2025-12-04 09:00:00"),
            ("Implement user authentication", "Add OAuth login options", "high", "open", "backend_team", "2025-12-08 09:00:00"),
            ("Fix memory leak", "App consumes too much memory on Android", "high", "in_progress", "mobile_team", "2025-11-25 11:00:00"),
            ("Add search functionality", "Implement search in ticket list", "medium", "open", "ui_team", "2025-12-06 13:00:00"),
            ("Database backup", "Set up automated backups", "medium", "closed", "ops_team", "2025-10-15 10:00:00"),
            ("Code refactoring", "Clean up legacy code", "low", "in_progress", "dev_team", "2025-11-20 15:00:00"),
            ("User onboarding", "Improve new user experience", "medium", "open", "product_team", "2025-12-07 14:00:00"),
            ("API documentation", "Update API docs", "low", "closed", "docs_team", "2025-09-30 12:00:00"),
            ("Performance monitoring", "Add monitoring tools", "high", "open", "backend_team", "2025-12-09 08:00:00"),
            ("Bug fix: UI glitch", "Fix button alignment issue", "low", "closed", "ui_team", "2025-11-10 16:00:00"),
            ("Feature: Notifications", "Add push notifications", "medium", "in_progress", "dev_team", "2025-11-27 10:00:00")
        ])
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database tables created and sample data inserted")
    except Exception as e:
        print(f"DB setup error: {e}")

# Route to get all tickets
@app.get("/tickets")
async def get_tickets():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM tickets;")
    tickets = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"tickets": tickets}

# Basic route
@app.get("/")
async def root():
    return {"message": "Backend is running!"}