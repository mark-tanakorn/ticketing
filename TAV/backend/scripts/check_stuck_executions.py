"""Check for stuck executions"""
import sys
sys.path.insert(0, '.')

from app.database.session import SessionLocal
from app.database.models.execution import Execution
from datetime import datetime, timezone

db = SessionLocal()

# Check for running/pending executions
running = db.query(Execution).filter(
    Execution.status.in_(['pending', 'running'])
).order_by(Execution.started_at.desc()).limit(10).all()

print("=" * 80)
print("STUCK/RUNNING EXECUTIONS:")
print("=" * 80)

if not running:
    print("✅ No stuck executions found")
else:
    for e in running:
        now = datetime.now() if not e.started_at.tzinfo else datetime.now(timezone.utc)
        age = now - e.started_at
        print(f"\nExecution: {e.id}")
        print(f"  Workflow: {e.workflow_id}")
        print(f"  Status: {e.status}")
        print(f"  Started: {e.started_at}")
        print(f"  Age: {age}")
        print(f"  Variables: {list(e.variables.keys()) if e.variables else 'None'}")

print("\n" + "=" * 80)
db.close()

