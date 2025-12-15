"""
Document Merger Node - Combine multiple documents/images into one

Merges PDFs, images, or mixed formats into a single PDF document.
Essential for workflows that append new documents (e.g., updated passport).
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import io

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="document_merger",
    category=NodeCategory.PROCESSING,
    name="Document Merger",
    description="Merge multiple documents/images into a single PDF. Perfect for appending updated documents.",
    icon="fa-solid fa-file-zipper",
    version="1.0.0"
)
class DocumentMergerNode(Node):
    """
    Document Merger Node - Combine Documents/Images
    
    **Purpose:**
    Combine multiple documents or images into a single PDF file.
    Essential for workflows where new documents need to be appended
    to existing ones (e.g., adding updated passport to application).
    
    **Supported Inputs:**
    - PDF files
    - Images (JPG, PNG, GIF, WebP)
    - Mixed (PDF + images)
    
    **Output:**
    - Single merged PDF file
    - File reference for downstream processing
    
    **Use Cases:**
    1. **Document Resubmission Workflows:**
       - Original application (PDF) + New passport (image) → Merged PDF
       - Loop back to document loader for re-analysis
    
    2. **Multi-Document Compilation:**
       - Form 1 + Form 2 + Form 3 → Complete application
    
    3. **Image Consolidation:**
       - Multiple images → Single PDF document
    
    **How It Works:**
    - Option A (Batch): Connect "documents_array" to File Trigger batch output
    - Option B (Individual): Connect document1, document2, etc. separately
    - Output: Merged PDF with all pages
    - Maintains page order
    - Preserves image quality
    
    **Technical Details:**
    - Uses PyPDF2 for PDF merging
    - Uses Pillow (PIL) for image conversion
    - Images converted to PDF before merging
    - Output always PDF format
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "documents_array",
                "type": PortType.UNIVERSAL,
                "display_name": "Documents Array (Batch)",
                "description": "Array of documents to merge (from File Trigger batch mode)",
                "required": False
            },
            {
                "name": "document1",
                "type": PortType.UNIVERSAL,
                "display_name": "Document 1 (Primary)",
                "description": "First document (original/base document)",
                "required": False
            },
            {
                "name": "document2",
                "type": PortType.UNIVERSAL,
                "display_name": "Document 2",
                "description": "Second document to append",
                "required": False
            },
            {
                "name": "document3",
                "type": PortType.UNIVERSAL,
                "display_name": "Document 3",
                "description": "Third document to append (optional)",
                "required": False
            },
            {
                "name": "document4",
                "type": PortType.UNIVERSAL,
                "display_name": "Document 4",
                "description": "Fourth document to append (optional)",
                "required": False
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "file",
                "type": PortType.UNIVERSAL,
                "display_name": "Merged File",
                "description": "Combined PDF document (compatible with Document Loader)"
            },
            {
                "name": "merged_document",
                "type": PortType.UNIVERSAL,
                "display_name": "Merged Document",
                "description": "Combined PDF document with all pages (legacy output)"
            },
            {
                "name": "metadata",
                "type": PortType.UNIVERSAL,
                "display_name": "Metadata",
                "description": "Merge operation metadata (page count, file size, etc.)"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "output_filename": {
                "type": "string",
                "label": "Output Filename",
                "description": "Name for merged PDF (without extension)",
                "required": False,
                "default": "merged_document_{timestamp}",
                "placeholder": "merged_application",
                "help": "Use {timestamp} for auto-generated timestamp"
            },
            "image_quality": {
                "type": "select",
                "label": "Image Quality",
                "description": "Quality for images converted to PDF",
                "required": False,
                "default": "high",
                "options": [
                    {"label": "Low (faster, smaller file)", "value": "low"},
                    {"label": "Medium", "value": "medium"},
                    {"label": "High (slower, larger file)", "value": "high"}
                ]
            },
            "page_size": {
                "type": "select",
                "label": "Page Size",
                "description": "Page size for image-to-PDF conversion",
                "required": False,
                "default": "A4",
                "options": [
                    {"label": "A4 (210x297mm)", "value": "A4"},
                    {"label": "Letter (8.5x11in)", "value": "Letter"},
                    {"label": "Legal (8.5x14in)", "value": "Legal"},
                    {"label": "Auto (fit to image)", "value": "auto"}
                ]
            },
            "preserve_metadata": {
                "type": "boolean",
                "label": "Preserve Metadata",
                "description": "Keep metadata from source documents",
                "required": False,
                "default": True
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute document merger"""
        try:
            logger.info(f"📄 Document Merger executing: {self.node_id}")
            
            # Collect input documents
            documents = []
            
            # Check if array input is provided (from File Trigger batch mode)
            documents_array = input_data.ports.get("documents_array")
            if documents_array:
                logger.info(f"📦 Batch mode: Processing documents array")
                
                # Handle File Trigger batch format: {"files": [...], "file_count": N}
                if isinstance(documents_array, dict) and "files" in documents_array:
                    files_list = documents_array.get("files", [])
                    logger.info(f"  ✓ Found {len(files_list)} files in batch")
                    for idx, file_data in enumerate(files_list):
                        documents.append({"port": f"array[{idx}]", "data": file_data})
                
                # Handle direct array format: [file1, file2, file3]
                elif isinstance(documents_array, list):
                    logger.info(f"  ✓ Found {len(documents_array)} files in array")
                    for idx, file_data in enumerate(documents_array):
                        documents.append({"port": f"array[{idx}]", "data": file_data})
                
                else:
                    logger.warning(f"⚠️ Unexpected array format: {type(documents_array)}")
            
            # If no array input, fall back to individual document ports
            if not documents:
                logger.info(f"📄 Individual mode: Checking document ports")
                for i in range(1, 5):
                    port_name = f"document{i}"
                    doc_data = input_data.ports.get(port_name)
                    if doc_data:
                        documents.append({"port": port_name, "data": doc_data})
                        logger.info(f"  ✓ {port_name}: Available")
            
            if not documents:
                raise ValueError("At least one document is required (connect documents_array or individual document ports)")
            
            logger.info(f"📊 Merging {len(documents)} document(s)")
            
            # Get configuration
            output_filename = self.resolve_config(input_data, "output_filename", "merged_document_{timestamp}")
            image_quality = self.resolve_config(input_data, "image_quality", "high")
            page_size = self.resolve_config(input_data, "page_size", "A4")
            preserve_metadata = self.resolve_config(input_data, "preserve_metadata", True)
            
            # Replace timestamp placeholder
            if "{timestamp}" in output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = output_filename.replace("{timestamp}", timestamp)
            
            # Ensure .pdf extension
            if not output_filename.endswith(".pdf"):
                output_filename = f"{output_filename}.pdf"
            
            # Process each document
            pdf_files = []
            total_pages = 0
            
            for doc_info in documents:
                doc_data = doc_info["data"]
                port_name = doc_info["port"]
                
                # Extract file path from document data
                file_path = self._extract_file_path(doc_data)
                if not file_path:
                    logger.warning(f"⚠️ Could not extract file path from {port_name}, skipping")
                    continue
                
                logger.info(f"📎 Processing {port_name}: {file_path}")
                
                # Determine file type
                file_path_obj = Path(file_path)
                
                # Don't prepend 'data' if path already starts with 'data'
                if not file_path_obj.is_absolute():
                    if not str(file_path).startswith("data"):
                        file_path_obj = Path("data") / file_path
                
                if not file_path_obj.exists():
                    logger.error(f"❌ File not found: {file_path_obj}")
                    continue
                
                # Handle based on file type
                if file_path_obj.suffix.lower() == ".pdf":
                    # Already PDF, add to list
                    pdf_files.append(str(file_path_obj))
                    page_count = self._count_pdf_pages(str(file_path_obj))
                    total_pages += page_count
                    logger.info(f"  📄 PDF: {page_count} page(s)")
                
                elif file_path_obj.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
                    # Image, convert to PDF first
                    temp_pdf = await self._image_to_pdf(
                        str(file_path_obj),
                        image_quality=image_quality,
                        page_size=page_size
                    )
                    if temp_pdf:
                        pdf_files.append(temp_pdf)
                        total_pages += 1
                        logger.info(f"  🖼️ Image → PDF: 1 page")
                    else:
                        logger.warning(f"  ⚠️ Failed to convert image to PDF")
                
                else:
                    logger.warning(f"  ⚠️ Unsupported file type: {file_path_obj.suffix}")
            
            if not pdf_files:
                raise ValueError("No valid documents to merge (all files failed processing)")
            
            # Merge PDFs
            logger.info(f"🔗 Merging {len(pdf_files)} PDF file(s)...")
            merged_pdf_path = await self._merge_pdfs(
                pdf_files=pdf_files,
                output_filename=output_filename,
                preserve_metadata=preserve_metadata
            )
            
            # Get file info
            merged_path = Path(merged_pdf_path)
            file_size = merged_path.stat().st_size
            
            logger.info(
                f"✅ Documents merged successfully:\n"
                f"  Output: {output_filename}\n"
                f"  Pages: {total_pages}\n"
                f"  Size: {file_size / 1024:.1f} KB"
            )
            
            # Build file reference output
            output_doc = {
                "file_id": None,  # Could generate UUID if needed
                "filename": output_filename,
                "storage_path": str(merged_pdf_path).replace("data/", ""),
                "file_path": str(merged_pdf_path),
                "mime_type": "application/pdf",
                "size_bytes": file_size,
                "modality": "document",
                "metadata": {
                    "page_count": total_pages,
                    "source_documents": len(documents),
                    "format": "pdf"
                }
            }
            
            # Build metadata
            metadata = {
                "merged_files": len(documents),
                "total_pages": total_pages,
                "output_filename": output_filename,
                "file_size_bytes": file_size,
                "file_size_kb": file_size / 1024,
                "image_quality": image_quality,
                "page_size": page_size
            }
            
            return {
                "file": output_doc,  # Primary output (compatible with Document Loader)
                "merged_document": output_doc,  # Legacy output (backward compatibility)
                "metadata": metadata
            }
            
        except Exception as e:
            error_msg = f"Document merger error: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                "merged_document": None,
                "metadata": {"error": error_msg}
            }
    
    def _extract_file_path(self, doc_data: Any) -> Optional[str]:
        """Extract file path from various document data formats"""
        if isinstance(doc_data, str):
            return doc_data
        
        if isinstance(doc_data, dict):
            # Try various path keys
            return (
                doc_data.get("file_path") or
                doc_data.get("storage_path") or
                doc_data.get("path") or
                doc_data.get("data")  # MediaFormat might have data as path
            )
        
        if isinstance(doc_data, list) and len(doc_data) > 0:
            # Array of files, take first
            return self._extract_file_path(doc_data[0])
        
        return None
    
    def _count_pdf_pages(self, pdf_path: str) -> int:
        """Count pages in PDF"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            return page_count
        except Exception as e:
            logger.warning(f"Could not count PDF pages: {e}")
            return 1
    
    async def _image_to_pdf(
        self,
        image_path: str,
        image_quality: str = "high",
        page_size: str = "A4"
    ) -> Optional[str]:
        """Convert image to PDF"""
        try:
            from PIL import Image
            
            # Load image
            img = Image.open(image_path)
            
            # Convert RGBA to RGB if needed
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if needed based on quality
            if image_quality == "low":
                max_dimension = 1200
            elif image_quality == "medium":
                max_dimension = 2000
            else:  # high
                max_dimension = 3000
            
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save as PDF
            temp_dir = Path("data/temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            pdf_path = temp_dir / f"img_to_pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{Path(image_path).stem}.pdf"
            img.save(str(pdf_path), "PDF", resolution=100.0)
            
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"Failed to convert image to PDF: {e}", exc_info=True)
            return None
    
    async def _merge_pdfs(
        self,
        pdf_files: List[str],
        output_filename: str,
        preserve_metadata: bool = True
    ) -> str:
        """Merge multiple PDFs into one using PyMuPDF"""
        try:
            import fitz  # PyMuPDF
            
            # Create new PDF document
            merged_doc = fitz.open()
            
            # Add all PDFs
            for pdf_path in pdf_files:
                try:
                    src_doc = fitz.open(pdf_path)
                    merged_doc.insert_pdf(src_doc)
                    src_doc.close()
                    logger.debug(f"  ✓ Added: {Path(pdf_path).name}")
                except Exception as e:
                    logger.error(f"  ✗ Failed to add {pdf_path}: {e}")
            
            # Write merged PDF
            output_dir = Path("data/uploads")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = output_dir / output_filename
            
            # Save merged PDF
            merged_doc.save(str(output_path))
            merged_doc.close()
            
            logger.info(f"✅ Merged PDF written: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to merge PDFs: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    print("✅ Document Merger Node loaded")

