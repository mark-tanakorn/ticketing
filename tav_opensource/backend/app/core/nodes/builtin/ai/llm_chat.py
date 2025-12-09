"""
LLM Chat Node

General-purpose LLM node for text generation, chat, and AI inference.
Supports all configured providers with automatic fallback.
"""

import logging
from typing import Dict, Any, List
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import LLMCapability
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="large_language_model",
    category=NodeCategory.AI,
    name="Large Language Model",
    description="Generate text using Large Language Models (GPT, Claude, DeepSeek, etc.)",
    icon="fa-solid fa-brain",
    version="1.0.0"
)
class LLMChatNode(Node, LLMCapability):
    """
    LLM Chat Node - General-purpose AI text generation.
    
    Features:
    - Supports all configured providers (OpenAI, Anthropic, DeepSeek, Google, Local)
    - Automatic fallback to alternative providers
    - Variable support in prompts (use {{node.field}} syntax)
    - System + User prompt configuration
    - Temperature control
    - Model selection per node
    
    Use Cases:
    - Text generation
    - Classification
    - Data extraction
    - Translation
    - Summarization
    - Question answering
    - Creative writing
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "context",
                "type": PortType.UNIVERSAL,
                "display_name": "Context",
                "description": "Optional context data to include in prompt",
                "required": False
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "response",
                "type": PortType.TEXT,
                "display_name": "Response",
                "description": "LLM generated response"
            },
            {
                "name": "metadata",
                "type": PortType.UNIVERSAL,
                "display_name": "Metadata",
                "description": "Response metadata (provider, model, tokens, etc.)"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Define configuration schema.
        
        Note: LLM config (provider, model, temperature) is auto-injected
        by the system because this node has LLMCapability.
        """
        return {
            "system_prompt": {
                "type": "string",
                "label": "System Prompt",
                "description": "System instructions to guide the AI's behavior",
                "required": False,
                "widget": "textarea",
                "placeholder": "You are a helpful AI assistant...",
                "default": "",
                "rows": 3
            },
            "user_prompt": {
                "type": "string",
                "label": "User Prompt",
                "description": "The main prompt/question for the AI. Supports variables: {{node.field}}",
                "required": True,
                "widget": "textarea",
                "placeholder": "Generate a greeting message...",
                "rows": 5
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute LLM chat node"""
        try:
            # Resolve prompts (supports variables and templates)
            system_prompt = self.resolve_config(input_data, "system_prompt", "")
            user_prompt = self.resolve_config(input_data, "user_prompt", "")
            
            # Validate user prompt
            if not user_prompt or not user_prompt.strip():
                raise ValueError("User prompt cannot be empty")
            
            # Get context from port (automatically if connected)
            context_data = input_data.ports.get("context")
            
            # Log prompts for debugging
            logger.info(
                f"🤖 LLM Chat Node executing:\n"
                f"  System: {system_prompt[:50]}{'...' if len(system_prompt) > 50 else ''}\n"
                f"  User: {user_prompt[:50]}{'...' if len(user_prompt) > 50 else ''}\n"
                f"  Context: {bool(context_data)}"
            )
            
            # DEBUG: Log full prompts and context
            logger.info("=" * 80)
            logger.info("📝 FULL SYSTEM PROMPT:")
            logger.info(system_prompt if system_prompt else "(empty)")
            logger.info("=" * 80)
            logger.info("📝 FULL USER PROMPT:")
            logger.info(user_prompt)
            logger.info("=" * 80)
            logger.info("📝 CONTEXT DATA:")
            if context_data:
                context_str = str(context_data)
                if len(context_str) > 500:
                    logger.info(f"{context_str[:500]}... (truncated, total length: {len(context_str)} chars)")
                else:
                    logger.info(context_str)
            else:
                logger.info("(no context)")
            logger.info("=" * 80)
            
            # Call LLM (config is auto-resolved by LLMCapability)
            response = await self.call_llm(
                user_prompt=user_prompt,
                system_prompt=system_prompt if system_prompt else None,
                context=context_data
            )
            
            # Calculate ACTUAL prompt length (system + user + context)
            actual_prompt_length = len(user_prompt)
            if system_prompt:
                actual_prompt_length += len(system_prompt)
            if context_data:
                actual_prompt_length += len(str(context_data))
            
            # Build metadata
            metadata = {
                "provider": self.llm_provider,
                "model": self.llm_model,
                "temperature": self.llm_temperature,
                "user_prompt_length": len(user_prompt),
                "system_prompt_length": len(system_prompt) if system_prompt else 0,
                "context_length": len(str(context_data)) if context_data else 0,
                "total_prompt_length": actual_prompt_length,
                "response_length": len(response),
                "has_system_prompt": bool(system_prompt),
                "has_context": bool(context_data)
            }
            
            logger.info(
                f"✅ LLM Chat completed: {len(response)} chars, "
                f"provider={metadata['provider']}, model={metadata['model']}"
            )
            
            return {
                "response": response,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ LLM Chat node error: {e}", exc_info=True)
            return {
                "response": "",
                "metadata": {"error": str(e)},
                "error": str(e)
            }

