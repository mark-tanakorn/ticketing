"""
While Loop Node

Repeats workflow execution N times, like a while loop in programming.

Perfect for:
- Running simulations for N days/hours/iterations
- Processing N batches of data
- Any scenario that needs "do this X times"
"""

from typing import Any, Dict, Optional, List
import logging

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import PortType, NodeCategory

logger = logging.getLogger(__name__)


@register_node(
    node_type="while_loop",
    category=NodeCategory.WORKFLOW,
    name="While Loop",
    description="Repeat workflow N times (like a while loop in code)",
    icon="fa-solid fa-repeat"
)
class WhileLoopNode(Node):
    """
    While Loop - repeats workflow execution N times.
    
    Think of it like:
    ```python
    for i in range(1, 31):  # Run 30 times
        # Your workflow runs here
    ```
    
    Pair with Virtual Time node for simulations, or use standalone
    for simple iteration counting.
    
    Use with a Decision node at the end to loop back to this node.
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "trigger",
                "type": PortType.SIGNAL,
                "display_name": "Trigger",
                "description": "Trigger loop start or continue to next iteration",
                "required": False
            },
            {
                "name": "iteration_data",
                "type": PortType.UNIVERSAL,
                "display_name": "Iteration Data",
                "description": "Optional data to pass through each iteration",
                "required": False
            },
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "iteration_number",
                "type": PortType.UNIVERSAL,
                "display_name": "Iteration Number",
                "description": "Current iteration number (1-based)"
            },
            {
                "name": "max_iterations",
                "type": PortType.UNIVERSAL,
                "display_name": "Max Iterations",
                "description": "Maximum number of iterations configured"
            },
            {
                "name": "iteration_label",
                "type": PortType.TEXT,
                "display_name": "Iteration Label",
                "description": "Human-readable iteration label (e.g., 'day_5')"
            },
            {
                "name": "continue_loop",
                "type": PortType.SIGNAL,
                "display_name": "Continue Loop",
                "description": "Signal to continue to next iteration"
            },
            {
                "name": "exit_loop",
                "type": PortType.SIGNAL,
                "display_name": "Exit Loop",
                "description": "Signal that loop is completed"
            },
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "max_iterations": {
                "label": "Max Iterations",
                "type": "number",
                "default": 10,
                "description": "Maximum number of loop iterations (e.g., 30 for 30 days)",
            },
            "iteration_label_template": {
                "label": "Iteration Label Template",
                "type": "string",
                "default": "iteration_{n}",
                "description": "Label template for each iteration (use {n} for iteration number, e.g., 'day_{n}')",
            },
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """
        Execute loop orchestration logic.
        
        The node uses config for max_iterations and tracks the current
        iteration via shared variables (_loop_iteration).
        """
        # Get max iterations from config (handle string or int)
        max_iterations_raw = self.resolve_config(input_data, "max_iterations", 10)
        try:
            max_iterations = int(max_iterations_raw)
        except (ValueError, TypeError):
            logger.warning(f"Invalid max_iterations '{max_iterations_raw}', using default 10")
            max_iterations = 10
        
        # Get current iteration from variables (start at 1)
        current_iteration = input_data.variables.get("_loop_iteration", 1)
        
        # Generate iteration label
        template = self.resolve_config(input_data, "iteration_label_template", "iteration_{n}")
        iteration_label = template.format(n=current_iteration)
        
        # Check if we should continue
        should_exit = current_iteration >= max_iterations
        
        logger.info(f"🔁 Loop iteration {current_iteration}/{max_iterations} (label: {iteration_label})")
        
        # Increment for next iteration (stored in variables)
        if not should_exit:
            input_data.variables["_loop_iteration"] = current_iteration + 1
        else:
            logger.info(f"✅ Loop completed after {current_iteration} iterations")
        
        return {
            "iteration_number": current_iteration,
            "max_iterations": max_iterations,
            "iteration_label": iteration_label,
            "continue_loop": not should_exit,
            "exit_loop": should_exit,
        }
