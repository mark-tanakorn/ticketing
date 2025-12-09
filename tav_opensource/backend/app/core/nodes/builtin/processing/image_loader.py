"""
Image Loader Node

Load image file and convert to base64 or other formats.
Uses MediaFormat for standardized input/output.
"""

import logging
import base64
from typing import Dict, Any, List
from pathlib import Path

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.core.nodes.capabilities import PasswordProtectedFileCapability
from app.core.nodes.multimodal import ImageFormatter
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="image_loader",
    category=NodeCategory.PROCESSING,
    name="Image Loader",
    description="Load image file and convert to base64 or other formats (MediaFormat)",
    icon="fa-solid fa-image",
    version="1.0.0"
)
class ImageLoaderNode(Node, PasswordProtectedFileCapability):
    """
    Image Loader Node - Load image into memory
    
    Input: MediaFormat image or legacy file reference
    Output: MediaFormat with base64 data or image blob
    
    Use for loading images for Vision LLM nodes or image processing.
    Supports password-protected files (for archived images).
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "file",
                "type": PortType.UNIVERSAL,
                "display_name": "File Reference",
                "description": "Image file reference (MediaFormat or legacy)",
                "required": True
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "image",
                "type": PortType.UNIVERSAL,
                "display_name": "Image Data",
                "description": "Base64-encoded image (MediaFormat)"
            },
            {
                "name": "metadata",
                "type": PortType.UNIVERSAL,
                "display_name": "Metadata",
                "description": "Image metadata (dimensions, format, etc.)"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "output_format": {
                "type": "select",
                "widget": "select",
                "label": "Output Format",
                "description": "Format for image output",
                "required": False,
                "default": "base64",
                "options": [
                    {"label": "Base64 String", "value": "base64"},
                    {"label": "Data URL", "value": "data_url"},
                    {"label": "File Path", "value": "file_path"}
                ]
            },
            "include_dimensions": {
                "type": "boolean",
                "label": "Include Dimensions",
                "description": "Extract image width and height",
                "required": False,
                "default": True,
                "widget": "checkbox"
            },
            "annotations": {
                "type": "json",
                "label": "Annotations",
                "description": "JSON annotations from frontend",
                "required": False,
                "widget": "hidden"
            }
        }
    
    async def execute(self, inputs: NodeExecutionInput) -> Dict[str, Any]:
        """Execute image loader node."""
        try:
            file_ref = inputs.ports.get("file")
            annotations = self.config.get("annotations")
            
            if not file_ref:
                raise ValueError("No file reference provided. Connect to an Image Upload or File Converter node.")
            
            # Handle MediaFormat input
            if isinstance(file_ref, dict) and file_ref.get("type") == "image":
                # It's MediaFormat!
                file_path = file_ref.get("data")
                data_type = file_ref.get("data_type")
                image_format = file_ref.get("format", "png")
                metadata = file_ref.get("metadata", {})
                
                if data_type != "file_path":
                    # Already base64 or URL - just pass through or convert
                    if self.config.get("output_format") == "base64" and data_type == "base64":
                        return {"image": file_ref, "metadata": metadata}
                    # For other conversions, we'll need the file
                    raise ValueError(f"Image Loader currently only supports file_path MediaFormat. Got: {data_type}")
                
            # Handle legacy formats
            else:
                # Extract path from various legacy formats
                storage_path = None
                filename = None
                file_size = None
                mime_type = None
                image_format = "png"
                
                if isinstance(file_ref, dict):
                    # Legacy format - various possible structures
                    if file_ref.get("modality") == "image":
                        storage_path = file_ref.get("storage_path")
                        filename = file_ref.get("filename")
                        file_size = file_ref.get("size_bytes")
                        mime_type = file_ref.get("mime_type")
                    elif file_ref.get("file_path"):
                        storage_path = file_ref.get("file_path")
                        filename = file_ref.get("filename")
                        image_format = file_ref.get("format", "png")
                    else:
                        storage_path = file_ref.get("path") or file_ref.get("file_path") or file_ref.get("storage_path")
                        filename = file_ref.get("filename") or file_ref.get("name")
                
                elif isinstance(file_ref, str):
                    storage_path = file_ref
                
                else:
                    raise ValueError(f"Invalid file reference type: {type(file_ref)}")
                
                if not storage_path:
                    raise ValueError("File reference missing path/storage_path")
                
                file_path = storage_path
                metadata = {
                    "filename": filename,
                    "file_size": file_size,
                    "mime_type": mime_type
                }
            
            # Build full path (handle both absolute and relative paths)
            full_path = Path(file_path)
            
            # Don't prepend if already absolute or already starts with "data"
            if not full_path.is_absolute():
                if not str(file_path).startswith("data"):
                    base_path = Path("data")
                    full_path = base_path / file_path
            
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {full_path}")
            
            logger.info(f"🖼️ Loading image: {full_path}")
            
            output_format = self.config.get("output_format", "base64")
            include_dimensions = self.config.get("include_dimensions", True)
            
            # Get image dimensions if requested
            if include_dimensions:
                try:
                    from PIL import Image
                    with Image.open(full_path) as img:
                        metadata["width"] = img.width
                        metadata["height"] = img.height
                        metadata["pil_format"] = img.format
                        metadata["mode"] = img.mode
                    logger.info(f"📐 Image dimensions: {metadata['width']}x{metadata['height']}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not extract image dimensions: {e}")
            
            # Attach annotations to metadata if present
            if annotations:
                metadata["annotations"] = annotations
                logger.info(f"📋 Attached {len(annotations)} annotations to image metadata")
            
            # Load image based on output format
            if output_format == "file_path":
                # Return MediaFormat with file_path
                image_data = ImageFormatter.from_file_path(
                    file_path=str(full_path),
                    format=image_format,
                    metadata=metadata
                )
            
            elif output_format == "base64":
                # Convert to base64 and return MediaFormat
                with open(full_path, "rb") as f:
                    image_bytes = f.read()
                b64_string = base64.b64encode(image_bytes).decode('utf-8')
                
                image_data = ImageFormatter.from_base64(
                    base64_data=b64_string,
                    format=image_format,
                    metadata=metadata
                )
            
            elif output_format == "data_url":
                # Convert to data URL and return MediaFormat
                with open(full_path, "rb") as f:
                    image_bytes = f.read()
                b64_string = base64.b64encode(image_bytes).decode('utf-8')
                mime_type = metadata.get("mime_type") or f"image/{image_format}"
                data_url = f"data:{mime_type};base64,{b64_string}"
                
                image_data = ImageFormatter.from_url(
                    url=data_url,
                    format=image_format,
                    metadata=metadata
                )
            
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
            
            logger.info(f"✅ Image loaded: {output_format} format (MediaFormat)")
            
            return {
                "image": image_data,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Image loader failed: {e}", exc_info=True)
            raise
