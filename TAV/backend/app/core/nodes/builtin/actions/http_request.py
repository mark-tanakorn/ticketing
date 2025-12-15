"""
HTTP Request Node - Make HTTP/HTTPS API Calls

The foundation node for custom integrations. Make authenticated API calls to any service.
Supports all HTTP methods, authentication types, and request formats.
"""

import logging
import httpx
import json
from typing import Dict, Any, List, Optional
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="http_request",
    category=NodeCategory.ACTIONS,
    name="HTTP Request",
    description="Make HTTP/HTTPS API calls with authentication and custom headers",
    icon="fa-solid fa-globe",
    version="1.0.0"
)
class HTTPRequestNode(Node):
    """
    HTTP Request Node - Universal API integration
    
    Features:
    - All HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
    - Multiple authentication types (None, Basic, Bearer, API Key, Custom)
    - Credential integration (use stored credentials securely)
    - Custom headers and query parameters
    - Request body formats (JSON, Form Data, Raw Text)
    - Variable substitution in URL, headers, and body
    - Response parsing (JSON, Text, Binary)
    - Status code and headers output
    - Error handling (4xx, 5xx with details)
    
    Use Cases:
    - Call any REST API
    - Integrate with third-party services
    - Webhook callbacks
    - Custom integrations
    - Data fetching
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "data",
                "type": PortType.UNIVERSAL,
                "display_name": "Request Data",
                "description": "Optional data to inject into request (accessible as {{input.field}})",
                "required": False
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "response",
                "type": PortType.UNIVERSAL,
                "display_name": "Response",
                "description": "Response body (parsed JSON if possible, otherwise text)"
            },
            {
                "name": "status_code",
                "type": PortType.UNIVERSAL,
                "display_name": "Status Code",
                "description": "HTTP status code (200, 404, etc.)"
            },
            {
                "name": "headers",
                "type": PortType.UNIVERSAL,
                "display_name": "Headers",
                "description": "Response headers as dictionary"
            },
            {
                "name": "success",
                "type": PortType.UNIVERSAL,
                "display_name": "Success",
                "description": "Boolean indicating if request succeeded (2xx status)"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "url": {
                "type": "string",
                "label": "URL",
                "description": "Request URL (supports variables: {{trigger.api_url}})",
                "required": True,
                "placeholder": "https://api.example.com/endpoint",
                "widget": "text"
            },
            "method": {
                "type": "string",
                "widget": "select",
                "label": "HTTP Method",
                "description": "HTTP method to use",
                "required": True,
                "options": [
                    {"label": "GET", "value": "GET"},
                    {"label": "POST", "value": "POST"},
                    {"label": "PUT", "value": "PUT"},
                    {"label": "DELETE", "value": "DELETE"},
                    {"label": "PATCH", "value": "PATCH"},
                    {"label": "HEAD", "value": "HEAD"},
                    {"label": "OPTIONS", "value": "OPTIONS"}
                ],
                "default": "GET"
            },
            "auth_type": {
                "type": "string",
                "widget": "select",
                "label": "Authentication",
                "description": "Authentication method",
                "required": True,
                "options": [
                    {"label": "None", "value": "none"},
                    {"label": "Basic Auth", "value": "basic"},
                    {"label": "Bearer Token", "value": "bearer"},
                    {"label": "API Key (Header)", "value": "api_key_header"},
                    {"label": "API Key (Query)", "value": "api_key_query"},
                    {"label": "From Credential", "value": "credential"}
                ],
                "default": "none"
            },
            "credential_id": {
                "type": "credential",
                "widget": "credential",
                "label": "Credential",
                "description": "Select credential for authentication",
                "credential_types": ["api_key", "bearer_token", "basic_auth", "oauth2"],
                "required": False,
                "visible_when": {"auth_type": "credential"}
            },
            "auth_username": {
                "type": "string",
                "label": "Username",
                "description": "Username for basic authentication",
                "required": False,
                "visible_when": {"auth_type": "basic"},
                "widget": "text"
            },
            "auth_password": {
                "type": "string",
                "label": "Password",
                "description": "Password for basic authentication",
                "required": False,
                "visible_when": {"auth_type": "basic"},
                "widget": "password"
            },
            "auth_token": {
                "type": "string",
                "label": "Token",
                "description": "Bearer token or API key value",
                "required": False,
                "visible_when": {"auth_type": ["bearer", "api_key_header", "api_key_query"]},
                "widget": "password"
            },
            "api_key_name": {
                "type": "string",
                "widget": "text",
                "label": "API Key Name",
                "description": "Header name or query parameter name for API key",
                "required": False,
                "visible_when": {"auth_type": ["api_key_header", "api_key_query"]},
                "placeholder": "X-API-Key or api_key",
                "default": "X-API-Key"
            },
            "headers": {
                "type": "keyvalue",
                "widget": "keyvalue",
                "label": "Headers",
                "description": "Custom HTTP headers (supports variables)",
                "required": False,
                "placeholder": "e.g., Content-Type: application/json"
            },
            "query_params": {
                "type": "keyvalue",
                "widget": "keyvalue",
                "label": "Query Parameters",
                "description": "URL query parameters (supports variables)",
                "required": False,
                "placeholder": "e.g., limit: 10"
            },
            "body_type": {
                "type": "string",
                "widget": "select",
                "label": "Body Type",
                "description": "Request body format (for POST/PUT/PATCH)",
                "required": False,
                "options": [
                    {"label": "None", "value": "none"},
                    {"label": "JSON", "value": "json"},
                    {"label": "Form Data", "value": "form"},
                    {"label": "Raw Text", "value": "text"}
                ],
                "default": "json",
                "visible_when": {"method": ["POST", "PUT", "PATCH"]}
            },
            "body": {
                "type": "string",
                "widget": "textarea",
                "label": "Request Body",
                "description": "Request body content (JSON, form data, or raw text)",
                "required": False,
                "placeholder": '{"key": "value"}',
                "visible_when": {"method": ["POST", "PUT", "PATCH"]}
            },
            "timeout": {
                "type": "number",
                "label": "Timeout (seconds)",
                "description": "Request timeout in seconds",
                "required": False,
                "default": 30,
                "min": 1,
                "max": 300
            },
            "follow_redirects": {
                "type": "boolean",
                "label": "Follow Redirects",
                "description": "Automatically follow HTTP redirects",
                "required": False,
                "default": True
            },
            "verify_ssl": {
                "type": "boolean",
                "label": "Verify SSL",
                "description": "Verify SSL certificates",
                "required": False,
                "default": True
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute HTTP request"""
        try:
            # Get URL and resolve variables
            url = self.resolve_config(input_data, "url")
            if not url:
                raise ValueError("URL is required")
            
            # Get HTTP method
            method = self.resolve_config(input_data, "method", "GET").upper()
            
            # Get timeout and SSL settings
            timeout = self.resolve_config(input_data, "timeout", 30)
            verify_ssl = self.resolve_config(input_data, "verify_ssl", True)
            follow_redirects = self.resolve_config(input_data, "follow_redirects", True)
            
            # Prepare headers
            headers = self._prepare_headers(input_data)
            
            # Prepare query parameters
            params = self._prepare_query_params(input_data)
            
            # Prepare authentication
            auth_headers, auth_params = self._prepare_auth(input_data)
            headers.update(auth_headers)
            params.update(auth_params)
            
            # Prepare request body
            body = None
            if method in ["POST", "PUT", "PATCH"]:
                body = self._prepare_body(input_data)
            
            # Log request (without sensitive data)
            logger.info(f"🌐 HTTP Request: {method} {url}")
            logger.info(f"🌐 Headers (sanitized): {[k for k in headers.keys()]}")
            logger.info(f"🌐 Params: {list(params.keys())}")
            if body:
                body_preview = str(body)[:500] if body else "None"
                logger.info(f"🌐 Body Preview: {body_preview}")
                logger.info(f"🌐 Body Type: {type(body)}")
            if "Authorization" in headers:
                auth_type_display = headers["Authorization"].split()[0] if headers["Authorization"] else "None"
                logger.info(f"🔐 Auth Type in Headers: {auth_type_display}")
            
            # Make HTTP request
            async with httpx.AsyncClient(
                timeout=timeout,
                verify=verify_ssl,
                follow_redirects=follow_redirects
            ) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    content=body if isinstance(body, (str, bytes)) else None,
                    json=body if isinstance(body, dict) and headers.get("Content-Type") == "application/json" else None,
                    data=body if isinstance(body, dict) and headers.get("Content-Type") == "application/x-www-form-urlencoded" else None
                )
            
            # Parse response
            response_data = await self._parse_response(response)
            success = 200 <= response.status_code < 300
            
            # Log response
            logger.info(f"HTTP Response: {response.status_code}")
            
            return {
                "response": response_data,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "success": success
            }
            
        except httpx.TimeoutException as e:
            logger.error(f"HTTP request timeout: {e}")
            return {
                "response": None,
                "status_code": 0,
                "headers": {},
                "success": False,
                "error": f"Request timeout after {timeout}s"
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code}")
            response_data = await self._parse_response(e.response)
            return {
                "response": response_data,
                "status_code": e.response.status_code,
                "headers": dict(e.response.headers),
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
            }
        except Exception as e:
            logger.error(f"HTTP request failed: {e}", exc_info=True)
            return {
                "response": None,
                "status_code": 0,
                "headers": {},
                "success": False,
                "error": str(e)
            }
    
    def _prepare_headers(self, input_data: NodeExecutionInput) -> Dict[str, str]:
        """Prepare HTTP headers"""
        headers = {}
        
        # Get custom headers from config
        custom_headers = self.resolve_config(input_data, "headers", {})
        logger.info(f"📋 Custom Headers Raw: {custom_headers}")
        logger.info(f"📋 Custom Headers Type: {type(custom_headers)}")
        
        if isinstance(custom_headers, dict):
            for key, value in custom_headers.items():
                # Resolve variables in header values
                resolved_value = self.resolve_template(input_data, str(value))
                headers[key] = resolved_value
                logger.info(f"📋 Header: {key} = {resolved_value}")
        
        # Set default Content-Type based on body_type
        body_type = self.resolve_config(input_data, "body_type", "json")
        if body_type == "json" and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
        elif body_type == "form" and "Content-Type" not in headers:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        
        logger.info(f"📋 Final Headers: {headers}")
        return headers
    
    def _prepare_query_params(self, input_data: NodeExecutionInput) -> Dict[str, str]:
        """Prepare URL query parameters"""
        params = {}
        
        # Get query params from config
        custom_params = self.resolve_config(input_data, "query_params", {})
        if isinstance(custom_params, dict):
            for key, value in custom_params.items():
                # Resolve variables in parameter values
                resolved_value = self.resolve_template(input_data, str(value))
                params[key] = resolved_value
        
        return params
    
    def _prepare_auth(self, input_data: NodeExecutionInput) -> tuple[Dict[str, str], Dict[str, str]]:
        """
        Prepare authentication headers and parameters.
        
        Returns:
            Tuple of (headers_dict, params_dict)
        """
        headers = {}
        params = {}
        
        auth_type = self.resolve_config(input_data, "auth_type", "none")
        logger.info(f"🔐 Auth Type: {auth_type}")
        
        if auth_type == "none":
            pass
        
        elif auth_type == "credential":
            # Use stored credential
            credential = self.resolve_credential(input_data, "credential_id")
            if not credential:
                logger.warning("⚠️ Credential selected but not found")
                return headers, params
            
            logger.info(f"🔐 Using credential (fields: {list(credential.keys())})")
            
            # Handle different credential types
            if "token" in credential:
                # Bearer token
                headers["Authorization"] = f"Bearer {credential['token']}"
                logger.info("🔐 Applied Bearer token from credential")
            
            elif "api_key" in credential:
                # API Key - try to determine where to put it
                api_key = credential['api_key']
                # Default to header unless specified in config
                headers["Authorization"] = f"Bearer {api_key}"
                logger.info("🔐 Applied API key from credential as Bearer")
            
            elif "username" in credential and "password" in credential:
                # Basic auth
                import base64
                username = credential['username']
                password = credential['password']
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
                logger.info(f"🔐 Applied Basic Auth from credential (username: {username})")
            
            elif "access_token" in credential:
                # OAuth 2.0
                headers["Authorization"] = f"Bearer {credential['access_token']}"
                logger.info("🔐 Applied OAuth2 access token from credential")
            
            else:
                logger.warning(f"⚠️ Unknown credential format: {list(credential.keys())}")
        
        elif auth_type == "basic":
            # Basic Authentication
            username = self.resolve_config(input_data, "auth_username", "")
            password = self.resolve_config(input_data, "auth_password", "")
            
            # Decrypt password if encrypted
            from app.security.encryption import decrypt_value, is_encrypted
            if password and is_encrypted(password):
                try:
                    password = decrypt_value(password)
                    logger.info(f"🔓 Decrypted basic auth password")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to decrypt password: {e}")
            
            if username and password:
                import base64
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
                logger.info(f"🔐 Basic Auth: username={username}")
        
        elif auth_type == "bearer":
            # Bearer Token
            token = self.resolve_config(input_data, "auth_token", "")
            
            # Decrypt if encrypted (passwords are auto-encrypted when workflows are saved)
            from app.security.encryption import decrypt_value, is_encrypted
            if token and is_encrypted(token):
                try:
                    token = decrypt_value(token)
                    logger.info(f"🔓 Decrypted bearer token")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to decrypt token: {e}")
            
            logger.info(f"🔐 Bearer Token Length: {len(token) if token else 0} chars")
            logger.info(f"🔐 Token starts with: {token[:10] if token else 'EMPTY'}...")
            if token:
                headers["Authorization"] = f"Bearer {token}"
                logger.info(f"✅ Authorization header set")
        
        elif auth_type == "api_key_header":
            # API Key in Header
            key_name = self.resolve_config(input_data, "api_key_name", "X-API-Key")
            key_value = self.resolve_config(input_data, "auth_token", "")
            
            # Decrypt if encrypted
            from app.security.encryption import decrypt_value, is_encrypted
            if key_value and is_encrypted(key_value):
                try:
                    key_value = decrypt_value(key_value)
                    logger.info(f"🔓 Decrypted API key")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to decrypt API key: {e}")
            
            if key_value:
                headers[key_name] = key_value
        
        elif auth_type == "api_key_query":
            # API Key in Query Parameter
            key_name = self.resolve_config(input_data, "api_key_name", "api_key")
            key_value = self.resolve_config(input_data, "auth_token", "")
            
            # Decrypt if encrypted
            from app.security.encryption import decrypt_value, is_encrypted
            if key_value and is_encrypted(key_value):
                try:
                    key_value = decrypt_value(key_value)
                    logger.info(f"🔓 Decrypted API key")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to decrypt API key: {e}")
            
            if key_value:
                params[key_name] = key_value
        
        elif auth_type == "credential":
            # Use stored credential
            credential = self.resolve_credential(input_data, "credential_id")
            if credential:
                # Detect credential type and apply appropriately
                if "token" in credential:
                    # Bearer token
                    headers["Authorization"] = f"Bearer {credential['token']}"
                elif "api_key" in credential:
                    # API key - default to header
                    headers["X-API-Key"] = credential["api_key"]
                elif "username" in credential and "password" in credential:
                    # Basic auth
                    import base64
                    username = credential["username"]
                    password = credential["password"]
                    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                    headers["Authorization"] = f"Basic {credentials}"
                elif "access_token" in credential:
                    # OAuth2
                    headers["Authorization"] = f"Bearer {credential['access_token']}"
        
        return headers, params
    
    def _prepare_body(self, input_data: NodeExecutionInput) -> Optional[Any]:
        """Prepare request body"""
        body_type = self.resolve_config(input_data, "body_type", "json")
        body_content = self.resolve_config(input_data, "body", "")
        
        logger.info(f"📦 Body Type: {body_type}")
        logger.info(f"📦 Body Content (raw): {body_content[:300] if body_content else 'None'}...")
        
        if not body_content:
            return None
        
        # Resolve variables in body
        body_content = self.resolve_template(input_data, body_content)
        logger.info(f"📦 Body Content (after template): {body_content[:300] if body_content else 'None'}...")
        
        if body_type == "json":
            # Parse JSON
            try:
                parsed = json.loads(body_content)
                logger.info(f"✅ JSON parsed successfully: {type(parsed)}")
                return parsed
            except json.JSONDecodeError as e:
                logger.warning(f"❌ Invalid JSON in body: {e}")
                logger.warning(f"   Problematic content: {body_content[:200]}")
                return body_content
        
        elif body_type == "form":
            # Parse form data (key=value pairs)
            form_data = {}
            for line in body_content.split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    form_data[key.strip()] = value.strip()
            return form_data
        
        else:  # text or default
            return body_content
    
    async def _parse_response(self, response: httpx.Response) -> Any:
        """Parse HTTP response"""
        content_type = response.headers.get("Content-Type", "")
        
        # Try JSON first
        if "application/json" in content_type:
            try:
                return response.json()
            except Exception:
                pass
        
        # Try text
        try:
            return response.text
        except Exception:
            pass
        
        # Return bytes as fallback
        return response.content

