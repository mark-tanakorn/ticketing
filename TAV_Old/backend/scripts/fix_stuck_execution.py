"""Fix stuck execution"""
import sys
sys.path.insert(0, '.')

from app.database.session import SessionLocal
from app.database.models.execution import Execution
from datetime import datetime

execution_id = "d79adec5-620e-49dd-936b-c4ff5ca7d51a"

db = SessionLocal()

try:
    # Get the execution
    exec = db.query(Execution).filter(Execution.id == execution_id).first()
    
    if not exec:
        print(f"❌ Execution not found: {execution_id}")
    else:
        print(f"Found execution: {exec.id}")
        print(f"  Current status: {exec.status}")
        print(f"  Started: {exec.started_at}")
        
        # Mark as failed (since it's stuck)
        exec.status = "failed"
        exec.completed_at = datetime.now()
        exec.error = "Execution timed out or was interrupted"
        
        db.commit()
        
        print("DONE - Execution marked as failed")
        print(f"  New status: {exec.status}")
        print(f"  Completed at: {exec.completed_at}")
        
finally:
    db.close()

print("\nDone! Try accessing the workflow now.")

