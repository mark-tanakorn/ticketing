"""
Audio Upload Node

Upload audio files (MP3, WAV, M4A, OGG, FLAC).
Outputs standardized MediaFormat for downstream processing nodes.
"""

import logging
from typing import Dict, Any, List
from pathlib import Path

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.core.nodes.multimodal import AudioFormatter
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="audio_upload",
    category=NodeCategory.INPUT,
    name="Audio Upload",
    description="Upload audio files (MP3, WAV, M4A, OGG, FLAC)",
    icon="fa-solid fa-microphone",
    version="1.0.0"
)
class AudioUploadNode(Node):
    """
    Audio Upload Node - Upload audio files
    
    Accepts: MP3, WAV, M4A, OGG, WEBM, FLAC
    Outputs: MediaFormat audio reference
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
                "description": "Audio file reference (MediaFormat)"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "file_id": {
                "type": "file_picker",
                "label": "Audio File",
                "description": "Select or upload an audio file",
                "required": True,
                "widget": "file_picker",
                "accept": ".mp3,.wav,.m4a,.ogg,.webm,.flac",
                "file_category": "audio",
                "max_size_mb": 100
            }
        }
    
    async def execute(self, inputs: NodeExecutionInput) -> Dict[str, Any]:
        """Execute audio upload node."""
        try:
            file_id = self.config.get("file_id")
            
            if not file_id:
                raise ValueError("No file selected. Please upload or select an audio file.")
            
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
                audio_format = Path(file_record.filename).suffix.lstrip('.') or "mp3"
                
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
                
                # Use AudioFormatter to create standardized format
                audio = AudioFormatter.from_file_path(
                    file_path=str(full_path),
                    format=audio_format,
                    metadata=metadata
                )
                
                logger.info(f"🎵 Audio upload node output: {file_record.filename} (MediaFormat standardized)")
                
                return {"file": audio}
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Audio upload node failed: {e}", exc_info=True)
            raise

