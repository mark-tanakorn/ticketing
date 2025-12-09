"""
Anomaly Detector Node

Detects anomalies and failures in workflow execution.
"""

from typing import Any, Dict, Optional, List
import logging
import json

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import PortType, NodeCategory

logger = logging.getLogger(__name__)


@register_node(
    node_type="anomaly_detector",
    category=NodeCategory.ANALYTICS,
    name="Anomaly Detector",
    description="Detect anomalies and failures using rules",
    icon="fa-solid fa-triangle-exclamation"
)
class AnomalyDetectorNode(Node):
    """
    Detect anomalies and failures.
    
    Monitors metrics and detects anomalies using rules or thresholds.
    Use cases:
    - Detect business failures (stockout, long wait times)
    - Monitor performance degradation
    - Alert on threshold violations
    - Track simulation meltdowns
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "trigger",
                "type": PortType.SIGNAL,
                "display_name": "Trigger",
                "description": "Trigger anomaly check",
                "required": False
            },
            {
                "name": "metrics",
                "type": PortType.UNIVERSAL,
                "display_name": "Metrics",
                "description": "Metrics to check",
                "required": True
            },
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "normal",
                "type": PortType.SIGNAL,
                "display_name": "Normal",
                "description": "No anomalies detected"
            },
            {
                "name": "anomaly_detected",
                "type": PortType.SIGNAL,
                "display_name": "Anomaly Detected",
                "description": "Anomaly detected"
            },
            {
                "name": "anomalies",
                "type": PortType.UNIVERSAL,
                "display_name": "Anomalies",
                "description": "List of detected anomalies"
            },
            {
                "name": "severity",
                "type": PortType.TEXT,
                "display_name": "Severity",
                "description": "Highest severity level (low, medium, high, critical)"
            },
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "rules": {
                "label": "Detection Rules",
                "type": "json",
                "default": [],
                "description": "Array of anomaly detection rules: [{metric, condition, threshold, severity, description}]",
            },
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Detect anomalies"""
        metrics = input_data.ports.get("metrics", {})
        
        if not isinstance(metrics, dict):
            raise ValueError("metrics must be an object")
        
        rules = self.resolve_config(input_data, "rules", [])
        
        # Parse rules if it's a string
        if isinstance(rules, str) and rules:
            try:
                rules = json.loads(rules)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Could not parse rules as JSON: {rules}")
                rules = []
        
        detected_anomalies = []
        
        # Check each rule
        for rule in rules:
            metric_name = rule.get("metric")
            condition = rule.get("condition")
            threshold = rule.get("threshold")
            severity = rule.get("severity", "medium")
            description = rule.get("description", f"{metric_name} {condition} {threshold}")
            
            if metric_name not in metrics:
                continue
            
            metric_value = metrics[metric_name]
            
            # Evaluate condition
            is_anomaly = False
            
            if condition == "greater_than" and isinstance(metric_value, (int, float)) and isinstance(threshold, (int, float)):
                is_anomaly = metric_value > threshold
            elif condition == "less_than" and isinstance(metric_value, (int, float)) and isinstance(threshold, (int, float)):
                is_anomaly = metric_value < threshold
            elif condition == "equals":
                is_anomaly = metric_value == threshold
            elif condition == "not_equals":
                is_anomaly = metric_value != threshold
            
            if is_anomaly:
                anomaly = {
                    "metric": metric_name,
                    "value": metric_value,
                    "threshold": threshold,
                    "condition": condition,
                    "severity": severity,
                    "description": description,
                }
                detected_anomalies.append(anomaly)
        
        # Determine highest severity
        severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        max_severity = "low"
        
        for anomaly in detected_anomalies:
            if severity_order.get(anomaly["severity"], 0) > severity_order.get(max_severity, 0):
                max_severity = anomaly["severity"]
        
        has_anomalies = len(detected_anomalies) > 0
        
        if has_anomalies:
            logger.warning(f"🚨 {len(detected_anomalies)} anomaly(ies) detected (severity: {max_severity})")
        else:
            logger.debug(f"✅ No anomalies detected")
        
        return {
            "normal": not has_anomalies,
            "anomaly_detected": has_anomalies,
            "anomalies": detected_anomalies,
            "severity": max_severity if has_anomalies else "none",  # Always return a value
        }
