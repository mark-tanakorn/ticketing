"""
Execution API Endpoints

Handles execution-related endpoints including:
- Real-time SSE streaming for execution updates
- Execution status queries
- Execution control (moved from workflows.py for better modularity)
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user, get_current_user_smart
from app.database.models.user import User
from app.database.models.execution import Execution
from app.database.models.workflow import Workflow


logger = logging.getLogger(__name__)

router = APIRouter()


# In-memory event queues for SSE streaming
# Structure: {execution_id: {client_id: asyncio.Queue}}
_sse_event_queues: Dict[str, Dict[str, asyncio.Queue]] = {}

# Workflow-level event queues for trigger workflows
# Structure: {workflow_id: {client_id: asyncio.Queue}}
_workflow_event_queues: Dict[str, Dict[str, asyncio.Queue]] = {}

# Connection tracking
_sse_connections: Dict[str, Dict[str, Any]] = {}

# Configuration
SSE_CONFIG = {
    "max_connections_per_execution": 50,
    "heartbeat_interval": 30,  # seconds
    "max_queue_size": 100,
}


# ============================================================================
# SSE EVENT BROADCASTING
# ============================================================================

def broadcast_sse_event(execution_id: str, event: Dict[str, Any]) -> int:
    """
    Broadcast an event to all SSE clients connected to an execution.
    
    Args:
        execution_id: Execution ID to broadcast to
        event: Event data dictionary (must include 'type' field)
    
    Returns:
        Number of clients the event was sent to
    """
    if execution_id not in _sse_event_queues:
        logger.debug(f"No SSE clients connected for execution {execution_id}")
        return 0
    
    clients = _sse_event_queues[execution_id]
    sent_count = 0
    
    for client_id, queue in clients.items():
        try:
            # Non-blocking put - if queue is full, skip this client
            queue.put_nowait(event)
            sent_count += 1
        except asyncio.QueueFull:
            logger.warning(f"SSE queue full for client {client_id}, dropping event")
        except Exception as e:
            logger.error(f"Error broadcasting to client {client_id}: {e}")
    
    if sent_count > 0:
        logger.debug(f"Broadcasted event '{event.get('type')}' to {sent_count} clients for execution {execution_id}")
    
    return sent_count


# ============================================================================
# SSE EVENT PUBLISHING
# ============================================================================

async def publish_execution_event(execution_id: str, event: Dict[str, Any]):
    """
    Publish an event to all SSE clients listening to this execution.
    
    Args:
        execution_id: Execution UUID
        event: Event data dictionary
    """
    # Add timestamp if not present
    if "timestamp" not in event:
        event["timestamp"] = datetime.utcnow().isoformat()
    
    # Publish to execution-level clients (if any)
    clients_to_remove = []
    if execution_id in _sse_event_queues:
        for client_id, queue in _sse_event_queues[execution_id].items():
            try:
                # Non-blocking put
                queue.put_nowait(event)
                
                # Update activity tracking
                if client_id in _sse_connections:
                    _sse_connections[client_id]["last_activity"] = datetime.utcnow()
            
            except asyncio.QueueFull:
                logger.warning(f"Queue full for SSE client {client_id}, dropping event")
            
            except Exception as e:
                logger.error(f"Error publishing to SSE client {client_id}: {e}")
                clients_to_remove.append(client_id)
        
        # Clean up dead clients
        for client_id in clients_to_remove:
            _cleanup_sse_client(execution_id, client_id)
    
    # ALSO broadcast to workflow-level streams (for trigger workflows)
    try:
        from app.database.session import SessionLocal
        db = SessionLocal()
        try:
            execution = db.query(Execution).filter(Execution.id == execution_id).first()
            if execution:
                logger.info(f"🔍 Checking workflow-level broadcast: workflow_id={execution.workflow_id}, has_listeners={execution.workflow_id in _workflow_event_queues}")
                if execution.workflow_id in _workflow_event_queues:
                    # Add execution_id to event for workflow-level listeners
                    event_with_exec_id = {**event, "execution_id": execution_id}
                    
                    # Broadcast to workflow-level listeners
                    workflow_clients_to_remove = []
                    for client_id, queue in _workflow_event_queues[execution.workflow_id].items():
                        try:
                            logger.info(f"🎯 Putting {event['type']} into queue for workflow client {client_id}, queue size: {queue.qsize()}")
                            queue.put_nowait(event_with_exec_id)
                            logger.info(f"📤 Broadcasted {event['type']} to workflow-level client {client_id}, new queue size: {queue.qsize()}")
                        except asyncio.QueueFull:
                            logger.warning(f"Workflow-level queue full for client {client_id}")
                        except Exception as e:
                            logger.error(f"Error broadcasting to workflow client {client_id}: {e}")
                            workflow_clients_to_remove.append(client_id)
                    
                    # Clean up dead workflow clients
                    for client_id in workflow_clients_to_remove:
                        _cleanup_workflow_sse_client(execution.workflow_id, client_id)
                    
                    logger.info(f"📡 Broadcasted {event['type']} to {len(_workflow_event_queues[execution.workflow_id])} workflow-level clients")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to broadcast to workflow-level streams: {e}", exc_info=True)


def _cleanup_sse_client(execution_id: str, client_id: str):
    """Clean up SSE client resources."""
    if execution_id in _sse_event_queues and client_id in _sse_event_queues[execution_id]:
        del _sse_event_queues[execution_id][client_id]
        
        # Clean up empty execution dict
        if not _sse_event_queues[execution_id]:
            del _sse_event_queues[execution_id]
    
    if client_id in _sse_connections:
        del _sse_connections[client_id]
        logger.debug(f"Cleaned up SSE client {client_id}")


def _cleanup_workflow_sse_client(workflow_id: str, client_id: str):
    """Clean up workflow-level SSE client resources."""
    if workflow_id in _workflow_event_queues and client_id in _workflow_event_queues[workflow_id]:
        del _workflow_event_queues[workflow_id][client_id]
        
        # Clean up empty workflow dict
        if not _workflow_event_queues[workflow_id]:
            del _workflow_event_queues[workflow_id]
    
    if client_id in _sse_connections:
        del _sse_connections[client_id]
        logger.debug(f"Cleaned up workflow SSE client {client_id}")


# ============================================================================
# SSE STREAMING ENDPOINT
# ============================================================================

@router.get(
    "/{execution_id}/stream",
    summary="Stream execution events (SSE)",
    description="Server-Sent Events endpoint for real-time execution updates"
)
async def stream_execution_events(
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Stream real-time execution events using Server-Sent Events (SSE).
    
    This endpoint keeps the connection open and streams events as they occur:
    - Node start/completion events
    - Progress updates
    - Error notifications
    - Execution status changes
    - Heartbeats (every 30s to keep connection alive)
    
    **Event Types:**
    - `execution_start`: Execution begins
    - `node_start`: Node execution starts
    - `node_complete`: Node completes successfully
    - `node_error`: Node fails
    - `execution_complete`: Execution finishes
    - `execution_failed`: Execution fails
    - `execution_stopped`: Execution stopped by user
    - `progress_update`: Progress percentage update
    - `heartbeat`: Keep-alive message
    
    **Example Event:**
    ```
    data: {"type": "node_complete", "node_id": "node-1", "status": "success"}
    ```
    
    Args:
        execution_id: Execution UUID to stream
        db: Database session
        current_user: Authenticated user
    
    Returns:
        StreamingResponse with text/event-stream content type
    
    Raises:
        404: Execution not found
    """
    # Verify execution exists
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found"
        )
    
    # Generate unique client ID
    client_id = str(uuid4())
    
    # Check connection limits
    if execution_id in _sse_event_queues:
        current_connections = len(_sse_event_queues[execution_id])
        if current_connections >= SSE_CONFIG["max_connections_per_execution"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Max SSE connections reached for this execution ({SSE_CONFIG['max_connections_per_execution']})"
            )
    
    # Create client queue and register connection
    if execution_id not in _sse_event_queues:
        _sse_event_queues[execution_id] = {}
    
    client_queue = asyncio.Queue(maxsize=SSE_CONFIG["max_queue_size"])
    _sse_event_queues[execution_id][client_id] = client_queue
    
    _sse_connections[client_id] = {
        "execution_id": execution_id,
        "connected_at": datetime.utcnow(),
        "last_activity": datetime.utcnow(),
        "user_id": current_user.id
    }
    
    logger.info(f"SSE client {client_id} connected to execution {execution_id}")
    
    async def event_generator():
        """Generate SSE events."""
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'client_id': client_id, 'execution_id': execution_id})}\n\n"
            
            # Send current execution state
            initial_event = {
                "type": "execution_start",
                "execution_id": execution_id,
                "status": execution.status,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
            }
            yield f"data: {json.dumps(initial_event)}\n\n"
            
            # If execution has node results, send them as node_complete events
            if execution.node_results:
                node_results = execution.node_results
                total_nodes = len(node_results)
                completed_nodes = 0
                
                # Send individual node completion events
                for node_id, result in node_results.items():
                    # Check if node is currently executing (running state)
                    is_running = (
                        result.get("metadata", {}).get("status") == "executing"
                        and result.get("completed_at") is None
                    )
                    
                    if is_running:
                        # Node is currently running - send node_start event
                        node_event = {
                            "type": "node_start",
                            "node_id": node_id,
                            "status": "executing",
                            "started_at": result.get("started_at"),
                        }
                    elif result.get("success"):
                        # Node completed successfully
                        node_event = {
                            "type": "node_complete",
                            "node_id": node_id,
                            "status": "completed",
                            "completed_at": result.get("completed_at"),
                            "error": result.get("error"),
                            "outputs": result.get("outputs", {})  # Include node outputs for preview
                        }
                        completed_nodes += 1
                    else:
                        # Node failed
                        node_event = {
                            "type": "node_failed",
                            "node_id": node_id,
                            "status": "failed",
                            "completed_at": result.get("completed_at"),
                            "error": result.get("error"),
                            "outputs": result.get("outputs", {})
                        }
                    
                    yield f"data: {json.dumps(node_event)}\n\n"
                
                # Send progress summary
                progress_event = {
                    "type": "progress_update",
                    "execution_id": execution_id,
                    "total_nodes": total_nodes,
                    "completed_nodes": completed_nodes,
                    "progress_percentage": round((completed_nodes / total_nodes * 100) if total_nodes > 0 else 0, 2)
                }
                yield f"data: {json.dumps(progress_event)}\n\n"
            
            # If execution is already complete, send terminal event
            if execution.status in ["completed", "failed", "stopped"]:
                # Map status to event type (match orchestrator naming)
                event_type_map = {
                    "completed": "execution_complete",
                    "failed": "execution_failed",
                    "stopped": "execution_stopped"
                }
                terminal_event = {
                    "type": event_type_map.get(execution.status, f"execution_{execution.status}"),
                    "execution_id": execution_id,
                    "status": execution.status,
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None
                }
                yield f"data: {json.dumps(terminal_event)}\n\n"
                
                # Small delay to ensure client receives the message before connection closes
                await asyncio.sleep(0.1)
                
                logger.info(f"Execution {execution_id} already {execution.status}, closing SSE after sending final state")
                return
            
            # Stream events from queue
            last_heartbeat = datetime.utcnow()
            
            while True:
                try:
                    # Wait for event with timeout
                    event = await asyncio.wait_for(
                        client_queue.get(),
                        timeout=SSE_CONFIG["heartbeat_interval"]
                    )
                    
                    yield f"data: {json.dumps(event)}\n\n"
                    
                    # Check if this is a terminal event
                    if event.get("type") in ["execution_complete", "execution_failed", "execution_stopped"]:
                        logger.info(f"Closing SSE stream for {execution_id}: {event.get('type')}")
                        break
                
                except asyncio.TimeoutError:
                    # Send heartbeat
                    # Query execution status from DB (create new session for async context)
                    from app.database.session import SessionLocal
                    heartbeat_db = SessionLocal()
                    try:
                        current_execution = heartbeat_db.query(Execution).filter(
                            Execution.id == execution_id
                        ).first()
                        
                        if not current_execution:
                            logger.warning(f"Execution {execution_id} not found during heartbeat")
                            break
                        
                        heartbeat = {
                            "type": "heartbeat",
                            "execution_id": execution_id,
                            "status": current_execution.status,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        yield f"data: {json.dumps(heartbeat)}\n\n"
                        
                        last_heartbeat = datetime.utcnow()
                        
                        # Check if execution is done
                        if current_execution.status in ["completed", "failed", "stopped"]:
                            final_event = {
                                "type": f"execution_{current_execution.status}",
                                "execution_id": execution_id,
                                "status": current_execution.status,
                                "message": f"Execution {current_execution.status}"
                            }
                            yield f"data: {json.dumps(final_event)}\n\n"
                            break
                    finally:
                        heartbeat_db.close()
        
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for client {client_id}")
        
        except Exception as e:
            logger.error(f"Error in SSE stream for {execution_id}: {e}", exc_info=True)
            error_event = {
                "type": "error",
                "execution_id": execution_id,
                "error": str(e)
            }
            yield f"data: {json.dumps(error_event)}\n\n"
        
        finally:
            # Clean up client resources
            _cleanup_sse_client(execution_id, client_id)
            logger.info(f"SSE client {client_id} disconnected from execution {execution_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get(
    "/workflow/{workflow_id}/stream",
    summary="Stream workflow events (SSE) for monitoring workflows",
    description="Server-Sent Events endpoint for real-time workflow monitoring (for trigger workflows)"
)
async def stream_workflow_events(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Stream real-time workflow events using Server-Sent Events (SSE).
    
    This endpoint is designed for monitoring workflows (workflows with triggers).
    It connects at the workflow level and receives events from ALL executions
    of this workflow.
    
    This endpoint keeps the connection open and streams events as they occur:
    - Execution start/completion events
    - Node start/completion events (from all executions)
    - Progress updates
    - Error notifications
    - Heartbeats (every 30s to keep connection alive)
    
    **Event Types:**
    - `execution_start`: Execution begins
    - `node_start`: Node execution starts
    - `node_complete`: Node completes successfully
    - `node_error`: Node fails
    - `execution_complete`: Execution finishes
    - `execution_failed`: Execution fails
    - `execution_stopped`: Execution stopped by user
    - `progress_update`: Progress percentage update
    - `heartbeat`: Keep-alive message
    
    **Example Event:**
    ```
    data: {"type": "node_complete", "execution_id": "exec-123", "node_id": "node-1", "status": "success"}
    ```
    
    Args:
        workflow_id: Workflow UUID to stream
        db: Database session
        current_user: Authenticated user
    
    Returns:
        StreamingResponse with text/event-stream content type
    
    Raises:
        404: Workflow not found
    """
    # Verify workflow exists
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    # Generate unique client ID
    client_id = str(uuid4())
    
    # Check connection limits
    if workflow_id in _workflow_event_queues:
        current_connections = len(_workflow_event_queues[workflow_id])
        if current_connections >= SSE_CONFIG["max_connections_per_execution"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Max SSE connections reached for this workflow ({SSE_CONFIG['max_connections_per_execution']})"
            )
    
    # Create client queue and register connection
    if workflow_id not in _workflow_event_queues:
        _workflow_event_queues[workflow_id] = {}
    
    client_queue = asyncio.Queue(maxsize=SSE_CONFIG["max_queue_size"])
    _workflow_event_queues[workflow_id][client_id] = client_queue
    
    _sse_connections[client_id] = {
        "workflow_id": workflow_id,
        "connected_at": datetime.utcnow(),
        "last_activity": datetime.utcnow(),
        "user_id": current_user.id
    }
    
    logger.info(f"SSE client {client_id} connected to workflow {workflow_id}")
    
    async def event_generator():
        """Generate SSE events for workflow-level monitoring."""
        # Create a dedicated DB session for this generator (endpoint's db closes immediately)
        from app.database.session import SessionLocal
        gen_db = SessionLocal()
        
        try:
            # Send initial connection event
            conn_event = {'type': 'connected', 'client_id': client_id, 'workflow_id': workflow_id}
            logger.info(f"📡 Sending initial connection event to client {client_id}: {conn_event}")
            yield f"data: {json.dumps(conn_event)}\n\n"
            await asyncio.sleep(0)  # Force flush
            
            # Send current workflow state
            from app.schemas.workflow import WorkflowDefinition, NodeCategory
            try:
                # Re-query workflow with our generator's session
                current_workflow = gen_db.query(Workflow).filter(Workflow.id == workflow_id).first()
                if current_workflow:
                    workflow_def = WorkflowDefinition(**current_workflow.workflow_data)
                    has_triggers = any(node.category == NodeCategory.TRIGGERS for node in workflow_def.nodes)
                    
                    initial_event = {
                        "type": "workflow_monitoring_start",
                        "workflow_id": workflow_id,
                        "workflow_name": current_workflow.name,
                        "has_triggers": has_triggers,
                        "status": current_workflow.status,
                    }
                    yield f"data: {json.dumps(initial_event)}\n\n"
            except Exception as e:
                logger.warning(f"Failed to send initial workflow state: {e}", exc_info=True)
            
            # Get recent running executions for this workflow
            running_executions = gen_db.query(Execution).filter(
                Execution.workflow_id == workflow_id,
                Execution.status == "running"
            ).all()
            
            if running_executions:
                for execution in running_executions:
                    exec_event = {
                        "type": "execution_start",
                        "execution_id": execution.id,
                        "workflow_id": workflow_id,
                        "status": execution.status,
                        "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    }
                    yield f"data: {json.dumps(exec_event)}\n\n"
                    
                    # Send node results if available
                    if execution.node_results:
                        for node_id, result in execution.node_results.items():
                            # Check if node is currently executing (running state)
                            is_running = (
                                result.get("metadata", {}).get("status") == "executing"
                                and result.get("completed_at") is None
                            )
                            
                            if is_running:
                                # Node is currently running - send node_start event
                                node_event = {
                                    "type": "node_start",
                                    "execution_id": execution.id,
                                    "node_id": node_id,
                                    "status": "executing",
                                    "started_at": result.get("started_at"),
                                }
                            elif result.get("success"):
                                # Node completed successfully
                                node_event = {
                                    "type": "node_complete",
                                    "execution_id": execution.id,
                                    "node_id": node_id,
                                    "status": "completed",
                                    "completed_at": result.get("completed_at"),
                                    "error": result.get("error"),
                                    "outputs": result.get("outputs", {})
                                }
                            else:
                                # Node failed
                                node_event = {
                                    "type": "node_failed",
                                    "execution_id": execution.id,
                                    "node_id": node_id,
                                    "status": "failed",
                                    "completed_at": result.get("completed_at"),
                                    "error": result.get("error"),
                                    "outputs": result.get("outputs", {})
                                }
                            
                            yield f"data: {json.dumps(node_event)}\n\n"
            
            # Stream events from queue
            last_heartbeat = datetime.utcnow()
            
            while True:
                try:
                    # Wait for event with timeout
                    event = await asyncio.wait_for(
                        client_queue.get(),
                        timeout=SSE_CONFIG["heartbeat_interval"]
                    )
                    
                    logger.info(f"🔥 Yielding workflow event to SSE client {client_id}: {event.get('type')}, node_id={event.get('node_id')}")
                    event_data = f"data: {json.dumps(event)}\n\n"
                    logger.info(f"🔥 Event data to yield: {repr(event_data[:100])}")
                    yield event_data
                    await asyncio.sleep(0)  # Force event loop to flush
                
                except asyncio.TimeoutError:
                    # Send heartbeat
                    from app.database.session import SessionLocal
                    heartbeat_db = SessionLocal()
                    try:
                        current_workflow = heartbeat_db.query(Workflow).filter(
                            Workflow.id == workflow_id
                        ).first()
                        
                        if not current_workflow:
                            logger.warning(f"Workflow {workflow_id} not found during heartbeat")
                            break
                        
                        # Count running executions
                        running_count = heartbeat_db.query(Execution).filter(
                            Execution.workflow_id == workflow_id,
                            Execution.status == "running"
                        ).count()
                        
                        heartbeat = {
                            "type": "heartbeat",
                            "workflow_id": workflow_id,
                            "status": current_workflow.status,
                            "running_executions": running_count,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        yield f"data: {json.dumps(heartbeat)}\n\n"
                        
                        last_heartbeat = datetime.utcnow()
                    finally:
                        heartbeat_db.close()
        
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for client {client_id}")
        
        except Exception as e:
            logger.error(f"Error in SSE stream for workflow {workflow_id}: {e}", exc_info=True)
            error_event = {
                "type": "error",
                "workflow_id": workflow_id,
                "error": str(e)
            }
            yield f"data: {json.dumps(error_event)}\n\n"
        
        finally:
            # Close the generator's database session
            gen_db.close()
            # Clean up client resources
            _cleanup_workflow_sse_client(workflow_id, client_id)
            logger.info(f"SSE client {client_id} disconnected from workflow {workflow_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# ============================================================================
# SSE MANAGEMENT ENDPOINTS
# ============================================================================

@router.get(
    "/sse/stats",
    summary="Get SSE connection statistics",
    description="Get current SSE connection statistics for monitoring"
)
async def get_sse_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get SSE connection statistics.
    
    Returns:
        Connection statistics including active connections, connections per execution, etc.
    """
    stats = {
        "total_connections": len(_sse_connections),
        "total_executions": len(_sse_event_queues),
        "connections_per_execution": {
            exec_id: len(clients)
            for exec_id, clients in _sse_event_queues.items()
        },
        "config": SSE_CONFIG
    }
    
    return stats


@router.post(
    "/sse/test/{execution_id}",
    summary="Test SSE event publishing",
    description="Send a test event to SSE clients (for testing only)"
)
async def test_sse_event(
    execution_id: str,
    event_type: str = "test",
    message: str = "Test event",
    current_user: User = Depends(get_current_active_user)
):
    """
    Send a test event to all SSE clients listening to an execution.
    
    Useful for testing SSE integration.
    
    Args:
        execution_id: Execution UUID
        event_type: Event type (default: "test")
        message: Event message
        current_user: Authenticated user
    
    Returns:
        Status of event publishing
    """
    test_event = {
        "type": event_type,
        "execution_id": execution_id,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await publish_execution_event(execution_id, test_event)
    
    clients_count = 0
    if execution_id in _sse_event_queues:
        clients_count = len(_sse_event_queues[execution_id])
    
    return {
        "success": True,
        "message": f"Test event published to {clients_count} client(s)",
        "event": test_event
    }


# ============================================================================
# HELPER FUNCTIONS FOR ORCHESTRATOR INTEGRATION
# ============================================================================

async def notify_node_start(execution_id: str, node_id: str, node_index: int, total_nodes: int):
    """Notify SSE clients that a node has started."""
    event = {
        "type": "node_start",
        "execution_id": execution_id,
        "node_id": node_id,
        "node_index": node_index,
        "total_nodes": total_nodes,
        "progress_percentage": round((node_index / total_nodes * 100) if total_nodes > 0 else 0, 2)
    }
    await publish_execution_event(execution_id, event)


async def notify_node_complete(execution_id: str, node_id: str, node_index: int, total_nodes: int, outputs: Optional[Dict] = None):
    """Notify SSE clients that a node has completed."""
    event = {
        "type": "node_complete",
        "execution_id": execution_id,
        "node_id": node_id,
        "node_index": node_index,
        "total_nodes": total_nodes,
        "progress_percentage": round(((node_index + 1) / total_nodes * 100) if total_nodes > 0 else 0, 2),
        "outputs": outputs
    }
    await publish_execution_event(execution_id, event)


async def notify_node_error(execution_id: str, node_id: str, error_message: str):
    """Notify SSE clients that a node has failed."""
    event = {
        "type": "node_error",
        "execution_id": execution_id,
        "node_id": node_id,
        "error": error_message
    }
    await publish_execution_event(execution_id, event)


async def notify_execution_complete(execution_id: str, final_outputs: Optional[Dict] = None):
    """Notify SSE clients that execution has completed."""
    event = {
        "type": "execution_complete",
        "execution_id": execution_id,
        "status": "completed",
        "final_outputs": final_outputs
    }
    await publish_execution_event(execution_id, event)


async def notify_execution_failed(execution_id: str, error_message: str):
    """Notify SSE clients that execution has failed."""
    event = {
        "type": "execution_failed",
        "execution_id": execution_id,
        "status": "failed",
        "error": error_message
    }
    await publish_execution_event(execution_id, event)


async def notify_execution_stopped(execution_id: str):
    """Notify SSE clients that execution has been stopped."""
    event = {
        "type": "execution_stopped",
        "execution_id": execution_id,
        "status": "stopped",
        "message": "Execution stopped by user"
    }
    await publish_execution_event(execution_id, event)


# ============================================================================
# RETRY FROM CHECKPOINT ENDPOINTS
# ============================================================================

@router.get(
    "/{execution_id}/retry-info",
    summary="Get retry information for an execution",
    description="Check if an execution can be retried and what nodes would be skipped"
)
async def get_retry_info(
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Get retry information for an execution.
    
    Returns:
    - can_retry: Whether the execution can be retried
    - completed_nodes: List of nodes that completed successfully (will be skipped)
    - failed_nodes: List of nodes that failed
    - has_structure_changes: Whether workflow structure changed since execution
    - structure_warnings: Specific warnings about structure changes
    
    Args:
        execution_id: Execution UUID
        db: Database session
        current_user: Authenticated user
    
    Returns:
        Retry information dict
    
    Raises:
        404: Execution not found
    """
    from app.core.execution.orchestrator import WorkflowOrchestrator
    
    orchestrator = WorkflowOrchestrator(db)
    retry_info = orchestrator.get_retry_info(execution_id)
    
    if not retry_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found"
        )
    
    return retry_info


@router.post(
    "/{execution_id}/retry",
    summary="Retry execution from checkpoint",
    description="Create a new execution that skips already-completed nodes"
)
async def retry_execution(
    execution_id: str,
    force: bool = Query(
        default=False,
        description="Force retry even if workflow structure changed"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_smart)
):
    """
    Retry a failed execution from where it stopped.
    
    This creates a NEW execution that:
    - Uses the CURRENT workflow definition (so you can fix issues)
    - Skips nodes that already completed successfully
    - Only runs pending/failed nodes
    
    **Use Case:**
    1. Execution fails at node X
    2. User fixes node X configuration
    3. User clicks "Retry"
    4. System skips all nodes before X and resumes from X
    
    **Important:**
    - Uses CURRENT workflow config (not snapshot) - allows you to fix issues
    - If workflow structure changed significantly, returns warnings
    - Set `force=true` to retry despite structure changes
    
    Args:
        execution_id: Original execution ID to retry from
        force: If True, retry even if workflow structure changed
        db: Database session
        current_user: Authenticated user
    
    Returns:
        - execution_id: New execution ID (null if requires confirmation)
        - skipped_nodes: List of node IDs that were skipped
        - warnings: Structure change warnings (if any)
        - requires_confirmation: True if user should confirm due to warnings
    
    Raises:
        400: Execution cannot be retried
        404: Execution not found
    """
    import asyncio
    from app.core.execution.orchestrator import WorkflowOrchestrator
    
    # Get frontend origin from request headers (for email links, etc.)
    frontend_origin = None
    # Note: We'd need to pass Request to get headers, but for now we'll skip this
    
    orchestrator = WorkflowOrchestrator(db)
    
    try:
        # Step 1: Prepare the retry (validation + create execution record)
        result = await orchestrator.retry_from_checkpoint(
            original_execution_id=execution_id,
            started_by=str(current_user.id),
            frontend_origin=frontend_origin,
            force=force,
            prepare_only=True  # Don't execute yet, just prepare
        )
        
        # If requires confirmation (structure changed), return 200 with flag
        if result.get("requires_confirmation"):
            return {
                "success": False,
                "requires_confirmation": True,
                "execution_id": None,
                "skipped_nodes": [],
                "warnings": result.get("warnings", []),
                "message": "Workflow structure has changed. Review warnings and retry with force=true to proceed."
            }
        
        new_execution_id = result.get("execution_id")
        skipped_nodes = result.get("skipped_nodes", [])
        warnings = result.get("warnings", [])
        
        # Step 2: Run execution in background (returns immediately)
        async def run_retry_background():
            """Background task to execute retry"""
            try:
                # Small delay to allow SSE connection to establish first
                await asyncio.sleep(0.3)
                
                # Get fresh orchestrator for background task
                from app.database.session import SessionLocal
                background_db = SessionLocal()
                try:
                    background_orchestrator = WorkflowOrchestrator(background_db)
                    await background_orchestrator.run_prepared_retry(result)
                finally:
                    background_db.close()
            except Exception as e:
                logger.error(f"Background retry execution {new_execution_id} failed: {e}", exc_info=True)
        
        # Start background task
        asyncio.create_task(run_retry_background())
        
        logger.info(f"Retry execution started in background: {new_execution_id}")
        
        return {
            "success": True,
            "requires_confirmation": False,
            "execution_id": new_execution_id,
            "skipped_nodes": skipped_nodes,
            "warnings": warnings,
            "message": f"Retry started. Skipping {len(skipped_nodes)} completed node(s)."
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Retry failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retry failed: {str(e)}"
        )