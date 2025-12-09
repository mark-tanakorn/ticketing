"""
Email Interaction API Endpoints

Handles submission and retrieval of email approval interactions.
"""

import logging
import base64
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.database.models.email_interaction import EmailInteraction
from app.utils.timezone import get_local_now

logger = logging.getLogger(__name__)

router = APIRouter()


class EmailInteractionSubmission(BaseModel):
    """Request model for email approval submission"""
    token: str
    action: str  # "approve" or "reject"
    edited_draft: dict  # Edited email draft with recipient, subject, body


class EmailInteractionResponse(BaseModel):
    """Response model for interaction retrieval"""
    interaction_id: str
    status: str
    original_draft: dict
    expires_at: str
    time_remaining_seconds: int
    is_expired: bool


@router.get("/{interaction_id}", response_model=EmailInteractionResponse)
async def get_email_interaction(
    interaction_id: str,
    token: str = Query(..., description="Security token for verification"),
    db: Session = Depends(get_db),
    response: Response = None
):
    """
    Get email interaction details for review
    
    This endpoint is called when user opens the review link.
    It returns the draft content and interaction status.
    """
    # Add CORS headers explicitly
    if response:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
    logger.info(f"📥 Retrieving interaction: {interaction_id}")
    
    # Find interaction
    interaction = db.query(EmailInteraction).filter(
        EmailInteraction.id == interaction_id,
        EmailInteraction.token == token
    ).first()
    
    if not interaction:
        logger.warning(f"❌ Interaction not found or invalid token: {interaction_id}")
        raise HTTPException(status_code=404, detail="Interaction not found or invalid token")
    
    # Check if expired
    if interaction.is_expired:
        logger.warning(f"⏰ Interaction expired: {interaction_id}")
        interaction.mark_expired()
        db.commit()
        raise HTTPException(status_code=410, detail="Interaction has expired")
    
    # Check if already processed
    if interaction.status != "pending":
        logger.warning(f"⚠️ Interaction already processed: {interaction_id}, status={interaction.status}")
        raise HTTPException(status_code=409, detail=f"Interaction already {interaction.status}")
    
    logger.info(f"✅ Interaction retrieved: {interaction_id}, expires in {interaction.time_remaining_seconds}s")
    
    return EmailInteractionResponse(
        interaction_id=interaction.id,
        status=interaction.status,
        original_draft=interaction.original_draft,
        expires_at=interaction.expires_at.isoformat(),
        time_remaining_seconds=interaction.time_remaining_seconds,
        is_expired=interaction.is_expired
    )


@router.post("/{interaction_id}/submit")
async def submit_email_interaction(
    interaction_id: str,
    submission: EmailInteractionSubmission,
    request: Request,
    db: Session = Depends(get_db),
    response: Response = None
):
    """
    Submit email approval decision
    
    This endpoint is called when user clicks "Approve" or "Reject".
    It updates the database and resumes the paused workflow.
    """
    # Add CORS headers explicitly
    if response:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    logger.info(f"📤 Submitting interaction: {interaction_id}, action={submission.action}")
    
    # Find interaction
    interaction = db.query(EmailInteraction).filter(
        EmailInteraction.id == interaction_id,
        EmailInteraction.token == submission.token
    ).first()
    
    if not interaction:
        logger.warning(f"❌ Interaction not found or invalid token: {interaction_id}")
        raise HTTPException(status_code=404, detail="Interaction not found or invalid token")
    
    # Check if expired
    if interaction.is_expired:
        logger.warning(f"⏰ Interaction expired: {interaction_id}")
        interaction.mark_expired()
        db.commit()
        raise HTTPException(status_code=410, detail="Interaction has expired")
    
    # Check if already processed
    if interaction.status != "pending":
        logger.warning(f"⚠️ Interaction already processed: {interaction_id}, status={interaction.status}")
        raise HTTPException(status_code=409, detail=f"Interaction already {interaction.status}")
    
    # Get user agent and IP for audit
    user_agent = request.headers.get("user-agent")
    # Get real IP (considering proxies)
    ip_address = request.headers.get("x-forwarded-for", request.client.host if request.client else None)
    if ip_address and "," in ip_address:
        ip_address = ip_address.split(",")[0].strip()
    
    # Determine action
    approved = submission.action.lower() in ("approve", "confirm", "send", "yes")
    
    if approved:
        # Mark as approved with edited draft
        interaction.mark_approved(
            edited_draft=submission.edited_draft,
            user_agent=user_agent,
            ip_address=ip_address
        )
        logger.info(f"✅ Interaction approved: {interaction_id}")
    else:
        # Mark as rejected
        interaction.mark_rejected(
            user_agent=user_agent,
            ip_address=ip_address
        )
        logger.info(f"❌ Interaction rejected: {interaction_id}")
    
    db.commit()
    
    # Resume workflow execution
    try:
        await _resume_workflow(interaction, submission.edited_draft if approved else None, db)
    except Exception as e:
        logger.error(f"❌ Failed to resume workflow: {e}", exc_info=True)
        # Don't fail the request - interaction is already saved
        # Workflow can be resumed later via cleanup job
    
    return {
        "success": True,
        "message": "Email approved and sent" if approved else "Email draft rejected",
        "interaction_id": interaction_id,
        "action": submission.action,
        "approved": approved,
        "status": interaction.status
    }


async def _resume_workflow(interaction: EmailInteraction, edited_draft: Optional[dict], db: Session):
    """
    Resume paused workflow execution
    
    This function retrieves the active executor for the workflow and resumes it
    with the approval result.
    """
    try:
        logger.info(f"🔄 Resuming workflow: execution_id={interaction.execution_id}")
        
        # Import here to avoid circular dependency
        from app.core.execution.orchestrator import get_active_executor
        from app.core.nodes.builtin.communication.email_approval import EmailApprovalNode
        from app.core.nodes.registry import NodeRegistry
        
        # Get active executor
        executor = get_active_executor(interaction.workflow_id)
        
        if not executor:
            logger.warning(f"⚠️ No active executor found for workflow: {interaction.workflow_id}")
            # Workflow might have timed out or been stopped
            return
        
        # Get the approval node to call its interaction handler
        node_class = NodeRegistry.get("email_approval")
        if not node_class:
            logger.error(f"❌ Email approval node not found in registry")
            return
        
        # Create a temporary node instance to call handle_interaction
        # Note: We need the node config, which we can get from the workflow definition
        from app.database.models.workflow import Workflow
        workflow_db = db.query(Workflow).filter(Workflow.id == interaction.workflow_id).first()
        
        if not workflow_db:
            logger.error(f"❌ Workflow not found: {interaction.workflow_id}")
            return
        
        # Find the node config in workflow
        from app.schemas.workflow import WorkflowDefinition, NodeConfiguration
        workflow_def = WorkflowDefinition(**workflow_db.workflow_data)
        node_config = None
        
        for node in workflow_def.nodes:
            if node.node_id == interaction.node_id:
                node_config = node
                break
        
        if not node_config:
            logger.error(f"❌ Node config not found: {interaction.node_id}")
            return
        
        # Instantiate node
        node_instance = node_class(node_config)
        
        # Build continuation data (what the node needs to send email)
        continuation = {
            "original_draft": interaction.original_draft,
            "smtp_config": interaction.smtp_config,
            "auto_send": True  # Always send after approval for now
        }
        
        # Determine action
        action = "approve" if edited_draft else "reject"
        form = edited_draft or {}
        
        # Call the node's interaction handler
        result = await node_instance.handle_interaction(
            action=action,
            form=form,
            continuation=continuation,
            payload=None
        )
        
        logger.info(f"✅ Interaction handled by node: {result}")
        
        # Update interaction with send status
        if result.get("sent"):
            interaction.mark_sent()
            db.commit()
        
        # Update executor context with the final node outputs
        # The ParallelExecutor will handle resuming execution automatically
        from app.utils.timezone import get_local_now
        from app.core.execution.context import NodeExecutionResult
        
        context = executor.context
        
        # Update node outputs (replace the _await marker with actual result)
        context.node_outputs[interaction.node_id] = result
        
        # Update node result with completion info
        context.node_results[interaction.node_id] = NodeExecutionResult(
            node_id=interaction.node_id,
            success=result.get("success", True),
            outputs=result,
            error=result.get("error"),
            started_at=context.node_results[interaction.node_id].started_at if interaction.node_id in context.node_results else get_local_now(),
            completed_at=get_local_now(),
            metadata={
                "interaction_completed": True,
                "interaction_id": interaction.id,
                "action": action
            }
        )
        
        # Remove from pending interactions
        if interaction.node_id in context.pending_interactions:
            del context.pending_interactions[interaction.node_id]
        
        # Mark node as completed in the graph (for accurate progress tracking)
        if executor.graph and interaction.node_id in executor.graph.nodes:
            executor.graph.mark_node_completed(interaction.node_id)
            progress = executor.get_progress()
            logger.info(f"Progress updated: {progress.get('completed', 0)}/{progress.get('total_nodes', 0)} nodes completed")
        
        logger.info(f"✅ Node {interaction.node_id} marked as completed")
        
        # Broadcast node_complete event so UI updates
        try:
            from app.api.v1.endpoints.executions import publish_execution_event
            await publish_execution_event(context.execution_id, {
                "type": "node_complete",
                "node_id": interaction.node_id,
                "node_type": "email_approval",
                "node_name": f"Email Approval - {action}",
                "status": "completed",
                "outputs": result,
                "progress": executor.get_progress() if executor.graph else None
            })
        except Exception as e:
            logger.warning(f"Failed to broadcast node_complete event: {e}")
        
        # Resume execution - the executor will continue with dependent nodes
        executor.resume()
        
        logger.info(f"✅ Workflow resumed: execution_id={interaction.execution_id}")
    
    except Exception as e:
        logger.error(f"❌ Error resuming workflow: {e}", exc_info=True)
        raise


@router.get("/")
async def list_pending_interactions(
    execution_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List pending email interactions
    
    Useful for debugging and monitoring. Can filter by execution or workflow.
    """
    query = db.query(EmailInteraction).filter(EmailInteraction.status == "pending")
    
    if execution_id:
        query = query.filter(EmailInteraction.execution_id == execution_id)
    
    if workflow_id:
        query = query.filter(EmailInteraction.workflow_id == workflow_id)
    
    interactions = query.order_by(EmailInteraction.created_at.desc()).limit(100).all()
    
    return {
        "count": len(interactions),
        "interactions": [
            {
                "interaction_id": i.id,
                "execution_id": i.execution_id,
                "workflow_id": i.workflow_id,
                "status": i.status,
                "created_at": i.created_at.isoformat(),
                "expires_at": i.expires_at.isoformat(),
                "time_remaining_seconds": i.time_remaining_seconds,
                "is_expired": i.is_expired
            }
            for i in interactions
        ]
    }


@router.get("/{interaction_id}/attachments/{attachment_index}")
async def download_attachment(
    interaction_id: str,
    attachment_index: int,
    token: str = Query(..., description="Security token for verification"),
    db: Session = Depends(get_db),
):
    """
    Download an attachment from an email interaction
    
    Gmail-style approach: separate endpoint for attachment download
    """
    logger.info(f"📎 Downloading attachment {attachment_index} from interaction {interaction_id}")
    
    # Find interaction
    interaction = db.query(EmailInteraction).filter(
        EmailInteraction.id == interaction_id,
        EmailInteraction.token == token
    ).first()
    
    if not interaction:
        logger.warning(f"❌ Interaction not found or invalid token: {interaction_id}")
        raise HTTPException(status_code=404, detail="Interaction not found or invalid token")
    
    # Get attachments from original draft
    draft = interaction.original_draft
    attachments = draft.get("attachments", [])
    
    if attachment_index < 0 or attachment_index >= len(attachments):
        logger.warning(f"❌ Attachment index out of range: {attachment_index}")
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    attachment = attachments[attachment_index]
    
    # Get file path from attachment
    file_path_str = attachment.get("path") or attachment.get("file_path")
    
    if not file_path_str:
        logger.error(f"❌ Attachment has no file path: {attachment}")
        raise HTTPException(status_code=404, detail="Attachment file not found")
    
    file_path = Path(file_path_str)
    
    # Security check: make sure file exists and is readable
    if not file_path.exists():
        logger.error(f"❌ Attachment file does not exist: {file_path}")
        raise HTTPException(status_code=404, detail="Attachment file not found on server")
    
    # Read file content
    try:
        content = file_path.read_bytes()
        filename = attachment.get("filename", file_path.name)
        content_type = attachment.get("content_type", "application/octet-stream")
        
        logger.info(f"✅ Serving attachment: {filename} ({content_type}, {len(content)} bytes)")
        
        # Return as streaming response with proper headers for inline viewing
        return StreamingResponse(
            iter([content]),
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Expose-Headers": "Content-Disposition, Content-Type",
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        logger.error(f"❌ Error reading attachment file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to read attachment")

