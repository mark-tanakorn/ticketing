"""
File Converter Node

Converts files between different formats (e.g., PDF to images, DOCX to PDF, etc.).
Primary use case: Converting multi-page PDFs to individual images for vision AI processing.
Uses MediaFormat for standardized output.
"""

import logging
import os
import uuid
from typing import Dict, Any, List, Optional
from pathlib import Path
import fitz  # PyMuPDF

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.core.nodes.capabilities import PasswordProtectedFileCapability
from app.core.nodes.multimodal import ImageFormatter, MediaFormat
from app.schemas.workflow import NodeCategory, PortType
from app.config import settings

logger = logging.getLogger(__name__)


@register_node(
    node_type="file_converter",
    category=NodeCategory.PROCESSING,
    name="File Converter",
    description="Convert files between formats (PDF→Images, etc.)",
    icon="fa-solid fa-file-export",
    version="1.0.0"
)
class FileConverterNode(Node, PasswordProtectedFileCapability):
    """
    File Converter Node - Converts files between different formats.
    
    Features:
    - PDF to Images (PNG/JPEG)
    - Per-page extraction
    - Configurable DPI and format
    - Outputs array of image file paths
    - Supports password-protected PDFs
    
    Use Cases:
    - Converting PDF documents to images for vision AI
    - Splitting multi-page PDFs for individual processing
    - Format conversion for compatibility
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "file",
                "type": PortType.UNIVERSAL,
                "display_name": "Input File",
                "description": "File to convert (PDF, DOCX, etc.)",
                "required": True
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "files",
                "type": PortType.UNIVERSAL,
                "display_name": "Output Files",
                "description": "Array of converted file paths/IDs"
            },
            {
                "name": "first_file",
                "type": PortType.UNIVERSAL,
                "display_name": "First File",
                "description": "First converted file (for convenience)"
            },
            {
                "name": "metadata",
                "type": PortType.UNIVERSAL,
                "display_name": "Metadata",
                "description": "Conversion metadata (page count, format, etc.)"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "conversion_type": {
                "type": "string",
                "widget": "select",
                "label": "Conversion Type",
                "description": "Type of conversion to perform",
                "required": True,
                "default": "pdf_to_images",
                "options": [
                    {"value": "pdf_to_images", "label": "PDF to Images"},
                    {"value": "pdf_to_png", "label": "PDF to PNG (per page)"},
                    {"value": "pdf_to_jpeg", "label": "PDF to JPEG (per page)"}
                ]
            },
            "dpi": {
                "type": "integer",
                "widget": "number",
                "label": "DPI (Resolution)",
                "description": "Image resolution in dots per inch (higher = better quality, larger file)",
                "required": False,
                "default": 300,
                "min": 72,
                "max": 600
            },
            "image_format": {
                "type": "string",
                "widget": "select",
                "label": "Image Format",
                "description": "Output image format",
                "required": False,
                "default": "png",
                "options": [
                    {"value": "png", "label": "PNG (lossless, larger)"},
                    {"value": "jpeg", "label": "JPEG (lossy, smaller)"}
                ]
            },
            "extract_pages": {
                "type": "string",
                "widget": "text",
                "label": "Extract Pages (Optional)",
                "description": "Specific pages to extract (e.g., '1,3,5' or '1-3' or 'all')",
                "required": False,
                "default": "all",
                "placeholder": "all"
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute file conversion"""
        try:
            # Get input file
            file_data = input_data.ports.get("file")
            if not file_data:
                raise ValueError("No input file provided")
            
            # Get configuration
            conversion_type = self.resolve_config(input_data, "conversion_type", "pdf_to_images")
            dpi = self.resolve_config(input_data, "dpi", 300)
            image_format = self.resolve_config(input_data, "image_format", "png")
            extract_pages = self.resolve_config(input_data, "extract_pages", "all")
            
            logger.info(
                f"🔄 File Converter executing:\n"
                f"  Type: {conversion_type}\n"
                f"  DPI: {dpi}\n"
                f"  Format: {image_format}\n"
                f"  Pages: {extract_pages}"
            )
            
            # Get file path from file data
            # Handle both old format and MediaFormat
            if isinstance(file_data, dict):
                # Check if it's MediaFormat
                if file_data.get("type") in ["document", "image", "audio", "video"]:
                    # MediaFormat - extract file path from data
                    if file_data.get("data_type") == "file_path":
                        file_path = file_data.get("data")
                    else:
                        raise ValueError("File Converter only supports file_path data type")
                else:
                    # Old format - extract storage_path
                    file_path = file_data.get("file_path") or file_data.get("path") or file_data.get("storage_path")
                    
                file_id = file_data.get("file_id") or file_data.get("id")
            else:
                file_path = str(file_data)
                file_id = None
            
            # If path is relative, build full path
            # Don't prepend if already starts with "data/"
            if file_path and not os.path.isabs(file_path):
                if not file_path.startswith("data"):
                    base_path = Path("data")
                    file_path = str(base_path / file_path)
            
            if not file_path or not os.path.exists(file_path):
                raise ValueError(f"File not found: {file_path}")
            
            # Determine conversion method
            if conversion_type in ["pdf_to_images", "pdf_to_png", "pdf_to_jpeg"]:
                # Get password if provided (will auto-decrypt and resolve templates)
                password = self.resolve_config(input_data, "file_password")
                
                if password:
                    logger.info(f"🔑 Using password for PDF decryption (length: {len(password)})")
                
                result = await self._convert_pdf_to_images(
                    file_path, dpi, image_format, extract_pages, password
                )
            else:
                raise ValueError(f"Unsupported conversion type: {conversion_type}")
            
            logger.info(
                f"✅ File conversion completed: {len(result['files'])} files generated"
            )
            
            # Add first file for convenience (for single-file workflows)
            if result['files']:
                result['first_file'] = result['files'][0]
            else:
                result['first_file'] = None
            
            return result
            
        except Exception as e:
            logger.error(f"❌ File converter error: {e}", exc_info=True)
            return {
                "files": [],
                "metadata": {"error": str(e)},
                "error": str(e)
            }
    
    async def _convert_pdf_to_images(
        self,
        pdf_path: str,
        dpi: int,
        image_format: str,
        extract_pages: str,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert PDF to images using PyMuPDF.
        
        Args:
            pdf_path: Path to PDF file
            dpi: Resolution in dots per inch
            image_format: Output format (png or jpeg)
            extract_pages: Pages to extract ("all" or "1,3,5" or "1-3")
            password: Optional password for encrypted PDF
        
        Returns:
            Dictionary with files array and metadata
        """
        # Use hardcoded data path (consistent with rest of app)
        temp_dir = Path("data") / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Open PDF with password support
        doc = self.open_pdf_with_password(pdf_path, password)
        total_pages = len(doc)
        
        logger.info(f"📄 PDF opened: {total_pages} pages")
        
        # Parse page selection
        if extract_pages == "all" or not extract_pages:
            page_numbers = list(range(total_pages))
        else:
            page_numbers = self._parse_page_selection(extract_pages, total_pages)
        
        logger.info(f"📑 Extracting {len(page_numbers)} pages: {page_numbers}")
        
        # Convert pages to images
        output_files = []
        zoom = dpi / 72  # Convert DPI to zoom factor (72 is default PDF DPI)
        matrix = fitz.Matrix(zoom, zoom)
        
        for page_idx in page_numbers:
            try:
                page = doc.load_page(page_idx)
                
                # Render page to pixmap (image)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                
                # Generate unique filename
                file_id = str(uuid.uuid4())
                ext = "png" if image_format == "png" else "jpg"
                filename = f"{file_id}_page_{page_idx + 1}.{ext}"
                output_path = temp_dir / filename
                
                # Save image
                if image_format == "png":
                    pix.save(output_path)
                else:
                    # Convert to RGB for JPEG (PyMuPDF default is RGBA)
                    if pix.alpha:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    pix.save(output_path, "jpeg")
                
                # Use ImageFormatter to create standardized MediaFormat
                image_metadata = {
                    "file_id": file_id,
                    "filename": filename,
                    "page_number": page_idx + 1,
                    "width": pix.width,
                    "height": pix.height,
                    "source_page": page_idx + 1,
                    "source_pdf": os.path.basename(pdf_path)
                }
                
                image_media = ImageFormatter.from_file_path(
                    file_path=str(output_path),
                    format=image_format,
                    metadata=image_metadata
                )
                
                output_files.append(image_media)
                
                logger.info(f"✅ Page {page_idx + 1} converted: {filename} (MediaFormat)")
                
            except Exception as e:
                logger.error(f"❌ Error converting page {page_idx + 1}: {e}")
                continue
        
        doc.close()
        
        # Build metadata
        metadata = {
            "total_pages": total_pages,
            "extracted_pages": len(output_files),
            "dpi": dpi,
            "format": image_format,
            "source_file": os.path.basename(pdf_path)
        }
        
        return {
            "files": output_files,
            "metadata": metadata
        }
    
    def _parse_page_selection(self, selection: str, total_pages: int) -> List[int]:
        """
        Parse page selection string.
        
        Examples:
            "1,3,5" → [0, 2, 4]
            "1-3" → [0, 1, 2]
            "1,3-5,7" → [0, 2, 3, 4, 6]
        
        Args:
            selection: Page selection string
            total_pages: Total number of pages
        
        Returns:
            List of page indices (0-based)
        """
        page_numbers = set()
        
        for part in selection.split(","):
            part = part.strip()
            
            if "-" in part:
                # Range (e.g., "1-3")
                start, end = part.split("-")
                start = int(start.strip())
                end = int(end.strip())
                
                # Convert to 0-based indices
                for i in range(start - 1, end):
                    if 0 <= i < total_pages:
                        page_numbers.add(i)
            else:
                # Single page (e.g., "5")
                page_num = int(part) - 1  # Convert to 0-based
                if 0 <= page_num < total_pages:
                    page_numbers.add(page_num)
        
        return sorted(list(page_numbers))

