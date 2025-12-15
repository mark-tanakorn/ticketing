"""
Node Generator - AI-powered Python node code generation

Generates production-ready node code from conversation requirements.
Uses LangChainManager to call user-configured AI providers.
"""

import logging
import json
import re
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.ai.manager import LangChainManager
from app.database.models.conversation import Conversation
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class NodeGenerator:
    """
    Generates Python node code from conversation requirements.
    
    Uses LangChainManager with specialized prompts to create
    complete, production-ready node classes.
    """
    
    # Code generation system prompt
    CODE_GENERATION_PROMPT = """You are an expert Python developer specializing in creating workflow nodes.

Your task: Generate a complete, production-ready Python node class based on requirements.

CRITICAL RULES:
1. Generate ONLY Python code - no explanations, no markdown, no comments outside the code
2. Use @register_node decorator with proper metadata
3. Inherit from Node base class (and capability mixins if needed)
4. Define get_input_ports(), get_output_ports(), get_config_schema() class methods
5. Implement async execute() method with proper error handling
6. Use appropriate type hints
7. Include helpful docstrings

SECURITY - ONLY use these imports:
- app.core.nodes.base (Node, NodeExecutionInput)
- app.core.nodes.registry (register_node)
- app.core.nodes.capabilities (LLMCapability, ExportCapability, etc.)
- app.core.nodes.multimodal (TextFormatter, MediaFormat, etc.)
- app.schemas.workflow (NodeCategory, PortType)
- typing (Dict, Any, List, Optional)
- logging
- json
- datetime
- httpx (for HTTP requests)
- pathlib (for file paths)

DO NOT use: os, subprocess, eval, exec, __import__, sys

CODE STRUCTURE:
```python
\"\"\"
Node description
\"\"\"

import logging
from typing import Dict, Any, List
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)

@register_node(
    node_type="your_node_type",
    category=NodeCategory.PROCESSING,
    name="Your Node Name",
    description="Clear description",
    icon="fa-solid fa-icon",
    version="1.0.0"
)
class YourNodeClass(Node):
    \"\"\"
    Detailed docstring
    \"\"\"
    
    @classmethod
    def get_input_ports(cls):
        return [
            {
                "name": "input",
                "type": PortType.TEXT,
                "display_name": "Input",
                "description": "Input description",
                "required": True
            }
        ]
    
    @classmethod
    def get_output_ports(cls):
        return [
            {
                "name": "output",
                "type": PortType.UNIVERSAL,
                "display_name": "Output",
                "description": "Output description"
            }
        ]
    
    @classmethod
    def get_config_schema(cls):
        return {
            "config_field": {
                "type": "string",
                "label": "Field Label",
                "description": "Field description",
                "required": False,
                "default": "value"
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput):
        try:
            logger.info(f"Executing node...")
            
            # Get inputs
            input_value = input_data.ports.get("input")
            config_value = self.resolve_config(input_data, "config_field")
            
            # Your logic here
            result = input_value  # Process data
            
            logger.info(f"✅ Node executed successfully")
            
            return {
                "output": result
            }
        
        except Exception as e:
            logger.error(f"❌ Node execution failed: {e}", exc_info=True)
            return {
                "output": None,
                "error": str(e)
            }
```

BEST PRACTICES:
- Use descriptive variable names
- Add logging for debugging
- Handle errors gracefully with try/except
- Return meaningful error messages
- Use resolve_config() for config values
- Use resolve_variable() for dynamic variables
- Add type hints everywhere
- Keep execute() method clean and readable

Generate the complete code now based on the requirements provided."""

    def __init__(self, db: Session):
        """Initialize node generator"""
        self.db = db
        self.langchain_manager = LangChainManager(db)
    
    async def generate_from_conversation(
        self, 
        conversation: Conversation
    ) -> Dict[str, Any]:
        """
        Generate node code from conversation requirements.
        
        Args:
            conversation: Conversation with requirements
        
        Returns:
            Dict with:
            - code: Generated Python code
            - node_type: Extracted node type
            - class_name: Extracted class name
        """
        logger.info(f"✨ Generating code for conversation {conversation.id}")
        
        try:
            # Build generation prompt with requirements
            prompt = self._build_generation_prompt(conversation)
            
            # Call AI to generate code
            generated_code = await self.langchain_manager.call_llm(
                prompt=prompt,
                provider=conversation.provider,
                model=conversation.model,
                temperature=0.2,  # Lower temperature for more consistent code
                max_tokens=4000,  # Enough for a complete node
                fallback=True
            )
            
            # Clean up the generated code
            code = self._clean_generated_code(generated_code)
            
            # Extract metadata
            node_type = self._extract_node_type(code)
            class_name = self._extract_class_name(code)
            
            logger.info(f"✅ Code generated: {node_type} ({len(code)} chars)")
            
            return {
                "code": code,
                "node_type": node_type,
                "class_name": class_name
            }
        
        except Exception as e:
            logger.error(f"❌ Code generation failed: {e}", exc_info=True)
            raise Exception(f"Failed to generate code: {str(e)}")
    
    def _build_generation_prompt(self, conversation: Conversation) -> str:
        """
        Build the code generation prompt with all requirements.
        """
        prompt = self.CODE_GENERATION_PROMPT + "\n\n"
        prompt += "=== REQUIREMENTS ===\n\n"
        
        # Add conversation context
        prompt += "**Conversation Summary:**\n"
        for msg in conversation.messages[:10]:  # First 10 messages for context
            if msg.role == "user":
                prompt += f"- User wants: {msg.content[:100]}\n"
        
        prompt += "\n"
        
        # Add structured requirements if available
        if conversation.requirements:
            prompt += "**Structured Requirements:**\n"
            prompt += json.dumps(conversation.requirements, indent=2)
            prompt += "\n\n"
        
        # Add specific instructions
        prompt += "**Generate:**\n"
        prompt += f"- Category: {conversation.requirements.get('category', 'processing') if conversation.requirements else 'processing'}\n"
        prompt += "- Include proper error handling\n"
        prompt += "- Add clear docstrings\n"
        prompt += "- Use logging for debugging\n"
        prompt += "\n"
        
        prompt += "Generate the complete Python code now (ONLY code, no explanations):"
        
        return prompt
    
    def _clean_generated_code(self, code: str) -> str:
        """
        Clean up AI-generated code.
        
        Removes markdown code blocks, extra whitespace, etc.
        """
        # Remove markdown code blocks
        code = re.sub(r'```python\s*\n', '', code)
        code = re.sub(r'```\s*$', '', code)
        code = re.sub(r'^```\s*', '', code)
        
        # Remove any leading/trailing whitespace
        code = code.strip()
        
        # Ensure proper spacing
        code = re.sub(r'\n{3,}', '\n\n', code)
        
        return code
    
    def _extract_node_type(self, code: str) -> str:
        """
        Extract node_type from @register_node decorator.
        """
        match = re.search(r'node_type=["\']([^"\']+)["\']', code)
        if match:
            return match.group(1)
        
        # Fallback: look for class name and generate node_type
        class_match = re.search(r'class\s+(\w+)', code)
        if class_match:
            class_name = class_match.group(1)
            # Convert CamelCase to snake_case
            node_type = re.sub('([a-z0-9])([A-Z])', r'\1_\2', class_name).lower()
            node_type = node_type.replace('_node', '')
            return node_type
        
        return "custom_node"
    
    def _extract_class_name(self, code: str) -> str:
        """
        Extract class name from generated code.
        """
        match = re.search(r'class\s+(\w+)', code)
        if match:
            return match.group(1)
        return "CustomNode"
    
    async def refine_code(
        self, 
        conversation: Conversation,
        refinement_request: str
    ) -> Dict[str, Any]:
        """
        Refine existing generated code based on user feedback.
        
        Args:
            conversation: Conversation with generated code
            refinement_request: What to change/improve
        
        Returns:
            Dict with:
            - code: Updated code
            - explanation: What was changed
        """
        logger.info(f"🔄 Refining code for conversation {conversation.id}")
        
        try:
            prompt = f"""You are refining a Python workflow node based on user feedback.

CURRENT CODE:
```python
{conversation.generated_code}
```

USER FEEDBACK:
{refinement_request}

TASK:
Modify the code according to the feedback. Return ONLY the complete updated Python code.
Maintain the same structure and follow all the rules from before.

Generate the updated code now:"""
            
            # Call AI with lower temperature for precise refinement
            refined_code = await self.langchain_manager.call_llm(
                prompt=prompt,
                provider=conversation.provider,
                model=conversation.model,
                temperature=0.2,
                fallback=True
            )
            
            # Clean up
            code = self._clean_generated_code(refined_code)
            
            logger.info(f"✅ Code refined successfully")
            
            return {
                "code": code,
                "explanation": f"Updated code based on your request: {refinement_request}"
            }
        
        except Exception as e:
            logger.error(f"❌ Code refinement failed: {e}", exc_info=True)
            raise Exception(f"Failed to refine code: {str(e)}")

