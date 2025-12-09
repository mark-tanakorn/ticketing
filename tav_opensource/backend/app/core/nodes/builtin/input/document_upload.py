"""
Document Upload Node

Upload documents (PDF, DOCX, TXT, MD, CSV, JSON).
Outputs standardized MediaFormat for downstream processing nodes.
"""

import logging
from typing import Dict, Any, List
from pathlib import Path

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.core.nodes.multimodal import DocumentFormatter
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="document_upload",
    category=NodeCategory.INPUT,
    name="Document Upload",
    description="Upload documents (PDF, DOCX, TXT, MD, CSV, JSON)",
    icon="fa-solid fa-file-pdf",
    version="1.0.0"
)
class DocumentUploadNode(Node):
    """
    Document Upload Node - Upload document files
    
    Accepts: PDF, DOCX, TXT, MD, CSV, JSON
    Outputs: File reference object
    
    File reference contains:
    - file_id: Unique identifier
    - filename: Original filename
    - storage_path: Server storage path
    - mime_type: File MIME type
    - size_bytes: File size
    - url: Download URL
    - metadata: Additional info (pages, format, etc.)
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return []  # No input ports - file selected in config
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "file",
                "type": PortType.UNIVERSAL,
                "display_name": "File Reference",
                "description": "File reference object with metadata"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "file_id": {
                "type": "file_picker",
                "label": "Document File",
                "description": "Select or upload a document",
                "required": True,
                "widget": "file_picker",
                "accept": ".pdf,.docx,.doc,.txt,.md,.csv,.json,.xlsx,.xls,.xlsm",
                "file_category": "document",
                "max_size_mb": 50
            }
        }
    
    async def execute(self, inputs: NodeExecutionInput) -> Dict[str, Any]:
        """Execute document upload node."""
        try:
            file_id = self.config.get("file_id")
            
            if not file_id:
                raise ValueError("No file selected. Please upload or select a document file.")
            
            # Get file metadata from database
            from app.database.session import SessionLocal
            from app.database.repositories.file import FileRepository
            
            db = SessionLocal()
            try:
                file_repo = FileRepository(db)
                file_record = file_repo.get_by_id(file_id)
                
                if not file_record:
                    raise ValueError(f"File not found: {file_id}")
                
                # Update access tracking
                file_repo.update_access(file_id)
                
                # Build full path for MediaFormat
                full_path = Path("data") / file_record.storage_path
                
                # Detect format
                doc_format = Path(file_record.filename).suffix.lstrip('.') or "pdf"
                
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
                
                # Use DocumentFormatter with FULL path (so downstream nodes don't need to prepend)
                document = DocumentFormatter.from_file_path(
                    file_path=str(full_path),  # Full path: data/uploads/...
                    format=doc_format,
                    metadata=metadata
                )
                
                logger.info(f"📄 Document upload node output: {file_record.filename} (MediaFormat standardized)")
                
                return {"file": document}
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Document upload node failed: {e}", exc_info=True)
            raise
