"""
Twilio Service - WhatsApp and SMS messaging

Handles WhatsApp message sending through Twilio API.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class TwilioService:
    """
    Service for sending WhatsApp messages via Twilio.
    
    Features:
    - WhatsApp messaging via Twilio API
    - SMS fallback support
    - Media attachment support
    - Delivery status tracking
    - Async execution
    
    Note: Requires twilio library: pip install twilio
    """
    
    async def send_whatsapp(
        self,
        to: str,
        from_number: str,
        account_sid: str,
        auth_token: str,
        body: Optional[str] = None,
        media_url: Optional[List[str]] = None,
        content_sid: Optional[str] = None,
        content_variables: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send WhatsApp message via Twilio.
        
        Args:
            to: Recipient phone number (e.g., +1234567890)
            from_number: Sender WhatsApp number (your Twilio number)
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            body: Message content (for custom messages)
            media_url: Optional list of media URLs to attach
            content_sid: Optional Twilio approved template Content SID (starts with 'HX')
            content_variables: Optional dict of template variables for ContentSID
        
        Returns:
            Result dict with success status and message SID
            
        Example (Custom Message):
            >>> service = TwilioService()
            >>> result = await service.send_whatsapp(
            ...     to="+1234567890",
            ...     body="Your document is incomplete",
            ...     from_number="+14155238886",
            ...     account_sid="AC...",
            ...     auth_token="..."
            ... )
            
        Example (Approved Template):
            >>> result = await service.send_whatsapp(
            ...     to="+1234567890",
            ...     from_number="+14155238886",
            ...     account_sid="AC...",
            ...     auth_token="...",
            ...     content_sid="HXabcd1234...",
            ...     content_variables={"1": "John", "2": "Passport"}
            ... )
        """
        try:
            # Import Twilio library (deferred to avoid requiring it globally)
            try:
                from twilio.rest import Client
                from twilio.base.exceptions import TwilioRestException
            except ImportError:
                logger.error("❌ Twilio library not installed. Run: pip install twilio")
                return {
                    "success": False,
                    "error": "Twilio library not installed. Install with: pip install twilio"
                }
            
            # Ensure WhatsApp prefix
            if not to.startswith("whatsapp:"):
                to = f"whatsapp:{to}"
            if not from_number.startswith("whatsapp:"):
                from_number = f"whatsapp:{from_number}"
            
            logger.info(f"📱 Sending WhatsApp: {from_number} → {to}")
            
            # Create Twilio client
            client = Client(account_sid, auth_token)
            
            # Prepare message parameters
            message_params = {
                "from_": from_number,
                "to": to
            }
            
            # Use approved template (ContentSID) or custom message
            if content_sid:
                # Template mode
                message_params["content_sid"] = content_sid
                logger.info(f"📄 Using approved template: {content_sid}")
                
                if content_variables:
                    # Twilio expects ContentVariables as JSON string
                    import json
                    message_params["content_variables"] = json.dumps(content_variables)
                    logger.debug(f"📋 Template variables: {content_variables}")
            else:
                # Custom message mode
                if not body:
                    logger.error("❌ Either body or content_sid must be provided")
                    return {
                        "success": False,
                        "error": "Either body or content_sid must be provided"
                    }
                
                message_params["body"] = body
                logger.debug(f"Message: {body[:100]}..." if len(body) > 100 else f"Message: {body}")
            
            # Add media URLs if provided (works with both modes)
            if media_url:
                message_params["media_url"] = media_url
                logger.debug(f"📎 Attaching {len(media_url)} media URL(s)")
            
            # Send message (sync call - we'll run in thread pool)
            message = await asyncio.to_thread(
                client.messages.create,
                **message_params
            )
            
            logger.info(f"✅ WhatsApp sent successfully: {message.sid} (status: {message.status})")
            
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status,
                "to": to,
                "from": from_number,
                "body": body
            }
            
        except TwilioRestException as e:
            error_msg = f"Twilio API error: {e.msg}"
            logger.error(f"❌ {error_msg} (code: {e.code})")
            return {
                "success": False,
                "error": error_msg,
                "error_code": e.code,
                "error_details": str(e)
            }
        except Exception as e:
            error_msg = f"Unexpected error sending WhatsApp: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def send_sms(
        self,
        to: str,
        body: str,
        from_number: str,
        account_sid: str,
        auth_token: str,
        media_url: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send SMS message via Twilio.
        
        Args:
            to: Recipient phone number (e.g., +1234567890)
            body: Message content
            from_number: Sender phone number (your Twilio number)
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            media_url: Optional list of media URLs to attach (MMS)
        
        Returns:
            Result dict with success status and message SID
        """
        try:
            try:
                from twilio.rest import Client
                from twilio.base.exceptions import TwilioRestException
            except ImportError:
                return {
                    "success": False,
                    "error": "Twilio library not installed. Install with: pip install twilio"
                }
            
            logger.info(f"📱 Sending SMS: {from_number} → {to}")
            
            # Create Twilio client
            client = Client(account_sid, auth_token)
            
            # Prepare message parameters
            message_params = {
                "body": body,
                "from_": from_number,
                "to": to
            }
            
            if media_url:
                message_params["media_url"] = media_url
            
            # Send message
            message = await asyncio.to_thread(
                client.messages.create,
                **message_params
            )
            
            logger.info(f"✅ SMS sent successfully: {message.sid}")
            
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status,
                "to": to,
                "from": from_number
            }
            
        except TwilioRestException as e:
            error_msg = f"Twilio API error: {e.msg}"
            logger.error(f"❌ {error_msg} (code: {e.code})")
            return {
                "success": False,
                "error": error_msg,
                "error_code": e.code
            }
        except Exception as e:
            error_msg = f"Unexpected error sending SMS: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def get_message_status(
        self,
        message_sid: str,
        account_sid: str,
        auth_token: str
    ) -> Dict[str, Any]:
        """
        Get status of a sent message.
        
        Args:
            message_sid: Twilio message SID
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
        
        Returns:
            Message status dict
        """
        try:
            try:
                from twilio.rest import Client
                from twilio.base.exceptions import TwilioRestException
            except ImportError:
                return {
                    "success": False,
                    "error": "Twilio library not installed"
                }
            
            client = Client(account_sid, auth_token)
            
            # Fetch message
            message = await asyncio.to_thread(
                client.messages(message_sid).fetch
            )
            
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status,
                "to": message.to,
                "from": message.from_,
                "body": message.body,
                "date_sent": message.date_sent.isoformat() if message.date_sent else None,
                "error_code": message.error_code,
                "error_message": message.error_message
            }
            
        except TwilioRestException as e:
            return {
                "success": False,
                "error": f"Twilio API error: {e.msg}",
                "error_code": e.code
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_twilio_service: Optional[TwilioService] = None


def get_twilio_service() -> TwilioService:
    """Get singleton Twilio service instance"""
    global _twilio_service
    if _twilio_service is None:
        _twilio_service = TwilioService()
    return _twilio_service

