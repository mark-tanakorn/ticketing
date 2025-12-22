"""
Conversation Manager - Multi-turn AI chat for custom node building

Uses the centralized LangChainManager to call user-configured AI providers.
Guides users through defining node requirements via natural conversation.
"""

import logging
import json
import re
import uuid
import zipfile
import base64
import shutil
from xml.etree import ElementTree as ET
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

    # In-process capability cache for whether a given provider+model supports vision inputs.
    # Key: "<provider>::<model>" -> bool
    _vision_capability_cache: Dict[str, bool] = {}
    
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
        self._workflow_examples_dir = Path("docs/reference/workflow-examples")
    
    async def get_initial_message(self) -> str:
        """
        Get the initial AI greeting when starting a conversation.
        
        Returns a friendly greeting that introduces the AI assistant.
        """
        return """Hi! 👋 I'm here to help you build **custom nodes** and **workflows**.

You can do either:

**A) Create / refine a custom node (Python code)**
- "Create a node that sends a Telegram message"
- "Build a node that calls an HTTP API and returns JSON"

**B) Draft a workflow (workflow JSON for the editor)**
- "Create a workflow: Text Input → Telegram: Send Message → Text Display"
- "Draft a workflow JSON that watches a folder and emails a report"

Tell me what you want to build, and I’ll guide you step-by-step."""
    
    async def process_message(
        self, 
        conversation: Conversation, 
        user_message: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[int] = None,
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
            
            effective_attachments = attachments
            if (not effective_attachments) and self._should_include_recent_attachments(user_message):
                effective_attachments = self._get_last_attachments_from_conversation(conversation)

            attachments_block = self._format_attachments_for_prompt(
                attachments=effective_attachments,
                user_id=user_id or getattr(conversation, "user_id", None),
            )
            effective_user_message = user_message + (f"\n\n{attachments_block}" if attachments_block else "")

            # Build conversation history for context
            conversation_history = self._build_conversation_history(conversation, effective_user_message)
            
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
            requirements = self._extract_requirements(conversation, effective_user_message, ai_response)
            
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
        user_message: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[int] = None,
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
            yield {"type": "status", "message": "Building context…"}

            effective_attachments = attachments
            source = "request"
            if (not effective_attachments) and self._should_include_recent_attachments(user_message):
                effective_attachments = self._get_last_attachments_from_conversation(conversation)
                source = "memory"

            attachments_block = ""
            if effective_attachments:
                yield {"type": "tool_start", "tool": {"name": "attachments_parse", "source": source, "count": len(effective_attachments)}}
                attachments_block, stats = self._format_attachments_for_prompt_with_stats(
                    attachments=effective_attachments,
                    user_id=user_id or getattr(conversation, "user_id", None),
                    source=source,
                )
                yield {"type": "tool_end", "tool": {"name": "attachments_parse", "source": source, "result": stats}}

            effective_user_message = user_message + (f"\n\n{attachments_block}" if attachments_block else "")
            
            # Build conversation history for context
            conversation_history = self._build_conversation_history(conversation, effective_user_message)

            # Attach scoped reference context (read-only "tool" lookups)
            yield {"type": "status", "message": "Looking up relevant references…"}
            yield {"type": "tool_start", "tool": {"name": "reference_lookup", "query": user_message}}
            context_snippets = self._gather_references(user_message)
            yield {"type": "tool_end", "tool": {"name": "reference_lookup", "result_count": len(context_snippets)}}
            if context_snippets:
                conversation_history += "\n\n### REFERENCE CONTEXT (from repo, do NOT verbatim copy comments):\n"
                for label, snippet in context_snippets:
                    conversation_history += f"\n# {label}:\n{snippet}\n"
            
            # Add specific instruction for code generation if user seems to be asking for it
            user_confirming = self._check_user_confirmation(user_message)
            workflow_confirming = self._check_workflow_request(user_message)

            # Semantic intent routing (LLM classifier) to avoid brittle keyword/phrase-only activation.
            # We only invoke this when needed to keep costs/latency low.
            routed_intent = None
            if not workflow_confirming:
                yield {"type": "tool_start", "tool": {"name": "intent_router", "mode": "semantic", "query": user_message}}
                routed_intent = await self._semantic_route_intent(conversation, user_message)
                yield {"type": "tool_end", "tool": {"name": "intent_router", "result": routed_intent}}
                if isinstance(routed_intent, dict):
                    intent = (routed_intent.get("intent") or "").strip().upper()
                    conf = routed_intent.get("confidence")
                    try:
                        conf_f = float(conf) if conf is not None else 0.0
                    except Exception:
                        conf_f = 0.0
                    if intent == "WORKFLOW_DRAFT" and conf_f >= 0.55:
                        workflow_confirming = True
                    elif intent == "NODE_CODE" and conf_f >= 0.65:
                        # Allow semantic router to trigger code-gen mode explicitly.
                        user_confirming = True

            # Ground the model in the real node catalog (NodeRegistry) so it can reuse existing nodes.
            # This prevents it from asking "do you have X node?" when it already exists.
            yield {"type": "tool_start", "tool": {"name": "node_catalog_check", "query": user_message}}
            catalog_matches = self._node_catalog_lookup(user_message, limit=8)
            yield {"type": "tool_end", "tool": {"name": "node_catalog_check", "matches": catalog_matches}}
            if catalog_matches:
                conversation_history += "\n\n### NODE CATALOG CHECK (ground truth; use these nodes if relevant):\n"
                conversation_history += json.dumps(catalog_matches, ensure_ascii=False, indent=2)

            if workflow_confirming:
                yield {"type": "status", "message": "Workflow draft mode requested…"}

                # Add a few workflow JSON examples (sanitized) to reduce schema drift.
                yield {"type": "tool_start", "tool": {"name": "workflow_example_lookup", "query": user_message}}
                examples = self._gather_workflow_examples(user_message, max_examples=3, max_chars_each=4500)
                yield {"type": "tool_end", "tool": {"name": "workflow_example_lookup", "examples": [e[0] for e in examples]}}
                if examples:
                    conversation_history += "\n\n### WORKFLOW EXAMPLES (sanitized; copy the SHAPE, not IDs):\n"
                    for label, snippet in examples:
                        conversation_history += f"\n# {label}:\n{snippet}\n"

                conversation_history += """

============================================
WORKFLOW DRAFT MODE
============================================
The user is asking you to draft a workflow for the workflow editor.

Constraints:
- The user will manually activate/run workflows. Do NOT imply automatic triggering.
- Prefer existing built-in/custom nodes. If something is missing, list it under missing_custom_nodes.
- If NODE CATALOG CHECK contains a relevant node (e.g. Telegram/HTTP/Text Input), you MUST reuse it and must NOT ask the user if it exists.

Response format:
- You may include 1–2 short sentences of natural lead-in.
- Then output a SINGLE ```json code block containing an object with this shape:
  {
    "name": "string",
    "description": "string",
    "version": "1.0",
    "nodes": [...],
    "connections": [...],
    "canvas_objects": [...],
    "tags": ["ai_draft"],
    "metadata": { "created_by": "builder" },
    "missing_custom_nodes": [
      {
        "node_type": "string",
        "name": "string",
        "description": "string",
        "category": "processing|actions|ai|workflow|...",
        "icon": "fa-solid fa-...",
        "inputs": [{"name":"...","type":"...","description":"...","required":true}],
        "outputs": [{"name":"...","type":"...","description":"...","required":true}],
        "config": {"field": {"type":"text|number|select|...","label":"...","description":"...","required":false,"default":""}},
        "why": "string"
      }
    ]
  }
- Do not include any other code blocks.
============================================
"""
            elif user_confirming:
                yield {"type": "status", "message": "Code generation mode requested…"}
                conversation_history += """

============================================
CODE GENERATION MODE
============================================
The user is asking you to generate the custom node code now.

Response format:
- You may include 1–2 short sentences of natural lead-in.
- Then output a SINGLE ```python code block with the complete, working node implementation.
- Do not include any other code blocks.
============================================
"""
            
            # Stream AI response
            yield {"type": "status", "message": "Calling AI model…"}
            full_response = ""

            # Vision path: if attachments include images, try sending them as structured content.
            image_parts, image_stats = self._collect_image_parts(
                attachments=effective_attachments,
                user_id=user_id or getattr(conversation, "user_id", None),
            )
            has_images = len(image_parts) > 0

            if has_images:
                key = f"{conversation.provider}::{conversation.model}"
                cached = self._vision_capability_cache.get(key)
                yield {
                    "type": "tool_start",
                    "tool": {
                        "name": "vision_capability_check",
                        "provider": conversation.provider,
                        "model": conversation.model,
                        "cached": cached,
                        "images": image_stats,
                    },
                }

                if cached is False:
                    yield {
                        "type": "tool_end",
                        "tool": {
                            "name": "vision_capability_check",
                            "provider": conversation.provider,
                            "model": conversation.model,
                            "result": "unsupported_cached",
                        },
                    }
                    msg = self._vision_unsupported_message(conversation.provider, conversation.model)
                    for ch in msg:
                        yield {"type": "token", "content": ch}
                    yield {
                        "type": "done",
                        "assistant_message": msg,
                        "ready_to_generate": False,
                        "requirements": conversation.requirements,
                        "generated_code": None,
                    }
                    return

                yield {
                    "type": "tool_end",
                    "tool": {
                        "name": "vision_capability_check",
                        "provider": conversation.provider,
                        "model": conversation.model,
                        "result": "attempt",
                    },
                }

                provider_image_parts = self._adapt_image_parts_for_provider(conversation.provider, image_parts)
                vision_messages = [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": conversation_history}, *provider_image_parts],
                    }
                ]

                try:
                    async for token in self.langchain_manager.call_llm_stream_with_messages(
                        messages=vision_messages,
                        provider=conversation.provider,
                        model=conversation.model,
                        temperature=float(conversation.temperature) if conversation.temperature else 0.3,
                        fallback=False,  # do not silently change provider/model when user chose one
                    ):
                        full_response += token
                        yield {"type": "token", "content": token}
                    self._vision_capability_cache[key] = True
                except Exception as e:
                    # If we hit a provider schema mismatch (e.g. OpenAI expecting image_url object),
                    # do not treat it as "unsupported vision"—it's a formatting bug.
                    if self._looks_like_image_url_shape_error(e):
                        raise
                    if self._looks_like_vision_unsupported(e):
                        self._vision_capability_cache[key] = False
                        msg = self._vision_unsupported_message(conversation.provider, conversation.model)
                        for ch in msg:
                            yield {"type": "token", "content": ch}
                        yield {
                            "type": "done",
                            "assistant_message": msg,
                            "ready_to_generate": False,
                            "requirements": conversation.requirements,
                            "generated_code": None,
                        }
                        return
                    raise
            else:
                async for token in self.langchain_manager.call_llm_stream(
                    prompt=conversation_history,
                    provider=conversation.provider,
                    model=conversation.model,
                    temperature=float(conversation.temperature) if conversation.temperature else 0.3,
                ):
                    full_response += token
                    yield {
                        "type": "token",
                        "content": token
                    }
            
            # Extract requirements from full response
            yield {"type": "status", "message": "Extracting requirements and code…"}
            requirements = self._extract_requirements(conversation, user_message, full_response)

            workflow_draft = None
            if workflow_confirming:
                yield {"type": "status", "message": "Extracting workflow draft…"}
                workflow_draft = self._extract_workflow_draft(full_response)
                if workflow_draft:
                    # Normalize to editor-compatible schema (node_id/node_type + source_node_id/target_node_id)
                    workflow_draft = self._normalize_workflow_draft(workflow_draft)
                    yield {"type": "workflow_draft", "workflow": workflow_draft}
            
            # Check for generated code block
            generated_code = self._extract_code_block(full_response)
            ready_to_generate = bool(generated_code)
            
            logger.info(f"✅ AI streaming complete (code_found={ready_to_generate})")
            
            yield {
                "type": "done",
                "assistant_message": full_response,
                "ready_to_generate": ready_to_generate,
                "requirements": requirements,
                "generated_code": generated_code,
                "workflow_draft": workflow_draft,
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

    def _extract_workflow_draft(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract a single JSON code block representing a workflow draft.
        """
        pattern = r"```(?:json)?\s*(\{[\s\S]*?\})\s*```"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if not match:
            return None
        raw = match.group(1).strip()
        try:
            obj = json.loads(raw)
        except Exception:
            return None
        if not isinstance(obj, dict):
            return None
        if not isinstance(obj.get("nodes"), list) or not isinstance(obj.get("connections"), list):
            return None
        if "canvas_objects" in obj and not isinstance(obj.get("canvas_objects"), list):
            return None
        # Ensure missing_custom_nodes is a list if provided
        if "missing_custom_nodes" in obj and not isinstance(obj.get("missing_custom_nodes"), list):
            obj["missing_custom_nodes"] = []
        return obj

    def _format_attachments_for_prompt(
        self,
        attachments: Optional[List[Dict[str, Any]]],
        user_id: Optional[int],
        max_chars: int = 8000,
    ) -> str:
        """
        Convert uploaded file references into a compact prompt block.

        We intentionally avoid relying on provider-specific multimodal support.
        Instead, we best-effort extract text for common document formats and include metadata
        for images/audio/etc.
        """
        text, _stats = self._format_attachments_for_prompt_with_stats(
            attachments=attachments,
            user_id=user_id,
            max_chars=max_chars,
            source="request",
        )
        return text

    def _format_attachments_for_prompt_with_stats(
        self,
        attachments: Optional[List[Dict[str, Any]]],
        user_id: Optional[int],
        max_chars: int = 8000,
        source: str = "request",
    ) -> tuple[str, Dict[str, Any]]:
        """
        Like _format_attachments_for_prompt, but also returns non-sensitive stats for UI traces.
        """
        stats: Dict[str, Any] = {"source": source, "count": 0, "files": [], "total_extracted_chars": 0}

        if not attachments or not isinstance(attachments, list):
            return "", stats

        # Defensive cap (also enforced at API layer)
        attachments = attachments[:5]

        try:
            from app.database.repositories.file import FileRepository
        except Exception:
            return "", stats

        repo = FileRepository(self.db)
        base = Path("data")

        lines: List[str] = [
            "### ATTACHMENTS",
            "Use these attachments to answer questions about the file(s).",
            "If no text is available, explicitly say you cannot read the content yet and suggest OCR/transcription.",
        ]

        for idx, a in enumerate(attachments, start=1):
            if not isinstance(a, dict):
                continue
            file_id = a.get("file_id") or a.get("id")
            if not file_id:
                continue

            record = repo.get_by_id(str(file_id))
            if not record:
                lines.append(f"{idx}) [missing] file_id={file_id}")
                stats["files"].append({"file_id": str(file_id), "status": "missing"})
                continue

            # Ownership guardrail (if available)
            uploaded_by = getattr(record, "uploaded_by_id", None)
            if user_id is not None and uploaded_by not in (None, user_id):
                lines.append(f"{idx}) [forbidden] file_id={record.id}")
                stats["files"].append({"file_id": str(record.id), "status": "forbidden"})
                continue

            filename = getattr(record, "filename", None) or a.get("filename") or str(file_id)
            mime = getattr(record, "mime_type", None) or a.get("mime_type") or "application/octet-stream"
            size = getattr(record, "file_size_bytes", None) or a.get("file_size_bytes")
            category = getattr(record, "file_category", None)
            category_val = category.value if hasattr(category, "value") else (str(category) if category else a.get("file_category") or "")

            header = f"{idx}) {filename} ({mime}{', ' + category_val if category_val else ''}{', ' + str(size) + ' bytes' if size is not None else ''}) [file_id={record.id}]"
            lines.append(header)

            file_path = (base / getattr(record, "storage_path", ""))

            # Audio: attempt transcription (cached in file_metadata)
            excerpt = None
            try:
                if str(mime).lower().startswith("audio/"):
                    excerpt = self._try_transcribe_audio_excerpt(
                        record=record,
                        file_path=file_path,
                        max_chars=max_chars,
                    )
            except Exception:
                excerpt = None

            # Documents: best-effort text extraction
            if excerpt is None:
                excerpt = self._try_extract_text_excerpt(
                    file_path=file_path,
                    filename=str(filename),
                    mime_type=str(mime),
                    max_chars=max_chars,
                )
            extracted_chars = len(excerpt) if excerpt else 0
            is_placeholder = bool(excerpt) and excerpt.lstrip().startswith("[") and "No text extracted" in excerpt

            stats["files"].append(
                {
                    "file_id": str(record.id),
                    "filename": str(filename),
                    "mime_type": str(mime),
                    "file_category": str(category_val),
                    "file_size_bytes": int(size) if isinstance(size, (int, float)) else None,
                    "status": "ok",
                    "extracted_chars": extracted_chars,
                    "extraction_kind": "placeholder" if is_placeholder else ("text" if excerpt else "none"),
                }
            )
            stats["total_extracted_chars"] += extracted_chars

            if excerpt:
                lines.append("   Extracted text (excerpt):")
                for ln in excerpt.splitlines()[:80]:
                    lines.append(f"   {ln}")
            else:
                lines.append("   (No text extracted; treat as non-text attachment unless user asks to transcribe/OCR.)")

        stats["count"] = len(stats["files"])
        return "\n".join(lines).strip(), stats

    def _try_transcribe_audio_excerpt(
        self,
        record: Any,
        file_path: Path,
        max_chars: int = 8000,
    ) -> Optional[str]:
        """
        Best-effort audio transcription.
        - Caches transcript in File.file_metadata to avoid re-transcribing on follow-ups.
        - Requires ffmpeg for most audio formats (mp3/m4a/webm/ogg).
        - Uses faster-whisper if installed.
        """
        try:
            if not file_path.exists() or not file_path.is_file():
                return "[Audio attached, but the file was not found on server storage.]"
        except Exception:
            return "[Audio attached, but the file was not accessible on server storage.]"

        # Cache hit
        meta = getattr(record, "file_metadata", None) or {}
        if isinstance(meta, dict):
            cached = meta.get("transcript_text")
            if isinstance(cached, str) and cached.strip():
                return cached.strip()[:max_chars]

        # Prefer faster-whisper (CPU-friendly)
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except Exception:
            return "[Audio attached. Transcription engine is not installed (missing faster-whisper). Install it and try again.]"

        model_name = "base"
        try:
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
            ffmpeg_ok = shutil.which("ffmpeg") is not None

            # If ffmpeg is available, let faster-whisper decode from file path (supports most codecs).
            if ffmpeg_ok:
                segments, info = model.transcribe(
                    str(file_path),
                    vad_filter=True,
                    beam_size=1,
                )
            else:
                # No ffmpeg: try decoding via librosa/soundfile (works for WAV/PCM, and whatever soundfile supports).
                # This avoids hard-stopping on formats that don't actually require ffmpeg.
                try:
                    import librosa  # type: ignore
                except Exception:
                    return "[Audio attached. ffmpeg is not installed and librosa is unavailable, so transcription cannot run. Install ffmpeg and try again.]"

                try:
                    # Load and resample to 16k mono for Whisper
                    audio, sr = librosa.load(str(file_path), sr=16000, mono=True)
                except Exception:
                    return "[Audio attached. Transcription requires ffmpeg on the server to decode this audio format (not found). Install ffmpeg and try again.]"

                # Limit to first ~120s to keep latency reasonable
                try:
                    max_seconds = 120
                    if audio is not None and hasattr(audio, "__len__") and len(audio) > max_seconds * 16000:
                        audio = audio[: max_seconds * 16000]
                except Exception:
                    pass

                segments, info = model.transcribe(
                    audio,
                    vad_filter=True,
                    beam_size=1,
                )

            parts: List[str] = []
            total = 0
            for seg in segments:
                text = (getattr(seg, "text", "") or "").strip()
                if not text:
                    continue
                parts.append(text)
                total += len(text) + 1
                if total >= max_chars:
                    break

            transcript = "\n".join(parts).strip()
            if not transcript:
                transcript = "[Audio attached, but no speech/text was transcribed.]"

            # Cache back to DB record (best-effort; don't fail request if commit fails)
            try:
                meta2 = getattr(record, "file_metadata", None) or {}
                if not isinstance(meta2, dict):
                    meta2 = {}
                meta2["transcript_text"] = transcript[:50000]  # cap stored transcript
                meta2["transcript_engine"] = "faster-whisper"
                meta2["transcript_model"] = model_name
                setattr(record, "file_metadata", meta2)
                self.db.add(record)
                self.db.commit()
            except Exception:
                try:
                    self.db.rollback()
                except Exception:
                    pass

            return transcript[:max_chars]
        except Exception as e:
            return f"[Audio attached. Transcription failed: {type(e).__name__}: {e}]"

    def _should_include_recent_attachments(self, user_message: str) -> bool:
        msg = (user_message or "").lower()
        triggers = [
            "this document",
            "that document",
            "the document",
            "this file",
            "that file",
            "the file",
            "attachment",
            "attached",
            "pdf",
            "docx",
            "image",
            "audio",
            "transcribe",
            "summarize",
            "what is this",
            "what is that",
            "what is the document about",
            "what is this about",
        ]
        return any(t in msg for t in triggers)

    def _get_last_attachments_from_conversation(self, conversation: Conversation, max_files: int = 5) -> Optional[List[Dict[str, Any]]]:
        try:
            msgs = list(getattr(conversation, "messages", []) or [])
        except Exception:
            msgs = []
        for m in reversed(msgs):
            try:
                if getattr(m, "role", None) != "user":
                    continue
                act = getattr(m, "activity", None)
                if isinstance(act, dict) and isinstance(act.get("attachments"), list) and act.get("attachments"):
                    return act.get("attachments")[:max_files]
            except Exception:
                continue
        return None

    def _collect_image_parts(
        self,
        attachments: Optional[List[Dict[str, Any]]],
        user_id: Optional[int],
        max_images: int = 2,
        max_bytes_each: int = 5_000_000,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Load image attachments from disk and return structured content parts usable by vision models.

        Returns: (parts, stats)
          - parts: [{"type":"image_url","image_url":"data:<mime>;base64,<...>"}]
          - stats: per-file non-sensitive stats for tool traces
        """
        parts: List[Dict[str, Any]] = []
        stats: List[Dict[str, Any]] = []
        if not attachments or not isinstance(attachments, list):
            return parts, stats

        try:
            from app.database.repositories.file import FileRepository
        except Exception:
            return parts, stats

        repo = FileRepository(self.db)
        base = Path("data")

        for a in attachments[: max_images * 2]:
            if len(parts) >= max_images:
                break
            if not isinstance(a, dict):
                continue
            file_id = a.get("file_id") or a.get("id")
            if not file_id:
                continue
            record = repo.get_by_id(str(file_id))
            if not record:
                stats.append({"file_id": str(file_id), "status": "missing"})
                continue
            uploaded_by = getattr(record, "uploaded_by_id", None)
            if user_id is not None and uploaded_by not in (None, user_id):
                stats.append({"file_id": str(record.id), "status": "forbidden"})
                continue

            mime = getattr(record, "mime_type", None) or a.get("mime_type") or "application/octet-stream"
            if not str(mime).lower().startswith("image/"):
                continue

            file_path = base / getattr(record, "storage_path", "")
            try:
                data = file_path.read_bytes()
            except Exception:
                stats.append({"file_id": str(record.id), "status": "unreadable"})
                continue

            if len(data) > max_bytes_each:
                stats.append({"file_id": str(record.id), "status": "too_large", "bytes": len(data)})
                continue

            b64 = base64.b64encode(data).decode("utf-8")
            parts.append({"type": "image_url", "image_url": f"data:{mime};base64,{b64}"})
            stats.append(
                {
                    "file_id": str(record.id),
                    "filename": getattr(record, "filename", None),
                    "mime_type": str(mime),
                    "bytes": len(data),
                    "status": "ok",
                }
            )

        return parts, stats

    def _looks_like_vision_unsupported(self, e: Exception) -> bool:
        msg = (str(e) or "").lower()
        patterns = [
            "does not support image",
            "doesn't support image",
            "image is not supported",
            "images are not supported",
            "vision is not supported",
            "multimodal is not supported",
            "only supports text",
            "unsupported content type",
        ]
        return any(p in msg for p in patterns)

    def _looks_like_image_url_shape_error(self, e: Exception) -> bool:
        """
        Detect OpenAI-style schema errors like:
        "Invalid type for 'messages[0].content[1].image_url': expected an object, but got a string instead."
        """
        msg = (str(e) or "").lower()
        return (
            "invalid type for 'messages[" in msg
            and "image_url" in msg
            and "expected an object" in msg
        )

    def _adapt_image_parts_for_provider(self, provider: str, image_parts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert our internal image parts into the provider's expected structured-content format.
        """
        p = (provider or "").lower()
        if not image_parts:
            return []

        # OpenAI-compatible: image_url is an object: {"url": "..."}
        if p in ("openai", "deepseek", "groq", "mistral", "together", "perplexity", "google"):
            out: List[Dict[str, Any]] = []
            for part in image_parts:
                url = part.get("image_url")
                if not url:
                    continue
                out.append({"type": "image_url", "image_url": {"url": url}})
            return out

        # Anthropic: image part with base64 source
        if p == "anthropic":
            out = []
            for part in image_parts:
                url = part.get("image_url") or ""
                if not isinstance(url, str) or not url.startswith("data:") or ";base64," not in url:
                    continue
                try:
                    header, b64 = url.split(";base64,", 1)
                    mime = header[5:]  # strip "data:"
                except Exception:
                    continue
                out.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}})
            return out

        # Local/Ollama: LangChain's ChatOllama path often accepts image_url as string data URL
        return image_parts

    def _vision_unsupported_message(self, provider: str, model: str) -> str:
        return (
            f"Your selected model **{provider}/{model}** doesn’t support image/vision inputs.\n\n"
            f"- Switch to a vision-capable model, then resend your message.\n"
            f"- Or remove the image attachment and ask using text only."
        )

    def _try_extract_text_excerpt(
        self,
        file_path: Path,
        filename: str,
        mime_type: str,
        max_chars: int = 8000,
    ) -> Optional[str]:
        """
        Best-effort text extraction.
        - PDF: PyMuPDF (fitz) first pages
        - DOCX: parse word/document.xml from zip
        - text/*, json, csv, md: read as utf-8 (lossy)
        """
        try:
            if not file_path.exists() or not file_path.is_file():
                return None
        except Exception:
            return None

        ext = Path(filename).suffix.lower().lstrip(".")

        if mime_type.startswith(("image/", "audio/", "video/")):
            return None

        if ext == "pdf" or mime_type == "application/pdf":
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(str(file_path))
                parts: List[str] = []
                for i in range(min(len(doc), 2)):
                    page = doc[i]
                    parts.append(page.get_text("text") or "")
                doc.close()
                text = "\n".join(parts).strip()
                if not text:
                    return "[No text extracted from PDF; it may be scanned/image-based. Consider OCR.]"
                return text[:max_chars]
            except Exception:
                return None

        if ext == "docx" or mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            try:
                with zipfile.ZipFile(str(file_path), "r") as z:
                    xml_bytes = z.read("word/document.xml")
                root = ET.fromstring(xml_bytes)
                text_nodes: List[str] = []
                for node in root.iter():
                    if node.tag.endswith("}t") and node.text:
                        text_nodes.append(node.text)
                text = "\n".join([t.strip() for t in text_nodes if t.strip()]).strip()
                if not text:
                    return "[No text extracted from DOCX.]"
                return text[:max_chars]
            except Exception:
                return None

        if mime_type.startswith("text/") or ext in ("txt", "md", "csv", "json"):
            try:
                data = file_path.read_bytes()
                text = data.decode("utf-8", errors="ignore").strip()
                if not text:
                    return None
                return text[:max_chars]
            except Exception:
                return None

        return None

    def _normalize_workflow_draft(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize model-produced workflow JSON into the editor-compatible schema.

        Handles common model drift:
        - nodes use {id,type} instead of {node_id,node_type}
        - connections use {from_node_id,to_node_id,from_port,to_port}
        - canvas_objects include unsupported {type:"note"}; convert to text annotations
        """
        obj = draft if isinstance(draft, dict) else {}

        # Base envelope
        out: Dict[str, Any] = {
            "name": obj.get("name") or "Untitled Workflow",
            "description": obj.get("description") or "",
            "version": obj.get("version") or "1.0",
            "nodes": [],
            "connections": [],
            "canvas_objects": [],
            "tags": obj.get("tags") if isinstance(obj.get("tags"), list) else [],
            "metadata": obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {},
            "missing_custom_nodes": obj.get("missing_custom_nodes") if isinstance(obj.get("missing_custom_nodes"), list) else [],
        }

        # Ensure tag
        if "ai_draft" not in out["tags"]:
            out["tags"].append("ai_draft")
        out["metadata"] = {**out["metadata"], "created_by": out["metadata"].get("created_by") or "builder"}

        # Node metadata from registry (if available)
        registry_details: Dict[str, Any] = {}
        try:
            from app.core.nodes.registry import NodeRegistry
            registry_details = NodeRegistry.list_all_with_details()
        except Exception:
            registry_details = {}

        nodes_in = obj.get("nodes") if isinstance(obj.get("nodes"), list) else []
        id_map: Dict[str, str] = {}

        for idx, n in enumerate(nodes_in):
            if not isinstance(n, dict):
                continue
            raw_id = n.get("node_id") or n.get("id") or f"node_{idx+1}"
            node_id = str(raw_id)
            node_type = n.get("node_type") or n.get("type") or n.get("name") or "custom_node"
            node_type = str(node_type)
            id_map[str(raw_id)] = node_id

            meta = registry_details.get(node_type) or {}

            # Prefer model-provided ports if present, else fill from registry
            input_ports = n.get("input_ports") if isinstance(n.get("input_ports"), list) else meta.get("input_ports") or []
            output_ports = n.get("output_ports") if isinstance(n.get("output_ports"), list) else meta.get("output_ports") or []

            out["nodes"].append(
                {
                    "node_id": node_id,
                    "node_type": node_type,
                    "name": n.get("name") or meta.get("display_name") or meta.get("name") or node_type,
                    "category": n.get("category") or meta.get("category") or "default",
                    "position": n.get("position") or {"x": 100 + idx * 280, "y": 120},
                    "input_ports": input_ports,
                    "output_ports": output_ports,
                    "config": n.get("config") if isinstance(n.get("config"), dict) else {},
                    "status": n.get("status") or "idle",
                    "icon": n.get("icon") or meta.get("icon"),
                    "share_output_to_variables": bool(n.get("share_output_to_variables", False)),
                    "variable_name": n.get("variable_name"),
                    "flipped": bool(n.get("flipped", False)),
                }
            )

        # Normalize connections
        conns_in = obj.get("connections") if isinstance(obj.get("connections"), list) else []
        for c in conns_in:
            if not isinstance(c, dict):
                continue

            # Support both schemas
            src = c.get("source_node_id") or c.get("from_node_id") or c.get("sourceNodeId")
            tgt = c.get("target_node_id") or c.get("to_node_id") or c.get("targetNodeId")
            src_port = c.get("source_port") or c.get("from_port") or c.get("sourcePort")
            tgt_port = c.get("target_port") or c.get("to_port") or c.get("targetPort")

            if not src or not tgt or not src_port or not tgt_port:
                continue

            src_id = id_map.get(str(src), str(src))
            tgt_id = id_map.get(str(tgt), str(tgt))

            out["connections"].append(
                {
                    "connection_id": c.get("connection_id") or c.get("id") or f"conn_{uuid.uuid4().hex[:12]}",
                    "source_node_id": src_id,
                    "source_port": str(src_port),
                    "target_node_id": tgt_id,
                    "target_port": str(tgt_port),
                }
            )

        # Normalize canvas objects: editor supports group + text. Convert "note" to "text".
        canvas_in = obj.get("canvas_objects") if isinstance(obj.get("canvas_objects"), list) else []
        for co in canvas_in:
            if not isinstance(co, dict):
                continue
            ctype = co.get("type")
            if ctype == "note":
                # Convert note → text annotation (keep content)
                pos = co.get("position") or {"x": 120, "y": 80}
                out["canvas_objects"].append(
                    {
                        "id": co.get("id") or f"co_text_{uuid.uuid4().hex[:8]}",
                        "type": "text",
                        "position": pos,
                        "content": co.get("content") or "",
                        "fontSize": 14,
                        "color": "#374151",
                        "zIndex": 0,
                    }
                )
            elif ctype in ("text", "group"):
                out["canvas_objects"].append(co)

        return out

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

        # Semantic-ish routing (no hard-coded keywords):
        # Always try to retrieve relevant existing node types from the in-process NodeRegistry.
        # If nothing matches the message, we add nothing.
        try:
            catalog = self._node_catalog_matches(user_message, limit=8)
            if catalog:
                refs.append(("node catalog matches (existing node types)", catalog))
        except Exception:
            pass

        # Trim to avoid token blow-up
        return refs[:7]

    def _node_catalog_matches(self, user_message: str, limit: int = 8) -> str:
        """
        Return a compact list of node definitions that match keywords in the user message.
        Uses NodeRegistry (already loaded in-process) so the AI can ground itself on existing nodes.
        """
        msg = (user_message or "").lower()
        tokens = [t for t in re.split(r"[^a-z0-9_]+", msg) if t]
        tokens = [t for t in tokens if len(t) >= 3][:12]
        if not tokens:
            return ""

        from app.core.nodes.registry import NodeRegistry

        # Pull detailed metadata (ports + config schema) so the AI can align with real system types.
        all_nodes = NodeRegistry.list_all_with_details()
        scored: List[tuple] = []
        for node_type, meta in all_nodes.items():
            hay = " ".join(
                [
                    (node_type or ""),
                    str(meta.get("display_name") or ""),
                    str(meta.get("description") or ""),
                    str(meta.get("category") or ""),
                ]
            ).lower()
            score = sum(1 for t in tokens if t in hay)
            if score > 0:
                scored.append((score, node_type, meta))

        scored.sort(key=lambda x: (-x[0], x[1]))
        scored = scored[:limit]
        if not scored:
            return ""

        lines: List[str] = []
        lines.append("Top matching existing nodes (for reuse/consistency):")
        for score, node_type, meta in scored:
            # Compact port/config summary
            def _ports_summary(ports: Any) -> str:
                if not isinstance(ports, list):
                    return ""
                parts: List[str] = []
                for p in ports[:6]:
                    if isinstance(p, dict):
                        n = p.get("name")
                        t = p.get("type")
                        if n and t:
                            parts.append(f"{n}:{t}")
                return ", ".join(parts)

            def _config_summary(schema: Any) -> str:
                if not isinstance(schema, dict):
                    return ""
                parts: List[str] = []
                for k, v in list(schema.items())[:8]:
                    if isinstance(v, dict):
                        t = v.get("type")
                        w = v.get("widget")
                        if t and w:
                            parts.append(f"{k}:{t}/{w}")
                        elif t:
                            parts.append(f"{k}:{t}")
                        else:
                            parts.append(str(k))
                    else:
                        parts.append(str(k))
                return ", ".join(parts)

            in_ports = _ports_summary(meta.get("input_ports"))
            out_ports = _ports_summary(meta.get("output_ports"))
            cfg = _config_summary(meta.get("config_schema"))

            lines.append(
                f"- {node_type} | name={meta.get('display_name')} | category={meta.get('category')} | "
                f"in=[{in_ports}] | out=[{out_ports}] | config=[{cfg}]"
            )
        return "\n".join(lines)

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

    def _check_workflow_request(self, user_message: str) -> bool:
        """
        Check if user is explicitly asking for a workflow draft.
        We gate on workflow/automation keywords to avoid stealing the node-generation flow.
        """
        msg = (user_message or "").lower().strip()
        # Keep this check conservative; semantic routing can still activate workflow draft mode
        # for messages like "recreate the flow again" without the literal word "workflow".
        if "workflow" not in msg and "automation" not in msg and "workflow json" not in msg:
            # Still allow some direct phrases that often omit "workflow" but clearly mean it.
            if not any(p in msg for p in ["workflow again", "recreate workflow", "rebuild workflow", "workflow json"]):
                return False
        phrases = [
            "create workflow",
            "build workflow",
            "generate workflow",
            "draft workflow",
            "workflow json",
            "make workflow",
            "recreate workflow",
            "re-create workflow",
            "rebuild workflow",
            "redo workflow",
            "workflow again",
            "make the workflow again",
        ]
        return any(p in msg for p in phrases) or msg in ["workflow", "build a workflow", "make a workflow"]

    async def _semantic_route_intent(self, conversation: Conversation, user_message: str) -> Dict[str, Any]:
        """
        Use a tiny LLM classification prompt to route intent:
        - WORKFLOW_DRAFT: user wants workflow JSON / workflow structure / regenerate workflow
        - NODE_CODE: user wants Python node code generation/editing/registration
        - CHAT: normal discussion/clarifications

        Returns: {"intent": "...", "confidence": 0..1, "reason": "..."} (best-effort)
        """
        try:
            # Build a small amount of context (avoid bloating prompt)
            recent_lines: List[str] = []
            try:
                msgs = list(getattr(conversation, "messages", []) or [])
            except Exception:
                msgs = []
            for m in msgs[-6:]:
                role = getattr(m, "role", "unknown")
                content = (getattr(m, "content", "") or "").strip()
                if not content:
                    continue
                if len(content) > 280:
                    content = content[:280] + "…"
                recent_lines.append(f"{role}: {content}")
            recent = "\n".join(recent_lines)

            prompt = (
                "You are an intent router for an AI Builder.\n"
                "Classify the user's latest message into exactly ONE intent:\n"
                "- WORKFLOW_DRAFT: wants a workflow plan/JSON, nodes+connections, regenerate/recreate a workflow, a 'flow/pipeline' for the editor.\n"
                "- NODE_CODE: wants Python node class code generation, edits, validation, or registration.\n"
                "- CHAT: discussion/clarifying questions/feedback.\n\n"
                "Return ONLY a JSON object with keys: intent, confidence, reason.\n"
                'Example: {"intent":"WORKFLOW_DRAFT","confidence":0.78,"reason":"User asked to recreate the workflow JSON"}\n\n'
                f"Recent conversation (may be empty):\n{recent}\n\n"
                f"User message:\n{(user_message or '').strip()}\n"
            )

            text = await self.langchain_manager.call_llm(
                prompt=prompt,
                provider=conversation.provider,
                model=conversation.model,
                temperature=0.0,
                max_tokens=120,
                fallback=True,
            )
            raw = (text or "").strip()
            # Strip code fences if any
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
            raw = re.sub(r"\s*```$", "", raw).strip()
            obj = json.loads(raw)
            if not isinstance(obj, dict):
                return {"intent": "CHAT", "confidence": 0.0, "reason": "Router returned non-object"}
            return {
                "intent": obj.get("intent") or "CHAT",
                "confidence": obj.get("confidence", 0.0),
                "reason": obj.get("reason", ""),
            }
        except Exception as e:
            logger.debug(f"Semantic intent routing failed: {type(e).__name__}: {e}")
            return {"intent": "CHAT", "confidence": 0.0, "reason": "Router failed"}

    def _node_catalog_lookup(self, user_message: str, limit: int = 8) -> List[Dict[str, Any]]:
        """
        Return a small, relevant slice of the registered node catalog (NodeRegistry) for grounding.
        Keeps output bounded to avoid bloating prompts.
        """
        try:
            from app.core.nodes.registry import NodeRegistry
            from app.core.nodes.loader import get_node_port_definitions

            query = (user_message or "").lower()
            tokens = [t for t in re.split(r"[^a-z0-9_]+", query) if len(t) >= 3]

            all_meta = NodeRegistry.list_all()  # {node_type: {...}}
            scored: List[tuple[int, str]] = []
            for node_type, meta in all_meta.items():
                hay = " ".join(
                    [
                        node_type.lower(),
                        str(meta.get("display_name", "")).lower(),
                        str(meta.get("description", "")).lower(),
                        str(meta.get("category", "")).lower(),
                    ]
                )
                score = 0
                for t in tokens:
                    if t in node_type.lower():
                        score += 3
                    if t in str(meta.get("display_name", "")).lower():
                        score += 2
                    if t in str(meta.get("description", "")).lower():
                        score += 1
                    if t in str(meta.get("category", "")).lower():
                        score += 1
                # Also match common intents even when tokenization misses (e.g. "telegram", "prompt")
                if "telegram" in query and "telegram" in hay:
                    score += 5
                if ("text input" in query or "prompt" in query) and ("text" in hay and "input" in hay):
                    score += 2
                if score > 0:
                    scored.append((score, node_type))

            scored.sort(key=lambda x: x[0], reverse=True)
            picked_types = [t for _, t in scored[:limit]]

            # Add a few ultra-common nodes if present (helps even if query is short)
            for t in ["telegram_send_message", "text_input", "text_display"]:
                if t not in picked_types and NodeRegistry.is_registered(t):
                    picked_types.append(t)
                    if len(picked_types) >= limit:
                        break

            out: List[Dict[str, Any]] = []
            for node_type in picked_types[:limit]:
                node_cls = NodeRegistry.get(node_type)
                meta = NodeRegistry.get_metadata(node_type) or {}
                ports = get_node_port_definitions(node_cls) if node_cls else {"input_ports": [], "output_ports": []}
                out.append(
                    {
                        "node_type": node_type,
                        "name": meta.get("display_name") or node_type,
                        "category": meta.get("category"),
                        "description": meta.get("description") or "",
                        "icon": meta.get("icon"),
                        "input_ports": ports.get("input_ports", []),
                        "output_ports": ports.get("output_ports", []),
                    }
                )

            return out
        except Exception as e:
            logger.debug(f"Node catalog lookup failed: {type(e).__name__}: {e}")
            return []

    def _gather_workflow_examples(self, user_message: str, max_examples: int = 3, max_chars_each: int = 4500) -> List[tuple]:
        """
        Return a small set of relevant workflow JSON examples (sanitized) to ground workflow drafting.
        """
        try:
            root = self._workflow_examples_dir
            if not root.exists() or not root.is_dir():
                return []

            query = (user_message or "").lower()
            tokens = [t for t in re.split(r"[^a-z0-9_]+", query) if len(t) >= 3]

            # Score files by filename + contents keywords (bounded read)
            candidates: List[tuple[int, Path]] = []
            for p in sorted(root.glob("*.json")):
                score = 0
                name = p.name.lower()
                for t in tokens:
                    if t in name:
                        score += 3
                # Lightweight content scan (first ~8KB)
                try:
                    data = p.read_text(encoding="utf-8", errors="ignore")[:8000].lower()
                except Exception:
                    data = ""
                for t in tokens:
                    if t in data:
                        score += 1
                # Intent boosts
                if "whatsapp" in query and "whatsapp" in (name + " " + data):
                    score += 4
                if "telegram" in query and "telegram" in (name + " " + data):
                    score += 4
                if "loop" in query and "loop" in (name + " " + data):
                    score += 4
                if ("pdf" in query or "document" in query) and ("pdf" in (name + " " + data) or "document" in (name + " " + data)):
                    score += 3
                if score > 0:
                    candidates.append((score, p))

            candidates.sort(key=lambda x: x[0], reverse=True)

            # Fallback: if nothing matched, include a couple diverse examples (bounded)
            picked: List[Path] = [p for _, p in candidates[:max_examples]]
            if not picked:
                # Prefer a linear + a loop + an agent example if present
                preferred = [
                    "csv_structure_data__excel__llm__csv.json",
                    "virtual_vending_machine__loop__state__simulation.json",
                    "employer_skill_enhancement__docs__llm__agent__email.json",
                ]
                for name in preferred:
                    pp = root / name
                    if pp.exists():
                        picked.append(pp)
                        if len(picked) >= max_examples:
                            break

            out: List[tuple] = []
            for p in picked[:max_examples]:
                try:
                    raw = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                snippet = raw.strip()
                if len(snippet) > max_chars_each:
                    snippet = snippet[:max_chars_each] + "\n...\n"
                out.append((p.name, snippet))
            return out
        except Exception as e:
            logger.debug(f"Workflow example lookup failed: {type(e).__name__}: {e}")
            return []
    
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

