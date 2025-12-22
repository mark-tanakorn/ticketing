"""
IMAP Service - Email reading with multi-provider support

Handles email reading through various providers (Gmail, Outlook, Yahoo, etc.)
with automatic IMAP configuration.
"""

import asyncio
import logging
import imaplib
import email
from email.header import decode_header
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


# Provider configurations with automatic IMAP settings
EMAIL_IMAP_PROVIDERS = {
    "gmail": {
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "display_name": "Gmail",
        "notes": "Requires app-specific password (not regular Gmail password)"
    },
    "outlook": {
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "display_name": "Outlook",
        "notes": "Works with @outlook.com and @hotmail.com addresses"
    },
    "yahoo": {
        "imap_server": "imap.mail.yahoo.com",
        "imap_port": 993,
        "display_name": "Yahoo Mail",
        "notes": "Requires app-specific password"
    },
    "office365": {
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "display_name": "Office 365",
        "notes": "For business/enterprise Office 365 accounts"
    },
    "custom": {
        "imap_server": None,  # User must provide
        "imap_port": 993,
        "display_name": "Custom IMAP",
        "notes": "Specify your own IMAP server settings"
    }
}


class IMAPService:
    """
    Service for reading emails through various IMAP providers.
    
    Features:
    - Multi-provider support with auto-configuration
    - SSL/TLS support
    - Email filtering (unread, sender, subject)
    - Email parsing (headers, body, attachments)
    - Async execution
    
    Example:
        imap_service = IMAPService()
        emails = await imap_service.fetch_emails(
            email_address="user@gmail.com",
            password="app_password",
            provider="gmail"
        )
    """
    
    @staticmethod
    def get_provider_config(provider: str) -> Dict[str, Any]:
        """
        Get IMAP configuration for a provider.
        
        Args:
            provider: Provider name (gmail, outlook, yahoo, office365, custom)
        
        Returns:
            Provider configuration dict
        """
        provider_lower = provider.lower()
        if provider_lower not in EMAIL_IMAP_PROVIDERS:
            logger.warning(f"Unknown provider '{provider}', using custom")
            provider_lower = "custom"
        
        return EMAIL_IMAP_PROVIDERS[provider_lower].copy()
    
    @staticmethod
    def get_available_providers() -> Dict[str, Dict[str, Any]]:
        """Get list of all available email providers"""
        return EMAIL_IMAP_PROVIDERS.copy()
    
    async def fetch_emails(
        self,
        email_address: str,
        password: str,
        provider: str = "gmail",
        imap_server: Optional[str] = None,
        imap_port: Optional[int] = None,
        folder_name: str = "INBOX",
        only_unread: bool = True,
        filter_sender: Optional[str] = None,
        filter_subject: Optional[str] = None,
        max_emails: int = 10,
        mark_as_read: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails from IMAP server.
        
        Args:
            email_address: Email address
            password: Email password or app-specific password
            provider: Provider name (gmail, outlook, yahoo, office365, custom)
            imap_server: Custom IMAP server (for custom provider)
            imap_port: Custom IMAP port (for custom provider)
            folder_name: Email folder to read from (default: INBOX)
            only_unread: Only fetch unread emails (default: True)
            filter_sender: Filter by sender email address (optional)
            filter_subject: Filter by subject text (optional)
            max_emails: Maximum number of emails to fetch (default: 10)
            mark_as_read: Mark emails as read after fetching (default: False)
        
        Returns:
            List of email dictionaries
        """
        # Get provider configuration
        provider_config = self.get_provider_config(provider)
        
        # Use custom server/port if provided, otherwise use provider defaults
        if provider == "custom":
            if not imap_server:
                raise ValueError("Custom provider requires imap_server")
            final_imap_server = imap_server
            final_imap_port = imap_port or 993
        else:
            final_imap_server = provider_config["imap_server"]
            final_imap_port = provider_config["imap_port"]
        
        # Run IMAP operations in executor (blocking operations)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._fetch_emails_sync,
            email_address,
            password,
            final_imap_server,
            final_imap_port,
            folder_name,
            only_unread,
            filter_sender,
            filter_subject,
            max_emails,
            mark_as_read
        )
    
    def _fetch_emails_sync(
        self,
        email_address: str,
        password: str,
        imap_server: str,
        imap_port: int,
        folder_name: str,
        only_unread: bool,
        filter_sender: Optional[str],
        filter_subject: Optional[str],
        max_emails: int,
        mark_as_read: bool
    ) -> List[Dict[str, Any]]:
        """
        Synchronous email fetching (runs in executor).
        """
        try:
            logger.info(f"📧 Connecting to IMAP server: {imap_server}:{imap_port}")
            
            # Create IMAP connection
            imap_conn = imaplib.IMAP4_SSL(imap_server, imap_port)
            
            # Login
            logger.debug(f"🔑 Logging in as {email_address}")
            imap_conn.login(email_address, password)
            
            # Select folder
            logger.debug(f"📁 Selecting folder: {folder_name}")
            folder_status, folder_count = imap_conn.select(folder_name)
            if folder_status != 'OK':
                logger.error(f"❌ Failed to select folder {folder_name}: {folder_status}")
                imap_conn.logout()
                return []
            
            # Build search criteria
            search_criteria = []
            if only_unread:
                search_criteria.append('UNSEEN')
            if filter_sender:
                search_criteria.extend(['FROM', f'"{filter_sender}"'])
            if filter_subject:
                search_criteria.extend(['SUBJECT', f'"{filter_subject}"'])
            if not search_criteria:
                search_criteria.append('ALL')
            
            logger.debug(f"🔍 Search criteria: {search_criteria}")
            
            # Search for emails
            try:
                status, messages = imap_conn.search('UTF-8', *search_criteria)
            except:
                try:
                    status, messages = imap_conn.search(None, *search_criteria)
                except Exception as e:
                    logger.error(f"❌ IMAP search failed: {e}")
                    imap_conn.logout()
                    return []
            
            if status != 'OK':
                logger.error(f"❌ IMAP search failed: {status}")
                imap_conn.logout()
                return []
            
            # Get message IDs
            message_ids = messages[0].split()
            logger.info(f"📨 Found {len(message_ids)} emails matching criteria")
            
            # Limit number of emails
            if len(message_ids) > max_emails:
                message_ids = message_ids[-max_emails:]  # Get newest emails
                logger.info(f"📨 Limited to {max_emails} newest emails")
            
            # Fetch each email
            emails = []
            for msg_id in message_ids:
                try:
                    email_data = self._parse_email(imap_conn, msg_id)
                    if email_data:
                        emails.append(email_data)
                        
                        # Mark as read if configured
                        if mark_as_read:
                            imap_conn.store(msg_id, '+FLAGS', '\\Seen')
                
                except Exception as e:
                    logger.error(f"❌ Error processing email {msg_id}: {e}")
                    continue
            
            # Close connection
            imap_conn.close()
            imap_conn.logout()
            
            logger.info(f"✅ Fetched {len(emails)} emails successfully")
            
            return emails
        
        except imaplib.IMAP4.error as e:
            error_msg = str(e).lower()
            if "authentication failed" in error_msg or "invalid credentials" in error_msg:
                logger.error(f"❌ Authentication failed for {email_address}")
                logger.error("💡 Tip: Make sure you're using an App Password, not your regular email password")
            else:
                logger.error(f"❌ IMAP error: {e}")
            return []
        
        except Exception as e:
            logger.error(f"❌ IMAP fetch error: {e}", exc_info=True)
            return []
    
    def _parse_email(self, imap_conn, msg_id: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse email from IMAP message ID.
        
        Args:
            imap_conn: IMAP connection object
            msg_id: Message ID bytes
        
        Returns:
            Email data dictionary
        """
        try:
            # Fetch email
            status, msg_data = imap_conn.fetch(msg_id, '(RFC822)')
            if status != 'OK':
                logger.error(f"❌ Failed to fetch email {msg_id}: {status}")
                return None
            
            # Parse email
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Extract headers
            subject = self._decode_header(email_message.get('Subject', ''))
            sender = self._decode_header(email_message.get('From', ''))
            to = self._decode_header(email_message.get('To', ''))
            cc = self._decode_header(email_message.get('Cc', ''))
            received_date = email_message.get('Date', '')
            message_id = email_message.get('Message-ID', '')
            
            # Extract content
            content = ""
            html_content = ""
            attachments = []
            
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))
                    
                    if content_type == 'text/plain' and 'attachment' not in content_disposition:
                        try:
                            content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except:
                            content = str(part.get_payload())
                    
                    elif content_type == 'text/html' and 'attachment' not in content_disposition:
                        try:
                            html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except:
                            html_content = str(part.get_payload())
                    
                    elif 'attachment' in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            attachments.append({
                                'filename': filename,
                                'content_type': content_type,
                                'size': len(part.get_payload(decode=True) or b'')
                            })
            else:
                # Single part email
                try:
                    content = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    content = str(email_message.get_payload())
            
            return {
                'subject': subject,
                'sender': sender,
                'to': to,
                'cc': cc,
                'content': content,
                'html_content': html_content,
                'received_date': received_date,
                'message_id': message_id,
                'attachments': attachments
            }
        
        except Exception as e:
            logger.error(f"❌ Error parsing email: {e}")
            return None
    
    def _decode_header(self, header_value: str) -> str:
        """
        Decode email header value.
        
        Args:
            header_value: Raw header value
        
        Returns:
            Decoded string
        """
        if not header_value:
            return ""
        
        try:
            decoded_parts = decode_header(header_value)
            decoded_string = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding)
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += part
            
            return decoded_string
        
        except Exception as e:
            logger.error(f"❌ Error decoding header: {e}")
            return str(header_value)
    
    async def test_connection(
        self,
        email_address: str,
        password: str,
        provider: str = "gmail",
        imap_server: Optional[str] = None,
        imap_port: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Test IMAP connection.
        
        Args:
            email_address: Email address
            password: Email password or app-specific password
            provider: Provider name
            imap_server: Custom IMAP server (for custom provider)
            imap_port: Custom IMAP port (for custom provider)
        
        Returns:
            Result dictionary with success status and details
        """
        # Get provider configuration
        provider_config = self.get_provider_config(provider)
        
        # Use custom server/port if provided
        if provider == "custom":
            if not imap_server:
                return {
                    "success": False,
                    "error": "Custom provider requires imap_server"
                }
            final_imap_server = imap_server
            final_imap_port = imap_port or 993
        else:
            final_imap_server = provider_config["imap_server"]
            final_imap_port = provider_config["imap_port"]
        
        # Run test in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._test_connection_sync,
            email_address,
            password,
            final_imap_server,
            final_imap_port,
            provider
        )
    
    def _test_connection_sync(
        self,
        email_address: str,
        password: str,
        imap_server: str,
        imap_port: int,
        provider: str
    ) -> Dict[str, Any]:
        """
        Synchronous connection test.
        """
        try:
            logger.info(f"🧪 Testing IMAP connection for {email_address}")
            
            # Create IMAP connection
            imap_conn = imaplib.IMAP4_SSL(imap_server, imap_port, timeout=10)
            
            # Login
            imap_conn.login(email_address, password)
            
            # Test folder access
            folder_status = "Unable to check"
            try:
                imap_conn.select("INBOX")
                folder_status = "Successfully accessed INBOX"
            except Exception as e:
                folder_status = f"Warning: Could not access INBOX: {e}"
            
            # Test search capability
            search_status = "Unable to check"
            try:
                status, messages = imap_conn.search(None, 'ALL')
                if status == 'OK':
                    message_count = len(messages[0].split()) if messages[0] else 0
                    search_status = f"Found {message_count} emails in INBOX"
                else:
                    search_status = "Warning: Could not search emails"
            except Exception as e:
                search_status = f"Warning: Search test failed: {e}"
            
            # Close connection
            imap_conn.close()
            imap_conn.logout()
            
            return {
                "success": True,
                "message": "✅ IMAP connection successful!",
                "details": {
                    "server": f"{imap_server}:{imap_port}",
                    "folder": folder_status,
                    "search": search_status,
                    "provider": provider.title()
                }
            }
        
        except imaplib.IMAP4.error as e:
            error_msg = str(e).lower()
            if "authentication failed" in error_msg or "invalid credentials" in error_msg:
                return {
                    "success": False,
                    "error": "Authentication failed",
                    "help": "Your password or app password might be incorrect. Make sure you're using an App Password (not your regular password)"
                }
            else:
                return {
                    "success": False,
                    "error": f"IMAP error: {e}",
                    "help": "Please check your IMAP server settings and try again"
                }
        
        except Exception as e:
            if "connection refused" in str(e).lower():
                return {
                    "success": False,
                    "error": "Connection refused",
                    "help": "Cannot connect to IMAP server. Check your internet connection and IMAP settings"
                }
            elif "timeout" in str(e).lower():
                return {
                    "success": False,
                    "error": "Connection timeout",
                    "help": "Connection to IMAP server timed out. Check your internet connection"
                }
            else:
                return {
                    "success": False,
                    "error": f"Connection test failed: {e}",
                    "help": "Please check your configuration and try again"
                }


# Singleton instance
_imap_service = None


def get_imap_service() -> IMAPService:
    """Get singleton IMAP service instance"""
    global _imap_service
    if _imap_service is None:
        _imap_service = IMAPService()
    return _imap_service

