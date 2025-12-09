"""
WhatsApp Send Node - Send WhatsApp messages via Twilio

Features:
- Send text messages via WhatsApp
- Attach media files (images, PDFs, etc.)
- Credential manager integration
- Template variable support
- Manual or credential-based authentication
"""

import logging
from typing import Dict, Any, List, Optional
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
from app.services.twilio_service import get_twilio_service

logger = logging.getLogger(__name__)


@register_node(
    node_type="whatsapp_send",
    category=NodeCategory.COMMUNICATION,
    name="WhatsApp Send",
    description="Send WhatsApp messages via Twilio. Supports text messages and media attachments.",
    icon="fa-brands fa-whatsapp",
    version="1.0.0"
)
class WhatsAppSendNode(Node):
    """
    WhatsApp Send Node - Send messages via Twilio WhatsApp Business API
    
    Features:
    - Text messages
    - Media attachments (images, documents, etc.)
    - Credential manager integration
    - Template variable support ({{node.variable}})
    - Phone number validation
    
    Requirements:
    - Twilio account with WhatsApp enabled
    - Verified WhatsApp sender number
    - Recipient must have initiated conversation (WhatsApp requirement)
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "trigger",
                "type": PortType.SIGNAL,
                "display_name": "Trigger",
                "description": "Trigger input to send WhatsApp message",
                "required": False
            },
            {
                "name": "message_content",
                "type": PortType.UNIVERSAL,
                "display_name": "Message Content",
                "description": "Message text content (overrides config if provided)",
                "required": False
            },
            {
                "name": "media_url",
                "type": PortType.UNIVERSAL,
                "display_name": "Media URL",
                "description": "URL to media file to attach (image, PDF, etc.)",
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
                "display_name": "Send Result",
                "description": "Result of WhatsApp send operation (success, message_sid, status)",
            },
            {
                "name": "message_sid",
                "type": PortType.TEXT,
                "display_name": "Message SID",
                "description": "Twilio message SID for tracking",
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            # Authentication Mode
            "auth_mode": {
                "type": "select",
                "label": "Authentication",
                "description": "How to authenticate with Twilio",
                "required": True,
                "options": [
                    {"label": "From Credential Manager", "value": "credential"},
                    {"label": "Manual (Enter credentials)", "value": "manual"}
                ],
                "default": "credential",
                "widget": "select"
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
                "label": "Account SID",
                "description": "Your Twilio Account SID (starts with 'AC')",
                "required": False,
                "placeholder": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "widget": "text",
                "visible_when": {"auth_mode": "manual"}
            },
            "auth_token": {
                "type": "string",
                "label": "Auth Token",
                "description": "Your Twilio Auth Token",
                "required": False,
                "widget": "password",
                "visible_when": {"auth_mode": "manual"}
            },
            "whatsapp_from": {
                "type": "string",
                "label": "WhatsApp From Number",
                "description": "Your Twilio WhatsApp number (e.g., +14155238886)",
                "required": False,
                "placeholder": "+14155238886",
                "widget": "text",
                "help": "Must be a Twilio WhatsApp-enabled number",
                "visible_when": {"auth_mode": "manual"}
            },
            
            # Message Content
            "to_number": {
                "type": "string",
                "label": "Recipient Phone Number",
                "description": "Recipient's phone number in international format (supports {{variables}})",
                "required": True,
                "placeholder": "+1234567890 or {{json_parser.phone_number}}",
                "widget": "text",
                "help": "Must include country code (e.g., +1 for US, +66 for Thailand)"
            },
            
            # Template vs Custom Message
            "message_mode": {
                "type": "select",
                "label": "Message Type",
                "description": "Use approved template or custom message",
                "required": True,
                "options": [
                    {"label": "Custom Message", "value": "custom"},
                    {"label": "Approved Template (ContentSID)", "value": "template"}
                ],
                "default": "custom",
                "widget": "select",
                "help": "Templates require prior approval from Twilio/WhatsApp"
            },
            
            # Custom Message Mode
            "message_body": {
                "type": "string",
                "label": "Message Body",
                "description": "Message text content (supports {{variables}})",
                "required": False,
                "widget": "textarea",
                "placeholder": "Your document submission is incomplete. Please resubmit your passport.",
                "rows": 6,
                "help": "Use {{node.variable}} to insert dynamic content",
                "visible_when": {"message_mode": "custom"}
            },
            
            # Template Mode
            "content_sid": {
                "type": "string",
                "label": "Content SID",
                "description": "Twilio approved template Content SID (starts with 'HX')",
                "required": False,
                "placeholder": "HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "widget": "text",
                "visible_when": {"message_mode": "template"},
                "help": "Find this in your Twilio Console under Messaging > Content Templates"
            },
            "content_variables": {
                "type": "string",
                "label": "Template Variables (JSON)",
                "description": "Template variables as JSON (supports {{variables}})",
                "required": False,
                "widget": "textarea",
                "placeholder": '{"1": "John", "2": "{{json_parser.document_type}}"}',
                "rows": 4,
                "visible_when": {"message_mode": "template"},
                "help": "Map template placeholder numbers to values. Example: {\"1\": \"value1\", \"2\": \"value2\"}"
            },
            
            # Media Options
            "include_media": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Include Media Attachment",
                "description": "Attach media file (image, PDF, etc.)",
                "required": False,
                "default": False
            },
            "media_url": {
                "type": "string",
                "label": "Media URL",
                "description": "URL to media file (must be publicly accessible, supports {{variables}})",
                "required": False,
                "placeholder": "https://example.com/file.jpg or {{file_node.url}}",
                "widget": "text",
                "show_if": {"include_media": True},
                "help": "Supports images (JPG, PNG), documents (PDF), video, audio"
            },
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute WhatsApp send node"""
        try:
            logger.info(f"📱 WhatsApp Send Node executing: {self.node_id}")
            
            # DEBUG: Log the entire config to see what we have
            logger.info(f"🔍 Node config keys: {list(input_data.config.keys())}")
            logger.info(f"🔍 auth_mode: {input_data.config.get('auth_mode')}")
            logger.info(f"🔍 credential_id: {input_data.config.get('credential_id')}")
            logger.info(f"🔍 credentials dict: {input_data.credentials}")
            
            # Get authentication credentials
            auth_mode = self.resolve_config(input_data, "auth_mode", "credential")
            
            if auth_mode == "credential":
                # Get from credential manager
                credential = self.resolve_credential(input_data, "credential_id")
                if not credential:
                    error_msg = "Twilio credential not found. Please select a valid credential."
                    logger.error(f"❌ {error_msg}")
                    return {
                        "result": {"success": False, "error": error_msg},
                        "message_sid": None
                    }
                
                # Extract Twilio credentials
                account_sid = credential.get("account_sid")
                auth_token = credential.get("auth_token")
                whatsapp_from = credential.get("whatsapp_from")
                
                if not account_sid or not auth_token:
                    error_msg = "Invalid Twilio credential: missing account_sid or auth_token"
                    logger.error(f"❌ {error_msg}")
                    return {
                        "result": {"success": False, "error": error_msg},
                        "message_sid": None
                    }
                
                logger.info(f"🔐 Using credential for Twilio: {account_sid[:10]}...")
            else:
                # Manual mode - get from config
                account_sid = self.resolve_config(input_data, "account_sid")
                auth_token = self.resolve_config(input_data, "auth_token")
                whatsapp_from = self.resolve_config(input_data, "whatsapp_from")
                
                if not account_sid or not auth_token or not whatsapp_from:
                    error_msg = "Manual mode requires account_sid, auth_token, and whatsapp_from"
                    logger.error(f"❌ {error_msg}")
                    return {
                        "result": {"success": False, "error": error_msg},
                        "message_sid": None
                    }
            
            # Get recipient phone number
            to_number = self.resolve_config(input_data, "to_number")
            if not to_number:
                error_msg = "Recipient phone number is required"
                logger.error(f"❌ {error_msg}")
                return {
                    "result": {"success": False, "error": error_msg},
                    "message_sid": None
                }
            
            # Clean and validate phone number
            to_number = str(to_number).strip()
            if not to_number.startswith("+"):
                logger.warning(f"⚠️ Phone number doesn't start with '+': {to_number}")
                logger.warning(f"⚠️ Adding '+' prefix. Ensure country code is included!")
                to_number = f"+{to_number}"
            
            # Check message mode (custom vs template)
            message_mode = self.resolve_config(input_data, "message_mode", "custom")
            
            message_body = None
            content_sid = None
            content_variables = None
            
            if message_mode == "template":
                # Template mode - get ContentSID
                content_sid = self.resolve_config(input_data, "content_sid")
                if not content_sid:
                    error_msg = "Content SID is required when using template mode"
                    logger.error(f"❌ {error_msg}")
                    return {
                        "result": {"success": False, "error": error_msg},
                        "message_sid": None
                    }
                
                content_sid = str(content_sid).strip()
                
                # Get template variables (optional)
                content_vars_str = self.resolve_config(input_data, "content_variables")
                if content_vars_str:
                    import json
                    try:
                        content_variables = json.loads(str(content_vars_str))
                        logger.info(f"📋 Template variables: {content_variables}")
                    except json.JSONDecodeError as e:
                        error_msg = f"Invalid JSON in content_variables: {e}"
                        logger.error(f"❌ {error_msg}")
                        return {
                            "result": {"success": False, "error": error_msg},
                            "message_sid": None
                        }
                
                logger.info(f"📄 Using approved template: {content_sid}")
            else:
                # Custom message mode - get message body
                from app.core.nodes.multimodal import extract_content
                message_input = input_data.ports.get("message_content")
                message_body = extract_content(message_input) if message_input else None
                
                if not message_body:
                    message_body = self.resolve_config(input_data, "message_body")
                
                if not message_body:
                    error_msg = "Message body is required in custom message mode"
                    logger.error(f"❌ {error_msg}")
                    return {
                        "result": {"success": False, "error": error_msg},
                        "message_sid": None
                    }
                
                message_body = str(message_body).strip()
            
            # Get media URL (from port input or config)
            media_urls = None
            include_media = self.resolve_config(input_data, "include_media", False)
            
            if include_media:
                media_url = input_data.ports.get("media_url")
                if not media_url:
                    media_url = self.resolve_config(input_data, "media_url")
                
                if media_url:
                    media_url = str(media_url).strip()
                    media_urls = [media_url]
                    logger.info(f"📎 Media attachment: {media_url}")
            
            # Validate sender number
            if not whatsapp_from:
                error_msg = "WhatsApp from number is required (configured in credential or manual settings)"
                logger.error(f"❌ {error_msg}")
                return {
                    "result": {"success": False, "error": error_msg},
                    "message_sid": None
                }
            
            # Get Twilio service
            twilio_service = get_twilio_service()
            
            # Send WhatsApp message
            logger.info(f"📱 Sending WhatsApp: {whatsapp_from} → {to_number}")
            if message_mode == "template":
                logger.info(f"📄 Using template: {content_sid}")
            else:
                logger.info(f"📝 Message: {message_body[:100]}{'...' if len(message_body) > 100 else ''}")
            
            result = await twilio_service.send_whatsapp(
                to=to_number,
                body=message_body,
                from_number=whatsapp_from,
                account_sid=account_sid,
                auth_token=auth_token,
                media_url=media_urls,
                content_sid=content_sid,
                content_variables=content_variables
            )
            
            if result.get("success"):
                message_sid = result.get("message_sid")
                logger.info(f"✅ WhatsApp sent successfully: {message_sid}")
                return {
                    "result": result,
                    "message_sid": message_sid
                }
            else:
                error = result.get("error", "Unknown error")
                logger.error(f"❌ WhatsApp send failed: {error}")
                return {
                    "result": result,
                    "message_sid": None
                }
        
        except Exception as e:
            error_msg = f"WhatsApp send error: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                "result": {"success": False, "error": error_msg},
                "message_sid": None
            }


if __name__ == "__main__":
    print("✅ WhatsApp Send Node loaded")

