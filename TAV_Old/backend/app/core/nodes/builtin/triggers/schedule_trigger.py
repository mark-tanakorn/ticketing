"""
Schedule Trigger Node

Fires workflow on a schedule (cron expression or interval).
"""

import asyncio
import logging
from typing import Dict, Any, Callable, Awaitable

from app.utils.timezone import get_local_now

from app.core.nodes import Node, NodeExecutionInput, TriggerCapability, register_node
from app.schemas.workflow import NodeCategory

logger = logging.getLogger(__name__)


@register_node(
    node_type="schedule_trigger",
    category=NodeCategory.TRIGGERS,
    name="Schedule Trigger",
    description="Fires workflow on a schedule",
    icon="fa-solid fa-clock",
    version="1.0.0"
)
class ScheduleTriggerNode(Node, TriggerCapability):
    """
    Schedule trigger node.
    
    Fires workflow at regular intervals based on configured time.
    
    Config:
    - interval_hours: Hours between triggers (0-23)
    - interval_minutes: Minutes between triggers (0-59)
    - interval_seconds: Seconds between triggers (0-59)
    
    Output:
    - signal: Universal signal to activate next node
    """
    
    trigger_type = "schedule"  # Used for execution_source tracking
    
    @classmethod
    def get_input_ports(cls):
        """Triggers typically have NO input ports - they start the workflow"""
        return []
    
    @classmethod
    def get_output_ports(cls):
        """Define output ports - single universal signal to trigger next node"""
        from app.schemas.workflow import PortType
        return [
            {
                "name": "signal",
                "type": PortType.UNIVERSAL,
                "display_name": "Signal",
                "description": "Trigger signal sent when schedule fires"
            }
        ]
    
    @classmethod
    def get_config_schema(cls):
        """Define configuration schema"""
        return {
            "interval_hours": {
                "type": "integer",
                "label": "Hours",
                "description": "Hours between triggers",
                "required": False,
                "default": 0,
                "widget": "number",
                "min": 0,
                "max": 23
            },
            "interval_minutes": {
                "type": "integer",
                "label": "Minutes",
                "description": "Minutes between triggers",
                "required": False,
                "default": 5,
                "widget": "number",
                "min": 0,
                "max": 59
            },
            "interval_seconds": {
                "type": "integer",
                "label": "Seconds",
                "description": "Seconds between triggers",
                "required": False,
                "default": 0,
                "widget": "number",
                "min": 0,
                "max": 59
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """
        Execute schedule trigger.
        
        Returns:
            Signal with trigger metadata
        """
        logger.info(f"Schedule trigger {self.node_id} executed")
        
        return {
            "signal": {
                "triggered_at": get_local_now().isoformat(),
                "source": "schedule"
            }
        }
    
    async def start_monitoring(
        self,
        workflow_id: str,
        executor_callback: Callable[[str, Dict[str, Any], str], Awaitable[None]]
    ):
        """
        Start schedule monitoring.
        
        Runs background loop that fires at specified intervals.
        
        Args:
            workflow_id: Workflow UUID
            executor_callback: Callback to spawn executions
        """
        # Store callback
        self._workflow_id = workflow_id
        self._executor_callback = executor_callback
        self._is_monitoring = True
        
        # Get config and calculate total interval in seconds
        hours = self.config.get("interval_hours", 0)
        minutes = self.config.get("interval_minutes", 0)
        seconds = self.config.get("interval_seconds", 0)
        
        # Calculate total seconds
        interval_seconds = (hours * 3600) + (minutes * 60) + seconds
        
        # Validate interval
        if interval_seconds < 1:
            raise ValueError(
                f"Schedule trigger {self.node_id} must have at least 1 second interval "
                f"(got {hours}h {minutes}m {seconds}s)"
            )
        
        logger.info(
            f"Schedule trigger {self.node_id} monitoring started: "
            f"interval={hours}h {minutes}m {seconds}s ({interval_seconds}s total)"
        )
        
        # Start monitoring loop
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
    
    async def stop_monitoring(self):
        """Stop schedule monitoring."""
        logger.info(f"Schedule trigger {self.node_id} monitoring stopped")
        
        self._is_monitoring = False
        
        # Cancel monitoring task
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self, interval_seconds: int):
        """
        Monitoring loop that fires at intervals.
        
        Args:
            interval_seconds: Fire every N seconds
        """
        execution_count = 0
        
        try:
            while self._is_monitoring:
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
                # Fire trigger with metadata
                trigger_data = {
                    "triggered_at": get_local_now().isoformat(),
                    "execution_count": execution_count,
                    "source": "schedule"
                }
                
                logger.debug(f"Schedule trigger {self.node_id} firing (execution {execution_count + 1})")
                
                try:
                    await self.fire_trigger(trigger_data)
                    execution_count += 1
                except Exception as e:
                    logger.error(f"Schedule trigger {self.node_id} fire failed: {e}", exc_info=True)
        
        except asyncio.CancelledError:
            logger.debug(f"Schedule trigger {self.node_id} monitoring loop cancelled")
            raise
        
        except Exception as e:
            logger.error(f"Schedule trigger {self.node_id} monitoring loop failed: {e}", exc_info=True)
            raise

