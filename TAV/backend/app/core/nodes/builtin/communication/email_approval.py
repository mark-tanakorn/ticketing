"""
Email Approval Node - Human-in-the-loop email review and approval

Pauses workflow execution to allow human review and editing of email drafts before sending.
"""

import logging
import secrets
from uuid import uuid4
from typing import Dict, Any, List, Optional
from datetime import timedelta

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
from app.services.smtp_service import get_smtp_service, EMAIL_PROVIDERS
from app.utils.timezone import get_local_now

logger = logging.getLogger(__name__)


@register_node(
    node_type="email_approval",
    category=NodeCategory.COMMUNICATION,
    name="Email Approval",
    description="Human-in-the-loop email review and approval. Pauses workflow for user to review/edit draft before sending.",
    icon="fa-solid fa-user-check",
    version="1.0.0"
)
class EmailApprovalNode(Node):
    """
    Email Approval Node - Human-in-the-loop workflow pause for email review
    
    Flow:
    1. Receives draft from Email Composer node
    2. Generates secure review link with token
    3. Returns special _await marker (pauses workflow)
    4. User clicks link, reviews/edits draft, approves or rejects
    5. API validates token, updates database
    6. Workflow resumes and sends email if approved
    
    Security:
    - Cryptographically secure tokens (32 bytes)
    - Single-use tokens (invalidated after submission)
    - 6-hour expiration (configurable)
    - IP address and user agent tracking
    
    Features:
    - Edit subject, body, recipient before sending
    - Approve or reject draft
    - Workflow automatically resumes after decision
    - Sends email immediately after approval
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "draft",
                "type": PortType.UNIVERSAL,
                "display_name": "Email Draft",
                "description": "Email draft from Email Composer node",
                "required": True
            },
            {
                "name": "smtp_config",
                "type": PortType.UNIVERSAL,
                "display_name": "SMTP Configuration",
                "description": "SMTP configuration for sending (from composer or override)",
                "required": False
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "result",
                "type": PortType.UNIVERSAL,
                "display_name": "Approval Result",
                "description": "Result of approval process (approved/rejected, email sent status)",
            },
            {
                "name": "final_draft",
                "type": PortType.UNIVERSAL,
                "display_name": "Final Draft",
                "description": "Final email draft after user edits",
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        
        # Get provider options
        provider_options = [
            {"label": config["display_name"], "value": provider}
            for provider, config in EMAIL_PROVIDERS.items()
        ]
        
        return {
            "timeout_hours": {
                "type": "integer",
                "label": "Timeout (hours)",
                "description": "Hours until review link expires and workflow terminates",
                "required": False,
                "default": 6,
                "widget": "number",
                "min": 1,
                "max": 168,  # 1 week max
                "help": "After this time, the review link expires and workflow terminates"
            },
            "base_url": {
                "type": "string",
                "label": "Review URL Base",
                "description": "Base URL for review links (e.g., https://your-domain.com)",
                "required": False,
                "placeholder": "https://tav-engine.com",
                "widget": "text",
                "help": "Leave empty to use environment variable BASE_URL"
            },
            "auto_send": {
                "type": "boolean",
                "label": "Auto-send After Approval",
                "description": "Automatically send email after user approves",
                "required": False,
                "default": True,
                "help": "If enabled, email sends immediately after approval"
            },
            
            # Notification Email Settings
            "send_notification": {
                "type": "boolean",
                "label": "Send Notification Email",
                "description": "Send review link to specified email address",
                "required": False,
                "default": False,
                "help": "Enable to automatically email the review link to a reviewer"
            },
            "notification_email": {
                "type": "string",
                "label": "Send Notification To",
                "description": "Email address to send review link notification",
                "required": False,
                "placeholder": "reviewer@example.com",
                "widget": "text",
                "show_if": {"send_notification": True},
                "help": "This person will receive an email with the review link"
            },
            
            # Notification Email Authentication
            "auth_mode": {
                "type": "select",
                "label": "Notification Authentication",
                "description": "How to authenticate for sending notification emails",
                "required": False,
                "options": [
                    {"label": "Manual (Enter credentials)", "value": "manual"},
                    {"label": "From Credential", "value": "credential"}
                ],
                "default": "manual",
                "widget": "select",
                "show_if": {"send_notification": True}
            },
            
            # Credential mode
            "credential_id": {
                "type": "credential",
                "widget": "credential",
                "label": "Email Credential",
                "description": "Select saved email credential for notifications",
                "required": False,
                "visible_when": {"auth_mode": "credential", "send_notification": True}
            },
            
            # Manual mode
            "provider": {
                "type": "select",
                "label": "Email Provider",
                "description": "Select your email provider (SMTP auto-configured)",
                "required": False,
                "options": provider_options,
                "default": "gmail",
                "widget": "select",
                "help": "Gmail and Yahoo require app-specific passwords",
                "visible_when": {"auth_mode": "manual", "send_notification": True}
            },
            "from_email": {
                "type": "string",
                "label": "Notification From Email",
                "description": "Email address to send notifications from",
                "required": False,
                "placeholder": "notifications@example.com",
                "widget": "text",
                "visible_when": {"auth_mode": "manual", "send_notification": True}
            },
            "password": {
                "type": "string",
                "label": "Password",
                "description": "Email password or app-specific password",
                "required": False,
                "widget": "password",
                "help": "Gmail/Yahoo: Use app-specific password. Outlook: Regular password or app password.",
                "visible_when": {"auth_mode": "manual", "send_notification": True}
            },
            "from_name": {
                "type": "string",
                "label": "From Name (optional)",
                "description": "Display name for notification sender",
                "required": False,
                "placeholder": "TAV Workflow Bot",
                "widget": "text",
                "visible_when": {"auth_mode": "manual", "send_notification": True}
            },
            
            # Custom SMTP (only for custom provider in manual mode)
            "custom_smtp_server": {
                "type": "string",
                "label": "SMTP Server",
                "description": "Your SMTP server address",
                "required": False,
                "placeholder": "smtp.example.com",
                "widget": "text",
                "show_if": {"provider": "custom", "auth_mode": "manual", "send_notification": True}
            },
            "custom_smtp_port": {
                "type": "integer",
                "label": "SMTP Port",
                "description": "SMTP port (usually 587 or 465)",
                "required": False,
                "default": 587,
                "widget": "number",
                "show_if": {"provider": "custom", "auth_mode": "manual", "send_notification": True}
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """
        Execute email approval node
        
        This returns a special _await marker that tells the executor to pause the workflow.
        The executor detects this and waits for human interaction.
        """
        try:
            logger.info(f"📋 Email Approval Node executing: {self.node_id}")
            
            # Get draft from input
            draft = input_data.ports.get("draft")
            if not draft:
                return {
                    "result": {"success": False, "error": "No draft provided"},
                    "final_draft": None
                }
            
            if isinstance(draft, dict) and "error" in draft:
                return {
                    "result": {"success": False, "error": f"Draft has error: {draft['error']}"},
                    "final_draft": None
                }
            
            # Get SMTP config (from input or stored in config)
            smtp_config = input_data.ports.get("smtp_config", {})
            if not smtp_config:
                # Try to extract from draft itself
                smtp_config = draft.get("smtp_config", {})
            
            # Note: We allow drafts with missing recipient - user can add it in the review form
            # Just log a warning if recipient is missing
            if not draft.get("recipient"):
                logger.warning(f"⚠️ Draft missing recipient - user will need to add it in review form")
            
            # Generate interaction ID and secure token
            interaction_id = str(uuid4())
            token = secrets.token_urlsafe(32)  # 32 bytes = 256 bits of entropy
            
            logger.info(f"🔐 Generated interaction: {interaction_id}")
            
            # Get configuration
            timeout_hours = self.resolve_config(input_data, "timeout_hours", 6)
            base_url = self.resolve_config(input_data, "base_url", "")
            
            # BASE_URL Priority:
            # 1. Node config (user-specified in node settings)
            # 2. Auto-detect (from request Origin/Referer headers)
            # 3. Environment variable (BASE_URL if explicitly set)
            # 4. Fallback to localhost
            
            if base_url:
                # Priority 1: Node config - user explicitly configured
                logger.info(f"✅ Using node config base_url: {base_url}")
            elif input_data.frontend_origin:
                # Priority 2: Auto-detect from request headers
                base_url = input_data.frontend_origin
                logger.info(f"✅ Using auto-detected frontend origin: {base_url}")
            else:
                # Priority 3: Environment variable (if explicitly set, not default)
                from app.config import settings
                env_base_url = getattr(settings, "BASE_URL", None)
                
                # Check if BASE_URL was explicitly set (not auto-generated default)
                default_base_url = f"http://localhost:{settings.FRONTEND_PORT}"
                if env_base_url and env_base_url != default_base_url:
                    base_url = env_base_url
                    logger.info(f"✅ Using BASE_URL from environment: {base_url}")
                else:
                    # Priority 4: Fallback to localhost with configured port
                    base_url = default_base_url
                    logger.warning(f"⚠️ No BASE_URL configured, using default: {base_url}")
            
            # Create review URL
            review_url = f"{base_url}/review-email/{interaction_id}?token={token}"
            
            # Store interaction in database
            await self._store_interaction(
                interaction_id=interaction_id,
                token=token,
                execution_id=input_data.execution_id,
                workflow_id=input_data.workflow_id,
                node_id=input_data.node_id,
                original_draft=draft,
                smtp_config=smtp_config,
                timeout_hours=timeout_hours
            )
            
            logger.info(f"✅ Interaction stored, review URL: {review_url}")
            
            # Send notification email if enabled
            notification_sent = False
            if self.resolve_config(input_data, "send_notification", False):
                notification_result = await self._send_notification_email(
                    input_data=input_data,
                    review_url=review_url,
                    draft=draft,
                    timeout_hours=timeout_hours
                )
                notification_sent = notification_result.get("success", False)
                if notification_sent:
                    logger.info(f"📧 Notification email sent successfully")
                else:
                    logger.warning(f"⚠️ Failed to send notification email: {notification_result.get('error')}")
            
            # Return special _await marker to pause workflow
            return {
                "_await": "human_input",  # ← Special marker detected by executor
                "interaction_id": interaction_id,
                "interaction_type": "email_approval",
                "review_url": review_url,
                "notification_sent": notification_sent,
                "expires_at": (get_local_now() + timedelta(hours=timeout_hours)).isoformat(),
                "preview": {
                    "recipient": draft.get("recipient"),
                    "subject": draft.get("subject"),
                    "body_preview": draft.get("body", "")[:200] + "..." if len(draft.get("body", "")) > 200 else draft.get("body", "")
                },
                "status": "awaiting_approval",
                "message": f"Workflow paused. Review link expires in {timeout_hours} hours."
            }
        
        except Exception as e:
            logger.error(f"❌ Email Approval error: {e}", exc_info=True)
            return {
                "result": {"success": False, "error": str(e)},
                "final_draft": None
            }
    
    async def handle_interaction(
        self,
        action: str,
        form: Dict[str, Any],
        continuation: Dict[str, Any],
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle user interaction (approval/rejection)
        
        This method is called by the API endpoint when user submits the review form.
        It's part of the UI Interaction Contract pattern.
        
        Args:
            action: User action ("approve" or "reject")
            form: Form data with edited draft
            continuation: Stored interaction data
            payload: Optional additional payload
        
        Returns:
            Result dict with success status and email send result
        """
        try:
            logger.info(f"📥 Processing interaction: action={action}")
            
            # Check if approved
            approved = str(action or '').strip().lower() in ('approve', 'confirm', 'send', 'yes')
            
            if not approved:
                logger.info(f"❌ Draft rejected by user")
                return {
                    "success": True,
                    "approved": False,
                    "action": action,
                    "message": "Email draft rejected",
                    "result": {"status": "rejected", "sent": False}
                }
            
            # Extract edited draft from form
            edited_draft = {
                "recipient": form.get("recipient") or continuation.get("original_draft", {}).get("recipient"),
                "subject": form.get("subject") or continuation.get("original_draft", {}).get("subject"),
                "body": form.get("body") or continuation.get("original_draft", {}).get("body"),
                "attachments": form.get("attachments") or continuation.get("original_draft", {}).get("attachments", [])
            }
            
            logger.info(f"✅ Draft approved: {edited_draft['recipient']}")
            
            # Check if auto-send is enabled
            auto_send = continuation.get("auto_send", True)
            
            if auto_send:
                # Send email immediately
                smtp_config = continuation.get("smtp_config", {})
                send_result = await self._send_approved_email(edited_draft, smtp_config)
                
                return {
                    "success": True,
                    "approved": True,
                    "action": action,
                    "sent": send_result.get("success", False),
                    "message": "Email approved and sent" if send_result.get("success") else "Email approved but send failed",
                    "result": send_result,
                    "final_draft": edited_draft
                }
            else:
                # Just approve without sending
                return {
                    "success": True,
                    "approved": True,
                    "action": action,
                    "sent": False,
                    "message": "Email approved (not sent)",
                    "result": {"status": "approved", "sent": False},
                    "final_draft": edited_draft
                }
        
        except Exception as e:
            logger.error(f"❌ Interaction handling error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to process approval: {e}"
            }
    
    async def _store_interaction(
        self,
        interaction_id: str,
        token: str,
        execution_id: str,
        workflow_id: str,
        node_id: str,
        original_draft: dict,
        smtp_config: dict,
        timeout_hours: int
    ):
        """Store interaction in database"""
        try:
            from app.database.session import SessionLocal
            from app.database.models.email_interaction import EmailInteraction
            
            db = SessionLocal()
            try:
                # Create interaction record
                interaction = EmailInteraction.create_new(
                    interaction_id=interaction_id,
                    token=token,
                    execution_id=execution_id,
                    workflow_id=workflow_id,
                    node_id=node_id,
                    original_draft=original_draft,
                    smtp_config=smtp_config,
                    timeout_hours=timeout_hours
                )
                
                db.add(interaction)
                db.commit()
                
                logger.info(f"✅ Interaction stored in database: {interaction_id}")
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"❌ Failed to store interaction: {e}", exc_info=True)
            raise
    
    async def _send_notification_email(
        self,
        input_data: NodeExecutionInput,
        review_url: str,
        draft: Dict[str, Any],
        timeout_hours: int
    ) -> Dict[str, Any]:
        """
        Send notification email with review link.
        
        Supports two authentication modes:
        - credential: Use saved credential from credential manager
        - manual: Use manually entered credentials
        """
        try:
            notification_email = self.resolve_config(input_data, "notification_email", "")
            
            if not notification_email:
                return {"success": False, "error": "Notification email address not configured"}
            
            # Get auth mode (default to manual for backwards compatibility)
            auth_mode = self.resolve_config(input_data, "auth_mode", "manual")
            
            # Get SMTP credentials based on auth mode
            if auth_mode == "credential":
                # Get credential data
                credential = self.resolve_credential(input_data, "credential_id")
                if not credential:
                    return {"success": False, "error": "Email credential not found"}
                
                # Handle both email_smtp format and generic smtp format
                # email_smtp: {email, password, provider, from_name, smtp_server, smtp_port}
                # smtp: {host, port, username, password, use_tls}
                
                if "email" in credential:
                    # New email_smtp format
                    sender_email = credential.get("email", "")
                    smtp_password = credential.get("password", "")
                    provider = credential.get("provider", "gmail")
                    sender_name = credential.get("from_name", "TAV Workflow Bot")
                    smtp_server = credential.get("smtp_server", "")
                    smtp_port = credential.get("smtp_port", 587)
                elif "username" in credential:
                    # Generic smtp format (username = email, host = smtp_server)
                    sender_email = credential.get("username", "")
                    smtp_password = credential.get("password", "")
                    provider = "custom"  # Generic SMTP uses custom provider
                    sender_name = "TAV Workflow Bot"
                    smtp_server = credential.get("host", "")
                    smtp_port = credential.get("port", 587)
                else:
                    return {"success": False, "error": "Invalid credential format (missing email/username)"}
                
                logger.info(f"🔐 Using credential for notification: {sender_email} (provider: {provider})")
            else:
                # Manual mode - get from config
                provider = self.resolve_config(input_data, "provider", "gmail")
                sender_email = self.resolve_config(input_data, "from_email", "")
                smtp_password = self.resolve_config(input_data, "password", "")
                sender_name = self.resolve_config(input_data, "from_name", "TAV Workflow Bot")
                
                # Decrypt password if it's encrypted
                from app.security.encryption import decrypt_value, is_encrypted
                if smtp_password and is_encrypted(smtp_password):
                    try:
                        smtp_password = decrypt_value(smtp_password)
                        logger.debug("🔓 Decrypted notification SMTP password")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to decrypt password: {e}")
                
                # Custom SMTP settings (for custom provider)
                smtp_server = self.resolve_config(input_data, "custom_smtp_server", "")
                smtp_port = self.resolve_config(input_data, "custom_smtp_port", 587)
            
            # Validate credentials
            if not sender_email:
                return {"success": False, "error": "Sender email is required for notifications"}
            
            if not smtp_password:
                return {"success": False, "error": "Password is required for notifications"}
            
            # Create email template
            subject = "📧 Email Draft Ready for Review"
            
            # Get draft preview
            recipient_preview = draft.get("recipient", "N/A")
            subject_preview = draft.get("subject", "N/A")
            body_preview = draft.get("body", "")[:150]
            if len(draft.get("body", "")) > 150:
                body_preview += "..."
            
            # Email body template
            body = f"""
Hi there,

An email draft is awaiting your review and approval.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DRAFT PREVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

To: {recipient_preview}
Subject: {subject_preview}

{body_preview}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 REVIEW LINK:
{review_url}

⏰ This link will expire in {timeout_hours} hours.

Click the link above to review, edit, and approve or reject the email draft.

---
TAV Workflow Engine
Automated Email Review System
"""
            
            logger.info(f"📧 Sending notification to: {notification_email} from: {sender_email}")
            
            smtp_service = get_smtp_service()
            
            result = await smtp_service.send_email(
                to_addresses=[notification_email],
                subject=subject,
                body=body,
                from_address=sender_email,
                from_name=sender_name,
                provider=provider,
                smtp_server=smtp_server if smtp_server else None,
                smtp_port=smtp_port if smtp_port else None,
                smtp_password=smtp_password
            )
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Error sending notification email: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _send_approved_email(self, draft: Dict[str, Any], smtp_config: Dict[str, Any]) -> Dict[str, Any]:
        """Send approved email"""
        try:
            logger.info(f"📤 Sending approved email to: {draft.get('recipient')}")
            
            # Process attachments - convert file_ids to paths for newly uploaded files
            attachments = draft.get("attachments", [])
            processed_attachments = []
            
            for att in attachments:
                if att.get("is_new") and att.get("file_id"):
                    # This is a newly uploaded file - need to get its path from file API
                    logger.info(f"📎 Processing new attachment: {att.get('filename')} (file_id: {att.get('file_id')})")
                    
                    # Get file metadata from database
                    from app.database.repositories.file import FileRepository
                    from app.database.session import SessionLocal
                    from app.api.v1.endpoints.files import get_storage_base_path
                    
                    db = SessionLocal()
                    try:
                        file_repo = FileRepository(db)
                        file_record = file_repo.get_by_id(att.get("file_id"))
                        
                        if file_record:
                            # Get the full file path
                            file_path = get_storage_base_path() / file_record.storage_path
                            
                            processed_attachments.append({
                                "filename": att.get("filename"),
                                "path": str(file_path),
                                "mimetype": att.get("content_type"),
                                "content_type": att.get("content_type")
                            })
                            logger.info(f"✅ Resolved new file path: {file_path}")
                        else:
                            logger.warning(f"⚠️ File not found for file_id: {att.get('file_id')}")
                    finally:
                        db.close()
                else:
                    # Original attachment or already has path
                    processed_attachments.append({
                        "filename": att.get("filename"),
                        "path": att.get("path"),
                        "content": att.get("content"),
                        "mimetype": att.get("content_type") or att.get("mimetype"),
                        "content_type": att.get("content_type") or att.get("mimetype")
                    })
            
            logger.info(f"📎 Total attachments to send: {len(processed_attachments)}")
            
            smtp_service = get_smtp_service()
            
            # Extract SMTP config
            result = await smtp_service.send_email(
                to_addresses=[draft.get("recipient")],
                subject=draft.get("subject", ""),
                body=draft.get("body", ""),
                from_address=smtp_config.get("from_email"),
                from_name=smtp_config.get("from_name"),
                provider=smtp_config.get("provider", "gmail"),
                smtp_server=smtp_config.get("smtp_server"),
                smtp_port=smtp_config.get("smtp_port"),
                smtp_password=smtp_config.get("smtp_password"),
                cc_addresses=smtp_config.get("cc_addresses"),
                bcc_addresses=smtp_config.get("bcc_addresses"),
                attachments=processed_attachments if processed_attachments else None,
                reply_to=smtp_config.get("reply_to")
            )
            
            if result.get("success"):
                logger.info(f"✅ Approved email sent successfully with {len(processed_attachments)} attachment(s)")
            else:
                logger.error(f"❌ Failed to send approved email: {result.get('error')}")
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Error sending approved email: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    print("Email Approval Node - Human-in-the-loop email review")

