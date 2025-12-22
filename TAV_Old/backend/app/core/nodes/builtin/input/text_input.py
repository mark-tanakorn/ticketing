"""
Text Input Node

Emits configured text as output. Useful for providing static text input to workflows.
"""

import logging
from typing import Dict, Any, List
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="text_input",
    category=NodeCategory.INPUT,
    name="Text Input",
    description="Emit configured text as output",
    icon="fa-solid fa-i-cursor",
    version="1.0.0"
)
class TextInputNode(Node):
    """
    Text Input Node - Emits configured text.
    
    This node has no inputs and emits text configured in its settings.
    Useful for providing static text, prompts, or templates to workflows.
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """No input ports - this is a source node"""
        return [
            {
                "name": "input",
                "type": PortType.UNIVERSAL,
                "display_name": "Input",
                "description": "Input data",
                "required": False
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
                "description": "The configured text"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "text": {
                "type": "string",
                "label": "Text Content",
                "description": "Text to output from this node",
                "required": True,
                "default": "",
                "widget": "textarea",
                "placeholder": "Enter text here..."
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute text input node"""
        try:
            # Debug: Log raw config value
            raw_value = input_data.config.get("text", "")
            logger.info(f"🔍 Raw config value: {raw_value!r} (type: {type(raw_value).__name__})")
            logger.info(f"🔍 Available variables: {input_data.variables.get('_nodes', {}).keys()}")
            
            # Resolve config value (supports variables and templates)
            text = self.resolve_config(input_data, "text", "")
            logger.info(f"✅ Resolved text: {text!r}")
            logger.info(f"📝 Text Input emitting {len(text)} characters")
            
            return {
                "text": str(text)
            }
            
        except Exception as e:
            logger.error(f"❌ Text Input node error: {e}", exc_info=True)
            return {
                "text": "",
                "error": str(e)
            }


