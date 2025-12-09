"""
Custom nodes directory.

🚀 AUTO-DISCOVERY ENABLED
--------------------------
This is where hackathon participants can drop their custom nodes!

To create a custom node:
1. Create a new .py file here (e.g., my_business_node.py)
2. Define a class that inherits from Node
3. Set the required attributes: type, display_name, category, description
4. Implement the execute() method
5. Done! The node will be auto-discovered and available in the workflow editor.

Example (my_business_node.py):
--------------------------------
from app.core.nodes.base import Node, NodePort
from app.core.execution.context import ExecutionContext
from app.schemas.workflow import PortType, NodeCategory
from typing import Any, Dict

class MyBusinessNode(Node):
    type = "my_business_node"
    display_name = "My Business Node"
    category = NodeCategory.BUSINESS
    description = "Custom node for my business logic"
    
    @classmethod
    def get_input_ports(cls):
        return [
            NodePort(
                name="trigger",
                port_type=PortType.SIGNAL,
                description="Trigger execution"
            ),
            NodePort(
                name="data",
                port_type=PortType.UNIVERSAL,
                description="Input data"
            ),
        ]
    
    @classmethod
    def get_output_ports(cls):
        return [
            NodePort(
                name="result",
                port_type=PortType.UNIVERSAL,
                description="Output result"
            ),
        ]
    
    async def execute(self, inputs: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        # Your custom logic here
        data = inputs.get("data")
        result = f"Processed: {data}"
        return {"result": result}

No imports needed in __init__.py!
Auto-discovery handles everything.
"""

