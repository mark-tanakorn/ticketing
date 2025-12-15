"""
Multimodal Data Formatters

Utilities for handling different media types in workflow nodes.
Provides standardized formats for text, images, audio, video, and documents.

=== STANDARDIZED FORMAT (MediaFormat) ===

ALL data types now use the same structure:

{
    "type": "text|image|audio|video|document",
    "format": "plain|markdown|png|jpg|mp3|wav|mp4|pdf|...",
    "data": <actual_content>,
    "data_type": "string|base64|url|file_path",
    "metadata": {...}
}

Examples:
    Text:
        {"type": "text", "format": "plain", "data": "Hello world", "data_type": "string"}
    
    Image:
        {"type": "image", "format": "png", "data": "iVBORw0KG...", "data_type": "base64"}
        {"type": "image", "format": "jpg", "data": "/path/to/file.jpg", "data_type": "file_path"}
    
    Audio:
        {"type": "audio", "format": "mp3", "data": "/path/to/audio.mp3", "data_type": "file_path"}

=== USAGE ===

For nodes that PRODUCE data:
    from app.core.nodes.multimodal import TextFormatter, ImageFormatter, AudioFormatter
    
    # Text output
    output = TextFormatter.format("Hello world")
    
    # Image output
    output = ImageFormatter.from_file_path("/path/to/image.jpg")

For nodes that CONSUME data:
    from app.core.nodes.multimodal import extract_content
    
    # Works for ALL types (text, image, audio, video, document)
    content = extract_content(input_data)

=== BACKWARD COMPATIBILITY ===

Old text format is still supported but deprecated:
    {"type": "text", "content": "...", "metadata": {...}}  # OLD - will show warning

Use extract_content() to handle both old and new formats automatically.
"""

import base64
import mimetypes
from typing import Dict, Any, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# ==================== Standard Format Definitions ====================

class MediaFormat:
    """
    Standard format for multimodal data.
    
    All media (image, audio, video, document) uses this structure:
    {
        "type": "image|audio|video|document",
        "format": "png|jpg|mp3|wav|mp4|pdf|...",
        "data": <base64_string|url|file_path>,
        "data_type": "base64|url|file_path",
        "metadata": {...}
    }
    """
    
    def __init__(
        self,
        media_type: str,
        format: str,
        data: str,
        data_type: str = "base64",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.media_type = media_type
        self.format = format
        self.data = data
        self.data_type = data_type
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.media_type,
            "format": self.format,
            "data": self.data,
            "data_type": self.data_type,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MediaFormat":
        """Create from dictionary"""
        return cls(
            media_type=data["type"],
            format=data["format"],
            data=data["data"],
            data_type=data.get("data_type", "base64"),
            metadata=data.get("metadata", {})
        )


# ==================== Formatters ====================

class TextFormatter:
    """Format text data"""
    
    @staticmethod
    def format(
        text: str, 
        metadata: Optional[Dict[str, Any]] = None,
        format_type: str = "plain"
    ) -> Dict[str, Any]:
        """
        Format text data in standardized MediaFormat.
        
        Args:
            text: Text content
            metadata: Optional metadata (encoding, language, page_count, etc.)
            format_type: Text format type ("plain", "markdown", "html", etc.)
        
        Returns:
            Standardized format matching MediaFormat:
            {
                "type": "text",
                "format": "plain|markdown|html",
                "data": "...",
                "data_type": "string",
                "metadata": {...}
            }
        """
        return {
            "type": "text",
            "format": format_type,
            "data": text,
            "data_type": "string",
            "metadata": metadata or {
                "char_count": len(text),
                "word_count": len(text.split()),
                "line_count": text.count('\n') + 1
            }
        }


class ImageFormatter:
    """Format image data"""
    
    @staticmethod
    def from_base64(
        base64_data: str,
        format: str = "png",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format image from base64 string.
        
        Args:
            base64_data: Base64 encoded image
            format: Image format (png, jpg, webp, etc.)
            metadata: Optional metadata (width, height, etc.)
        
        Returns:
            MediaFormat dictionary
        """
        return MediaFormat(
            media_type="image",
            format=format,
            data=base64_data,
            data_type="base64",
            metadata=metadata or {}
        ).to_dict()
    
    @staticmethod
    def from_url(
        url: str,
        format: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format image from URL.
        
        Args:
            url: Image URL
            format: Image format (auto-detected if not provided)
            metadata: Optional metadata
        
        Returns:
            MediaFormat dictionary
        """
        if not format:
            # Try to detect from URL extension
            format = Path(url).suffix.lstrip('.') or "png"
        
        return MediaFormat(
            media_type="image",
            format=format,
            data=url,
            data_type="url",
            metadata=metadata or {}
        ).to_dict()
    
    @staticmethod
    def from_file_path(
        file_path: str,
        format: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format image from file path.
        
        Args:
            file_path: Path to image file
            format: Image format (auto-detected if not provided)
            metadata: Optional metadata
        
        Returns:
            MediaFormat dictionary
        """
        if not format:
            format = Path(file_path).suffix.lstrip('.') or "png"
        
        return MediaFormat(
            media_type="image",
            format=format,
            data=file_path,
            data_type="file_path",
            metadata=metadata or {}
        ).to_dict()


class AudioFormatter:
    """Format audio data"""
    
    @staticmethod
    def from_base64(
        base64_data: str,
        format: str = "mp3",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format audio from base64"""
        return MediaFormat(
            media_type="audio",
            format=format,
            data=base64_data,
            data_type="base64",
            metadata=metadata or {}
        ).to_dict()
    
    @staticmethod
    def from_url(
        url: str,
        format: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format audio from URL"""
        if not format:
            format = Path(url).suffix.lstrip('.') or "mp3"
        
        return MediaFormat(
            media_type="audio",
            format=format,
            data=url,
            data_type="url",
            metadata=metadata or {}
        ).to_dict()
    
    @staticmethod
    def from_file_path(
        file_path: str,
        format: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format audio from file path"""
        if not format:
            format = Path(file_path).suffix.lstrip('.') or "mp3"
        
        return MediaFormat(
            media_type="audio",
            format=format,
            data=file_path,
            data_type="file_path",
            metadata=metadata or {}
        ).to_dict()


class VideoFormatter:
    """Format video data"""
    
    @staticmethod
    def from_url(
        url: str,
        format: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format video from URL"""
        if not format:
            format = Path(url).suffix.lstrip('.') or "mp4"
        
        return MediaFormat(
            media_type="video",
            format=format,
            data=url,
            data_type="url",
            metadata=metadata or {}
        ).to_dict()
    
    @staticmethod
    def from_file_path(
        file_path: str,
        format: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format video from file path"""
        if not format:
            format = Path(file_path).suffix.lstrip('.') or "mp4"
        
        return MediaFormat(
            media_type="video",
            format=format,
            data=file_path,
            data_type="file_path",
            metadata=metadata or {}
        ).to_dict()


class DocumentFormatter:
    """Format document data"""
    
    @staticmethod
    def from_base64(
        base64_data: str,
        format: str = "pdf",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format document from base64"""
        return MediaFormat(
            media_type="document",
            format=format,
            data=base64_data,
            data_type="base64",
            metadata=metadata or {}
        ).to_dict()
    
    @staticmethod
    def from_url(
        url: str,
        format: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format document from URL"""
        if not format:
            format = Path(url).suffix.lstrip('.') or "pdf"
        
        return MediaFormat(
            media_type="document",
            format=format,
            data=url,
            data_type="url",
            metadata=metadata or {}
        ).to_dict()
    
    @staticmethod
    def from_file_path(
        file_path: str,
        format: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format document from file path"""
        if not format:
            format = Path(file_path).suffix.lstrip('.') or "pdf"
        
        return MediaFormat(
            media_type="document",
            format=format,
            data=file_path,
            data_type="file_path",
            metadata=metadata or {}
        ).to_dict()


# ==================== Helper Functions ====================

def auto_format_media(
    data: Union[str, bytes, Dict[str, Any]],
    media_type: Optional[str] = None,
    format: Optional[str] = None
) -> Dict[str, Any]:
    """
    Auto-detect and format media data.
    
    Args:
        data: Media data (base64, URL, file path, or dict)
        media_type: Media type (image, audio, video, document) - auto-detected if not provided
        format: Media format (png, mp3, etc.) - auto-detected if not provided
    
    Returns:
        MediaFormat dictionary
    
    Example:
        # From URL
        result = auto_format_media("https://example.com/image.png")
        
        # From file path
        result = auto_format_media("/path/to/audio.mp3")
        
        # From base64
        result = auto_format_media("iVBORw0KG...", media_type="image", format="png")
    """
    # If already formatted, return as-is
    if isinstance(data, dict) and "type" in data and "data" in data:
        return data
    
    # If bytes, convert to base64
    if isinstance(data, bytes):
        data = base64.b64encode(data).decode('utf-8')
    
    # Detect data type
    if data.startswith("http://") or data.startswith("https://"):
        data_type = "url"
        # Try to detect media type from URL
        if not media_type:
            ext = Path(data).suffix.lstrip('.').lower()
            if ext in ["png", "jpg", "jpeg", "gif", "webp", "bmp"]:
                media_type = "image"
            elif ext in ["mp3", "wav", "ogg", "m4a", "flac"]:
                media_type = "audio"
            elif ext in ["mp4", "webm", "mov", "avi"]:
                media_type = "video"
            elif ext in ["pdf", "docx", "doc", "txt"]:
                media_type = "document"
            else:
                media_type = "document"  # Default
        
        if not format:
            format = Path(data).suffix.lstrip('.') or "unknown"
    
    elif Path(data).exists() if len(data) < 500 else False:  # File path check (avoid checking long base64 strings)
        data_type = "file_path"
        if not format:
            format = Path(data).suffix.lstrip('.') or "unknown"
        
        if not media_type:
            # Detect from MIME type
            mime_type, _ = mimetypes.guess_type(data)
            if mime_type:
                if mime_type.startswith("image/"):
                    media_type = "image"
                elif mime_type.startswith("audio/"):
                    media_type = "audio"
                elif mime_type.startswith("video/"):
                    media_type = "video"
                else:
                    media_type = "document"
            else:
                media_type = "document"
    
    else:
        # Assume base64
        data_type = "base64"
        if not media_type:
            media_type = "image"  # Default to image
        if not format:
            format = "png"  # Default format
    
    return MediaFormat(
        media_type=media_type,
        format=format,
        data=data,
        data_type=data_type
    ).to_dict()


def is_media_format(data: Any) -> bool:
    """
    Check if data is in standardized MediaFormat structure.
    
    Now includes TEXT (after standardization).
    """
    if not isinstance(data, dict):
        return False
    
    required_fields = {"type", "format", "data", "data_type"}
    return required_fields.issubset(data.keys())


def extract_media_data(media: Dict[str, Any]) -> str:
    """Extract raw data from MediaFormat"""
    if is_media_format(media):
        return media["data"]
    return media


def extract_content(data: Any) -> Union[str, Dict[str, Any]]:
    """
    Universal content extractor for TAV's standardized formats.
    
    After standardization, ALL types use MediaFormat:
    - Text: {"type": "text", "format": "plain", "data": "...", "data_type": "string"}
    - Image: {"type": "image", "format": "png", "data": "...", "data_type": "base64|url|file_path"}
    - Audio: {"type": "audio", "format": "mp3", "data": "...", "data_type": "base64|url|file_path"}
    - Video: {"type": "video", "format": "mp4", "data": "...", "data_type": "url|file_path"}
    - Document: {"type": "document", "format": "pdf", "data": "...", "data_type": "base64|url|file_path"}
    
    Args:
        data: Input data in any format
        
    Returns:
        Extracted content/data
        
    Example:
        >>> # NEW standardized format (all types)
        >>> extract_content({"type": "text", "format": "plain", "data": "Hello", "data_type": "string"})
        "Hello"
        
        >>> extract_content({"type": "image", "data": "base64...", "data_type": "base64", "format": "png"})
        "base64..."
        
        >>> # OLD text format (backward compatibility)
        >>> extract_content({"type": "text", "content": "Hello"})
        "Hello"
        
        >>> # Plain string
        >>> extract_content("plain string")
        "plain string"
    """
    if isinstance(data, dict):
        # NEW standardized MediaFormat (all types including text)
        if is_media_format(data):
            return data["data"]
        
        # OLD text format (backward compatibility - DEPRECATED)
        elif "type" in data and data["type"] == "text" and "content" in data:
            logger.debug("⚠️ Using legacy text format with 'content' key - please update to standardized format")
            return data["content"]
        
        # Legacy 'text' key (really old workflows)
        elif "text" in data:
            return data["text"]
        
        # Last resort: stringify the dict
        else:
            return str(data)
    
    elif isinstance(data, (list, tuple)):
        # If it's a list, join the items
        return " ".join(str(item) for item in data)
    
    else:
        # Return as-is (string, int, etc.)
        return str(data) if not isinstance(data, str) else data

