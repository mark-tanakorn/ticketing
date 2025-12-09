"""
Email Polling Trigger Node

Monitors an email inbox for new emails and triggers workflow when emails are detected.
Uses polling mechanism (checks periodically) with IMAP.
"""

import asyncio
import logging
from typing import Dict, Any, Callable, Awaitable, Set, List, Optional
from datetime import datetime

from app.utils.timezone import get_local_now

from app.core.nodes import Node, NodeExecutionInput, TriggerCapability, register_node
from app.schemas.workflow import NodeCategory, PortType
from app.services.imap_service import get_imap_service, EMAIL_IMAP_PROVIDERS

logger = logging.getLogger(__name__)


@register_node(
    node_type="email_polling_trigger",
    category=NodeCategory.TRIGGERS,
    name="Email Polling Trigger",
    description="Monitors email inbox for new emails and triggers workflow (polling-based)",
    icon="fa-solid fa-envelope",
    version="1.0.0"
)
class EmailPollingTriggerNode(Node, TriggerCapability):
    """
    Email Polling Trigger - Monitor email inbox for new messages
    
    Polls an email inbox at regular intervals and triggers workflow when new emails are detected.
    
    Features:
    - Periodic polling (configurable interval)
    - IMAP support for all major providers
    - Credential integration (secure password storage)
    - Email filtering (sender, subject, keywords)
    - Track processed emails to avoid duplicates
    - Pass email content and metadata to workflow
    - Optional mark as read
    
    How it works:
    1. Every N seconds, checks email inbox via IMAP
    2. Identifies new emails (not seen before)
    3. Triggers workflow with email information
    4. Marks email as processed
    
    Use Cases:
    - Automated email processing
    - Support ticket workflows
    - Order confirmation processing
    - Email-to-workflow automation
    """
    
    trigger_type = "email_polling"  # Used for execution_source tracking
    
    # Class-level storage for processed emails (per node instance)
    # In production, this should be persisted to DB for multi-instance deployments
    _processed_emails: Dict[str, Set[str]] = {}  # node_id -> set of message IDs
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Triggers typically have NO input ports - they start the workflow"""
        return []
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "email",
                "type": PortType.UNIVERSAL,
                "display_name": "Email Data",
                "description": "Email content and metadata"
            },
            {
                "name": "subject",
                "type": PortType.UNIVERSAL,
                "display_name": "Subject",
                "description": "Email subject line"
            },
            {
                "name": "sender",
                "type": PortType.UNIVERSAL,
                "display_name": "Sender",
                "description": "Email sender address"
            },
            {
                "name": "content",
                "type": PortType.UNIVERSAL,
                "display_name": "Content",
                "description": "Email body text"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        
        # Get provider options
        provider_options = [
            {"label": config["display_name"], "value": provider}
            for provider, config in EMAIL_IMAP_PROVIDERS.items()
        ]
        
        return {
            # Authentication Mode
            "auth_mode": {
                "type": "select",
                "label": "Authentication",
                "description": "How to authenticate with email provider",
                "required": True,
                "options": [
                    {"label": "Manual (Enter credentials)", "value": "manual"},
                    {"label": "From Credential", "value": "credential"}
                ],
                "default": "manual",
                "widget": "select"
            },
            
            # Credential mode
            "credential_id": {
                "type": "credential",
                "widget": "credential",
                "label": "Email Credential",
                "description": "Select saved email credential (email_smtp type)",
                "required": False,
                "visible_when": {"auth_mode": "credential"}
            },
            
            # Manual mode - Provider selection
            "provider": {
                "type": "select",
                "label": "Email Provider",
                "description": "Select your email provider (IMAP auto-configured)",
                "required": False,
                "options": provider_options,
                "default": "gmail",
                "widget": "select",
                "help": "Gmail and Yahoo require app-specific passwords",
                "visible_when": {"auth_mode": "manual"}
            },
            
            # Manual mode - Credentials
            "email_address": {
                "type": "string",
                "label": "Email Address",
                "description": "Your email address",
                "required": False,
                "placeholder": "your.email@example.com",
                "widget": "text",
                "visible_when": {"auth_mode": "manual"}
            },
            "password": {
                "type": "string",
                "label": "Password / App Password",
                "description": "Email password or app-specific password",
                "required": False,
                "widget": "password",
                "help": "Gmail/Yahoo: Use app-specific password. Outlook: Regular password or app password.",
                "visible_when": {"auth_mode": "manual"}
            },
            
            # Custom IMAP (only for custom provider in manual mode)
            "custom_imap_server": {
                "type": "string",
                "label": "IMAP Server",
                "description": "Your IMAP server address",
                "required": False,
                "placeholder": "imap.example.com",
                "widget": "text",
                "show_if": {"provider": "custom", "auth_mode": "manual"}
            },
            "custom_imap_port": {
                "type": "integer",
                "label": "IMAP Port",
                "description": "IMAP port (usually 993 for SSL)",
                "required": False,
                "default": 993,
                "widget": "number",
                "show_if": {"provider": "custom", "auth_mode": "manual"}
            },
            
            # Polling Configuration
            "polling_interval": {
                "type": "integer",
                "label": "Polling Interval (seconds)",
                "description": "How often to check for new emails",
                "required": False,
                "default": 60,
                "widget": "number",
                "min": 30,
                "max": 3600,
                "help": "Checks inbox every N seconds (minimum 30s)"
            },
            
            # Email Folder
            "folder_name": {
                "type": "string",
                "label": "Email Folder",
                "description": "Folder to monitor (usually INBOX)",
                "required": False,
                "default": "INBOX",
                "placeholder": "INBOX",
                "widget": "text",
                "help": "Most common: INBOX, Sent, Drafts"
            },
            
            # Filtering Options
            "only_unread": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Only Unread Emails",
                "description": "Only trigger on unread emails",
                "required": False,
                "default": True,
                "help": "Enable to only process unread emails"
            },
            "filter_sender": {
                "type": "string",
                "label": "Filter by Sender (optional)",
                "description": "Only emails from this sender",
                "required": False,
                "placeholder": "example@domain.com",
                "widget": "text",
                "help": "Leave blank to accept all senders"
            },
            "filter_subject": {
                "type": "string",
                "label": "Filter by Subject (optional)",
                "description": "Only emails with this text in subject",
                "required": False,
                "placeholder": "Order Confirmation",
                "widget": "text",
                "help": "Partial match, case-insensitive"
            },
            "filter_keywords": {
                "type": "string",
                "label": "Filter Keywords (optional)",
                "description": "Comma-separated keywords to filter by",
                "required": False,
                "placeholder": "urgent, invoice, ticket",
                "widget": "text",
                "help": "Email must contain at least one keyword"
            },
            
            # Processing Options
            "mark_as_read": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Mark as Read After Processing",
                "description": "Automatically mark emails as read",
                "required": False,
                "default": False,
                "help": "Email will be marked as read after workflow triggers"
            },
            "max_emails_per_check": {
                "type": "integer",
                "label": "Max Emails per Check",
                "description": "Maximum emails to process in one check",
                "required": False,
                "default": 10,
                "widget": "number",
                "min": 1,
                "max": 50,
                "help": "Prevents overwhelming the system with too many emails at once"
            },
            "ignore_existing": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Ignore Existing Emails",
                "description": "Only trigger on emails received after trigger starts",
                "required": False,
                "default": True,
                "help": "Enable to skip emails that already exist when trigger starts"
            },
            
            # Trigger Mode
            "trigger_mode": {
                "type": "select",
                "widget": "select",
                "label": "Trigger Mode",
                "description": "When to trigger workflow",
                "required": False,
                "default": "per_email",
                "options": [
                    {"label": "Per Email (separate execution for each email)", "value": "per_email"},
                    {"label": "Batch (single execution for all new emails)", "value": "batch"}
                ],
                "help": "Per email = one workflow per email, Batch = one workflow for multiple emails"
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """
        Execute trigger - returns trigger data that was injected into execution context.
        
        When a trigger fires via fire_trigger(), the trigger data is injected into the
        execution context under "trigger_data" key.
        
        Returns output in the format expected by downstream nodes.
        """
        logger.info(f"📤 Email polling trigger execute() - extracting trigger data")
        
        # The trigger data was injected into variables["trigger_data"] by the orchestrator
        trigger_data = input_data.variables.get("trigger_data", {})
        
        logger.info(f"   Available variables: {list(input_data.variables.keys())}")
        logger.info(f"   Trigger data keys: {list(trigger_data.keys())}")
        logger.info(f"   Email subject: {trigger_data.get('subject')}")
        
        # Return the trigger data fields as our output ports
        return {
            "email": trigger_data,
            "subject": trigger_data.get("subject"),
            "sender": trigger_data.get("sender"),
            "content": trigger_data.get("content"),
            "signal": trigger_data.get("signal", "email_received")
        }
    
    async def start_monitoring(
        self,
        workflow_id: str,
        executor_callback: Callable[[str, Dict[str, Any], str], Awaitable[None]]
    ):
        """
        Start monitoring - required by TriggerCapability.
        
        This method is called by the trigger manager to start monitoring.
        It runs in a background task and calls executor_callback when emails are detected.
        
        Args:
            workflow_id: ID of the workflow being monitored
            executor_callback: Async function to call when trigger fires
        """
        self._workflow_id = workflow_id
        self._executor_callback = executor_callback
        self._is_monitoring = True
        
        # Start polling loop in background
        self._monitoring_task = asyncio.create_task(self._polling_loop())
        
        logger.info(f"✅ Email polling trigger monitoring started: {self.node_id}")
    
    async def stop_monitoring(self):
        """
        Stop monitoring - required by TriggerCapability.
        
        Called by trigger manager to stop this trigger.
        """
        self._is_monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        logger.info(f"⏹️ Email polling trigger monitoring stopped: {self.node_id}")
    
    async def _polling_loop(self):
        """
        Internal polling loop that monitors the email inbox.
        
        This runs continuously until stop_monitoring() is called.
        """
        # Get configuration
        polling_interval = self.config.get("polling_interval", 60)
        folder_name = self.config.get("folder_name", "INBOX")
        trigger_mode = self.config.get("trigger_mode", "per_email")
        ignore_existing = self.config.get("ignore_existing", True)
        
        # Get credentials
        auth_result = self._get_auth_credentials()
        if "error" in auth_result:
            logger.error(f"❌ Email polling trigger {self.node_id}: {auth_result['error']}")
            return
        
        email_address = auth_result["email"]
        password = auth_result["password"]
        imap_server = auth_result["imap_server"]
        imap_port = auth_result["imap_port"]
        
        logger.info(f"👁️ Email polling trigger started: {self.node_id}")
        logger.info(f"   Email: {email_address}")
        logger.info(f"   Server: {imap_server}:{imap_port}")
        logger.info(f"   Folder: {folder_name}")
        logger.info(f"   Interval: {polling_interval}s")
        
        # Initialize processed emails set for this node
        if self.node_id not in self._processed_emails:
            self._processed_emails[self.node_id] = set()
        
        # Initial scan - mark existing emails as processed if ignore_existing=True
        if ignore_existing:
            try:
                initial_emails = await self._check_for_new_emails(
                    email_address, password, imap_server, imap_port, folder_name
                )
                for email_data in initial_emails:
                    message_id = email_data.get("message_id", "")
                    if message_id:
                        self._processed_emails[self.node_id].add(message_id)
                logger.info(f"📂 Initial scan: {len(initial_emails)} existing emails marked as processed")
            except Exception as e:
                logger.warning(f"⚠️ Initial scan failed: {e}")
        
        # Start polling loop
        try:
            while self._is_monitoring:
                await asyncio.sleep(polling_interval)
                
                # Check if still monitoring
                if not self._is_monitoring:
                    break
                
                logger.debug(f"🔍 Polling inbox: {email_address}")
                
                try:
                    # Check for new emails
                    current_emails = await self._check_for_new_emails(
                        email_address, password, imap_server, imap_port, folder_name
                    )
                    
                    logger.debug(f"   Found {len(current_emails)} total emails")
                    
                    # Find new emails
                    new_emails = []
                    for email_data in current_emails:
                        message_id = email_data.get("message_id", "")
                        if message_id and message_id not in self._processed_emails[self.node_id]:
                            new_emails.append(email_data)
                            self._processed_emails[self.node_id].add(message_id)
                    
                    logger.debug(f"   {len(new_emails)} new emails detected")
                    
                    if new_emails:
                        logger.info(f"📧 Detected {len(new_emails)} new email(s)")
                        
                        if trigger_mode == "per_email":
                            # Trigger once per email
                            for email_data in new_emails:
                                trigger_data = self._build_trigger_data(email_data)
                                logger.info(f"🔔 Triggering workflow for: {email_data.get('subject', 'No Subject')}")
                                await self.fire_trigger(trigger_data)
                        else:
                            # Batch mode - trigger once with all emails
                            trigger_data = self._build_batch_trigger_data(new_emails)
                            logger.info(f"🔔 Triggering workflow with {len(new_emails)} emails")
                            await self.fire_trigger(trigger_data)
                
                except Exception as e:
                    logger.error(f"❌ Error checking emails: {e}", exc_info=True)
        
        except asyncio.CancelledError:
            logger.info(f"⏹️ Email polling loop cancelled: {self.node_id}")
            raise
        except Exception as e:
            logger.error(f"❌ Error in email polling loop {self.node_id}: {e}", exc_info=True)
    
    def _get_auth_credentials(self) -> Dict[str, Any]:
        """
        Get email authentication credentials from config or credential manager.
        
        Returns dict with: email, password, imap_server, imap_port
        Or dict with: error
        """
        auth_mode = self.config.get("auth_mode", "manual")
        
        if auth_mode == "credential":
            # Get from credential
            credential_id = self.config.get("credential_id")
            if not credential_id:
                return {"error": "No credential selected"}
            
            # Resolve credential (this should be done through the credential manager)
            # For now, we'll try to get it from the config's credential_data
            credential = self.config.get("_credential_data")  # Injected by credential resolver
            if not credential:
                return {"error": "Email credential not found"}
            
            # Handle email_smtp format
            if "email" in credential:
                email_address = credential.get("email", "")
                password = credential.get("password", "")
                provider = credential.get("provider", "gmail")
                
                # Get IMAP settings for provider
                if provider == "custom":
                    imap_server = credential.get("smtp_server", "")  # Note: IMAP not in credential schema, fallback
                    imap_port = credential.get("smtp_port", 993)
                else:
                    provider_config = EMAIL_IMAP_PROVIDERS.get(provider, EMAIL_IMAP_PROVIDERS["gmail"])
                    imap_server = provider_config["imap_server"]
                    imap_port = provider_config["imap_port"]
                
                logger.info(f"🔐 Using credential: {email_address} (provider: {provider})")
                
                return {
                    "email": email_address,
                    "password": password,
                    "imap_server": imap_server,
                    "imap_port": imap_port
                }
            else:
                return {"error": "Invalid credential format (missing email)"}
        
        else:
            # Manual mode
            email_address = self.config.get("email_address", "")
            password = self.config.get("password", "")
            provider = self.config.get("provider", "gmail")
            
            if not email_address or not password:
                return {"error": "Email address and password are required"}
            
            # Decrypt password if it's encrypted
            from app.security.encryption import decrypt_value, is_encrypted
            if password and is_encrypted(password):
                try:
                    password = decrypt_value(password)
                    logger.debug("🔓 Decrypted email password")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to decrypt password: {e}")
            
            # Get IMAP settings
            if provider == "custom":
                imap_server = self.config.get("custom_imap_server", "")
                imap_port = self.config.get("custom_imap_port", 993)
                
                if not imap_server:
                    return {"error": "Custom IMAP server is required"}
            else:
                provider_config = EMAIL_IMAP_PROVIDERS.get(provider, EMAIL_IMAP_PROVIDERS["gmail"])
                imap_server = provider_config["imap_server"]
                imap_port = provider_config["imap_port"]
            
            return {
                "email": email_address,
                "password": password,
                "imap_server": imap_server,
                "imap_port": imap_port
            }
    
    async def _check_for_new_emails(
        self,
        email_address: str,
        password: str,
        imap_server: str,
        imap_port: int,
        folder_name: str
    ) -> List[Dict[str, Any]]:
        """
        Check for new emails using IMAP service.
        """
        try:
            # Get IMAP service
            imap_service = get_imap_service()
            
            # Get filter settings
            only_unread = self.config.get("only_unread", True)
            filter_sender = self.config.get("filter_sender", "")
            filter_subject = self.config.get("filter_subject", "")
            max_emails = self.config.get("max_emails_per_check", 10)
            mark_as_read = self.config.get("mark_as_read", False)
            
            # Fetch emails using service
            emails = await imap_service.fetch_emails(
                email_address=email_address,
                password=password,
                provider="custom",  # We provide server/port directly
                imap_server=imap_server,
                imap_port=imap_port,
                folder_name=folder_name,
                only_unread=only_unread,
                filter_sender=filter_sender if filter_sender else None,
                filter_subject=filter_subject if filter_subject else None,
                max_emails=max_emails,
                mark_as_read=mark_as_read
            )
            
            # Apply additional keyword filtering
            if self.config.get("filter_keywords", ""):
                emails = [e for e in emails if self._passes_filters(e)]
            
            return emails
        
        except Exception as e:
            logger.error(f"❌ Error checking emails: {e}", exc_info=True)
            return []
    
    def _passes_filters(self, email_data: Dict[str, Any]) -> bool:
        """Check if email passes configured filters"""
        try:
            # Filter by keywords
            filter_keywords = self.config.get("filter_keywords", "")
            if filter_keywords:
                keywords = [k.strip().lower() for k in filter_keywords.split(',')]
                email_text = f"{email_data.get('subject', '')} {email_data.get('content', '')}".lower()
                
                # Check if any keyword is found
                if not any(keyword in email_text for keyword in keywords if keyword):
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Error applying filters: {e}")
            return True  # Default to allowing email if filter fails
    
    def _build_trigger_data(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build trigger data dict for single email"""
        return {
            "email": email_data,
            "subject": email_data.get("subject", ""),
            "sender": email_data.get("sender", ""),
            "to": email_data.get("to", ""),
            "content": email_data.get("content", ""),
            "html_content": email_data.get("html_content", ""),
            "received_date": email_data.get("received_date", ""),
            "message_id": email_data.get("message_id", ""),
            "attachments": email_data.get("attachments", []),
            "signal": "email_received",
            "trigger_source": "email_polling"
        }
    
    def _build_batch_trigger_data(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build trigger data dict for batch of emails"""
        return {
            "emails": [self._build_trigger_data(e) for e in emails],
            "email_count": len(emails),
            "signal": "emails_received",
            "trigger_source": "email_polling"
        }


if __name__ == "__main__":
    print("Email Polling Trigger Node - Monitor email inbox for new messages")

