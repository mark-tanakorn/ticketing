"""
Conversation Manager - Multi-turn AI chat for custom node building

Uses the centralized LangChainManager to call user-configured AI providers.
Guides users through defining node requirements via natural conversation.
"""

import logging
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.ai.manager import LangChainManager
from app.database.models.conversation import Conversation, ConversationMessage

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversational AI for custom node building.
    
    Uses LangChainManager to call user-configured AI providers.
    Progressively extracts requirements from conversation.
    """
    
    # System prompt that guides the AI to be a node-building expert
    SYSTEM_PROMPT = """You are an expert workflow node designer helping users create custom nodes for a Python-based workflow automation system.

Your role:
1. Ask clarifying questions to understand what the user wants to build
2. Guide them through node design decisions (inputs, outputs, config)
3. Extract requirements progressively
4. Suggest best practices and patterns
5. Be conversational, friendly, and helpful

API CHEAT SHEET (use exactly this shape):
- Imports:
  from app.core.nodes.base import Node, NodeExecutionInput
  from app.core.nodes.registry import register_node
  from app.schemas.workflow import NodeCategory, PortType

- Decorator:
  @register_node(
      node_type="my_node",
      category=NodeCategory.ACTIONS,
      name="My Node",
      description="...",
      icon="fa-solid fa-circle",
      version="1.0.0"
  )

- Class skeleton:
  class MyNode(Node):
      @classmethod
      def get_input_ports(cls):
          return [{
              "name": "input",
              "type": PortType.UNIVERSAL,
              "display_name": "Input",
              "description": "Input data",
              "required": False
          }]

      @classmethod
      def get_output_ports(cls):
          return [{
              "name": "result",
              "type": PortType.UNIVERSAL,
              "display_name": "Result",
              "description": "Output data",
              "required": True
          }]

      @classmethod
      def get_config_schema(cls):
          return {
              "api_key": {
                  "type": "text",
                  "label": "API Key",
                  "description": "Secret key",
                  "required": True,
                  "secret": True,
                  "default": ""
              }
          }

      async def execute(self, input_data: NodeExecutionInput):
          # input_data.inputs is a dict
          # self.config is a dict of config values
          data = input_data.inputs.get("input")
          return {"result": data}

Node Structure Overview:
- Nodes process data through input ports and produce outputs
- Nodes can have configuration fields (API keys, settings, etc.)
- Nodes are organized by category (ai, processing, actions, etc.)
- Input/output ports have types: text, universal, document, image, etc.

Key Questions to Ask:
1. What should the node do? (core functionality)
2. What data does it need as input? (input ports)
3. What data should it output? (output ports)
4. What configuration is needed? (API keys, settings)
5. Does it need external APIs or libraries?
6. What category fits best? (ai, processing, actions, etc.)

Conversation Style:
- Be conversational and friendly
- Ask one or two questions at a time (don't overwhelm)
- Acknowledge their answers before asking next question
- Suggest ideas when they're unsure

CODE GENERATION PHASE:
- When you have enough information and the user says "proceed", "generate", or "go ahead":
- DO NOT say "I have everything I need".
- DO NOT ask more questions.
- IMMEDIATELY generate the full Python code for the node.
- Wrap the code in a markdown block like this:
  ```python
  ... code here ...
  ```
- The code must be a complete, working Python class inheriting from `Node`.
- Use the standard template structure (imports, class definition, `setup`, `execute`).
- Ensure all imports are standard or pre-approved.

Remember: You are the code generator. When confirmed, output the code directly in the chat.
"""

    def __init__(self, db: Session):
        """Initialize conversation manager"""
        self.db = db
        self.langchain_manager = LangChainManager(db)
        # Pre-load key reference files for context (bounded size, read on demand)
        self._base_path = Path("app/core/nodes/base.py")
        self._registry_path = Path("app/core/nodes/registry.py")
        self._builtin_root = Path("app/core/nodes/builtin")
        self._docs_path = Path("docs/reference/built-in-nodes.md")
    
    async def get_initial_message(self) -> str:
        """
        Get the initial AI greeting when starting a conversation.
        
        Returns a friendly greeting that introduces the AI assistant.
        """
        return """Hi! 👋 I'm here to help you create a custom workflow node.

I'll guide you through the process by asking a few questions about what you want to build.

**To get started, tell me:** What should your node do? What problem are you trying to solve?

For example:
- "Fetch weather data from an API"
- "Parse CSV files and extract specific columns"  
- "Send notifications via Slack"
- "Process images and detect objects"

Don't worry about technical details yet - just describe what you need! 😊"""
    
    async def process_message(
        self, 
        conversation: Conversation, 
        user_message: str
    ) -> Dict[str, Any]:
        """
        Process a user message and generate AI response.
        
        Uses LangChainManager to call the user-selected AI provider.
        Progressively extracts requirements from the conversation.
        
        Args:
            conversation: The conversation object
            user_message: The user's message
        
        Returns:
            Dict with:
            - assistant_message: AI's response
            - ready_to_generate: Whether we have enough info
            - requirements: Extracted requirements (if any)
            - tokens_used: Token count (if available)
            - response_time_ms: Response time in milliseconds
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"💬 Processing message in conversation {conversation.id}")
            
            # Check if user is confirming they want to generate code
            user_confirming_generation = self._check_user_confirmation(user_message)
            
            # If user is confirming and we already extracted requirements, skip AI and go straight to generation
            if user_confirming_generation and conversation.requirements:
                logger.info("✅ User confirmed generation - proceeding immediately")
                return {
                    "assistant_message": "Generating your custom node now...",
                    "ready_to_generate": True,
                    "requirements": conversation.requirements,
                    "tokens_used": None,
                    "response_time_ms": 0
                }
            
            # Build conversation history for context
            conversation_history = self._build_conversation_history(conversation, user_message)
            
            # Call AI via LangChainManager (respects user's provider/model selection)
            ai_response = await self.langchain_manager.call_llm(
                prompt=conversation_history,
                provider=conversation.provider,
                model=conversation.model,
                temperature=float(conversation.temperature) if conversation.temperature else 0.3,
                fallback=True  # Enable fallback to secondary provider
            )
            
            # Calculate response time
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Extract requirements from conversation so far
            requirements = self._extract_requirements(conversation, user_message, ai_response)
            
            # Check if AI indicates readiness to generate code
            ready_to_generate = self._check_ready_to_generate(ai_response)
            
            logger.info(f"✅ AI response generated (ready={ready_to_generate})")
            
            return {
                "assistant_message": ai_response,
                "ready_to_generate": ready_to_generate,
                "requirements": requirements,
                "tokens_used": None,  # LangChainManager doesn't return this yet
                "response_time_ms": int(response_time)
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to process message: {e}", exc_info=True)
            
            # Fallback response
            return {
                "assistant_message": f"I apologize, but I encountered an error processing your message. Could you try rephrasing that? (Error: {str(e)})",
                "ready_to_generate": False,
                "requirements": conversation.requirements,
                "tokens_used": None,
                "response_time_ms": 0
            }
    
    async def process_message_stream(
        self, 
        conversation: Conversation, 
        user_message: str
    ):
        """
        Process a user message and stream AI response token-by-token.
        
        Yields tokens as they arrive from the AI.
        
        Args:
            conversation: The conversation object
            user_message: The user's message
        
        Yields:
            Dict with:
            - type: "token" | "done"
            - content: Token text (for type="token")
            - ready_to_generate: bool (for type="done")
            - requirements: extracted requirements (for type="done")
            - generated_code: str (if code was extracted from response)
        """
        try:
            logger.info(f"💬 Processing streaming message in conversation {conversation.id}")
            
            # Build conversation history for context
            conversation_history = self._build_conversation_history(conversation, user_message)

            # Attach scoped reference context (read-only "tool" lookups)
            context_snippets = self._gather_references(user_message)
            if context_snippets:
                conversation_history += "\n\n### REFERENCE CONTEXT (from repo, do NOT verbatim copy comments):\n"
                for label, snippet in context_snippets:
                    conversation_history += f"\n# {label}:\n{snippet}\n"
            
            # Add specific instruction for code generation if user seems to be asking for it
            user_confirming = self._check_user_confirmation(user_message)
            if user_confirming:
                conversation_history += """

============================================
CRITICAL: CODE GENERATION MODE ACTIVATED
============================================
The user confirmed. Output ONLY the Python code wrapped in ```python markdown.

Your ENTIRE next response should be:

Here is the complete code for your custom node:

```python
[THE FULL WORKING PYTHON CODE HERE - DO NOT TRUNCATE]
```

DO NOT add explanations before or after the code block.
START WITH "Here is the complete code" then IMMEDIATELY the code block.
============================================
"""
            
            # Stream AI response
            full_response = ""
            async for token in self.langchain_manager.call_llm_stream(
                prompt=conversation_history,
                provider=conversation.provider,
                model=conversation.model,
                temperature=float(conversation.temperature) if conversation.temperature else 0.3
            ):
                full_response += token
                yield {
                    "type": "token",
                    "content": token
                }
            
            # Extract requirements from full response
            requirements = self._extract_requirements(conversation, user_message, full_response)
            
            # Check for generated code block
            generated_code = self._extract_code_block(full_response)
            ready_to_generate = bool(generated_code)
            
            logger.info(f"✅ AI streaming complete (code_found={ready_to_generate})")
            
            yield {
                "type": "done",
                "assistant_message": full_response,
                "ready_to_generate": ready_to_generate,
                "requirements": requirements,
                "generated_code": generated_code
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to stream message: {e}", exc_info=True)
            error_msg = f"I apologize, but I encountered an error processing your message. Could you try rephrasing that? (Error: {str(e)})"
            for char in error_msg:
                yield {
                    "type": "token",
                    "content": char
                }
            yield {
                "type": "done",
                "assistant_message": error_msg,
                "ready_to_generate": False,
                "requirements": conversation.requirements,
                "generated_code": None
            }
            
    def _extract_code_block(self, text: str) -> Optional[str]:
        """Extract Python code block from text"""
        # Look for ```python ... ``` or just ``` ... ```
        # Use a more robust pattern that captures content between backticks
        pattern = r"```(?:python|py)?\s*(.*?)```"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            code = match.group(1).strip()
            # Basic validation to ensure it looks like Python code
            if "class " in code or "def " in code or "import " in code:
                return code
        return None

    def _gather_references(self, user_message: str) -> List[tuple]:
        """
        Lightweight "tool calls" to retrieve scoped references from repo:
        - builtin nodes (searched by keyword)
        - base/registry APIs
        - docs reference
        - curated examples by heuristic
        """
        refs: List[tuple] = []
        # Heuristics
        msg_lower = user_message.lower()
        keywords = []
        if "weather" in msg_lower or "forecast" in msg_lower:
            keywords.append("weather")
        if "http" in msg_lower or "api" in msg_lower or "fetch" in msg_lower:
            keywords.append("http")
        if "llm" in msg_lower or "prompt" in msg_lower:
            keywords.append("llm")
        if not keywords:
            keywords.append("")  # generic

        # Helper: safe read
        def safe_read(path: Path, max_bytes: int = 4000) -> str:
            if not path.exists() or not path.is_file():
                return ""
            return path.read_bytes()[:max_bytes].decode(errors="ignore")

        # Always include base and registry snippets (short)
        base_snippet = safe_read(self._base_path, 2000)
        if base_snippet:
            refs.append(("base.py (Node API)", base_snippet))
        registry_snippet = safe_read(self._registry_path, 2000)
        if registry_snippet:
            refs.append(("registry.py (register_node)", registry_snippet))

        # Include docs reference
        docs_snippet = safe_read(self._docs_path, 2000)
        if docs_snippet:
            refs.append(("docs/built-in-nodes.md", docs_snippet))

        # Search builtin nodes for keyword
        if self._builtin_root.exists():
            for kw in keywords:
                if len(refs) >= 5:
                    break
                for file in sorted(self._builtin_root.rglob("*.py")):
                    if len(refs) >= 5:
                        break
                    try:
                        text = file.read_text(errors="ignore")
                        if kw in text.lower():
                            idx = text.lower().find(kw) if kw else 0
                            start = max(0, idx - 400)
                            end = min(len(text), idx + 400)
                            snippet = text[start:end]
                            refs.append((f"builtin::{file.name}", snippet))
                    except Exception:
                        continue

        # Add a curated example by heuristic
        curated = None
        if "weather" in keywords:
            curated = self._curated_examples().get("weather")
        elif "http" in keywords:
            curated = self._curated_examples().get("http")
        elif "llm" in keywords:
            curated = self._curated_examples().get("llm")
        else:
            curated = self._curated_examples().get("processing")
        if curated:
            refs.append(("curated example", curated))

        # Trim to avoid token blow-up
        return refs[:6]

    def _curated_examples(self) -> Dict[str, str]:
        """Small curated examples to reduce hallucinations"""
        return {
            "llm": """```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
from app.services.langchain_manager import LangChainManager

@register_node(
    node_type="llm_prompt",
    category=NodeCategory.AI,
    name="LLM Prompt",
    description="Call an LLM with a prompt",
    icon="fa-solid fa-robot",
)
class LLMPromptNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [{
            "name": "prompt",
            "type": PortType.TEXT,
            "display_name": "Prompt",
            "description": "Prompt to send",
            "required": True,
        }]

    @classmethod
    def get_output_ports(cls):
        return [{
            "name": "response",
            "type": PortType.TEXT,
            "display_name": "Response",
            "description": "LLM response",
            "required": True,
        }]

    @classmethod
    def get_config_schema(cls):
        return {
            "provider": {"type": "text", "label": "Provider", "default": "anthropic"},
            "model": {"type": "text", "label": "Model", "default": "claude-3-5-sonnet-20241022"},
            "temperature": {"type": "number", "label": "Temperature", "default": 0.2},
        }

    async def execute(self, input_data: NodeExecutionInput):
        manager = LangChainManager(self.db)
        prompt = input_data.inputs.get("prompt", "")
        result = await manager.call_llm(
            prompt=prompt,
            provider=self.config.get("provider", "anthropic"),
            model=self.config.get("model", "claude-3-5-sonnet-20241022"),
            temperature=float(self.config.get("temperature", 0.2)),
        )
        return {"response": result}
```""",
            "http": """```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
import requests

@register_node(
    node_type="http_get",
    category=NodeCategory.ACTIONS,
    name="HTTP GET",
    description="Fetch JSON from a URL",
    icon="fa-solid fa-globe",
)
class HttpGetNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [{
            "name": "trigger",
            "type": PortType.SIGNAL,
            "display_name": "Trigger",
            "description": "Trigger request",
            "required": False,
        }]

    @classmethod
    def get_output_ports(cls):
        return [{
            "name": "data",
            "type": PortType.UNIVERSAL,
            "display_name": "Data",
            "description": "Response JSON",
            "required": True,
        }]

    @classmethod
    def get_config_schema(cls):
        return {
            "url": {"type": "text", "label": "URL", "required": True, "default": "https://api.example.com/data"},
            "timeout": {"type": "number", "label": "Timeout (s)", "default": 10},
        }

    async def execute(self, input_data: NodeExecutionInput):
        url = self.config.get("url")
        timeout = float(self.config.get("timeout", 10))
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return {"data": resp.json()}
```""",
            "processing": """```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

@register_node(
    node_type="text_uppercase",
    category=NodeCategory.PROCESSING,
    name="Text Uppercase",
    description="Convert text to uppercase",
    icon="fa-solid fa-arrows-up-to-line",
)
class TextUppercaseNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [{
            "name": "text",
            "type": PortType.TEXT,
            "display_name": "Text",
            "description": "Input text",
            "required": True,
        }]

    @classmethod
    def get_output_ports(cls):
        return [{
            "name": "result",
            "type": PortType.TEXT,
            "display_name": "Uppercase Text",
            "description": "Uppercased text",
            "required": True,
        }]

    @classmethod
    def get_config_schema(cls):
        return {}

    async def execute(self, input_data: NodeExecutionInput):
        text = input_data.inputs.get("text", "")
        return {"result": text.upper()}
```""",
            "weather": """```python
from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
import requests

@register_node(
    node_type="weather_fetch",
    category=NodeCategory.ACTIONS,
    name="Weather Fetch",
    description="Fetch current weather for cities",
    icon="fa-solid fa-cloud-sun",
)
class WeatherFetchNode(Node):
    @classmethod
    def get_input_ports(cls):
        return [{
            "name": "trigger",
            "type": PortType.SIGNAL,
            "display_name": "Trigger",
            "description": "Trigger fetch",
            "required": False,
        }]

    @classmethod
    def get_output_ports(cls):
        return [
            {"name": "weather_json", "type": PortType.UNIVERSAL, "display_name": "Weather JSON", "description": "Raw weather data", "required": True},
            {"name": "summary", "type": PortType.TEXT, "display_name": "Summary", "description": "Summary text", "required": True},
        ]

    @classmethod
    def get_config_schema(cls):
        return {
            "api_key": {"type": "text", "label": "API Key", "required": True, "secret": True},
            "cities": {"type": "text", "label": "Cities (comma-separated)", "default": "Singapore, Bangkok", "required": True},
            "units": {"type": "select", "label": "Units", "default": "metric",
                      "options": [{"label": "Metric", "value": "metric"}, {"label": "Imperial", "value": "imperial"}, {"label": "Standard", "value": "standard"}]},
        }

    async def execute(self, input_data: NodeExecutionInput):
        api_key = self.config.get("api_key")
        units = self.config.get("units", "metric")
        cities_str = self.config.get("cities", "")
        cities = [c.strip() for c in cities_str.split(",") if c.strip()]
        if not api_key or not cities:
            raise ValueError("API key and at least one city are required")

        base_url = "https://api.openweathermap.org/data/2.5/weather"
        results = []
        for city in cities:
            try:
                params = {"q": city, "appid": api_key, "units": units}
                resp = requests.get(base_url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                results.append(data)
            except Exception as e:
                results.append({"city": city, "error": str(e)})

        summaries = []
        unit_symbol = "°C" if units == "metric" else ("°F" if units == "imperial" else "K")
        for r in results:
            if "error" in r:
                summaries.append(f"{r.get('city','?')}: {r['error']}")
            else:
                summaries.append(f"{r.get('name','?')}: {r.get('main',{}).get('temp','?')}{unit_symbol}, {r.get('weather',[{}])[0].get('description','')}")

        return {
            "weather_json": results,
            "summary": "\\n".join(summaries),
        }
```""",
        }
    
    def _build_conversation_history(
        self, 
        conversation: Conversation, 
        current_message: str
    ) -> str:
        """
        Build conversation history as a prompt for the AI.
        
        Formats all previous messages plus the current one into a single prompt.
        """
        # Start with system prompt
        prompt = self.SYSTEM_PROMPT + "\n\n"
        prompt += "=== CONVERSATION HISTORY ===\n\n"
        
        # Add all previous messages from database
        for msg in conversation.messages:
            if msg.role == "user":
                prompt += f"User: {msg.content}\n\n"
            elif msg.role == "assistant":
                prompt += f"Assistant: {msg.content}\n\n"
        
        # Add current user message
        prompt += f"User: {current_message}\n\n"
        
        # Add requirements context if we have any
        if conversation.requirements:
            prompt += "=== REQUIREMENTS EXTRACTED SO FAR ===\n"
            prompt += json.dumps(conversation.requirements, indent=2)
            prompt += "\n\n"
        
        prompt += "Assistant:"
        
        return prompt
    
    def _extract_requirements(
        self, 
        conversation: Conversation,
        user_message: str,
        ai_response: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structured requirements from conversation.
        
        Analyzes the conversation to extract:
        - Functionality description
        - Input ports
        - Output ports
        - Configuration fields
        - Category
        - External dependencies
        
        This is a progressive extraction - updates as more info is gathered.
        """
        # Start with existing requirements or empty dict
        requirements = conversation.requirements or {}
        
        # Extract functionality (what the node does)
        if not requirements.get("functionality"):
            # Look for action verbs and descriptions in user messages
            if any(word in user_message.lower() for word in ["fetch", "get", "retrieve", "download"]):
                requirements["functionality"] = user_message[:200]
            elif any(word in user_message.lower() for word in ["parse", "process", "transform", "convert"]):
                requirements["functionality"] = user_message[:200]
            elif any(word in user_message.lower() for word in ["send", "post", "upload", "publish"]):
                requirements["functionality"] = user_message[:200]
        
        # Extract category hints
        if not requirements.get("category"):
            if any(word in user_message.lower() for word in ["api", "http", "fetch", "request"]):
                requirements["category"] = "actions"
            elif any(word in user_message.lower() for word in ["parse", "process", "transform", "csv", "json"]):
                requirements["category"] = "processing"
            elif any(word in user_message.lower() for word in ["ai", "llm", "gpt", "generate", "analyze"]):
                requirements["category"] = "ai"
            elif any(word in user_message.lower() for word in ["send", "email", "slack", "notify"]):
                requirements["category"] = "communication"
            else:
                requirements["category"] = "processing"  # Default
        
        # Extract input/output hints
        if "input" in user_message.lower() or "takes" in user_message.lower():
            if not requirements.get("inputs_mentioned"):
                requirements["inputs_mentioned"] = True
        
        if "output" in user_message.lower() or "return" in user_message.lower():
            if not requirements.get("outputs_mentioned"):
                requirements["outputs_mentioned"] = True
        
        # Extract API/library mentions
        if not requirements.get("external_dependencies"):
            requirements["external_dependencies"] = []
        
        # Common API/library patterns
        api_patterns = [
            r"openweathermap",
            r"slack",
            r"twilio",
            r"stripe",
            r"github",
            r"requests",
            r"httpx",
        ]
        
        for pattern in api_patterns:
            if re.search(pattern, user_message.lower()) and pattern not in requirements["external_dependencies"]:
                requirements["external_dependencies"].append(pattern)
        
        return requirements if requirements else None
    
    def _check_user_confirmation(self, user_message: str) -> bool:
        """
        Check if user is confirming they want to proceed with code generation.
        
        Looks for phrases like:
        - "proceed"
        - "generate"
        - "go ahead"
        - "yes"
        - "start"
        """
        confirmation_phrases = [
            "proceed",
            "generate",
            "go ahead",
            "start generating",
            "create it",
            "make it",
            "build it",
            "do it",
            "yes",
            "ok",
            "okay",
        ]
        
        user_lower = user_message.lower().strip()
        
        # Check for exact matches or phrases
        if user_lower in ["yes", "ok", "okay", "proceed", "generate", "go ahead", "do it"]:
            return True
        
        return any(phrase in user_lower for phrase in confirmation_phrases)
    
    def _check_ready_to_generate(self, ai_response: str) -> bool:
        """
        Check if AI indicates it has enough information to generate code.
        
        DEPRECATED: This is only used for fallback now.
        Prefer checking for actual code blocks with _extract_code_block().
        """
        ready_phrases = [
            "have everything i need",
            "have all the information",
            "ready to generate",
            "ready to create",
            "let me generate",
            "let me create the code",
            "i can now generate",
            "i can now create",
            # Removed "generating your custom node" - that's part of the new response format
            "proceeding with",
        ]
        
        ai_lower = ai_response.lower()
        return any(phrase in ai_lower for phrase in ready_phrases)
    
    def generate_title(self, first_message: str) -> str:
        """
        Generate a title for the conversation from the first message.
        
        Creates a short, descriptive title (max 60 chars).
        """
        # Take first sentence or first 60 chars
        title = first_message.strip()
        
        # Remove common filler words
        title = re.sub(r'^(i want to|i need to|create a|make a|build a)\s+', '', title, flags=re.IGNORECASE)
        
        # Capitalize
        title = title.capitalize()
        
        # Truncate if too long
        if len(title) > 60:
            title = title[:57] + "..."
        
        return title or "New Custom Node"

