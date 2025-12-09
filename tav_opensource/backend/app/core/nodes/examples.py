"""
Example Node Implementations

Shows how to use Node base class and capability mixins.
"""

import httpx
from typing import Dict, Any

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import LLMCapability, AICapability
from app.core.nodes.registry import register_node


# ============================================================================
# Example 1: Basic Action Node (no LLM, no AI)
# ============================================================================

@register_node("http_request", category="communication", description="Make HTTP request")
class HTTPRequestNode(Node):
    """
    Basic HTTP request node.
    
    Resource pool: standard
    """
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        url = input_data.ports.get("url")
        method = input_data.config.get("method", "GET")
        
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                body = input_data.ports.get("body", {})
                response = await client.post(url, json=body)
            else:
                raise ValueError(f"Unsupported method: {method}")
        
        return {
            "output": response.json(),
            "status_code": response.status_code,
        }


# ============================================================================
# Example 2: Communication Node WITH LLM
# ============================================================================

@register_node("send_email_with_ai", category="communication", description="Send email with AI-generated subject")
class SendEmailWithAINode(Node, LLMCapability):
    """
    Email node that uses LLM to generate subject line.
    
    Resource pool: llm (because of LLMCapability)
    """
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        to = input_data.ports.get("to")
        content = input_data.ports.get("content")
        
        # Optional: use LLM to generate subject
        if input_data.config.get("auto_subject", False):
            subject = await self.call_llm(
                user_prompt=f"Generate a concise email subject line for: {content[:200]}",
                system_prompt="You are an email assistant. Generate only the subject line, no quotes.",
                max_tokens=50
            )
        else:
            subject = input_data.ports.get("subject", "No subject")
        
        # Send email (mock)
        print(f"Sending email to {to}: {subject}")
        
        return {
            "output": "sent",
            "subject_used": subject,
        }


# ============================================================================
# Example 3: Pure AI Compute Node (no LLM)
# ============================================================================

@register_node("image_classifier", category="ai", description="Classify images using local ML")
class ImageClassifierNode(Node, AICapability):
    """
    Image classifier using local ML model.
    
    Resource pool: ai (because of AICapability)
    """
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        image_path = input_data.ports.get("image")
        
        # Heavy local ML computation (mock)
        # In real implementation: load model, preprocess, inference
        result = {
            "class": "cat",
            "confidence": 0.95,
        }
        
        return {
            "output": result,
        }


# ============================================================================
# Example 4: AI Node WITH LLM (both!)
# ============================================================================

@register_node("image_analyzer_ai", category="ai", description="Analyze images with ML + LLM")
class ImageAnalyzerNode(Node, AICapability, LLMCapability):
    """
    Advanced image analyzer with ML + LLM.
    
    Resource pool: both ai AND llm (uses both semaphores)
    """
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        image_path = input_data.ports.get("image")
        
        # Step 1: Heavy ML computation to extract features (AICapability)
        features = {
            "objects": ["person", "dog", "tree"],
            "colors": ["blue", "green", "brown"],
            "scene": "outdoor",
        }
        
        # Step 2: Use LLM to generate natural description (LLMCapability)
        description = await self.call_llm(
            user_prompt=f"Describe this image based on features: {features}",
            system_prompt="You are an image description assistant. Be concise and descriptive.",
            max_tokens=100
        )
        
        return {
            "features": features,
            "description": description,
            "output": {
                "features": features,
                "description": description,
            }
        }


# ============================================================================
# Example 5: Text Processing with LLM (custom config)
# ============================================================================

@register_node("text_summarizer", category="ai", description="Summarize text using LLM")
class TextSummarizerNode(Node, LLMCapability):
    """
    Text summarizer with configurable LLM settings.
    
    Shows how to use node-level LLM config.
    """
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        text = input_data.ports.get("input")
        max_length = input_data.config.get("max_length", 100)
        
        # Call LLM with auto-injected config from node
        # Config cascade: node config → workflow variables → global defaults
        summary = await self.call_llm(
            user_prompt=f"Summarize this text in {max_length} words: {text}",
            system_prompt="You are a summarization assistant. Be concise.",
        )
        
        return {
            "output": summary,
            "provider_used": self.llm_provider,
            "model_used": self.llm_model,
        }


# ============================================================================
# Example 6: Multi-turn Conversation with Function Calling
# ============================================================================

@register_node("ai_assistant", category="ai", description="AI assistant with function calling")
class AIAssistantNode(Node, LLMCapability):
    """
    AI assistant that can use function calling.
    
    Shows advanced LLM features (messages, tools).
    """
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        user_message = input_data.ports.get("message")
        conversation_history = input_data.variables.get("conversation_history", [])
        
        # Build messages
        messages = conversation_history + [
            {"role": "user", "content": user_message}
        ]
        
        # Define tools (function calling)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_database",
                    "description": "Search the database for information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
        
        # Call LLM with messages and tools
        response = await self.call_llm_with_messages(
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        # Update conversation history
        new_history = messages + [
            {"role": "assistant", "content": response.content}
        ]
        
        return {
            "output": response.content,
            "conversation_history": new_history,
            "tool_calls": response.tool_calls,
        }


# ============================================================================
# Resource Class Detection Examples
# ============================================================================

def show_resource_classes():
    """
    Demonstrate resource class detection.
    
    This is for documentation purposes - shows how nodes are classified.
    """
    from app.schemas.workflow import NodeConfiguration, NodeCategory
    
    # Example 1: Standard node
    http_config = NodeConfiguration(
        node_id="http1",
        node_type="http_request",
        name="HTTP Request",
        category=NodeCategory.COMMUNICATION,
    )
    http_node = HTTPRequestNode(http_config)
    print(f"HTTP Node: {http_node.resource_classes}")  # ['standard']
    
    # Example 2: LLM node
    email_config = NodeConfiguration(
        node_id="email1",
        node_type="send_email_with_ai",
        name="Email with AI",
        category=NodeCategory.COMMUNICATION,
    )
    email_node = SendEmailWithAINode(email_config)
    print(f"Email Node: {email_node.resource_classes}")  # ['llm']
    
    # Example 3: AI compute node
    image_config = NodeConfiguration(
        node_id="img1",
        node_type="image_classifier",
        name="Image Classifier",
        category=NodeCategory.AI,
    )
    image_node = ImageClassifierNode(image_config)
    print(f"Image Node: {image_node.resource_classes}")  # ['ai']
    
    # Example 4: Both AI + LLM
    analyzer_config = NodeConfiguration(
        node_id="analyzer1",
        node_type="image_analyzer_ai",
        name="Image Analyzer",
        category=NodeCategory.AI,
    )
    analyzer_node = ImageAnalyzerNode(analyzer_config)
    print(f"Analyzer Node: {analyzer_node.resource_classes}")  # ['llm', 'ai']

