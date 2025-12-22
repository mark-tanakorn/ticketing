"""
Email Composer Node - Draft and send emails with AI assistance

Features:
- Multi-provider support (Gmail, Outlook, Yahoo, Office365, Custom)
- AI-powered email generation from freeform prompts
- Manual email composition
- Optional review workflow
- File attachments (manual files + file IDs from variables)
"""

import logging
import re
from typing import Dict, Any, List, Optional
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import LLMCapability
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
from app.services.smtp_service import get_smtp_service, EMAIL_PROVIDERS

logger = logging.getLogger(__name__)


@register_node(
    node_type="email_composer",
    category=NodeCategory.COMMUNICATION,
    name="Email Composer",
    description="Compose and send emails with AI assistance or manual input. Supports multiple email providers.",
    icon="fa-solid fa-envelope-open-text",
    version="1.0.0"
)
class EmailComposerNode(Node, LLMCapability):
    """
    Email Composer Node - Intelligent email composition and sending
    
    Modes:
    1. Manual Draft: User provides subject, body, recipient
    2. AI Draft: AI generates email from freeform prompt
    
    Features:
    - Auto-configured SMTP for popular providers
    - AI can extract recipient from prompt
    - Optional review workflow (pauses for human approval)
    - Direct send mode (sends immediately)
    - File attachments support
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "content",
                "type": PortType.UNIVERSAL,
                "display_name": "Content",
                "description": "Input content for email (used in AI mode or as body in manual mode)",
                "required": False
            },
            {
                "name": "attachments",
                "type": PortType.UNIVERSAL,
                "display_name": "Attachments",
                "description": "File attachments (file IDs from upload nodes or file paths)",
                "required": False
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "draft",
                "type": PortType.UNIVERSAL,
                "display_name": "Email Draft",
                "description": "Email draft output (for approval node if review required)",
            },
            {
                "name": "result",
                "type": PortType.UNIVERSAL,
                "display_name": "Send Result",
                "description": "Result of email sending (if sent directly)",
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
            # Mode Selection
            "composition_mode": {
                "type": "select",
                "label": "Composition Mode",
                "description": "How to compose the email",
                "required": True,
                "options": [
                    {"label": "AI Draft (from prompt)", "value": "ai_draft"},
                    {"label": "Manual Draft", "value": "manual"}
                ],
                "default": "ai_draft",
                "widget": "select"
            },
            "review_required": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Require Review Before Sending",
                "description": "Pause workflow for human review (connect to Email Approval node)",
                "required": False,
                "default": False,
                "help": "If enabled, pauses workflow for review. If disabled, sends immediately."
            },
            
            # Provider & Credentials
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
                "description": "Select saved email credential",
                "required": False,
                "visible_when": {"auth_mode": "credential"}
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
                "visible_when": {"auth_mode": "manual"}
            },
            "from_email": {
                "type": "string",
                "label": "From Email",
                "description": "Your email address",
                "required": False,
                "placeholder": "your.email@example.com",
                "widget": "text",
                "visible_when": {"auth_mode": "manual"}
            },
            "password": {
                "type": "string",
                "label": "Password",
                "description": "Email password or app-specific password",
                "required": False,
                "widget": "password",
                "help": "Gmail/Yahoo: Use app-specific password. Outlook: Regular password or app password.",
                "visible_when": {"auth_mode": "manual"}
            },
            "from_name": {
                "type": "string",
                "label": "From Name (optional)",
                "description": "Display name for sender",
                "required": False,
                "placeholder": "John Doe",
                "widget": "text",
                "visible_when": {"auth_mode": "manual"}
            },
            
            # Custom SMTP (only for custom provider in manual mode)
            "custom_smtp_server": {
                "type": "string",
                "label": "SMTP Server",
                "description": "Your SMTP server address",
                "required": False,
                "placeholder": "smtp.example.com",
                "widget": "text",
                "show_if": {"provider": "custom", "auth_mode": "manual"}
            },
            "custom_smtp_port": {
                "type": "integer",
                "label": "SMTP Port",
                "description": "SMTP port (usually 587 or 465)",
                "required": False,
                "default": 587,
                "widget": "number",
                "show_if": {"provider": "custom", "auth_mode": "manual"}
            },
            
            # AI Draft Mode
            "ai_prompt": {
                "type": "string",
                "label": "AI Prompt",
                "description": "Describe the email you want AI to generate",
                "required": False,
                "widget": "textarea",
                "placeholder": "Example: Tell john@example.com that order #1234 has shipped and will arrive Tuesday",
                "help": "AI will extract recipient, generate subject, and compose body",
                "show_if": {"composition_mode": "ai_draft"},
                "rows": 4
            },
            
            # Manual Draft Mode
            "recipient": {
                "type": "string",
                "label": "Recipient Email",
                "description": "Who to send to (supports {{variables}})",
                "required": False,
                "placeholder": "recipient@example.com",
                "widget": "text",
                "show_if": {"composition_mode": "manual"}
            },
            "subject": {
                "type": "string",
                "label": "Subject",
                "description": "Email subject line (supports {{variables}})",
                "required": False,
                "placeholder": "Your order has shipped",
                "widget": "text",
                "show_if": {"composition_mode": "manual"}
            },
            "body": {
                "type": "string",
                "label": "Body",
                "description": "Email body content (supports {{variables}})",
                "required": False,
                "widget": "textarea",
                "placeholder": "Dear Customer,\n\nYour order has shipped...",
                "show_if": {"composition_mode": "manual"},
                "rows": 8
            },
            
            # Optional Fields (always shown)
            "cc": {
                "type": "string",
                "label": "CC (optional)",
                "description": "CC recipients (comma-separated)",
                "required": False,
                "placeholder": "cc1@example.com, cc2@example.com",
                "widget": "text"
            },
            "bcc": {
                "type": "string",
                "label": "BCC (optional)",
                "description": "BCC recipients (comma-separated)",
                "required": False,
                "placeholder": "bcc1@example.com",
                "widget": "text"
            },
            "reply_to": {
                "type": "string",
                "label": "Reply-To (optional)",
                "description": "Reply-To email address",
                "required": False,
                "placeholder": "replies@example.com",
                "widget": "text"
            },
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute email composer node"""
        try:
            logger.info(f"📧 Email Composer Node executing: {self.node_id}")
            
            # Get composition mode
            composition_mode = self.resolve_config(input_data, "composition_mode", "manual")
            review_required = self.resolve_config(input_data, "review_required", False)
            
            # Compose email based on mode
            if composition_mode == "ai_draft":
                draft = await self._compose_ai_draft(input_data)
            else:
                draft = await self._compose_manual_draft(input_data)
            
            if "error" in draft:
                return {
                    "draft": draft,
                    "result": {"success": False, "error": draft["error"]}
                }
            
            # Get attachments from input port or variables
            attachments = await self._get_attachments(input_data)
            draft["attachments"] = attachments
            
            # Add SMTP config to draft for Email Approval Node to use later
            auth_mode = self.resolve_config(input_data, "auth_mode", "manual")
            
            if auth_mode == "credential":
                # Get credential data
                credential = self.resolve_credential(input_data, "credential_id")
                if not credential:
                    return {
                        "draft": {"error": "Email credential not found"},
                        "result": {"success": False, "error": "Email credential not found"}
                    }
                
                # Handle both email_smtp format and generic smtp format
                # email_smtp: {email, password, provider, from_name, smtp_server, smtp_port}
                # smtp: {host, port, username, password, use_tls}
                
                if "email" in credential:
                    # New email_smtp format
                    from_email = credential.get("email", "")
                    password = credential.get("password", "")
                    provider = credential.get("provider", "gmail")
                    from_name = credential.get("from_name", "")
                    smtp_server = credential.get("smtp_server", "")
                    smtp_port = credential.get("smtp_port", 587)
                elif "username" in credential:
                    # Generic smtp format (username = email, host = smtp_server)
                    from_email = credential.get("username", "")
                    password = credential.get("password", "")
                    provider = "custom"  # Generic SMTP uses custom provider
                    from_name = ""
                    smtp_server = credential.get("host", "")
                    smtp_port = credential.get("port", 587)
                else:
                    return {
                        "draft": {"error": "Invalid credential format (missing email/username)"},
                        "result": {"success": False, "error": "Invalid credential format"}
                    }
                
                # Extract SMTP config from credential
                draft["smtp_config"] = {
                    "provider": provider,
                    "from_email": from_email,
                    "smtp_password": password,
                    "from_name": from_name,
                    "smtp_server": smtp_server,
                    "smtp_port": smtp_port,
                    "auth_mode": "credential"
                }
                logger.info(f"🔐 Using credential for SMTP: {from_email} (provider: {provider})")
            else:
                # Manual mode - get from config
                provider = self.resolve_config(input_data, "provider", "gmail")
                from_email = self.resolve_config(input_data, "from_email", "")
                password = self.resolve_config(input_data, "password", "")
                from_name = self.resolve_config(input_data, "from_name", "")
                
                # Decrypt password if it's encrypted
                from app.security.encryption import decrypt_value, is_encrypted
                if password and is_encrypted(password):
                    try:
                        password = decrypt_value(password)
                        logger.debug("🔓 Decrypted SMTP password")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to decrypt password: {e}")
                
                draft["smtp_config"] = {
                    "provider": provider,
                    "from_email": from_email,
                    "smtp_password": password,
                    "from_name": from_name,
                    "smtp_server": self.resolve_config(input_data, "custom_smtp_server", ""),
                    "smtp_port": self.resolve_config(input_data, "custom_smtp_port", 587),
                    "auth_mode": "manual"
                }
            
            # Decision: Review or Send?
            if review_required:
                logger.info(f"📋 Review required, outputting draft for approval")
                return {
                    "draft": draft,
                    "result": {"status": "draft_created", "review_required": True}
                }
            else:
                logger.info(f"📨 No review required, sending immediately")
                send_result = await self._send_email(draft, input_data)
                return {
                    "draft": draft,
                    "result": send_result
                }
        
        except Exception as e:
            logger.error(f"❌ Email Composer error: {e}", exc_info=True)
            return {
                "draft": {"error": str(e)},
                "result": {"success": False, "error": str(e)}
            }
    
    async def _compose_ai_draft(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Compose email using AI"""
        try:
            # Get AI prompt from config or input
            ai_prompt = self.resolve_config(input_data, "ai_prompt", "")
            
            # If no prompt in config, try to get from input port
            if not ai_prompt:
                content_input = input_data.ports.get("content")
                from app.core.nodes.multimodal import extract_content
                ai_prompt = extract_content(content_input) if content_input else ""
            
            if not ai_prompt:
                return {"error": "No prompt provided for AI draft mode"}
            
            logger.info(f"🤖 Generating AI draft from prompt")
            
            # Build AI prompt for email generation
            # Note: More explicit instructions for local LLMs that struggle with JSON
            system_prompt = """You are an email composition assistant. Your task is to create an email based on the user's request.

RESPONSE FORMAT - YOU MUST RESPOND WITH VALID JSON ONLY:
{
  "recipient": "email@example.com or null",
  "subject": "Email subject line",
  "body": "Email body content"
}

CRITICAL RULES:
1. Output ONLY the JSON object above - NO other text, NO markdown, NO explanations
2. Do NOT wrap the JSON in code blocks or backticks
3. Do NOT add any text before or after the JSON
4. The JSON must be valid and parseable
5. If no recipient is mentioned, use null for recipient
6. Make the subject concise (under 10 words)
7. Make the body professional and well-formatted

Example correct response:
{"recipient": null, "subject": "Meeting Summary", "body": "Here is the summary..."}

Example WRONG response:
Here is the email:
```json
{"recipient": null, "subject": "...", "body": "..."}
```

RESPOND WITH JSON ONLY - START YOUR RESPONSE WITH { AND END WITH }"""
            
            # Call LLM with JSON format forced
            # Note: Some LLMs struggle with JSON, so we use temperature=0 for more deterministic output
            # Try to enable JSON mode if the provider supports it (OpenAI, some local models)
            # Note: max_tokens will use global AI Settings > Default Max Tokens
            llm_config = {
                "temperature": 0,
                # max_tokens intentionally omitted - uses global default_max_tokens from AI Settings
            }
            
            # Try to force JSON mode for OpenAI-compatible providers
            # This helps ensure the model returns valid JSON
            try:
                llm_response = await self.call_llm(
                    user_prompt=ai_prompt,
                    system_prompt=system_prompt,
                    response_format={"type": "json_object"},  # OpenAI JSON mode
                    **llm_config
                )
            except (TypeError, ValueError):
                # Fallback: response_format not supported by this provider
                logger.debug("Provider doesn't support response_format, using standard call")
                llm_response = await self.call_llm(
                    user_prompt=ai_prompt,
                    system_prompt=system_prompt,
                    **llm_config
                )
            
            logger.info(f"📝 Raw LLM response (first 500 chars): {llm_response[:500]}")
            
            # Parse JSON response
            import json
            email_data = None
            parse_error = None
            
            try:
                # Try to extract JSON from response (LLM might wrap it in markdown or add text)
                # Strategy 1: Remove markdown code fences if present
                clean_response = llm_response.strip()
                
                # Check for markdown code fence and remove it
                if clean_response.startswith('```'):
                    # Find the end of the opening fence (could be ```json or just ```)
                    first_newline = clean_response.find('\n')
                    if first_newline != -1:
                        # Remove opening fence
                        clean_response = clean_response[first_newline + 1:]
                        # Remove closing fence if present
                        if clean_response.rstrip().endswith('```'):
                            clean_response = clean_response.rstrip()[:-3].rstrip()
                        logger.debug("🧹 Removed markdown code fences from response")
                
                # Strategy 2: Try to parse the cleaned response
                try:
                    email_data = json.loads(clean_response)
                    logger.debug("✅ Parsed JSON successfully")
                except json.JSONDecodeError as e1:
                    parse_error = e1
                    # Strategy 3: Try to repair truncated JSON
                    # Check if it's an unterminated string (common when max_tokens is hit)
                    if "Unterminated string" in str(e1) or "Expecting" in str(e1):
                        logger.warning(f"🔧 Attempting to repair truncated JSON...")
                        repaired = self._repair_truncated_json(clean_response)
                        if repaired:
                            try:
                                email_data = json.loads(repaired)
                                logger.info("✅ Successfully repaired and parsed truncated JSON")
                            except json.JSONDecodeError as e2:
                                logger.debug(f"Repair attempt failed: {e2}")
                    
                    # Strategy 4: Try to find JSON object in the response using regex
                    if not email_data:
                        json_match = re.search(r'\{[\s\S]*\}', clean_response)
                        if json_match:
                            json_str = json_match.group().strip()
                            try:
                                email_data = json.loads(json_str)
                                logger.debug("✅ Extracted and parsed JSON from response")
                            except json.JSONDecodeError:
                                pass
                    
                    # Strategy 5: Last resort - try original response
                    if not email_data:
                        email_data = json.loads(llm_response)
                        logger.debug("✅ Parsed original response as JSON")
            
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Failed to parse AI response as JSON, using fallback: {e}")
                logger.info(f"Full LLM Response: {llm_response}")
                
                # Fallback: Try to extract recipient from original prompt
                recipient_from_prompt = None
                if ai_prompt:
                    # Look for email patterns in the prompt
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    email_matches = re.findall(email_pattern, ai_prompt)
                    if email_matches:
                        recipient_from_prompt = email_matches[0]  # Use first email found
                        logger.info(f"📧 Extracted recipient from prompt: {recipient_from_prompt}")
                
                # Try to extract subject from prompt (look for keywords)
                subject_from_prompt = "Generated Email"
                if ai_prompt:
                    # Look for "about X" or "regarding X" patterns
                    subject_patterns = [
                        r'(?:about|regarding|concerning|re:)\s+([^\n,.]{5,50})',
                        r'(?:subject|topic):\s*([^\n,.]{5,50})',
                    ]
                    for pattern in subject_patterns:
                        match = re.search(pattern, ai_prompt, re.IGNORECASE)
                        if match:
                            subject_from_prompt = match.group(1).strip()
                            logger.info(f"📝 Extracted subject from prompt: {subject_from_prompt}")
                            break
                
                # Fallback: Use raw response as body with extracted metadata
                email_data = {
                    "recipient": recipient_from_prompt,
                    "subject": subject_from_prompt,
                    "body": llm_response
                }
            
            # Extract or override recipient from config
            manual_recipient = self.resolve_config(input_data, "recipient", "")
            if manual_recipient:
                email_data["recipient"] = manual_recipient
            
            # If still no recipient, check if there's a default or try to extract from context
            if not email_data.get("recipient"):
                # Try to find an email in the conversation context
                context_input = input_data.ports.get("input", {})
                if isinstance(context_input, dict):
                    # Look for common email fields
                    for key in ["recipient", "to", "email", "to_email"]:
                        if context_input.get(key):
                            email_data["recipient"] = context_input[key]
                            logger.info(f"📧 Using recipient from context: {email_data['recipient']}")
                            break
            
            logger.info(f"✅ AI draft generated: to={email_data.get('recipient')}, subject={email_data.get('subject')}")
            
            return email_data
        
        except Exception as e:
            logger.error(f"❌ AI draft generation error: {e}", exc_info=True)
            return {"error": f"AI draft generation failed: {e}"}
    
    def _repair_truncated_json(self, json_str: str) -> Optional[str]:
        """
        Attempt to repair truncated JSON (happens when max_tokens is reached).
        
        Common issues:
        1. Unterminated string: {"key": "value without closing quote
        2. Missing closing braces: {"key": "value"}  <- missing }
        3. Incomplete nested structure
        """
        try:
            # Count opening and closing braces
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            open_quotes = json_str.count('"')
            
            # If odd number of quotes, we have an unterminated string
            if open_quotes % 2 != 0:
                # Add closing quote and truncation indicator
                json_str = json_str + '..." (truncated)'
                logger.debug(f"Added closing quote to unterminated string")
            
            # Add missing closing braces
            if open_braces > close_braces:
                missing_braces = open_braces - close_braces
                json_str = json_str + ('}' * missing_braces)
                logger.debug(f"Added {missing_braces} missing closing brace(s)")
            
            # Verify it's now valid JSON
            import json
            json.loads(json_str)  # Test parse
            return json_str
            
        except Exception as e:
            logger.debug(f"JSON repair failed: {e}")
            return None
    
    async def _compose_manual_draft(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Compose email manually from config"""
        try:
            recipient = self.resolve_config(input_data, "recipient", "")
            subject = self.resolve_config(input_data, "subject", "")
            body = self.resolve_config(input_data, "body", "")
            
            # Try to get from content port if body is still empty
            if not body:
                content_input = input_data.ports.get("content")
                from app.core.nodes.multimodal import extract_content
                body = extract_content(content_input) if content_input else ""
            
            if not recipient:
                return {"error": "Recipient email is required"}
            
            if not subject:
                return {"error": "Email subject is required"}
            
            if not body:
                return {"error": "Email body is required"}
            
            logger.info(f"✍️ Manual draft composed: to={recipient}, subject={subject}")
            
            return {
                "recipient": recipient,
                "subject": subject,
                "body": body
            }
        
        except Exception as e:
            logger.error(f"❌ Manual draft composition error: {e}", exc_info=True)
            return {"error": f"Manual draft failed: {e}"}
    
    async def _get_attachments(self, input_data: NodeExecutionInput) -> List[Dict[str, Any]]:
        """
        Get attachments from input port and convert to Email-compatible format.
        
        Supports multiple formats:
        1. MediaFormat (from upload nodes): {type: "document", data: path, data_type: "file_path", ...}
        2. Export format (from PDF/CSV writers): {filename: "x.pdf", path: "data/temp/x.pdf", ...}
        3. Legacy format: {filename: "x.pdf", file_path: "...", ...}
        4. Direct SMTP format: {filename: "x.pdf", path: "...", content: bytes}
        """
        attachments = []
        
        try:
            # Get attachments from input port
            attachments_input = input_data.ports.get("attachments")
            
            if not attachments_input:
                return []
            
            # Normalize to list
            if isinstance(attachments_input, dict):
                attachments_input = [attachments_input]
            elif not isinstance(attachments_input, list):
                logger.warning(f"⚠️ Unexpected attachment format: {type(attachments_input)}")
                return []
            
            # Convert each attachment to email-compatible format
            for item in attachments_input:
                converted = self._convert_to_email_attachment(item)
                if converted:
                    attachments.append(converted)
            
            logger.info(f"📎 Prepared {len(attachments)} attachment(s) for email")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to process attachments: {e}", exc_info=True)
        
        return attachments
    
    def _convert_to_email_attachment(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert various file formats to email attachment format.
        
        Output format for SMTP service:
        {
            "filename": "document.pdf",
            "path": "data/uploads/document.pdf",  # OR
            "content": b"<bytes>",                # Raw content
            "mimetype": "application/pdf"         # Optional
        }
        """
        try:
            # Check if it's MediaFormat (from upload/loader nodes)
            if item.get("type") in ["document", "image", "audio", "video"]:
                logger.debug(f"📄 Converting MediaFormat attachment: {item.get('format')}")
                
                # Extract filename from metadata
                metadata = item.get("metadata", {})
                filename = metadata.get("filename", f"attachment.{item.get('format', 'bin')}")
                mimetype = metadata.get("mime_type", "application/octet-stream")
                
                # Get file path based on data_type
                data_type = item.get("data_type")
                data = item.get("data")
                
                if data_type == "file_path":
                    # File path - perfect for email
                    return {
                        "filename": filename,
                        "path": data,
                        "mimetype": mimetype
                    }
                elif data_type == "base64":
                    # Base64 - decode and send as content
                    import base64
                    content = base64.b64decode(data)
                    return {
                        "filename": filename,
                        "content": content,
                        "mimetype": mimetype
                    }
                elif data_type == "url":
                    # URL - would need to download first
                    logger.warning(f"⚠️ URL-based attachments not yet supported: {data}")
                    return None
            
            # Check if it's export format (from PDF/CSV/Excel writers)
            elif "path" in item and "filename" in item:
                logger.debug(f"📊 Converting export format attachment: {item.get('filename')}")
                return {
                    "filename": item["filename"],
                    "path": item["path"],
                    "mimetype": item.get("mimetype", "application/octet-stream")
                }
            
            # Check legacy format (file_path instead of path)
            elif "file_path" in item:
                filename = item.get("filename", "attachment")
                logger.debug(f"📁 Converting legacy format attachment: {filename}")
                return {
                    "filename": filename,
                    "path": item["file_path"],
                    "mimetype": item.get("mimetype", "application/octet-stream")
                }
            
            # Already in correct format (has path or content + filename)
            elif ("path" in item or "content" in item) and "filename" in item:
                logger.debug(f"✅ Attachment already in correct format: {item.get('filename')}")
                return item
            
            # Unknown format
            else:
                logger.warning(f"⚠️ Unknown attachment format, keys: {list(item.keys())}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to convert attachment: {e}", exc_info=True)
            return None
    
    async def _send_email(self, draft: Dict[str, Any], input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Send email using SMTP service"""
        try:
            # Get auth mode
            auth_mode = self.resolve_config(input_data, "auth_mode", "manual")
            
            if auth_mode == "credential":
                # Get from credential
                credential = self.resolve_credential(input_data, "credential_id")
                if not credential:
                    return {"success": False, "error": "Email credential not found"}
                
                # Handle both email_smtp format and generic smtp format
                if "email" in credential:
                    # New email_smtp format
                    from_email = credential.get("email", "")
                    password = credential.get("password", "")
                    provider = credential.get("provider", "gmail")
                    from_name = credential.get("from_name")
                    custom_server = credential.get("smtp_server")
                    custom_port = credential.get("smtp_port")
                elif "username" in credential:
                    # Generic smtp format (username = email, host = smtp_server)
                    from_email = credential.get("username", "")
                    password = credential.get("password", "")
                    provider = "custom"
                    from_name = None
                    custom_server = credential.get("host")
                    custom_port = credential.get("port")
                else:
                    return {"success": False, "error": "Invalid credential format (missing email/username)"}
                
                logger.info(f"🔐 Using credential for sending: {from_email} (provider: {provider})")
            else:
                # Manual mode
                provider = self.resolve_config(input_data, "provider", "gmail")
                from_email = self.resolve_config(input_data, "from_email", "")
                from_name = self.resolve_config(input_data, "from_name")
                password = self.resolve_config(input_data, "password", "")
                
                # Decrypt password if it's encrypted
                from app.security.encryption import decrypt_value, is_encrypted
                if password and is_encrypted(password):
                    try:
                        password = decrypt_value(password)
                        logger.debug("🔓 Decrypted SMTP password for direct send")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to decrypt password: {e}")
                
                # Custom SMTP settings (for custom provider)
                custom_server = self.resolve_config(input_data, "custom_smtp_server")
                custom_port = self.resolve_config(input_data, "custom_smtp_port")
            
            # Optional fields
            cc = self.resolve_config(input_data, "cc")
            bcc = self.resolve_config(input_data, "bcc")
            reply_to = self.resolve_config(input_data, "reply_to")
            
            # Parse CC/BCC (comma-separated)
            cc_addresses = [email.strip() for email in cc.split(",")] if cc else None
            bcc_addresses = [email.strip() for email in bcc.split(",")] if bcc else None
            
            # Validate
            if not from_email:
                return {"success": False, "error": "From email is required"}
            
            if not password:
                return {"success": False, "error": "Password is required"}
            
            recipient = draft.get("recipient")
            if not recipient:
                return {"success": False, "error": "Recipient email is required in draft"}
            
            # Get SMTP service
            smtp_service = get_smtp_service()
            
            # Send email
            logger.info(f"📤 Sending email: {from_email} → {recipient}")
            
            result = await smtp_service.send_email(
                to_addresses=[recipient],
                subject=draft.get("subject", ""),
                body=draft.get("body", ""),
                from_address=from_email,
                from_name=from_name,
                provider=provider,
                smtp_server=custom_server,
                smtp_port=custom_port,
                smtp_password=password,  # SMTP service still uses smtp_password parameter
                cc_addresses=cc_addresses,
                bcc_addresses=bcc_addresses,
                attachments=draft.get("attachments"),
                reply_to=reply_to
            )
            
            if result.get("success"):
                logger.info(f"✅ Email sent successfully")
            else:
                logger.error(f"❌ Email send failed: {result.get('error')}")
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Email send error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    print("Email Composer Node - AI-powered email composition and sending")

