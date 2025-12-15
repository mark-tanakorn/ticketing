"""
Text Display Node

Display text inline within the node interface. Shows text content with preview.
"""

import logging
from typing import Dict, Any, List
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="text_display",
    category=NodeCategory.OUTPUT,
    name="Text Display",
    description="Display text inline within the node",
    icon="fa-solid fa-font",
    version="1.0.0"
)
class TextDisplayNode(Node):
    """
    Text Display Node - Shows text content directly within the node interface.
    
    Pass-through node that doesn't modify the text data.
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "text",
                "type": PortType.TEXT,
                "display_name": "Text Input",
                "description": "Text to display",
                "required": True
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "text",
                "type": PortType.TEXT,
                "display_name": "Text Output",
                "description": "Same text passed through"
            },
            {
                "name": "preview_data",
                "type": PortType.UNIVERSAL,
                "display_name": "Preview Data",
                "description": "Text preview metadata"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "max_preview_length": {
                "type": "integer",
                "label": "Max Preview Length",
                "description": "Maximum characters to show in preview",
                "required": False,
                "default": 1000,
                "widget": "number",
                "min": 100,
                "max": 10000
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute text display node"""
        try:
            # Get text from input port
            from app.core.nodes.multimodal import extract_content
            text_input = input_data.ports.get("text", "")
            text = extract_content(text_input) if text_input else ""
            text = str(text) if text else ""
            
            # Get config
            max_length = input_data.config.get("max_preview_length", 1000)
            
            # Calculate stats
            char_count = len(text)
            word_count = len(text.split()) if text.strip() else 0
            line_count = text.count('\n') + 1 if text else 0
            
            # Truncate for preview if needed
            preview_text = text
            is_truncated = False
            if char_count > max_length:
                preview_text = text[:max_length] + "..."
                is_truncated = True
            
            logger.info(f"📄 Text Display showing {char_count} chars ({word_count} words)")
            
            return {
                "text": text,
                "preview_data": {
                    "type": "text_preview",
                    "text": preview_text,
                    "char_count": char_count,
                    "word_count": word_count,
                    "line_count": line_count,
                    "is_truncated": is_truncated
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Text Display node error: {e}", exc_info=True)
            return {
                "text": "",
                "preview_data": {},
                "error": str(e)
            }


