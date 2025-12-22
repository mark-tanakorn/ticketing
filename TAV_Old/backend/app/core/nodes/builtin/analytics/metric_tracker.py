"""
Metric Tracker Node

Tracks and records performance metrics.
"""

from typing import Any, Dict, Optional, List
import logging

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import PortType, NodeCategory

logger = logging.getLogger(__name__)


@register_node(
    node_type="metric_tracker",
    category=NodeCategory.ANALYTICS,
    name="Metric Tracker",
    description="Track and record performance metrics",
    icon="fa-solid fa-chart-line"
)
class MetricTrackerNode(Node):
    """
    Track and record performance metrics.
    
    Records KPIs and metrics during workflow execution.
    Use cases:
    - Track business KPIs (revenue, profit, customer satisfaction)
    - Monitor performance metrics (latency, throughput)
    - Record simulation metrics (inventory levels, queue lengths)
    - Calculate aggregated statistics
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "trigger",
                "type": PortType.SIGNAL,
                "display_name": "Trigger",
                "description": "Trigger metric recording",
                "required": False
            },
            {
                "name": "metrics",
                "type": PortType.UNIVERSAL,
                "display_name": "Metrics",
                "description": "Metrics to record (object with key-value pairs)",
                "required": True
            },
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "success",
                "type": PortType.SIGNAL,
                "display_name": "Success",
                "description": "Metrics recorded"
            },
            {
                "name": "current_metrics",
                "type": PortType.UNIVERSAL,
                "display_name": "Current Metrics",
                "description": "Current metric values"
            },
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "track_history": {
                "label": "Track History",
                "type": "boolean",
                "default": False,
                "description": "Keep history of metric values in variables",
            },
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Track metrics"""
        metrics = input_data.ports.get("metrics", {})
        
        if not isinstance(metrics, dict):
            raise ValueError("metrics must be an object")
        
        # Store in variables
        for key, value in metrics.items():
            input_data.variables[f"metric_{key}"] = value
        
        # Track history if enabled
        track_history = self.resolve_config(input_data, "track_history", False)
        
        if track_history:
            history_key = "_metric_history"
            history = input_data.variables.get(history_key, {})
            
            for key, value in metrics.items():
                if key not in history:
                    history[key] = []
                
                history[key].append(value)
                
                # Keep last 100 values
                if len(history[key]) > 100:
                    history[key] = history[key][-100:]
            
            input_data.variables[history_key] = history
        
        logger.info(f"📊 Metrics recorded: {list(metrics.keys())}")
        
        return {
            "success": True,
            "current_metrics": metrics,
        }
