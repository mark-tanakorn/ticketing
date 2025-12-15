"""
JSON Parser Node - Parse JSON text into structured data

Extracts and parses JSON from text, handling markdown code blocks and malformed input.
"""

import json
import logging
import re
from typing import Dict, Any, List

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="json_parser",
    category=NodeCategory.PROCESSING,
    name="JSON Parser",
    description="Parse JSON text into structured data (dict/list) with smart extraction",
    icon="fa-solid fa-code",
    version="1.0.0"
)
class JSONParserNode(Node):
    """
    JSON Parser Node - Convert JSON text to structured data
    
    Features:
    - Auto-extracts JSON from markdown code blocks
    - Finds JSON patterns in mixed text
    - Handles malformed JSON gracefully
    - Strict/non-strict parsing modes
    
    Use Cases:
    - Parse LLM outputs that contain JSON
    - Extract structured data from text
    - Prepare data for CSV/Excel export
    - Data transformation pipelines
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "text",
                "type": PortType.TEXT,
                "display_name": "JSON Text",
                "description": "Text containing JSON (supports markdown code blocks)",
                "required": True
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "data",
                "type": PortType.UNIVERSAL,
                "display_name": "Parsed Data",
                "description": "Parsed JSON as dict or list"
            },
            {
                "name": "metadata",
                "type": PortType.UNIVERSAL,
                "display_name": "Metadata",
                "description": "Parse results and statistics"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "strict_mode": {
                "type": "boolean",
                "label": "Strict Mode",
                "description": "Fail on invalid JSON (instead of returning text as-is)",
                "required": False,
                "default": False,
                "widget": "checkbox",
                "help": "Enable to fail on parse errors. Disable to pass through original text."
            },
            "extract_from_markdown": {
                "type": "boolean",
                "label": "Extract from Markdown",
                "description": "Auto-extract JSON from markdown code blocks (```json...```)",
                "required": False,
                "default": True,
                "widget": "checkbox",
                "help": "Useful when LLM wraps JSON in markdown formatting"
            }
        }
    
    def _extract_json_from_markdown(self, text: str) -> str:
        """Extract JSON from markdown code blocks"""
        patterns = [
            r'```json\s*\n([\s\S]*?)\n```',  # ```json ... ```
            r'```\s*\n(\{[\s\S]*?\})\n```',  # ``` {...} ```
            r'```\s*\n(\[[\s\S]*?\])\n```',  # ``` [...] ```
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                logger.info(f"📝 Extracted JSON from markdown code block")
                return match.group(1).strip()
        
        return text
    
    def _find_json_in_text(self, text: str) -> str:
        """Try to find JSON object or array in text"""
        for pattern in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
            match = re.search(pattern, text)
            if match:
                logger.info(f"🔍 Found JSON pattern in text")
                return match.group(0)
        
        return text
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute JSON parser"""
        try:
            # Get input text
            from app.core.nodes.multimodal import extract_content
            text_input = input_data.ports.get("text")
            text = extract_content(text_input) if text_input else ""
            
            if not text:
                return {
                    "data": None,
                    "metadata": {"error": "No text provided"},
                    "error": "No text provided to parse"
                }
            
            # Get config
            strict_mode = self.resolve_config(input_data, "strict_mode", False)
            extract_markdown = self.resolve_config(input_data, "extract_from_markdown", True)
            
            logger.info(f"🔧 JSON Parser executing: {len(text)} chars, strict={strict_mode}")
            
            # Extract from markdown if enabled
            if extract_markdown:
                text = self._extract_json_from_markdown(text)
            
            # Try to parse JSON
            try:
                parsed_data = json.loads(text)
                
                # Determine type and size
                data_type = type(parsed_data).__name__
                size = len(parsed_data) if isinstance(parsed_data, (list, dict)) else 1
                
                logger.info(f"✅ JSON parsed successfully: type={data_type}, size={size}")
                
                return {
                    "data": parsed_data,
                    "metadata": {
                        "success": True,
                        "type": data_type,
                        "size": size,
                        "original_length": len(str(text))
                    }
                }
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ JSON parse failed: {e}")
                
                # Try to find JSON in text
                json_text = self._find_json_in_text(text)
                if json_text != text:
                    try:
                        parsed_data = json.loads(json_text)
                        
                        data_type = type(parsed_data).__name__
                        size = len(parsed_data) if isinstance(parsed_data, (list, dict)) else 1
                        
                        logger.info(f"✅ JSON extracted and parsed: type={data_type}, size={size}")
                        
                        return {
                            "data": parsed_data,
                            "metadata": {
                                "success": True,
                                "type": data_type,
                                "size": size,
                                "extracted": True
                            }
                        }
                    except:
                        pass
                
                # Handle strict mode
                if strict_mode:
                    return {
                        "data": None,
                        "metadata": {
                            "success": False,
                            "error": str(e),
                            "error_line": e.lineno,
                            "error_col": e.colno
                        },
                        "error": f"Invalid JSON: {e}"
                    }
                else:
                    # Non-strict: return original text
                    logger.info(f"📝 Non-strict mode: returning text as-is")
                    return {
                        "data": text,
                        "metadata": {
                            "success": False,
                            "warning": "Could not parse JSON, returning text",
                            "type": "string"
                        }
                    }
        
        except Exception as e:
            logger.error(f"❌ JSON Parser error: {e}", exc_info=True)
            return {
                "data": None,
                "metadata": {"error": str(e)},
                "error": str(e)
            }
