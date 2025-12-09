"""
SMTP Service - Email sending with multi-provider support

Handles email sending through various providers (Gmail, Outlook, Yahoo, etc.)
with automatic SMTP configuration.
"""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


# Provider configurations with automatic SMTP settings
EMAIL_PROVIDERS = {
    "gmail": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "use_tls": True,
        "display_name": "Gmail",
        "notes": "Requires app-specific password (not regular Gmail password)"
    },
    "outlook": {
        "smtp_server": "smtp-mail.outlook.com",
        "smtp_port": 587,
        "use_tls": True,
        "display_name": "Outlook",
        "notes": "Works with @outlook.com and @hotmail.com addresses"
    },
    "yahoo": {
        "smtp_server": "smtp.mail.yahoo.com",
        "smtp_port": 587,
        "use_tls": True,
        "display_name": "Yahoo Mail",
        "notes": "Requires app-specific password"
    },
    "office365": {
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
        "use_tls": True,
        "display_name": "Office 365",
        "notes": "For business/enterprise Office 365 accounts"
    },
    "custom": {
        "smtp_server": None,  # User must provide
        "smtp_port": 587,
        "use_tls": True,
        "display_name": "Custom SMTP",
        "notes": "Specify your own SMTP server settings"
    }
}


class SMTPService:
    """
    Service for sending emails through various SMTP providers.
    
    Features:
    - Multi-provider support with auto-configuration
    - TLS/SSL support
    - HTML and plain text emails
    - File attachments (manual files + file IDs)
    - Async execution
    """
    
    @staticmethod
    def get_provider_config(provider: str) -> Dict[str, Any]:
        """
        Get SMTP configuration for a provider.
        
        Args:
            provider: Provider name (gmail, outlook, yahoo, office365, custom)
        
        Returns:
            Provider configuration dict
        """
        provider_lower = provider.lower()
        if provider_lower not in EMAIL_PROVIDERS:
            logger.warning(f"Unknown provider '{provider}', using custom")
            provider_lower = "custom"
        
        return EMAIL_PROVIDERS[provider_lower].copy()
    
    @staticmethod
    def get_available_providers() -> Dict[str, Dict[str, Any]]:
        """Get list of all available email providers"""
        return EMAIL_PROVIDERS.copy()
    
    async def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        body: str,
        from_address: str,
        from_name: Optional[str] = None,
        provider: str = "gmail",
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        use_tls: Optional[bool] = None,
        html_body: Optional[str] = None,
        cc_addresses: Optional[List[str]] = None,
        bcc_addresses: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send email through SMTP.
        
        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            body: Plain text body
            from_address: Sender email address
            from_name: Sender display name (optional)
            provider: Provider name (auto-configures SMTP if not custom)
            smtp_server: SMTP server (overrides provider default)
            smtp_port: SMTP port (overrides provider default)
            smtp_username: SMTP username (usually same as from_address)
            smtp_password: SMTP password or app-specific password
            use_tls: Enable TLS (overrides provider default)
            html_body: HTML body (optional, falls back to plain text)
            cc_addresses: CC recipients (optional)
            bcc_addresses: BCC recipients (optional)
            attachments: List of attachment dicts with 'filename' and 'content' or 'path'
            reply_to: Reply-To address (optional)
        
        Returns:
            Dict with success status and details
        
        Example:
            await smtp_service.send_email(
                to_addresses=["user@example.com"],
                subject="Test Email",
                body="Hello!",
                from_address="sender@gmail.com",
                provider="gmail",
                smtp_password="app_specific_password"
            )
        """
        try:
            # Get provider config
            provider_config = self.get_provider_config(provider)
            
            # Merge configs (explicit params override provider defaults)
            final_server = smtp_server or provider_config.get("smtp_server")
            final_port = smtp_port or provider_config.get("smtp_port", 587)
            final_tls = use_tls if use_tls is not None else provider_config.get("use_tls", True)
            final_username = smtp_username or from_address
            
            # Sanitize inputs - strip whitespace
            if final_server:
                final_server = final_server.strip()
            if final_username:
                final_username = final_username.strip()
            
            # Validate required fields
            if not final_server:
                return {
                    "success": False,
                    "error": "SMTP server is required. For custom provider, specify smtp_server."
                }
            
            if not smtp_password:
                return {
                    "success": False,
                    "error": "SMTP password is required"
                }
            
            if not to_addresses:
                return {
                    "success": False,
                    "error": "At least one recipient is required"
                }
            
            # Run blocking SMTP in thread pool
            result = await asyncio.get_running_loop().run_in_executor(
                None,
                self._send_sync,
                to_addresses,
                subject,
                body,
                html_body,
                from_address,
                from_name,
                final_server,
                final_port,
                final_username,
                smtp_password,
                final_tls,
                cc_addresses,
                bcc_addresses,
                attachments,
                reply_to
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Email send error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _send_sync(
        self,
        to_addresses: List[str],
        subject: str,
        body: str,
        html_body: Optional[str],
        from_address: str,
        from_name: Optional[str],
        smtp_server: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        use_tls: bool,
        cc_addresses: Optional[List[str]],
        bcc_addresses: Optional[List[str]],
        attachments: Optional[List[Dict[str, Any]]],
        reply_to: Optional[str]
    ) -> Dict[str, Any]:
        """Synchronous email sending (runs in thread pool)"""
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_address}>" if from_name else from_address
            msg["To"] = ", ".join(to_addresses)
            
            if cc_addresses:
                msg["Cc"] = ", ".join(cc_addresses)
            
            if reply_to:
                msg["Reply-To"] = reply_to
            
            # Add body (plain text and/or HTML)
            if body:
                msg.attach(MIMEText(body, "plain", "utf-8"))
            
            if html_body:
                msg.attach(MIMEText(html_body, "html", "utf-8"))
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
            
            # All recipients (to + cc + bcc)
            all_recipients = to_addresses.copy()
            if cc_addresses:
                all_recipients.extend(cc_addresses)
            if bcc_addresses:
                all_recipients.extend(bcc_addresses)
            
            # Connect and send
            logger.info(f"📧 Connecting to SMTP server: {smtp_server}:{smtp_port}")
            
            with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                server.ehlo()  # Identify to SMTP server
                
                if use_tls:
                    logger.debug("🔒 Starting TLS")
                    server.starttls()
                    server.ehlo()  # Re-identify after STARTTLS
                
                # Login if credentials provided
                if smtp_username and smtp_password:
                    logger.debug(f"🔑 Logging in as {smtp_username}")
                    server.login(smtp_username, smtp_password)
                
                # Send email
                logger.info(f"📨 Sending email to {len(all_recipients)} recipient(s)")
                server.send_message(msg)
            
            logger.info(f"✅ Email sent successfully: {subject}")
            
            return {
                "success": True,
                "message": f"Email sent to {len(to_addresses)} recipient(s)",
                "recipients": to_addresses,
                "subject": subject
            }
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"Authentication failed: {e}. Check username/password."
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {e}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {"success": False, "error": error_msg}
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """
        Add attachment to email message.
        
        Attachment dict can contain:
        - filename: Name of the file
        - content: Raw bytes content
        - path: Path to file (alternative to content)
        - mimetype: MIME type (optional, auto-detected if not provided)
        """
        try:
            filename = attachment.get("filename", "attachment")
            content = attachment.get("content")
            file_path = attachment.get("path")
            mimetype = attachment.get("mimetype", "application/octet-stream")
            
            # Get content from path if not provided directly
            if content is None and file_path:
                with open(file_path, "rb") as f:
                    content = f.read()
            
            if content is None:
                logger.warning(f"⚠️ Attachment '{filename}' has no content, skipping")
                return
            
            # Create attachment part
            part = MIMEBase("application", "octet-stream")
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {filename}"
            )
            
            msg.attach(part)
            logger.debug(f"📎 Attached file: {filename}")
            
        except Exception as e:
            logger.error(f"❌ Failed to attach file: {e}")


# Singleton instance
_smtp_service: Optional[SMTPService] = None


def get_smtp_service() -> SMTPService:
    """Get singleton SMTP service instance"""
    global _smtp_service
    if _smtp_service is None:
        _smtp_service = SMTPService()
    return _smtp_service

