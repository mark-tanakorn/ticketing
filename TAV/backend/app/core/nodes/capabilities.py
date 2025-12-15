"""
Node Capabilities

Mixins that provide additional functionality to nodes (LLM, AI compute, Trigger, etc.).
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable
from abc import ABC, abstractmethod

from app.utils.timezone import get_local_now

logger = logging.getLogger(__name__)


class LLMCapability(ABC):
    """
    Mixin for nodes that call LLM APIs via LangChain.
    
    Provides:
    - Auto-injected LLM config (temperature, model, provider, max_tokens)
    - Helper methods for LLM calls via LangChainManager
    - Automatic resource pool assignment (llm)
    - Config cascade: node config → workflow variables → global defaults
    
    Usage:
        class MyLLMNode(Node, LLMCapability):
            async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
                response = await self.call_llm("Generate a greeting")
                return {"output": response}
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize LLM capability with config injection"""
        super().__init__(*args, **kwargs)
        self._llm_config_cache: Optional[Dict[str, Any]] = None
        self._langchain_manager = None
    
    def _get_langchain_manager(self):
        """Get LangChainManager instance (lazy-loaded)."""
        if self._langchain_manager is None:
            # Create a new DB session for LLM operations
            # Note: This session should be closed when the node is done
            from app.core.ai.manager import get_langchain_manager
            from app.database.session import SessionLocal
            
            db = SessionLocal()
            self._langchain_manager = get_langchain_manager(db)
            self._db_session = db  # Store reference so we can close it later
            
        return self._langchain_manager
    
    def cleanup(self):
        """Cleanup resources (close database session)."""
        if hasattr(self, '_db_session') and self._db_session:
            try:
                self._db_session.close()
                self._db_session = None
                self._langchain_manager = None
                logger.debug(f"✅ Closed database session for node {self.__class__.__name__}")
            except Exception as e:
                logger.warning(f"⚠️ Error closing database session: {e}")
    
    def _get_llm_config(self) -> Dict[str, Any]:
        """
        Get LLM config with cascade priority:
        1. Node-level config (highest priority)
        2. Workflow variables
        3. Global AI Governor defaults (lowest priority)
        
        Returns:
            Dictionary with llm_provider, llm_model, llm_temperature, llm_max_tokens
        """
        if self._llm_config_cache is not None:
            return self._llm_config_cache
        
        # Start with node-level config
        config = {
            "provider": self.config.get("llm_provider"),
            "model": self.config.get("llm_model"),
            "temperature": self.config.get("llm_temperature"),
            "max_tokens": self.config.get("llm_max_tokens"),
        }
        
        # Get workflow variables (if available from execution context)
        if hasattr(self, 'execution_context') and self.execution_context:
            workflow_vars = self.execution_context.variables
            
            # Fall back to workflow variables if node config is None
            if config["provider"] is None:
                config["provider"] = workflow_vars.get("llm_provider")
            if config["model"] is None:
                config["model"] = workflow_vars.get("llm_model")
            if config["temperature"] is None:
                config["temperature"] = workflow_vars.get("llm_temperature")
            if config["max_tokens"] is None:
                config["max_tokens"] = workflow_vars.get("llm_max_tokens")
        
        # Remove None values (will use AIGovernor defaults)
        config = {k: v for k, v in config.items() if v is not None}
        
        # Cache the result
        self._llm_config_cache = config
        
        logger.debug(f"Node {self.node_id} LLM config: {config}")
        return config
    
    async def call_llm(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Call LLM with auto-injected config via LangChain.
        
        Automatically injects conversation context from execution variables if available.
        
        Args:
            user_prompt: User prompt text
            system_prompt: Optional system prompt for context
            context: Optional additional context data
            **kwargs: Override LLM config for this call (provider, model, temperature, max_tokens)
        
        Returns:
            LLM response content as string
        
        Raises:
            Exception: If LLM call fails
        """
        # Merge: call kwargs → node config → workflow → global defaults
        llm_config = {**self._get_llm_config(), **kwargs}
        
        # AUTO-INJECT CONVERSATION CONTEXT if available in execution variables
        conversation_context = None
        if hasattr(self, 'execution_context') and self.execution_context:
            variables = self.execution_context.variables
            
            # Check if we have trigger conversation data
            if variables.get("trigger_conversation"):
                conversation_parts = []
                
                if variables.get("trigger_conversation"):
                    conversation_parts.append(f"CONVERSATION HISTORY:\n{variables.get('trigger_conversation')}")
                
                if variables.get("trigger_topic"):
                    conversation_parts.append(f"\nTOPIC: {variables.get('trigger_topic')}")
                
                if variables.get("trigger_priority"):
                    conversation_parts.append(f"PRIORITY: {variables.get('trigger_priority')}")
                
                if variables.get("trigger_timestamp"):
                    conversation_parts.append(f"TIMESTAMP: {variables.get('trigger_timestamp')}")
                
                if conversation_parts:
                    conversation_context = "\n".join(conversation_parts)
                    logger.info(f"🔗 Auto-injecting conversation context into LLM call for node {self.node_id}")
        
        # Build prompt with auto-injected conversation context
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
        else:
            full_prompt = user_prompt
        
        # Add conversation context BEFORE the main prompt (so LLM sees it first)
        # Keep it INFORMATIONAL - don't override node-specific instructions
        if conversation_context:
            full_prompt = f"""CONTEXT FROM TRIGGER (for your reference):
{conversation_context}

--- END OF CONTEXT ---

{full_prompt}"""
        
        if context:
            from app.core.nodes.multimodal import extract_content
            # Properly extract content instead of stringifying
            context_str = extract_content(context)
            full_prompt += f"\n\nContext: {context_str}"
        
        # DEBUG: Log the FINAL complete prompt being sent to LLM
        logger.info("=" * 80)
        logger.info(f"🚀 SENDING TO LLM (Node {self.node_id}):")
        logger.info(f"   Provider: {llm_config.get('provider')}")
        logger.info(f"   Model: {llm_config.get('model')}")
        logger.info(f"   Temperature: {llm_config.get('temperature')}")
        logger.info(f"   Prompt Length: {len(full_prompt)} characters")
        logger.info("-" * 80)
        logger.info("FULL PROMPT:")
        if len(full_prompt) > 2000:
            logger.info(f"{full_prompt[:1000]}\n... (middle truncated) ...\n{full_prompt[-1000:]}")
        else:
            logger.info(full_prompt)
        logger.info("=" * 80)
        
        # Call via LangChainManager
        manager = self._get_langchain_manager()
        
        try:
            response = await manager.call_llm(
                prompt=full_prompt,
                provider=llm_config.get("provider"),
                model=llm_config.get("model"),
                temperature=llm_config.get("temperature"),
                max_tokens=llm_config.get("max_tokens"),
                fallback=True
            )
            
            logger.info(f"✅ Node {self.node_id} LLM call succeeded")
            return response
        
        except Exception as e:
            error_msg = f"LLM call failed in node {self.node_id}: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    async def call_llm_with_messages(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call LLM with chat messages via LangChain.
        
        Args:
            messages: List of messages in OpenAI format [{"role": "user", "content": "..."}]
            tools: Optional list of tools for function calling
            tool_choice: Optional tool choice preference
            **kwargs: Override LLM config for this call
        
        Returns:
            Dict with "content" and optionally "tool_calls"
        
        Raises:
            Exception: If LLM call fails
        """
        # Merge config
        llm_config = {**self._get_llm_config(), **kwargs}
        
        # Call via LangChainManager
        manager = self._get_langchain_manager()
        
        try:
            response = await manager.call_llm_with_messages(
                messages=messages,
                provider=llm_config.get("provider"),
                model=llm_config.get("model"),
                temperature=llm_config.get("temperature"),
                max_tokens=llm_config.get("max_tokens"),
                fallback=True,
                **kwargs  # Forward additional kwargs like timeout
            )
            
            logger.info(f"✅ Node {self.node_id} LLM call (messages) succeeded")
            
            # Return in same format as before
            return {
                "content": response,
                "tool_calls": []  # LangChain tool calling will be added later
            }
        
        except Exception as e:
            error_msg = f"LLM call (messages) failed in node {self.node_id}: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    @property
    def llm_provider(self) -> Optional[str]:
        """Get configured LLM provider"""
        return self._get_llm_config().get("provider")
    
    @property
    def llm_model(self) -> Optional[str]:
        """Get configured LLM model"""
        return self._get_llm_config().get("model")
    
    @property
    def llm_temperature(self) -> Optional[float]:
        """Get configured LLM temperature"""
        return self._get_llm_config().get("temperature")
    
    @property
    def llm_max_tokens(self) -> Optional[int]:
        """Get configured LLM max tokens"""
        return self._get_llm_config().get("max_tokens")


class AICapability(ABC):
    """
    Mixin for compute-intensive AI nodes (embeddings, RAG, vision, etc.).
    
    Marks node as requiring AI resource pool (CPU/memory intensive).
    Used for:
    - Image processing
    - Embeddings generation
    - Local ML inference
    - Video/audio processing
    - RAG operations
    
    Provides helper methods for:
    - Embeddings via LangChain
    - RAG operations
    - Vector search
    
    Usage:
        class ImageClassifierNode(Node, AICapability):
            async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
                # Heavy local ML computation
                result = await classify_image(inputs["image"])
                return {"output": result}
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._langchain_manager = None
    
    def _get_langchain_manager(self):
        """Get LangChainManager instance (lazy-loaded)."""
        if self._langchain_manager is None:
            from app.core.ai.manager import get_langchain_manager
            from app.database.session import SessionLocal
            db = SessionLocal()
            self._langchain_manager = get_langchain_manager(db)
            self._db_session = db  # Store reference so we can close it later
        return self._langchain_manager
    
    def cleanup(self):
        """Cleanup resources (close database session)."""
        if hasattr(self, '_db_session') and self._db_session:
            try:
                self._db_session.close()
                self._db_session = None
                self._langchain_manager = None
                logger.debug(f"✅ Closed database session for node {self.__class__.__name__}")
            except Exception as e:
                logger.warning(f"⚠️ Error closing database session: {e}")
    
    def get_embeddings(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Get embeddings instance for semantic search/RAG.
        
        Args:
            provider: Provider name (defaults to HuggingFace local - FREE!)
            model: Model name (optional)
            
        Returns:
            LangChain Embeddings instance
        """
        manager = self._get_langchain_manager()
        return manager.get_embeddings(provider, model)
    
    async def embed_text(self, text: str, provider: Optional[str] = None) -> List[float]:
        """
        Embed a single text string.
        
        Args:
            text: Text to embed
            provider: Provider name (optional)
            
        Returns:
            Embedding vector (list of floats)
        """
        embeddings = self.get_embeddings(provider)
        return embeddings.embed_query(text)
    
    async def embed_documents(self, texts: List[str], provider: Optional[str] = None) -> List[List[float]]:
        """
        Embed multiple documents.
        
        Args:
            texts: List of texts to embed
            provider: Provider name (optional)
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.get_embeddings(provider)
        return embeddings.embed_documents(texts)


class ComputeCapability(ABC):
    """
    Mixin for heavy computation nodes (non-AI).
    
    Marks node as requiring compute resource pool.
    Used for:
    - Video encoding
    - Large file processing
    - Data transformation
    - Complex calculations
    
    Usage:
        class VideoProcessorNode(Node, ComputeCapability):
            async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
                # Heavy computation
                result = await process_video(inputs["video"])
                return {"output": result}
    """
    pass  # Marker mixin - used for resource pool assignment


def get_resource_classes(node: Any) -> List[str]:
    """
    Detect required resource pools based on node capabilities.
    
    Args:
        node: Node instance
    
    Returns:
        List of resource class names: ["standard"], ["llm"], ["ai"], or ["llm", "ai"]
    
    Examples:
        >>> node = HTTPRequestNode(...)
        >>> get_resource_classes(node)
        ['standard']
        
        >>> node = SendEmailNode(...)  # Has LLMCapability
        >>> get_resource_classes(node)
        ['llm']
        
        >>> node = ImageClassifierNode(...)  # Has AICapability
        >>> get_resource_classes(node)
        ['ai']
        
        >>> node = ImageAnalyzerNode(...)  # Has both
        >>> get_resource_classes(node)
        ['llm', 'ai']
    """
    classes = []
    
    if isinstance(node, LLMCapability):
        classes.append("llm")
    
    if isinstance(node, (AICapability, ComputeCapability)):
        classes.append("ai")
    
    if not classes:
        classes.append("standard")
    
    return classes


def has_llm_capability(node: Any) -> bool:
    """Check if node uses LLM"""
    return isinstance(node, LLMCapability)


def has_ai_capability(node: Any) -> bool:
    """Check if node is compute-intensive"""
    return isinstance(node, (AICapability, ComputeCapability))


class ExportCapability(ABC):
    """
    Mixin for export nodes (CSV, PDF, Excel, etc.) that generate downloadable files.
    
    Provides:
    - Auto-injected export mode config (download vs. server save)
    - Helper methods for file handling
    - Standardized download response format
    - Temporary file management for downloads
    
    Usage:
        class CSVExportNode(Node, ExportCapability):
            @classmethod
            def get_config_schema(cls):
                schema = super().get_export_config_schema()
                # Add your custom fields
                schema.update({
                    "delimiter": {...},
                    "columns": {...}
                })
                return schema
            
            async def execute(self, input_data):
                # Generate your file content
                csv_content = "..."
                filename = "export.csv"
                
                # Use export capability to handle download vs. save
                return await self.handle_export(
                    input_data=input_data,
                    file_content=csv_content,
                    filename=filename,
                    mime_type="text/csv"
                )
    """
    
    @classmethod
    def get_export_config_schema(cls) -> Dict[str, Any]:
        """
        Get standard export configuration fields.
        
        Returns config schema with export_mode, output_folder, and filename fields.
        Child classes should call this and extend with their own fields.
        """
        return {
            "export_mode": {
                "type": "select",
                "widget": "select",
                "label": "Export Mode",
                "description": "Where to save the exported file",
                "required": False,
                "default": "download",
                "options": [
                    {"label": "Quick Download (to Downloads folder)", "value": "download"},
                    {"label": "Save to Path", "value": "path"}
                ],
                "help": "'Quick Download' saves to browser Downloads folder. 'Save to Path' saves to a folder you specify."
            },
            "output_folder": {
                "type": "string",
                "label": "Output Folder",
                "description": "Folder where file will be saved (supports UNC paths like \\\\server\\share\\path)",
                "required": False,
                "placeholder": "C:\\Users\\YourName\\Desktop\\exports or \\\\192.168.1.100\\shared\\folder",
                "widget": "folder_picker",
                "help": "Full path to folder. Supports local paths (C:\\...) and network shares (\\\\server\\share\\path). Only used in 'Save to Path' mode.",
                "show_if": {"export_mode": "path"}
            },
            "network_credential": {
                "type": "string",
                "label": "Network Share Credential (Optional)",
                "description": "Credential for network share authentication",
                "required": False,
                "widget": "credential",
                "help": "Only needed for UNC network paths that require authentication (e.g., \\\\server\\share). Create a Basic Auth credential with username/password.",
                "show_if": {"export_mode": "path"}
            },
            "filename": {
                "type": "string",
                "label": "Filename",
                "description": "Name of the exported file",
                "required": False,
                "default": "export_{timestamp}",
                "placeholder": "export_{timestamp}.csv",
                "widget": "text",
                "help": "Use {timestamp}, {date}, {time} for dynamic names. File extension will be added automatically."
            }
        }
    
    async def handle_export(
        self,
        input_data: "NodeExecutionInput",
        file_content: bytes,
        filename: str,
        mime_type: str = "application/octet-stream"
    ) -> Dict[str, Any]:
        """
        Handle export based on mode.
        
        Modes:
        - 'download': Save to temp, return download marker (browser Downloads folder)
        - 'path': Save directly to specified output_folder path
        
        Args:
            input_data: Node execution input
            file_content: File content as bytes
            filename: Filename (with extension)
            mime_type: MIME type for download
        
        Returns:
            Result dict with file info, MediaFormat output, and download marker if in download mode
        """
        from pathlib import Path
        from app.core.nodes.base import NodeExecutionInput
        
        export_mode = self.resolve_config(input_data, "export_mode", "download")
        
        if export_mode == "path":
            # Save to specified path
            return await self._handle_path_mode(
                file_content=file_content,
                filename=filename,
                input_data=input_data
            )
        else:
            # Save to temp and trigger browser download
            return await self._handle_download_mode(
                file_content=file_content,
                filename=filename,
                mime_type=mime_type
            )
    
    def _create_media_format(
        self,
        file_path: str,
        filename: str,
        mime_type: str,
        size: int
    ) -> Dict[str, Any]:
        """
        Create MediaFormat output for exported files.
        
        Returns standardized MediaFormat that can be consumed by any node.
        """
        from pathlib import Path
        from app.core.nodes.multimodal import DocumentFormatter, ImageFormatter, AudioFormatter, VideoFormatter
        
        # Detect media type from MIME type
        format_ext = Path(filename).suffix.lstrip('.')
        
        metadata = {
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": size,
            "file_path": file_path  # Keep for backward compat
        }
        
        if mime_type.startswith("image/"):
            return ImageFormatter.from_file_path(
                file_path=file_path,
                format=format_ext,
                metadata=metadata
            )
        elif mime_type.startswith("audio/"):
            return AudioFormatter.from_file_path(
                file_path=file_path,
                format=format_ext,
                metadata=metadata
            )
        elif mime_type.startswith("video/"):
            return VideoFormatter.from_file_path(
                file_path=file_path,
                format=format_ext,
                metadata=metadata
            )
        else:
            # Default to document (PDF, CSV, Excel, etc.)
            return DocumentFormatter.from_file_path(
                file_path=file_path,
                format=format_ext,
                metadata=metadata
            )
    
    def _guess_mime_type(self, filename: str) -> str:
        """Guess MIME type from filename"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"
    
    async def _handle_download_mode(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str
    ) -> Dict[str, Any]:
        """Handle download mode - save to temp and return download marker"""
        from pathlib import Path
        
        try:
            # Save to temp file in data/temp
            temp_dir = Path("data") / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique temp filename
            from app.utils.timezone import get_local_now
            timestamp = get_local_now().strftime("%Y%m%d_%H%M%S")
            temp_filename = f"{timestamp}_{filename}"
            temp_path = temp_dir / temp_filename
            
            # Write file
            with open(temp_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"📥 File ready for download: {temp_filename} ({len(file_content)} bytes)")
            
            # Return special marker for frontend to trigger download
            return {
                "result": {
                    "success": True,
                    "export_mode": "download",
                    "filename": filename,
                    "file_size": len(file_content),
                    "file_path": str(temp_path),
                    "message": f"File ready for download: {filename}"
                },
                "file": self._create_media_format(
                    file_path=str(temp_path),
                    filename=filename,
                    mime_type=mime_type,
                    size=len(file_content)
                ),
                "_download": {
                    "filename": filename,
                    "temp_filename": temp_filename,
                    "mime_type": mime_type,
                    "size": len(file_content),
                    "mode": "download"
                }
            }
        
        except Exception as e:
            logger.error(f"❌ Download mode error: {e}", exc_info=True)
            return {
                "result": {
                    "success": False,
                    "error": f"Failed to prepare download: {e}"
                },
                "file": None
            }
    
    async def _handle_path_mode(
        self,
        file_content: bytes,
        filename: str,
        input_data: "NodeExecutionInput"
    ) -> Dict[str, Any]:
        """Handle path mode - save directly to specified folder (supports network shares)"""
        from pathlib import Path
        from app.utils.network_share import NetworkShareAuth
        
        try:
            output_folder = self.resolve_config(input_data, "output_folder")
            
            if not output_folder:
                return {
                    "result": {
                        "success": False,
                        "error": "Output folder not configured (required for 'Save to Path' mode)"
                    },
                    "file": None
                }
            
            # Full output path
            output_path = Path(output_folder) / filename
            
            # Check if this is a network share
            is_network = NetworkShareAuth.is_unc_path(output_folder)
            
            if is_network:
                # Network share path - may need credentials
                logger.info(f"📡 Detected network share: {output_folder}")
                
                # Get network credential if provided
                credential_id = self.resolve_config(input_data, "network_credential")
                username = None
                password = None
                
                if credential_id:
                    # Load credential
                    from app.services.credential_manager import CredentialManager
                    from app.database.session import SessionLocal
                    
                    db = SessionLocal()
                    try:
                        cred_manager = CredentialManager(db)
                        cred_data = cred_manager.get_credential_data(
                            credential_id=int(credential_id)
                        )
                        
                        if cred_data:
                            username = cred_data.get('username')
                            password = cred_data.get('password')
                            logger.info(f"🔐 Using network credential (user: {username})")
                    finally:
                        db.close()
                
                # Try to write to network path
                result = NetworkShareAuth.write_to_network_path(
                    file_content=file_content,
                    network_path=str(output_path),
                    username=username,
                    password=password
                )
                
                if result['success']:
                    # Detect MIME type
                    mime_type = self._guess_mime_type(filename)
                    
                    return {
                        "result": {
                            "success": True,
                            "export_mode": "path",
                            "file_path": str(output_path),
                            "filename": filename,
                            "file_size": len(file_content),
                            "message": f"File saved to network share: {output_path}"
                        },
                        "file": self._create_media_format(
                            file_path=str(output_path),
                            filename=filename,
                            mime_type=mime_type,
                            size=len(file_content)
                        )
                    }
                else:
                    return {
                        "result": {
                            "success": False,
                            "error": result.get('error', 'Failed to write to network share')
                        },
                        "file": None
                    }
            
            else:
                # Local path - standard file write
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write file
                with open(output_path, 'wb') as f:
                    f.write(file_content)
                
                logger.info(f"✅ File saved to path: {output_path} ({len(file_content)} bytes)")
                
                # Detect MIME type
                mime_type = self._guess_mime_type(filename)
                
                return {
                    "result": {
                        "success": True,
                        "export_mode": "path",
                        "file_path": str(output_path),
                        "filename": filename,
                        "file_size": len(file_content),
                        "message": f"File saved successfully: {output_path}"
                    },
                    "file": self._create_media_format(
                        file_path=str(output_path),
                        filename=filename,
                        mime_type=mime_type,
                        size=len(file_content)
                    )
                }
        
        except PermissionError as e:
            error_msg = f"Permission denied writing to {output_folder}. Check path and permissions."
            logger.error(f"❌ {error_msg}")
            return {
                "result": {
                    "success": False,
                    "error": error_msg
                },
                "file": None
            }
        except Exception as e:
            error_msg = f"Path save error: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                "result": {
                    "success": False,
                    "error": error_msg
                },
                "file": None
            }


class TriggerCapability(ABC):
    """
    Mixin for trigger nodes that initiate workflow execution.
    
    Triggers:
    - Have NO input ports (auto-detected from category or port config)
    - Implement start_monitoring() / stop_monitoring()
    - Fire workflow executions directly via callback
    - Run in background, independent of workflow execution
    
    Usage:
        @register_node("schedule_trigger", category="triggers")
        class ScheduleTriggerNode(Node, TriggerCapability):
            trigger_type = "schedule"
            
            async def execute(self, input_data):
                # Only for manual testing
                return {"output": "triggered"}
            
            async def start_monitoring(self, workflow_id, executor_callback):
                self._workflow_id = workflow_id
                self._executor_callback = executor_callback
                self._is_monitoring = True
                self._monitoring_task = asyncio.create_task(self._monitor_loop())
            
            async def stop_monitoring(self):
                self._is_monitoring = False
                if self._monitoring_task:
                    self._monitoring_task.cancel()
            
            async def _monitor_loop(self):
                while self._is_monitoring:
                    await asyncio.sleep(300)
                    await self.fire_trigger({"trigger_time": "..."})
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize trigger capability with monitoring state"""
        super().__init__(*args, **kwargs)
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
        self._workflow_id: Optional[str] = None
        self._executor_callback: Optional[Callable[[str, Dict[str, Any], str], Awaitable[None]]] = None
    
    @abstractmethod
    async def start_monitoring(
        self,
        workflow_id: str,
        executor_callback: Callable[[str, Dict[str, Any], str], Awaitable[None]]
    ):
        """
        Start monitoring for trigger events.
        
        Args:
            workflow_id: Workflow to trigger
            executor_callback: Function to call when triggered
                              Signature: async def callback(workflow_id, trigger_data, execution_source)
        
        Example:
            async def start_monitoring(self, workflow_id, executor_callback):
                self._workflow_id = workflow_id
                self._executor_callback = executor_callback
                self._is_monitoring = True
                
                # Start monitoring loop in background
                self._monitoring_task = asyncio.create_task(self._monitor_loop())
                
                logger.info(f"Started monitoring for {self.node_id}")
        """
        pass
    
    @abstractmethod
    async def stop_monitoring(self):
        """
        Stop monitoring for trigger events.
        
        Should:
        - Set self._is_monitoring = False
        - Cancel self._monitoring_task if exists
        - Clean up any resources (close connections, stop servers, etc.)
        
        Example:
            async def stop_monitoring(self):
                self._is_monitoring = False
                
                if self._monitoring_task:
                    self._monitoring_task.cancel()
                    try:
                        await self._monitoring_task
                    except asyncio.CancelledError:
                        pass
                
                logger.info(f"Stopped monitoring for {self.node_id}")
        """
        pass
    
    async def fire_trigger(self, trigger_data: Dict[str, Any]):
        """
        Fire the trigger (spawn workflow execution).
        
        Called by node when trigger condition is met.
        System handles concurrency limits and execution spawning.
        
        Args:
            trigger_data: Data to pass to workflow execution (becomes initial payload)
        
        Raises:
            RuntimeError: If executor callback is not set
        
        Example:
            # In your monitoring loop
            await self.fire_trigger({
                "trigger_time": get_local_now().isoformat(),
                "event_type": "schedule",
                "interval_seconds": 300
            })
        """
        if not self._executor_callback:
            logger.error(f"Trigger {self.node_id} has no executor callback - cannot fire")
            raise RuntimeError(f"Trigger {self.node_id} not properly initialized")
        
        # Get execution_source from node (e.g., "schedule", "webhook", "manual")
        execution_source = getattr(self, 'trigger_type', 'trigger')
        
        logger.info(
            f"🔔 Trigger {self.node_id} firing for workflow {self._workflow_id}, "
            f"source={execution_source}"
        )
        
        # Call executor to spawn workflow execution
        try:
            await self._executor_callback(
                workflow_id=self._workflow_id,
                trigger_data=trigger_data,
                execution_source=execution_source
            )
        except Exception as e:
            logger.error(f"Error firing trigger {self.node_id}: {e}", exc_info=True)
            raise
    
    @property
    def is_monitoring(self) -> bool:
        """Check if trigger is currently monitoring"""
        return self._is_monitoring


def has_trigger_capability(node: Any) -> bool:
    """Check if node is a trigger"""
    return isinstance(node, TriggerCapability)


class PasswordProtectedFileCapability(ABC):
    """
    Mixin for nodes that process password-protected files.
    
    Provides:
    - Automatic password configuration field injection (via loader.py)
    - Helper methods for opening encrypted PDFs
    - Helper methods for opening password-protected Office documents
    - Consistent password handling across all file processing nodes
    
    Supported file types:
    - PDF (via PyMuPDF/fitz)
    - Office Documents: DOCX, XLSX, PPTX (via msoffcrypto-tool)
    - ZIP archives (via zipfile)
    
    Usage:
        class DocumentLoaderNode(Node, PasswordProtectedFileCapability):
            # Password field automatically added to config schema by loader.py!
            
            async def execute(self, input_data):
                file_path = "document.pdf"
                password = self.resolve_config(input_data, "file_password")
                
                # Open with password support
                doc = self.open_pdf_with_password(file_path, password)
                # Process document...
    """
    
    def open_pdf_with_password(self, pdf_path: str, password: Optional[str] = None):
        """
        Open PDF with optional password support using PyMuPDF.
        
        Args:
            pdf_path: Path to PDF file
            password: Optional password for encrypted PDF
        
        Returns:
            PyMuPDF document object
        
        Raises:
            ImportError: If PyMuPDF is not installed
            ValueError: If PDF is encrypted but no password provided, or password is incorrect
        
        Example:
            doc = self.open_pdf_with_password("file.pdf", "secret123")
            for page in doc:
                text = page.get_text()
            doc.close()
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError(
                "PyMuPDF is required for PDF password support. "
                "Install with: pip install pymupdf"
            )
        
        # Open the PDF
        doc = fitz.open(pdf_path)
        
        # Check if encrypted
        if doc.is_encrypted:
            if not password:
                doc.close()
                raise ValueError(
                    f"PDF is password-protected but no password provided: {pdf_path}"
                )
            
            # Try to authenticate
            auth_result = doc.authenticate(password)
            
            if not auth_result:
                doc.close()
                raise ValueError(
                    f"Invalid password for encrypted PDF: {pdf_path}"
                )
            
            logger.info(f"🔓 Successfully opened password-protected PDF: {pdf_path}")
        
        return doc
    
    def open_office_doc_with_password(
        self,
        file_path: str,
        password: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        Decrypt password-protected Office document (DOCX, XLSX, PPTX).
        
        Uses msoffcrypto-tool to decrypt the file.
        Returns path to decrypted file (temporary if output_path not provided).
        
        Args:
            file_path: Path to encrypted Office document
            password: Password for decryption
            output_path: Optional path for decrypted file (creates temp file if None)
        
        Returns:
            Path to decrypted file
        
        Raises:
            ImportError: If msoffcrypto-tool is not installed
            ValueError: If password is incorrect or file is not encrypted
        
        Example:
            decrypted_path = self.open_office_doc_with_password(
                "encrypted.docx", 
                "secret123"
            )
            # Process decrypted file...
            # Remember to clean up temp file if needed
        """
        try:
            import msoffcrypto
        except ImportError:
            raise ImportError(
                "msoffcrypto-tool is required for Office document password support. "
                "Install with: pip install msoffcrypto-tool"
            )
        
        from pathlib import Path
        import tempfile
        
        if not password:
            # Not encrypted or no password provided - return original path
            return file_path
        
        # Create output path if not provided
        if not output_path:
            # Create temp file with same extension
            suffix = Path(file_path).suffix
            temp_fd, output_path = tempfile.mkstemp(suffix=suffix, dir="data/temp")
            import os
            os.close(temp_fd)  # Close file descriptor, we'll write with msoffcrypto
        
        try:
            # Open encrypted file
            with open(file_path, "rb") as encrypted_file:
                office_file = msoffcrypto.OfficeFile(encrypted_file)
                
                # Try to decrypt
                office_file.load_key(password=password)
                
                # Write decrypted file
                with open(output_path, "wb") as decrypted_file:
                    office_file.decrypt(decrypted_file)
            
            logger.info(f"🔓 Successfully decrypted password-protected Office document: {file_path}")
            return output_path
        
        except Exception as e:
            # Clean up temp file on error
            if output_path and Path(output_path).exists():
                try:
                    Path(output_path).unlink()
                except:
                    pass
            
            raise ValueError(
                f"Failed to decrypt Office document (wrong password or not encrypted): {e}"
            )
    
    def check_pdf_encrypted(self, pdf_path: str) -> bool:
        """
        Check if a PDF is password-protected.
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            True if PDF is encrypted, False otherwise
        """
        try:
            import fitz
            doc = fitz.open(pdf_path)
            is_encrypted = doc.is_encrypted
            doc.close()
            return is_encrypted
        except Exception as e:
            logger.warning(f"Could not check PDF encryption status: {e}")
            return False


def has_password_capability(node: Any) -> bool:
    """Check if node supports password-protected files"""
    return isinstance(node, PasswordProtectedFileCapability)