"""
Event Logger Node

Logs custom events with metadata.
"""

from typing import Any, Dict, Optional, List
import logging

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import PortType, NodeCategory

logger = logging.getLogger(__name__)


@register_node(
    node_type="event_logger",
    category=NodeCategory.ANALYTICS,
    name="Event Logger",
    description="Log custom events with metadata",
    icon="fa-solid fa-list"
)
class EventLoggerNode(Node):
    """
    Log custom events with metadata.
    
    Records structured events for analysis.
    Use cases:
    - Log business events (customer_arrived, sale_completed)
    - Record milestones (simulation_day_completed)
    - Track user actions
    - Create audit trail
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "trigger",
                "type": PortType.SIGNAL,
                "display_name": "Trigger",
                "description": "Trigger event logging",
                "required": False
            },
            {
                "name": "event_data",
                "type": PortType.UNIVERSAL,
                "display_name": "Event Data",
                "description": "Additional event data",
                "required": False
            },
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "success",
                "type": PortType.SIGNAL,
                "display_name": "Success",
                "description": "Event logged successfully"
            },
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "event_type": {
                "label": "Event Type",
                "type": "string",
                "default": "",
                "required": True,
                "description": "Event type/category (e.g., 'daily_summary')",
            },
            "message": {
                "label": "Message",
                "type": "string",
                "default": "",
                "required": True,
                "description": "Event message (supports variables like {{virtual_time.virtual_day}})",
            },
            "store_in_variables": {
                "label": "Store in Variables",
                "type": "boolean",
                "default": True,
                "description": "Store events in workflow variables",
            },
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Log event"""
        # Get from config
        event_type = self.resolve_config(input_data, "event_type")
        message = self.resolve_config(input_data, "message")
        store_in_variables = self.resolve_config(input_data, "store_in_variables", True)
        
        # Get from ports
        event_data = input_data.ports.get("event_data", {})
        
        if not event_type:
            raise ValueError("event_type is required")
        
        if not message:
            raise ValueError("message is required")
        
        # Log to console
        logger.info(f"📝 Event: {event_type} - {message}")
        
        # Store in variables if enabled
        if store_in_variables:
            events_key = "_logged_events"
            events = input_data.variables.get(events_key, [])
            
            events.append({
                "event_type": event_type,
                "message": message,
                "event_data": event_data,
            })
            
            # Keep last 100 events
            if len(events) > 100:
                events = events[-100:]
            
            input_data.variables[events_key] = events
        
        return {
            "success": True,
        }
