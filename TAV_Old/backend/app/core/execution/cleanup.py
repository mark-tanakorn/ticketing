"""
Execution Cleanup Utilities

Handles cleanup of orphaned executions after server restarts.
"""

import logging
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from app.database.models.execution import Execution

logger = logging.getLogger(__name__)


def cleanup_orphaned_executions_on_startup(db: Session) -> List[str]:
    """
    Cleanup orphaned executions from previous server session.
    
    When the server restarts (crash, manual restart, etc.), ALL executions
    marked as 'running' or 'pending' are orphaned - the executor process is gone.
    We need to mark them as failed so the UI doesn't try to reconnect to them.
    
    This is safe because:
    - If server just started, those executions CANNOT be running
    - They're remnants from the previous server session
    - Trigger-based workflows will restart on next trigger
    - One-shot workflows are truly dead
    
    Args:
        db: Database session
        
    Returns:
        List of execution IDs that were cleaned up
    """
    # Find ALL running/pending executions (they're all orphaned if server just started)
    orphaned = db.query(Execution).filter(
        Execution.status.in_(['pending', 'running']),
        Execution.completed_at.is_(None)
    ).all()
    
    if not orphaned:
        logger.info("✅ No orphaned executions from previous session")
        return []
    
    logger.warning(f"🔍 Found {len(orphaned)} orphaned execution(s) from previous session")
    
    cleaned_ids = []
    for exec in orphaned:
        age = datetime.now() - exec.started_at if exec.started_at else None
        logger.warning(
            f"  • Execution {exec.id} (workflow={exec.workflow_id}): "
            f"orphaned in '{exec.status}' state{f', age: {age}' if age else ''}"
        )
        
        # Mark as failed
        exec.status = "failed"
        exec.completed_at = datetime.now()
        exec.error = "Execution interrupted by server restart"
        
        cleaned_ids.append(exec.id)
    
    db.commit()
    logger.info(f"✅ Cleaned up {len(cleaned_ids)} orphaned execution(s)")
    
    return cleaned_ids

