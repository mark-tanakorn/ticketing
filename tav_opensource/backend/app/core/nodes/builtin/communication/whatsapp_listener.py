"""
WhatsApp Listener Node - Poll Twilio for incoming WhatsApp messages

Polls Twilio API for new messages, pauses workflow until message arrives.
Extracts message content and media, downloads images for workflow processing.
"""

import asyncio
import logging
import aiohttp
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
from app.services.twilio_service import get_twilio_service

logger = logging.getLogger(__name__)


@register_node(
    node_type="whatsapp_listener",
    category=NodeCategory.COMMUNICATION,
    name="WhatsApp Listener",
    description="Listen for incoming WhatsApp messages (polling mode). Pauses workflow until message received.",
    icon="fa-brands fa-whatsapp",
    version="1.0.0"
)
class WhatsAppListenerNode(Node):
    """
    WhatsApp Listener Node - Receive WhatsApp Messages via Polling
    
    **How It Works:**
    1. Node executes and starts polling Twilio API
    2. Workflow PAUSES (human-in-the-loop pattern)
    3. Polls every X seconds for new messages to specified number
    4. When message arrives:
       - Extracts message body (text)
       - Downloads media attachments (images)
       - Saves to file system
       - Resumes workflow with message data
    
    **Features:**
    - Configurable polling interval (1-60 seconds)
    - Timeout support (max wait time)
    - Media download (images, documents)
    - Message filtering (from specific sender)
    - Auto-resume workflow on message receipt
    
    **Use Cases:**
    - Document resubmission workflows (expired passport scenario)
    - Interactive forms (collect info via WhatsApp)
    - Approval workflows (admin responds via WhatsApp)
    - Customer support (wait for user reply)
    
    **Requirements:**
    - Twilio account with WhatsApp enabled
    - Credential manager or manual credentials
    - `from_number` must match message sender
    
    ⚠️ **Important Notes:**
    - This pauses the workflow - no nodes run while waiting
    - Long polling can tie up execution resources
    - Consider timeout to prevent infinite waiting
    - Polling interval affects near-realtime responsiveness
    - 1-2 seconds = near instant (recommended for user-facing)
    - 5-10 seconds = moderate (good for notifications)
    - 30-60 seconds = slow (background processes only)
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "trigger",
                "type": PortType.SIGNAL,
                "display_name": "Trigger",
                "description": "Trigger input to start listening",
                "required": False
            },
            {
                "name": "context",
                "type": PortType.UNIVERSAL,
                "display_name": "Context",
                "description": "Optional context data to pass through",
                "required": False
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "message_body",
                "type": PortType.TEXT,
                "display_name": "Message Text",
                "description": "Text content of the message"
            },
            {
                "name": "media",
                "type": PortType.UNIVERSAL,
                "display_name": "Media Files",
                "description": "Array of downloaded media files (images, documents)"
            },
            {
                "name": "message_metadata",
                "type": PortType.UNIVERSAL,
                "display_name": "Message Metadata",
                "description": "Message metadata (sid, timestamp, from, etc.)"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            # Authentication Mode
            "auth_mode": {
                "type": "select",
                "widget": "select",
                "label": "Authentication",
                "description": "How to authenticate with Twilio",
                "required": True,
                "options": [
                    {"label": "From Credential Manager", "value": "credential"},
                    {"label": "Manual (Enter credentials)", "value": "manual"}
                ],
                "default": "credential"
            },
            
            # Credential Mode
            "credential_id": {
                "type": "credential",
                "widget": "credential",
                "label": "Twilio Credential",
                "description": "Select saved Twilio credential",
                "required": False,
                "visible_when": {"auth_mode": "credential"},
            },
            
            # Manual Mode - Twilio Credentials
            "account_sid": {
                "type": "string",
                "widget": "text",
                "label": "Account SID",
                "description": "Your Twilio Account SID (starts with 'AC')",
                "required": False,
                "placeholder": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "visible_when": {"auth_mode": "manual"}
            },
            "auth_token": {
                "type": "string",
                "widget": "password",
                "label": "Auth Token",
                "description": "Your Twilio Auth Token",
                "required": False,
                "visible_when": {"auth_mode": "manual"}
            },
            "whatsapp_from": {
                "type": "string",
                "widget": "text",
                "label": "WhatsApp From Number",
                "description": "Your Twilio WhatsApp number (e.g., +14155238886)",
                "required": False,
                "placeholder": "+14155238886",
                "help": "Must be a Twilio WhatsApp-enabled number",
                "visible_when": {"auth_mode": "manual"}
            },
            
            # Listening Configuration
            "to_number": {
                "type": "string",
                "widget": "text",
                "label": "Listen For Number",
                "description": "Phone number to listen for messages FROM (supports {{variables}})",
                "required": True,
                "placeholder": "+1234567890 or {{json_parser.phone_number}}",
                "help": "The user's number that will SEND the message. Must include country code."
            },
            
            # Polling Configuration
            "polling_interval": {
                "type": "integer",
                "widget": "number",
                "label": "Polling Interval (seconds)",
                "description": "How often to check for new messages",
                "required": False,
                "default": 2,
                "min": 1,
                "max": 60,
                "help": "1-2s = near-instant, 5-10s = moderate, 30-60s = slow. Lower = more API calls."
            },
            "timeout_seconds": {
                "type": "integer",
                "widget": "number",
                "label": "Timeout (seconds)",
                "description": "Maximum time to wait for message. 0 = wait forever (not recommended!)",
                "required": False,
                "default": 300,  # 5 minutes default
                "min": 0,
                "max": 3600,  # 1 hour max
                "help": "After timeout, node will fail. 0 = infinite wait (can cause stuck workflows)."
            },
            
            # Message Filtering
            "listen_mode": {
                "type": "select",
                "widget": "select",
                "label": "Listen Mode",
                "description": "How to handle message timing",
                "required": False,
                "default": "new_only",
                "options": [
                    {"label": "New Messages Only (after listener starts)", "value": "new_only"},
                    {"label": "Include Recent (look back X minutes)", "value": "include_recent"}
                ],
                "help": "New Only = ignore all messages sent before listener started (RECOMMENDED). Include Recent = also check old messages."
            },
            "since_minutes": {
                "type": "integer",
                "widget": "number",
                "label": "Look Back Window (minutes)",
                "description": "How far back to check for messages (only if Include Recent mode)",
                "required": False,
                "default": 5,
                "min": 1,
                "max": 60,
                "visible_when": {"listen_mode": "include_recent"},
                "help": "Only used in 'Include Recent' mode. Set to time since WhatsApp Send + buffer."
            },
            
            # Media Handling
            "download_media": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Download Media Attachments",
                "description": "Automatically download images/documents attached to message",
                "required": False,
                "default": True,
                "help": "If enabled, media files will be downloaded and saved to server."
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute WhatsApp listener node with polling"""
        try:
            logger.info(f"📱 WhatsApp Listener Node executing: {self.node_id}")
            
            # Get authentication credentials
            auth_mode = self.resolve_config(input_data, "auth_mode", "credential")
            
            if auth_mode == "credential":
                credential = self.resolve_credential(input_data, "credential_id")
                if not credential:
                    error_msg = "Twilio credential not found. Please select a valid credential."
                    logger.error(f"❌ {error_msg}")
                    return {
                        "message_body": "",
                        "media": [],
                        "message_metadata": {"error": error_msg}
                    }
                
                account_sid = credential.get("account_sid")
                auth_token = credential.get("auth_token")
                whatsapp_from = credential.get("whatsapp_from")
            else:
                account_sid = self.resolve_config(input_data, "account_sid")
                auth_token = self.resolve_config(input_data, "auth_token")
                whatsapp_from = self.resolve_config(input_data, "whatsapp_from")
            
            # Validate credentials
            if not account_sid or not auth_token or not whatsapp_from:
                error_msg = "Missing Twilio credentials (account_sid, auth_token, whatsapp_from)"
                logger.error(f"❌ {error_msg}")
                return {
                    "message_body": "",
                    "media": [],
                    "message_metadata": {"error": error_msg}
                }
            
            # Get configuration
            to_number = self.resolve_config(input_data, "to_number")
            if not to_number:
                error_msg = "Recipient phone number (to_number) is required"
                logger.error(f"❌ {error_msg}")
                return {
                    "message_body": "",
                    "media": [],
                    "message_metadata": {"error": error_msg}
                }
            
            # Clean phone number
            to_number = str(to_number).strip()
            if not to_number.startswith("+"):
                to_number = f"+{to_number}"
            
            polling_interval = self.resolve_config(input_data, "polling_interval", 2)
            timeout_seconds = self.resolve_config(input_data, "timeout_seconds", 300)
            listen_mode = self.resolve_config(input_data, "listen_mode", "new_only")
            since_minutes = self.resolve_config(input_data, "since_minutes", 5)
            download_media = self.resolve_config(input_data, "download_media", True)
            
            # Store listener start time for "new_only" mode
            # IMPORTANT: Store as UTC for consistent comparison with Twilio API timestamps
            listener_start_time_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
            
            logger.info(
                f"🔊 Listening for WhatsApp message:\n"
                f"  From (user): {to_number}\n"
                f"  To (our number): {whatsapp_from}\n"
                f"  Mode: {listen_mode}\n"
                f"  Poll interval: {polling_interval}s\n"
                f"  Timeout: {timeout_seconds}s\n"
                f"  {'Listener started at: ' + listener_start_time_utc.strftime('%H:%M:%S UTC') if listen_mode == 'new_only' else f'Look back: {since_minutes}m'}"
            )
            
            # Start polling loop
            start_time = datetime.now()
            message_found = None
            elapsed = 0
            
            while True:
                # Check timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if timeout_seconds > 0 and elapsed >= timeout_seconds:
                    error_msg = f"Timeout after {elapsed:.1f}s - no message received from {to_number}"
                    logger.error(f"⏱️ {error_msg}")
                    return {
                        "message_body": "",
                        "media": [],
                        "message_metadata": {
                            "error": error_msg,
                            "timeout": True,
                            "elapsed_seconds": elapsed
                        }
                    }
                
                # Poll for messages
                logger.debug(f"🔍 Polling for messages... (elapsed: {elapsed:.1f}s)")
                
                messages = await self._fetch_recent_messages(
                    account_sid=account_sid,
                    auth_token=auth_token,
                    from_number=to_number,
                    to_number=whatsapp_from,
                    since_minutes=since_minutes,
                    listen_mode=listen_mode,
                    listener_start_time=listener_start_time_utc
                )
                
                if messages:
                    # Found message(s)!
                    message_found = messages[0]  # Get most recent
                    logger.info(
                        f"✅ Message received from {to_number}!\n"
                        f"  SID: {message_found.get('sid')}\n"
                        f"  Body: {message_found.get('body', '')[:100]}\n"
                        f"  Media: {message_found.get('num_media', 0)} file(s)"
                    )
                    break
                
                # No message yet, wait and poll again
                logger.debug(f"⏳ No message yet, waiting {polling_interval}s...")
                await asyncio.sleep(polling_interval)
            
            # Process message
            message_body = message_found.get("body", "")
            message_sid = message_found.get("sid")
            num_media = int(message_found.get("num_media", 0))
            
            # MEDIA RETRY LOGIC: WhatsApp media takes time to upload to Twilio
            # If num_media is 0, wait and re-fetch the message to check again
            if num_media == 0:
                logger.debug(f"📎 No media found initially, checking if media is still uploading...")
                message_found = await self._retry_fetch_message_for_media(
                    account_sid=account_sid,
                    auth_token=auth_token,
                    message_sid=message_sid,
                    max_retries=3,
                    retry_delay=2.0
                )
                num_media = int(message_found.get("num_media", 0))
                if num_media > 0:
                    logger.info(f"✅ Media found after retry: {num_media} file(s)")
                else:
                    logger.debug(f"ℹ️ No media attachments in this message")
            
            # Download media if configured
            media_files = []
            if download_media and num_media > 0:
                logger.info(f"📎 Downloading {num_media} media file(s)...")
                media_files = await self._download_media(
                    account_sid=account_sid,
                    auth_token=auth_token,
                    message_sid=message_sid,
                    num_media=num_media
                )
                logger.info(f"✅ Downloaded {len(media_files)} media file(s)")
            
            # Build metadata
            metadata = {
                "message_sid": message_sid,
                "from_number": to_number,
                "to_number": whatsapp_from,
                "timestamp": message_found.get("date_sent"),
                "num_media": num_media,
                "media_downloaded": len(media_files),
                "elapsed_seconds": elapsed,
                "polling_interval": polling_interval
            }
            
            logger.info(
                f"✅ WhatsApp Listener completed:\n"
                f"  Message: {len(message_body)} chars\n"
                f"  Media: {len(media_files)} file(s)\n"
                f"  Elapsed: {elapsed:.1f}s"
            )
            
            return {
                "message_body": message_body,
                "media": media_files,
                "message_metadata": metadata
            }
            
        except Exception as e:
            error_msg = f"WhatsApp listener error: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                "message_body": "",
                "media": [],
                "message_metadata": {"error": error_msg}
            }
    
    async def _retry_fetch_message_for_media(
        self,
        account_sid: str,
        auth_token: str,
        message_sid: str,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> Dict[str, Any]:
        """
        Retry fetching a specific message to check for media.
        
        WhatsApp media can take 1-3 seconds to upload to Twilio's servers.
        This method re-fetches the same message multiple times to check if media appears.
        
        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            message_sid: The specific message SID to re-fetch
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Seconds to wait between retries (default: 2.0)
            
        Returns:
            Updated message dict with latest num_media value
        """
        logger.debug(f"🔄 Starting media retry for message {message_sid} (max {max_retries} attempts)")
        
        for attempt in range(1, max_retries + 1):
            await asyncio.sleep(retry_delay)
            
            try:
                # Fetch specific message by SID
                url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages/{message_sid}.json"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        auth=aiohttp.BasicAuth(account_sid, auth_token),
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            message = await response.json()
                            num_media = int(message.get("num_media", 0))
                            
                            logger.debug(
                                f"  🔄 Retry {attempt}/{max_retries}: "
                                f"NumMedia = {num_media}"
                            )
                            
                            if num_media > 0:
                                logger.info(f"✅ Media appeared after {attempt} retries ({attempt * retry_delay:.1f}s)")
                                return message
                        else:
                            logger.warning(
                                f"  ⚠️ Retry {attempt}/{max_retries} failed: "
                                f"HTTP {response.status}"
                            )
            except Exception as e:
                logger.warning(f"  ⚠️ Retry {attempt}/{max_retries} error: {e}")
        
        # Return original message data if all retries exhausted
        logger.debug(f"ℹ️ Media did not appear after {max_retries} retries ({max_retries * retry_delay:.1f}s)")
        return {"sid": message_sid, "num_media": 0, "body": ""}
    
    async def _fetch_recent_messages(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        to_number: str,
        since_minutes: int,
        listen_mode: str = "new_only",
        listener_start_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent messages from Twilio API.
        
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: Sender's phone number (user)
            to_number: Recipient's phone number (our WhatsApp number)
            since_minutes: Only return messages from last X minutes (if include_recent mode)
            listen_mode: "new_only" or "include_recent"
            listener_start_time: When the listener started (for new_only mode)
        
        Returns:
            List of message dicts (sorted newest first)
        """
        try:
            # Build Twilio API URL
            # Messages API: https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Messages.json
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            
            # Calculate date filter based on mode
            if listen_mode == "new_only" and listener_start_time:
                # Only look for messages sent AFTER listener started
                # Use listener start time minus 5 seconds buffer for clock skew
                since_time = listener_start_time - timedelta(seconds=5)
                date_filter = since_time.strftime("%Y-%m-%d %H:%M:%S")  # Full datetime
                logger.debug(f"🕐 New-only mode: Only messages after {since_time.strftime('%H:%M:%S')}")
            else:
                # Include recent mode - look back X minutes
                since_time = datetime.utcnow() - timedelta(minutes=since_minutes)
                date_filter = since_time.strftime("%Y-%m-%d")  # YYYY-MM-DD format
                logger.debug(f"🕐 Include-recent mode: Looking back {since_minutes} minutes")
            
            # Ensure WhatsApp prefix
            from_whatsapp = f"whatsapp:{from_number}" if not from_number.startswith("whatsapp:") else from_number
            to_whatsapp = f"whatsapp:{to_number}" if not to_number.startswith("whatsapp:") else to_number
            
            # Query parameters
            params = {
                "From": from_whatsapp,
                "To": to_whatsapp,
                "DateSent>": date_filter,
                "PageSize": 10  # Limit results
            }
            
            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    auth=aiohttp.BasicAuth(account_sid, auth_token),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ Twilio API error ({response.status}): {error_text}")
                        return []
                    
                    data = await response.json()
                    messages = data.get("messages", [])
                    
                    # Additional filtering for new_only mode
                    if listen_mode == "new_only" and listener_start_time and messages:
                        # Filter to only messages sent AFTER listener started
                        filtered_messages = []
                        for msg in messages:
                            # Parse message timestamp
                            date_sent_str = msg.get("date_sent")
                            if date_sent_str:
                                try:
                                    # Twilio format: "Thu, 17 Nov 2025 03:00:55 +0000"
                                    from datetime import datetime as dt
                                    msg_time = dt.strptime(date_sent_str, "%a, %d %b %Y %H:%M:%S %z")
                                    
                                    # Compare: Both are timezone-aware now
                                    if msg_time > listener_start_time:
                                        filtered_messages.append(msg)
                                        logger.debug(f"  ✅ Message {msg.get('sid')} sent at {msg_time.strftime('%H:%M:%S %Z')} (AFTER listener start)")
                                    else:
                                        logger.debug(f"  ⏭️ Message {msg.get('sid')} sent at {msg_time.strftime('%H:%M:%S %Z')} (BEFORE listener start, skipping)")
                                except Exception as e:
                                    logger.warning(f"  ⚠️ Could not parse message timestamp: {e}")
                                    # If we can't parse timestamp, include it to be safe
                                    filtered_messages.append(msg)
                        
                        messages = filtered_messages
                        if messages:
                            logger.debug(f"📬 Found {len(messages)} NEW message(s) from {from_number} (after filtering)")
                    elif messages:
                        logger.debug(f"📬 Found {len(messages)} message(s) from {from_number}")
                    
                    return messages
        
        except Exception as e:
            logger.error(f"❌ Error fetching messages: {e}", exc_info=True)
            return []
    
    async def _download_media(
        self,
        account_sid: str,
        auth_token: str,
        message_sid: str,
        num_media: int
    ) -> List[Dict[str, Any]]:
        """
        Download media attachments from message.
        
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            message_sid: Message SID
            num_media: Number of media attachments
        
        Returns:
            List of media file dicts with file paths
        """
        media_files = []
        
        try:
            for media_index in range(num_media):
                # Build media URL
                # Media API: https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Messages/{MessageSid}/Media/{MediaSid}.json
                media_list_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages/{message_sid}/Media.json"
                
                # Fetch media list
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        media_list_url,
                        auth=aiohttp.BasicAuth(account_sid, auth_token),
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status != 200:
                            logger.error(f"❌ Failed to fetch media list: {response.status}")
                            continue
                        
                        data = await response.json()
                        media_list = data.get("media_list", [])
                        
                        if not media_list:
                            logger.warning(f"⚠️ No media found for message {message_sid}")
                            break
                        
                        # Download each media file
                        for media_item in media_list:
                            media_url = f"https://api.twilio.com{media_item['uri'].replace('.json', '')}"
                            content_type = media_item.get("content_type", "application/octet-stream")
                            media_sid = media_item.get("sid")
                            
                            # Download media content
                            async with session.get(
                                media_url,
                                auth=aiohttp.BasicAuth(account_sid, auth_token),
                                timeout=aiohttp.ClientTimeout(total=30)
                            ) as media_response:
                                if media_response.status != 200:
                                    logger.error(f"❌ Failed to download media: {media_response.status}")
                                    continue
                                
                                media_bytes = await media_response.read()
                                
                                # Determine file extension from content type
                                ext = self._get_extension_from_content_type(content_type)
                                
                                # Save to file system
                                uploads_dir = Path("data/uploads")
                                uploads_dir.mkdir(parents=True, exist_ok=True)
                                
                                filename = f"whatsapp_{media_sid}{ext}"
                                file_path = uploads_dir / filename
                                
                                with open(file_path, "wb") as f:
                                    f.write(media_bytes)
                                
                                logger.info(f"✅ Downloaded media: {filename} ({len(media_bytes)} bytes)")
                                
                                # Build file reference
                                media_files.append({
                                    "media_sid": media_sid,
                                    "filename": filename,
                                    "file_path": str(file_path),
                                    "storage_path": f"uploads/{filename}",
                                    "content_type": content_type,
                                    "size_bytes": len(media_bytes),
                                    "modality": self._get_modality_from_content_type(content_type)
                                })
        
        except Exception as e:
            logger.error(f"❌ Error downloading media: {e}", exc_info=True)
        
        return media_files
    
    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Map content type to file extension"""
        mapping = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "application/pdf": ".pdf",
            "application/msword": ".doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "text/plain": ".txt",
        }
        return mapping.get(content_type, ".bin")
    
    def _get_modality_from_content_type(self, content_type: str) -> str:
        """Determine media modality from content type"""
        if content_type.startswith("image/"):
            return "image"
        elif content_type.startswith("video/"):
            return "video"
        elif content_type.startswith("audio/"):
            return "audio"
        elif content_type == "application/pdf":
            return "document"
        else:
            return "file"


if __name__ == "__main__":
    print("✅ WhatsApp Listener Node loaded")

