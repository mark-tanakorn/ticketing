"""
Built-in nodes.

🚀 AUTO-DISCOVERY ENABLED
--------------------------
All nodes in this directory (and subdirectories) are automatically discovered
and registered by the NodeRegistry.

NO NEED TO EDIT THIS FILE!

To create a new node:
1. Create a new .py file anywhere in builtin/ (e.g., builtin/my_category/my_node.py)
2. Define a class that inherits from Node
3. Set the 'type', 'display_name', 'category', and 'description' attributes
4. That's it! It will be auto-discovered on startup.

Example:
--------
class MyCustomNode(Node):
    type = "my_custom_node"
    display_name = "My Custom Node"
    category = NodeCategory.ACTIONS
    description = "Does something cool"
    
    @classmethod
    def get_input_ports(cls):
        return [...]
    
    @classmethod
    def get_output_ports(cls):
        return [...]
    
    async def execute(self, inputs, context):
        return {...}
"""

# Auto-discovery happens in app/core/nodes/loader.py
# Called automatically on app startup