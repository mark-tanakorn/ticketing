"""
Image Upload Node

Upload images (PNG, JPG, WEBP, GIF, BMP, TIFF).
Outputs standardized MediaFormat for downstream processing nodes.
"""

import logging
from typing import Dict, Any, List
from pathlib import Path

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.core.nodes.multimodal import ImageFormatter
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="image_upload",
    category=NodeCategory.INPUT,
    name="Image Upload",
    description="Upload images (PNG, JPG, WEBP, GIF, BMP, TIFF)",
    icon="fa-solid fa-image",
    version="1.0.0"
)
class ImageUploadNode(Node):
    """
    Image Upload Node - Upload image files
    
    Accepts: PNG, JPG, JPEG, WEBP, GIF, BMP, TIFF
    Outputs: File reference object
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return []
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "file",
                "type": PortType.UNIVERSAL,
                "display_name": "File Reference",
                "description": "Image file reference"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "file_id": {
                "type": "file_picker",
                "label": "Image File",
                "description": "Select or upload an image",
                "required": True,
                "widget": "file_picker",
                "accept": ".png,.jpg,.jpeg,.webp,.gif,.bmp,.tiff",
                "file_category": "image",
                "max_size_mb": 20
            }
        }
    
    async def execute(self, inputs: NodeExecutionInput) -> Dict[str, Any]:
        """Execute image upload node."""
        try:
            file_id = self.config.get("file_id")
            
            if not file_id:
                raise ValueError("No file selected. Please upload or select an image file.")
            
            from app.database.session import SessionLocal
            from app.database.repositories.file import FileRepository
            
            db = SessionLocal()
            try:
                file_repo = FileRepository(db)
                file_record = file_repo.get_by_id(file_id)
                
                if not file_record:
                    raise ValueError(f"File not found: {file_id}")
                
                file_repo.update_access(file_id)
                
                # Build full path
                full_path = Path("data") / file_record.storage_path
                
                # Detect format
                image_format = Path(file_record.filename).suffix.lstrip('.') or "png"
                
                # Build metadata
                metadata = {
                    "file_id": file_record.id,
                    "filename": file_record.filename,
                    "mime_type": file_record.mime_type,
                    "size_bytes": file_record.file_size_bytes,
                    "url": f"/api/v1/files/{file_record.id}/download",
                    "storage_path": file_record.storage_path,  # Keep for backward compatibility
                    **(file_record.file_metadata or {})
                }
                
                # Use ImageFormatter to create standardized format
                image = ImageFormatter.from_file_path(
                    file_path=str(full_path),
                    format=image_format,
                    metadata=metadata
                )
                
                logger.info(f"🖼️ Image upload node output: {file_record.filename} (MediaFormat standardized)")
                
                return {"file": image}
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Image upload node failed: {e}", exc_info=True)
            raise

