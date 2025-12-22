"""
Vision Language Model Node

LLM node with vision capabilities for analyzing images.
Supports vision-capable models like GPT-4V, Claude 3, LLaVA.
Uses MediaFormat for standardized image input.
"""

import logging
import base64
import io
from typing import Dict, Any, List, Optional
from pathlib import Path
from PIL import Image

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import LLMCapability
from app.core.nodes.registry import register_node
from app.core.nodes.multimodal import MediaFormat
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="vision_llm",
    category=NodeCategory.AI,
    name="Vision Language Model",
    description="Analyze images with vision-capable AI models (GPT-4V, GPT-5, Claude 3, LLaVA, Qwen3-VL)",
    icon="fa-solid fa-eye",
    version="1.0.0"
)
class VisionLLMNode(Node, LLMCapability):
    """
    Vision Language Model Node - Analyze images with AI.
    
    Features:
    - Supports all vision-capable providers (OpenAI GPT-4V, Anthropic Claude 3, Local LLaVA)
    - Single or multiple image inputs
    - Variable support in prompts
    - System + User prompt configuration
    - Temperature control
    
    ⚠️ IMPORTANT: You must select a vision-capable model:
    - OpenAI: gpt-4-vision-preview, gpt-4-turbo, gpt-4o, gpt-4o-mini, o1, o3, gpt-5 (2025)
    - Anthropic: claude-3-opus-20240229, claude-3-sonnet-20240229, claude-3-5-sonnet-20240620
    - Local: llava, bakllava, qwen3-vl
    
    Regular text models (gpt-3.5-turbo, claude-2) will NOT work!
    
    Use Cases:
    - Document analysis and OCR
    - Image classification
    - Visual question answering
    - Object detection
    - Scene understanding
    - Handwriting recognition
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "images",
                "type": PortType.UNIVERSAL,
                "display_name": "Image(s)",
                "description": "Single image or array of images to analyze (base64 data or file paths)",
                "required": True
            },
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
                "description": "LLM analysis/description of the image"
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
                "placeholder": "You are an expert document analyzer...",
                "default": "",
                "rows": 3
            },
            "user_prompt": {
                "type": "string",
                "label": "User Prompt",
                "description": "Question/instruction for analyzing the image. Supports variables: {{node.field}}",
                "required": True,
                "widget": "textarea",
                "placeholder": "Extract the passport expiry date from this image...",
                "rows": 5
            },
            "detail_level": {
                "type": "string",
                "widget": "select",
                "label": "Detail Level",
                "description": "Image analysis detail level (GPT-4V only)",
                "required": False,
                "default": "auto",
                "options": [
                    {"value": "auto", "label": "Auto (recommended)"},
                    {"value": "low", "label": "Low (faster, cheaper)"},
                    {"value": "high", "label": "High (slower, more detailed)"}
                ]
            },
            "batch_size": {
                "type": "integer",
                "widget": "number",
                "label": "Batch Size",
                "description": "Max images per API call. For multi-page documents, use 1-3 to avoid timeouts. 0 = all at once (risky!)",
                "required": False,
                "default": 0,
                "min": 0,
                "max": 10
            },
            "combine_responses": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Combine Responses",
                "description": "When processing multiple images in batches, combine all responses into one",
                "required": False,
                "default": True
            },
            "timeout_seconds": {
                "type": "integer",
                "widget": "number",
                "label": "API Timeout (seconds)",
                "description": "Timeout for each vision API call. Vision models need 60-180s depending on image count. 0 = use default",
                "required": False,
                "default": 180,
                "min": 0,
                "max": 600
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute vision LLM analysis with automatic batching for multiple images."""
        try:
            # Get image data from port (can be single image or array)
            image_input = input_data.ports.get("images")
            if not image_input:
                raise ValueError("No images provided")
            
            logger.info(f"👁️ Vision LLM received image input type: {type(image_input)}")
            
            # Normalize to list
            if isinstance(image_input, list):
                image_list = image_input
                logger.info(f"👁️ Vision LLM processing {len(image_list)} images from list")
            else:
                image_list = [image_input]
                logger.info(f"👁️ Vision LLM processing 1 image (converted to list)")
            
            # Resolve prompts (supports variables and templates)
            system_prompt = self.resolve_config(input_data, "system_prompt", "")
            user_prompt = self.resolve_config(input_data, "user_prompt", "")
            detail_level = self.resolve_config(input_data, "detail_level", "auto")
            batch_size = self.resolve_config(input_data, "batch_size", 1)
            combine_responses = self.resolve_config(input_data, "combine_responses", True)
            timeout_seconds = self.resolve_config(input_data, "timeout_seconds", 180)
            
            # Validate user prompt
            if not user_prompt or not user_prompt.strip():
                raise ValueError("User prompt cannot be empty")
            
            # Get context from port (optional)
            context_data = input_data.ports.get("context")
            
            # Batch size validation
            if batch_size < 0:
                batch_size = len(image_list)  # Process all at once
            elif batch_size == 0:
                batch_size = len(image_list)  # 0 means all at once
            
            logger.info(
                f"👁️ Vision LLM Node executing:\n"
                f"  System: {system_prompt[:50]}{'...' if len(system_prompt) > 50 else ''}\n"
                f"  User: {user_prompt[:50]}{'...' if len(user_prompt) > 50 else ''}\n"
                f"  Images: {len(image_list)}\n"
                f"  Batch Size: {batch_size} ({'all at once' if batch_size >= len(image_list) else f'{(len(image_list) + batch_size - 1) // batch_size} batches'})\n"
                f"  Timeout: {timeout_seconds}s per batch\n"
                f"  Detail: {detail_level}\n"
                f"  Context: {bool(context_data)}"
            )
            
            # Process images in batches
            all_responses = []
            total_batches = (len(image_list) + batch_size - 1) // batch_size
            
            for batch_idx in range(0, len(image_list), batch_size):
                batch_images = image_list[batch_idx:batch_idx + batch_size]
                batch_num = (batch_idx // batch_size) + 1
                
                logger.info(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch_images)} images)...")
                
                # Process batch
                response = await self._process_image_batch(
                    batch_images, 
                    system_prompt, 
                    user_prompt, 
                    detail_level, 
                    context_data,
                    timeout_seconds,
                    batch_num,
                    total_batches
                )
                
                all_responses.append(response)
            
            # Combine or return responses
            if len(all_responses) == 1:
                # Single batch - return as is
                return all_responses[0]
            elif combine_responses:
                # Multiple batches - combine responses
                logger.info(f"🔗 Combining {len(all_responses)} batch responses...")
                combined_text = "\n\n".join([r["response"] for r in all_responses])
                combined_metadata = {
                    "provider": all_responses[0]["metadata"]["provider"],
                    "model": all_responses[0]["metadata"]["model"],
                    "temperature": all_responses[0]["metadata"]["temperature"],
                    "detail_level": detail_level,
                    "total_batches": len(all_responses),
                    "total_images": len(image_list),
                    "batch_size": batch_size,
                    "combined_length": len(combined_text)
                }
                return {
                    "response": combined_text,
                    "metadata": combined_metadata
                }
            else:
                # Multiple batches - return as array
                logger.info(f"📋 Returning {len(all_responses)} batch responses as array...")
                return {
                    "response": [r["response"] for r in all_responses],
                    "metadata": {
                        "provider": all_responses[0]["metadata"]["provider"],
                        "model": all_responses[0]["metadata"]["model"],
                        "total_batches": len(all_responses),
                        "total_images": len(image_list),
                        "batch_size": batch_size
                    }
                }
            
        except Exception as e:
            logger.error(f"❌ Vision LLM node error: {e}", exc_info=True)
            return {
                "response": "",
                "metadata": {"error": str(e)},
                "error": str(e)
            }
    
    async def _process_image_batch(
        self,
        image_list: List[Any],
        system_prompt: str,
        user_prompt: str,
        detail_level: str,
        context_data: Any,
        timeout_seconds: int,
        batch_num: int = 1,
        total_batches: int = 1
    ) -> Dict[str, Any]:
        """Process a batch of images."""
        try:
            # Process all images in batch to base64
            base64_images = []
            for idx, img_data in enumerate(image_list):
                try:
                    logger.info(f"  🔍 Image {idx + 1}: type={type(img_data)}, data preview={str(img_data)[:200]}")
                    base64_img = await self._prepare_image(img_data)
                    base64_images.append(base64_img)
                    logger.info(f"  ✅ Image {idx + 1}/{len(image_list)} prepared ({len(base64_img)} chars)")
                except Exception as e:
                    logger.error(f"  ❌ Failed to prepare image {idx + 1}: {e}", exc_info=True)
                    raise ValueError(f"Failed to prepare image {idx + 1}: {e}")
            
            # Build messages with images
            messages = []
            
            # Add system message if provided
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Get provider info to determine message format
            provider = self.llm_provider if hasattr(self, 'llm_provider') else "unknown"
            model = self.llm_model if hasattr(self, 'llm_model') else "unknown"
            logger.info(f"📸 Building vision messages for provider: {provider}, model: {model}")
            
            # Build user message with text + all images
            # Different providers use different formats
            if provider.lower() == "local":
                # Ollama format: Simple list with text and base64 images
                user_content = [user_prompt]
                
                # Add all images as base64 data URIs
                for idx, base64_image in enumerate(base64_images):
                    user_content.append(f"data:image/jpeg;base64,{base64_image}")
                    logger.info(f"  📸 Added image {idx + 1} to Ollama message (data URI)")
                
                # Add context if provided
                if context_data:
                    user_content[0] += f"\n\nAdditional Context: {context_data}"
                
                # For Ollama, pass as simple string (single image) or list (multiple)
                if len(base64_images) == 1:
                    # Single image: use simple format
                    messages.append({
                        "role": "user",
                        "content": user_content[0],  # text
                        "images": [base64_images[0]]  # image as separate field
                    })
                else:
                    # Multiple images: use list format
                    messages.append({
                        "role": "user",
                        "content": user_prompt + (f"\n\nAdditional Context: {context_data}" if context_data else ""),
                        "images": base64_images  # all images as array
                    })
            else:
                # OpenAI/Anthropic format: Structured content with image_url
                # NOTE: All OpenAI models (GPT-4V, GPT-4o, GPT-5) use image_url format
                user_content = [
                    {"type": "text", "text": user_prompt}
                ]
                
                # Add all images
                for idx, base64_image in enumerate(base64_images):
                    # Log image size for debugging timeouts
                    image_size_kb = len(base64_image) / 1024
                    image_size_mb = image_size_kb / 1024
                    logger.info(f"  📸 Image {idx + 1} size: {image_size_kb:.1f}KB ({image_size_mb:.2f}MB)")
                    
                    # Warn if image is very large (might cause timeout)
                    if image_size_mb > 3.0:
                        logger.warning(f"  ⚠️  Image {idx + 1} is large ({image_size_mb:.2f}MB) - this may cause slow API response or timeout")
                    if image_size_mb > 10.0:
                        logger.error(f"  🚨 Image {idx + 1} is very large ({image_size_mb:.2f}MB) - OpenAI has a 20MB limit, expect timeout or failure!")
                    
                    image_url_content = {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                    
                    # Add detail level for GPT-4V/GPT-5
                    if detail_level != "auto":
                        image_url_content["image_url"]["detail"] = detail_level
                    
                    user_content.append(image_url_content)
                    logger.info(f"  📸 Added image {idx + 1} to OpenAI/Anthropic message (image_url format)")
                
                # Add context if provided
                if context_data:
                    context_text = f"\n\nAdditional Context: {context_data}"
                    user_content[0]["text"] += context_text
                
                messages.append({
                    "role": "user",
                    "content": user_content
                })
            
            logger.info(f"📸 Calling vision LLM with {len(messages)} messages and {len(base64_images)} images")
            logger.debug(f"📸 Messages structure: {[{'role': m.get('role'), 'content_type': type(m.get('content'))} for m in messages]}")
            
            # Call LLM with messages (via LLMCapability) with custom timeout
            # The timeout will be passed through kwargs to LangChainManager
            response = await self.call_llm_with_messages(messages, timeout=timeout_seconds)
            
            logger.info(f"📸 Vision LLM response received: type={type(response)}, preview={str(response)[:200]}")
            
            # Extract response content
            if isinstance(response, dict):
                response_text = response.get("content", str(response))
            else:
                response_text = str(response)
            
            # Build metadata
            metadata = {
                "provider": self.llm_provider if hasattr(self, 'llm_provider') else "unknown",
                "model": self.llm_model if hasattr(self, 'llm_model') else "unknown",
                "temperature": self.llm_temperature if hasattr(self, 'llm_temperature') else None,
                "detail_level": detail_level,
                "prompt_length": len(user_prompt),
                "response_length": len(response_text),
                "has_system_prompt": bool(system_prompt),
                "has_context": bool(context_data),
                "image_count": len(base64_images),
                "total_image_size_kb": sum(len(img) / 1024 for img in base64_images)
            }
            
            logger.info(
                f"✅ Vision LLM completed: {len(response_text)} chars, "
                f"{len(base64_images)} images, "
                f"provider={metadata['provider']}, model={metadata['model']}"
            )
            
            return {
                "response": response_text,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Vision LLM node error: {e}", exc_info=True)
            return {
                "response": "",
                "metadata": {"error": str(e)},
                "error": str(e)
            }
    
    def _optimize_image(self, image_bytes: bytes, max_size: int = 2048, quality: int = 85) -> str:
        """
        Optimize image for vision API to reduce size.
        
        Large images (especially high-DPI scans) can cause API timeouts.
        This resizes and compresses images while maintaining readability.
        
        Different providers have different size limits:
        - OpenAI GPT-4V/GPT-5: 20MB limit, but smaller is faster
        - Anthropic Claude: 5MB limit
        - Local Ollama: No hard limit but smaller is faster
        
        Args:
            image_bytes: Raw image bytes
            max_size: Maximum dimension (width or height) in pixels
            quality: JPEG quality (1-100, higher = better quality but larger size)
        
        Returns:
            Base64-encoded optimized image
        """
        try:
            # Open image
            img = Image.open(io.BytesIO(image_bytes))
            original_size = img.size
            
            # Convert RGBA to RGB (for JPEG compatibility)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if too large
            if max(img.size) > max_size:
                # Calculate new size maintaining aspect ratio
                ratio = max_size / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"  🔽 Resized image: {original_size} → {new_size}")
            
            # Compress to JPEG
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            compressed_bytes = output.getvalue()
            
            # Check if still too large (> 5MB base64) and compress more aggressively
            b64_size = len(base64.b64encode(compressed_bytes))
            if b64_size > 5 * 1024 * 1024:  # 5MB
                logger.warning(f"  ⚠️  Image still large after first compression ({b64_size / 1024 / 1024:.1f}MB), compressing more aggressively...")
                
                # Reduce quality and/or size further
                if quality > 60:
                    # Try with lower quality first
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=60, optimize=True)
                    compressed_bytes = output.getvalue()
                    b64_size = len(base64.b64encode(compressed_bytes))
                    logger.info(f"  📉 Reduced quality to 60: {b64_size / 1024 / 1024:.1f}MB")
                
                # If still too large, reduce dimensions
                if b64_size > 5 * 1024 * 1024 and max(img.size) > 1024:
                    ratio = 1024 / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    output = io.BytesIO()
                    img.save(output, format='JPEG', quality=60, optimize=True)
                    compressed_bytes = output.getvalue()
                    b64_size = len(base64.b64encode(compressed_bytes))
                    logger.info(f"  📉 Reduced size to {new_size}: {b64_size / 1024 / 1024:.1f}MB")
            
            # Calculate size reduction
            original_b64_size = len(base64.b64encode(image_bytes))
            compressed_b64_size = len(base64.b64encode(compressed_bytes))
            reduction = ((original_b64_size - compressed_b64_size) / original_b64_size) * 100 if original_b64_size > 0 else 0
            
            logger.info(f"  📉 Image optimized: {original_b64_size / 1024:.1f}KB → {compressed_b64_size / 1024:.1f}KB ({reduction:.1f}% reduction)")
            
            return base64.b64encode(compressed_bytes).decode('utf-8')
            
        except Exception as e:
            logger.warning(f"  ⚠️ Image optimization failed: {e}, using original")
            # Fall back to original if optimization fails
            return base64.b64encode(image_bytes).decode('utf-8')
    
    async def _prepare_image(self, image_data: Any) -> str:
        """
        Prepare image data for vision LLM.
        
        Handles MediaFormat and legacy formats:
        - MediaFormat: {"type": "image", "data": "...", "data_type": "base64|url|file_path"}
        - Legacy: Base64 string, file path, or dict
        
        Optimizes images to reduce API payload size and prevent timeouts.
        
        Args:
            image_data: Image data in various formats
        
        Returns:
            Base64-encoded optimized image string
        """
        # Case 1: MediaFormat
        if isinstance(image_data, dict) and image_data.get("type") == "image":
            data_type = image_data.get("data_type")
            data = image_data.get("data")
            
            if data_type == "base64":
                # Even if already base64, decode and optimize
                img_bytes = base64.b64decode(data)
                return self._optimize_image(img_bytes)
            
            elif data_type == "file_path":
                if Path(data).exists():
                    logger.info(f"📁 Reading image from MediaFormat file_path: {data}")
                    with open(data, "rb") as f:
                        img_bytes = f.read()
                        return self._optimize_image(img_bytes)
                else:
                    raise ValueError(f"Image file not found: {data}")
            
            elif data_type == "url":
                # TODO: Download from URL
                raise ValueError("URL image loading not yet implemented")
            
            else:
                raise ValueError(f"Unknown MediaFormat data_type: {data_type}")
        
        # Case 2: Legacy - Already base64 string or file path
        if isinstance(image_data, str):
            # Check if it's a file path
            if image_data.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')):
                if Path(image_data).exists():
                    logger.info(f"📁 Reading image from legacy file path: {image_data}")
                    with open(image_data, "rb") as f:
                        img_bytes = f.read()
                        return self._optimize_image(img_bytes)
                else:
                    raise ValueError(f"Image file not found: {image_data}")
            else:
                # Assume it's already base64
                # Remove data URL prefix if present
                if image_data.startswith('data:image'):
                    image_data = image_data.split('base64,')[1]
                # Decode and optimize
                img_bytes = base64.b64decode(image_data)
                return self._optimize_image(img_bytes)
        
        # Case 3: Legacy - Dictionary with various keys
        if isinstance(image_data, dict):
            # Try base64_data
            if 'base64_data' in image_data:
                img_bytes = base64.b64decode(image_data['base64_data'])
                return self._optimize_image(img_bytes)
            
            # Try image_data
            if 'image_data' in image_data:
                img_bytes = base64.b64decode(image_data['image_data'])
                return self._optimize_image(img_bytes)
            
            # Try file_path or path
            file_path = image_data.get('file_path') or image_data.get('path')
            if file_path and Path(file_path).exists():
                logger.info(f"📁 Reading image from legacy dict file path: {file_path}")
                with open(file_path, "rb") as f:
                    img_bytes = f.read()
                    return self._optimize_image(img_bytes)
            
            raise ValueError(f"Image dict missing valid data: {image_data.keys()}")
        
        # Case 4: Bytes
        if isinstance(image_data, bytes):
            return self._optimize_image(image_data)
        
        raise ValueError(f"Unsupported image data type: {type(image_data)}")

