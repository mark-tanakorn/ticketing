"""
Audio Transcriber Node

Transcribe audio to text using Whisper or other transcription services.
"""

import logging
from typing import Dict, Any, List
from pathlib import Path

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="audio_transcriber",
    category=NodeCategory.PROCESSING,
    name="Audio Transcriber",
    description="Transcribe audio to text using Whisper or other transcription services",
    icon="fa-solid fa-closed-captioning",
    version="1.0.0"
)
class AudioTranscriberNode(Node):
    """
    Audio Transcriber Node - Convert audio to text
    
    Input: File reference (from Audio Upload node)
    Output: Transcribed text
    
    Uses OpenAI Whisper API or local Whisper model.
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "file",
                "type": PortType.UNIVERSAL,
                "display_name": "File Reference",
                "description": "Audio file reference from upload node",
                "required": True
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "text",
                "type": PortType.UNIVERSAL,
                "display_name": "Transcription",
                "description": "Transcribed text from audio"
            },
            {
                "name": "metadata",
                "type": PortType.UNIVERSAL,
                "display_name": "Metadata",
                "description": "Transcription metadata (language, confidence, etc.)"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "language": {
                "type": "select",
                "widget": "select",
                "label": "Language",
                "description": "Audio language (auto-detect if not specified)",
                "required": False,
                "default": "auto",
                "options": [
                    {"label": "Auto Detect", "value": "auto"},
                    {"label": "English", "value": "en"},
                    {"label": "Spanish", "value": "es"},
                    {"label": "French", "value": "fr"},
                    {"label": "German", "value": "de"},
                    {"label": "Chinese", "value": "zh"},
                    {"label": "Japanese", "value": "ja"}
                ]
            },
            "model": {
                "type": "select",
                "widget": "select",
                "label": "Model",
                "description": "Transcription model",
                "required": False,
                "default": "whisper-1",
                "options": [
                    {"label": "Whisper (API)", "value": "whisper-1"},
                    {"label": "Local Whisper (Not implemented)", "value": "local"}
                ]
            }
        }
    
    async def execute(self, inputs: NodeExecutionInput) -> Dict[str, Any]:
        """Execute audio transcriber node."""
        try:
            file_ref = inputs.ports.get("file")
            
            if not file_ref or not isinstance(file_ref, dict):
                raise ValueError("Invalid file reference. Connect to an Audio Upload node.")
            
            if file_ref.get("modality") != "audio":
                raise ValueError(f"Expected audio file, got {file_ref.get('modality')}")
            
            storage_path = file_ref.get("storage_path")
            if not storage_path:
                raise ValueError("File reference missing storage_path")
            
            # Build full path (don't prepend if already starts with "data")
            if storage_path.startswith("data"):
                file_path = Path(storage_path)
            else:
                base_path = Path("data")
                file_path = base_path / storage_path
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            logger.info(f"🎵 Transcribing audio: {file_path}")
            
            model = self.config.get("model", "whisper-1")
            language = self.config.get("language", "auto")
            
            # For now, return placeholder
            # TODO: Implement actual Whisper transcription
            transcription = f"[Audio transcription placeholder for {file_ref.get('filename')}]\n\n"
            transcription += "Note: Whisper transcription not yet implemented. "
            transcription += "Connect OpenAI API with Whisper model to enable transcription."
            
            metadata = {
                "filename": file_ref.get("filename"),
                "file_size": file_ref.get("size_bytes"),
                "model": model,
                "language": language if language != "auto" else "detected",
                "status": "placeholder"
            }
            
            logger.warning(f"⚠️ Audio transcription not fully implemented yet")
            
            return {
                "text": transcription,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Audio transcriber failed: {e}", exc_info=True)
            raise

