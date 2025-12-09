"""
Virtual Time Node

Calculates virtual date/time for simulations based on iteration number.

Perfect for:
- Business simulations (simulate 30 days)
- Time-based scenarios (deliveries arrive in X days)
- Any scenario needing virtual time progression
"""

from typing import Any, Dict, List
from datetime import datetime, timedelta
import logging

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import PortType, NodeCategory

logger = logging.getLogger(__name__)


@register_node(
    node_type="virtual_time",
    category=NodeCategory.WORKFLOW,
    name="Virtual Time",
    description="Calculate virtual date/time for simulations",
    icon="fa-solid fa-clock"
)
class VirtualTimeNode(Node):
    """
    Virtual Time - converts iteration numbers to virtual date/time.
    
    Example:
    ```
    Iteration 1 + time_step "1 day" → 2025-01-01 00:00:00
    Iteration 2 + time_step "1 day" → 2025-01-02 00:00:00
    Iteration 5 + time_step "6 hours" → 2025-01-01 00:00:00 + 30 hours
    ```
    
    Use with While Loop for simulations.
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "iteration_number",
                "type": PortType.UNIVERSAL,
                "display_name": "Iteration Number",
                "description": "Current iteration number (from While Loop)",
                "required": True
            },
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "virtual_datetime",
                "type": PortType.TEXT,
                "display_name": "Virtual DateTime",
                "description": "Current virtual date/time (ISO format)"
            },
            {
                "name": "virtual_timestamp",
                "type": PortType.UNIVERSAL,
                "display_name": "Virtual Timestamp",
                "description": "Unix timestamp of virtual time"
            },
            {
                "name": "virtual_day",
                "type": PortType.UNIVERSAL,
                "display_name": "Virtual Day",
                "description": "Day number (1-based)"
            },
            {
                "name": "time_step_hours",
                "type": PortType.UNIVERSAL,
                "display_name": "Time Step (Hours)",
                "description": "How many hours advance per iteration"
            },
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "start_datetime": {
                "label": "Start Date/Time",
                "type": "string",
                "default": "2025-01-01 00:00:00",
                "description": "Starting virtual date/time (YYYY-MM-DD HH:MM:SS)",
            },
            "time_step_value": {
                "label": "Time Step Value",
                "type": "number",
                "default": 1,
                "description": "How much time advances per iteration (e.g., 1, 6, 12)",
            },
            "time_step_unit": {
                "label": "Time Step Unit",
                "type": "select",
                "default": "days",
                "options": ["hours", "days", "weeks"],
                "description": "Unit of time for each step",
            },
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """
        Calculate virtual time based on iteration number.
        """
        # Get iteration number from input
        iteration_number = input_data.ports.get("iteration_number", 1)
        if not isinstance(iteration_number, (int, float)):
            raise ValueError(f"iteration_number must be a number, got {type(iteration_number)}")
        
        iteration_number = int(iteration_number)
        
        # Get config
        start_datetime_str = self.resolve_config(input_data, "start_datetime", "2025-01-01 00:00:00")
        time_step_value = float(self.resolve_config(input_data, "time_step_value", 1))
        time_step_unit = self.resolve_config(input_data, "time_step_unit", "days")
        
        # Parse start datetime
        try:
            start_dt = datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            logger.warning(f"Invalid start_datetime format '{start_datetime_str}', using default")
            start_dt = datetime(2025, 1, 1, 0, 0, 0)
        
        # Calculate time delta
        if time_step_unit == "hours":
            delta_hours = time_step_value
            time_delta = timedelta(hours=time_step_value * (iteration_number - 1))
        elif time_step_unit == "days":
            delta_hours = time_step_value * 24
            time_delta = timedelta(days=time_step_value * (iteration_number - 1))
        elif time_step_unit == "weeks":
            delta_hours = time_step_value * 24 * 7
            time_delta = timedelta(weeks=time_step_value * (iteration_number - 1))
        else:
            logger.warning(f"Unknown time_step_unit '{time_step_unit}', defaulting to days")
            delta_hours = time_step_value * 24
            time_delta = timedelta(days=time_step_value * (iteration_number - 1))
        
        # Calculate current virtual time
        virtual_dt = start_dt + time_delta
        
        # Calculate day number (for convenience)
        total_hours = (virtual_dt - start_dt).total_seconds() / 3600
        virtual_day = int(total_hours / 24) + 1
        
        logger.info(
            f"⏰ Virtual Time: Iteration {iteration_number} → "
            f"{virtual_dt.strftime('%Y-%m-%d %H:%M:%S')} (Day {virtual_day})"
        )
        
        return {
            "virtual_datetime": virtual_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "virtual_timestamp": int(virtual_dt.timestamp()),
            "virtual_day": virtual_day,
            "time_step_hours": delta_hours,
        }

