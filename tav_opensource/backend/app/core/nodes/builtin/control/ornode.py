"""
Merge Node - OR-logic Execution for Loop Entry Points

Unlike normal nodes (AND-logic: wait for ALL inputs), this node executes
when ANY input arrives. Essential for workflow loops and path merging.
"""

import logging
from typing import Dict, Any, List, Optional
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="or",
    category=NodeCategory.WORKFLOW,
    name="OR Gate",
    description="OR multiple paths - executes on FIRST available input (OR logic). Essential for loops.",
    icon="fa-solid fa-circle-nodes",
    version="1.0.0"
)
class ORGateNode(Node):
    """
    OR Gate Node - OR-based Path Merging
    
    **Critical for Loops:**
    Normal nodes use AND-logic (wait for ALL inputs to complete).
    This node uses OR-logic (execute when ANY input arrives).
    
    Use Cases:
    1. **Loop Entry Points:** When you need to loop back to earlier nodes
       - Initial path: Upload → Merge → Process
       - Loop path:   Retry  → Merge (same node)
       - Without Merge: Process waits for BOTH paths = DEADLOCK
       - With Merge: Process executes on EITHER path = SUCCESS
    
    2. **Path Merging:** After decision branches that need to reconverge
       - Decision → [True Path / False Path] → Merge → Continue
    
    3. **First-Wins:** Race conditions where first result triggers next step
       - [API 1 / API 2 / API 3] → Merge → Process (uses first response)
    
    How It Works:
    - Has multiple input ports (input1, input2, input3, ...)
    - Executes immediately when ANY input is available
    - Outputs the data from the first available input
    - Other inputs are ignored (not errors, just not needed)
    
    Configuration:
    - Merge Strategy: Which input to use when multiple arrive
    - Priority: If multiple inputs available, which to prefer
    
    ⚠️ Important Notes:
    - This node bypasses normal dependency resolution
    - In loop scenarios, one path will always be "unavailable" on first run
    - That's expected and handled gracefully
    - The executor won't wait for ALL inputs - it executes on FIRST
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """
        Define input ports.
        
        Multiple inputs with OR-logic:
        - Execute when ANY input is ready
        - Don't wait for all inputs
        """
        return [
            {
                "name": "input1",
                "type": PortType.UNIVERSAL,
                "display_name": "Input 1 (Primary)",
                "description": "First input path (e.g., initial upload)",
                "required": False  # Optional because OR-logic
            },
            {
                "name": "input2",
                "type": PortType.UNIVERSAL,
                "display_name": "Input 2 (Secondary)",
                "description": "Second input path (e.g., loop back)",
                "required": False  # Optional because OR-logic
            },
            {
                "name": "input3",
                "type": PortType.UNIVERSAL,
                "display_name": "Input 3",
                "description": "Third input path (optional)",
                "required": False
            },
            {
                "name": "input4",
                "type": PortType.UNIVERSAL,
                "display_name": "Input 4",
                "description": "Fourth input path (optional)",
                "required": False
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "output",
                "type": PortType.UNIVERSAL,
                "display_name": "OR Output",
                "description": "Data from the first available input"
            },
            {
                "name": "metadata",
                "type": PortType.UNIVERSAL,
                "display_name": "Metadata",
                "description": "Information about which input was used"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "merge_strategy": {
                "widget": "select",
                "label": "Merge Strategy",
                "description": "How to choose when multiple inputs are available",
                "required": False,
                "default": "priority",
                "options": [
                    {"label": "Priority (use input1, then input2, etc.)", "value": "priority"},
                    {"label": "First Available", "value": "first"},
                    {"label": "Combine All (merge all available inputs)", "value": "combine"}
                ],
                "help": "Priority: Prefers input1 > input2 > input3 > input4. First: Uses whichever arrived first. Combine: Merges all available inputs into array."
            },
            "passthrough_metadata": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Passthrough Metadata",
                "description": "Include metadata from source input",
                "required": False,
                "default": True,
                "help": "If enabled, passes through metadata from the source input"
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """
        Execute merge node with OR-logic.
        
        Key Behavior:
        - Collects all available inputs
        - Selects based on merge strategy
        - Returns immediately (doesn't wait for missing inputs)
        """
        try:
            merge_strategy = self.resolve_config(input_data, "merge_strategy", "priority")
            passthrough_metadata = self.resolve_config(input_data, "passthrough_metadata", True)
            
            logger.info(f"🔀 Merge Node executing: {self.node_id} (strategy: {merge_strategy})")
            
            # Collect available inputs
            available_inputs = {}
            for port_name in ["input1", "input2", "input3", "input4"]:
                port_data = input_data.ports.get(port_name)
                if port_data is not None:  # None means not connected or not available yet
                    available_inputs[port_name] = port_data
                    logger.info(f"  ✓ {port_name}: Available ({type(port_data).__name__})")
                else:
                    logger.debug(f"  ✗ {port_name}: Not available (OK for OR-logic)")
            
            # Validate at least one input
            if not available_inputs:
                error_msg = "Merge node has no available inputs. At least one input must be connected and provide data."
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)
            
            logger.info(f"📊 Merge node has {len(available_inputs)} available input(s): {list(available_inputs.keys())}")
            
            # Select output based on strategy
            selected_input_name = None
            selected_data = None
            
            if merge_strategy == "priority":
                # Use first available in priority order
                for port_name in ["input1", "input2", "input3", "input4"]:
                    if port_name in available_inputs:
                        selected_input_name = port_name
                        selected_data = available_inputs[port_name]
                        logger.info(f"🎯 Selected {port_name} (priority strategy)")
                        break
            
            elif merge_strategy == "first":
                # Use first available (arbitrary order)
                selected_input_name = list(available_inputs.keys())[0]
                selected_data = available_inputs[selected_input_name]
                logger.info(f"🎯 Selected {selected_input_name} (first available strategy)")
            
            elif merge_strategy == "combine":
                # Combine all inputs into array
                selected_input_name = "combined"
                selected_data = list(available_inputs.values())
                logger.info(f"🎯 Combined {len(available_inputs)} inputs into array")
            
            else:
                raise ValueError(f"Unknown merge strategy: {merge_strategy}")
            
            # Build metadata
            metadata = {
                "merge_strategy": merge_strategy,
                "selected_input": selected_input_name,
                "available_inputs": list(available_inputs.keys()),
                "num_available": len(available_inputs),
                "execution_mode": "OR-logic"
            }
            
            # Include source metadata if configured
            if passthrough_metadata and isinstance(selected_data, dict):
                source_metadata = selected_data.get("metadata", {})
                if source_metadata:
                    metadata["source_metadata"] = source_metadata
            
            logger.info(
                f"✅ Merge node completed: Output from {selected_input_name} "
                f"({len(available_inputs)} inputs available)"
            )
            
            return {
                "output": selected_data,
                "metadata": metadata
            }
            
        except Exception as e:
            error_msg = f"Merge node error: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                "output": None,
                "metadata": {
                    "error": error_msg,
                    "merge_strategy": merge_strategy if 'merge_strategy' in locals() else "unknown"
                }
            }


if __name__ == "__main__":
    print("✅ Merge Node (OR-logic) loaded")

