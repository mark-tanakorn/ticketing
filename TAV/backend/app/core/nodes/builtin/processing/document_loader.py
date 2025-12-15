"""
Document Loader Node

Load and extract text from documents using LangChain.
Uses MediaFormat for standardized input/output.
"""

import logging
from typing import Dict, Any, List
from pathlib import Path

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.core.nodes.capabilities import PasswordProtectedFileCapability
from app.core.nodes.multimodal import DocumentFormatter, TextFormatter
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="document_loader",
    category=NodeCategory.PROCESSING,
    name="Document Loader",
    description="Load and extract text from documents using LangChain",
    icon="fa-solid fa-file-lines",
    version="1.0.0"
)
class DocumentLoaderNode(Node, PasswordProtectedFileCapability):
    """
    Document Loader Node - Extract text from documents
    
    Input: File reference (from Document Upload node)
    Output: Extracted text content
    
    Supports: PDF, DOCX, TXT, MD, CSV, JSON
    Uses LangChain document loaders for robust parsing.
    Supports password-protected PDFs and Office documents.
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "file",
                "type": PortType.UNIVERSAL,
                "display_name": "File Reference",
                "description": "File reference from upload node",
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
                "display_name": "Text Content",
                "description": "Extracted text from document"
            },
            {
                "name": "metadata",
                "type": PortType.UNIVERSAL,
                "display_name": "Metadata",
                "description": "Document metadata (pages, author, etc.)"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "extract_pages": {
                "type": "string",
                "widget": "text",
                "label": "Extract Pages (Optional)",
                "description": "Specific pages to extract (e.g., '1,3,5' or '1-3' or 'all')",
                "required": False,
                "default": "all",
                "placeholder": "all",
                "help": "Leave as 'all' to extract entire document, or specify pages like '1,3,5' or '1-3'"
            },
            "chunk_text": {
                "type": "boolean",
                "label": "Chunk Text",
                "description": "Split text into chunks for processing",
                "required": False,
                "default": False,
                "widget": "checkbox"
            },
            "chunk_size": {
                "type": "integer",
                "widget": "number",
                "label": "Chunk Size",
                "description": "Size of text chunks (characters)",
                "required": False,
                "default": 1000,
                "min": 100,
                "max": 10000,
                "visible_when": {"chunk_text": True}
            },
            "chunk_overlap": {
                "type": "integer",
                "widget": "number",
                "label": "Chunk Overlap",
                "description": "Overlap between chunks (characters)",
                "required": False,
                "default": 200,
                "min": 0,
                "max": 1000,
                "visible_when": {"chunk_text": True}
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
        """Execute document loader node."""
        try:
            file_ref = inputs.ports.get("file")
            annotations = self.config.get("annotations")
            
            # Debug logging
            logger.info(f"📋 Document Loader received ports: {list(inputs.ports.keys())}")
            logger.info(f"📋 file_ref type: {type(file_ref)}, value: {str(file_ref)[:200]}")
            if annotations:
                logger.info(f"📋 Received {len(annotations)} pages of annotations")
            
            if not file_ref or not isinstance(file_ref, dict):
                raise ValueError("Invalid file reference. Connect to a Document Upload node.")
            
            # Handle MediaFormat input
            if file_ref.get("type") == "document":
                # It's MediaFormat!
                data_type = file_ref.get("data_type")
                if data_type != "file_path":
                    raise ValueError(f"Document Loader only supports file_path MediaFormat. Got: {data_type}")
                
                file_path_str = file_ref.get("data")
                doc_format = file_ref.get("format", "pdf")
                metadata_base = file_ref.get("metadata", {})
                
            # Handle legacy format
            elif file_ref.get("modality") == "document":
                storage_path = file_ref.get("storage_path")
                if not storage_path:
                    raise ValueError("File reference missing storage_path")
                file_path_str = storage_path
                doc_format = None
                metadata_base = {}
            
            else:
                raise ValueError(f"Expected document file, got type={file_ref.get('type')}, modality={file_ref.get('modality')}")
            
            # Build full path (handle both absolute and relative paths)
            file_path = Path(file_path_str)
            
            # Don't prepend if already absolute or already starts with "data"
            if not file_path.is_absolute():
                # Check if path already starts with "data/"
                if not file_path_str.startswith("data"):
                    base_path = Path("data")
                    file_path = base_path / file_path_str
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            logger.info(f"📄 Loading document: {file_path}")
            
            # Get password if provided
            password = self.resolve_config(inputs, "file_password")
            
            # Decrypt password if it's encrypted (stored in DB)
            if password:
                from app.security.encryption import decrypt_value, is_encrypted
                if is_encrypted(password):
                    try:
                        password = decrypt_value(password)
                        logger.debug("🔓 Decrypted file password")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to decrypt password: {e}")
            
            # Handle password-protected files
            file_to_load = str(file_path)
            temp_decrypted_file = None
            
            try:
                # Check file extension to determine how to handle password
                file_extension = file_path.suffix.lower()
                
                if password and file_extension == ".pdf":
                    # For PDFs, verify password works (PyMuPDF handles it internally in LangChain)
                    # Just validate the password is correct
                    try:
                        test_doc = self.open_pdf_with_password(str(file_path), password)
                        test_doc.close()
                        logger.info(f"🔓 PDF password validated successfully")
                    except ValueError as e:
                        raise ValueError(f"PDF password error: {e}")
                
                elif password and file_extension in [".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt"]:
                    # For Office docs, decrypt to temp file first
                    logger.info(f"🔓 Decrypting password-protected Office document...")
                    temp_decrypted_file = self.open_office_doc_with_password(
                        str(file_path),
                        password
                    )
                    file_to_load = temp_decrypted_file
                
                # Use LangChain document loader
                from app.core.ai.langchain.loaders import DocumentLoader
                
                doc_loader = DocumentLoader()
                
                # Pass password for PDF loading (LangChain PyMuPDF loader supports it)
                if file_extension == ".pdf" and password:
                    documents = doc_loader.load_document(file_to_load, password=password)
                else:
                    documents = doc_loader.load_document(file_to_load)
                
                # Handle page extraction if specified
                extract_pages = self.resolve_config(inputs, "extract_pages", "all")
                
                if extract_pages and extract_pages.strip().lower() != "all" and documents:
                    # Parse page selection
                    total_pages = len(documents)
                    page_indices = self._parse_page_selection(extract_pages, total_pages)
                    
                    # Filter documents to only selected pages
                    filtered_documents = [documents[i] for i in page_indices if i < len(documents)]
                    logger.info(f"📑 Extracted {len(filtered_documents)} pages from {total_pages}: {[i+1 for i in page_indices]}")
                    documents = filtered_documents
                
                # Extract text from documents
                text_content = "\n\n".join([doc.page_content for doc in documents])
                
                # Build metadata
                metadata = {
                    **metadata_base,
                    "num_documents": len(documents),
                    "char_count": len(text_content),
                    "word_count": len(text_content.split())
                }
                
                # Add annotations to metadata if present
                if annotations:
                    metadata["annotations"] = annotations
                    
                    # Append annotation summary to text content for LLM visibility
                    import json
                    annotation_text = "\n\n--- DOCUMENT ANNOTATIONS ---\n"
                    annotation_text += "The user has provided the following visual annotations/instructions for this document:\n"
                    annotation_text += json.dumps(annotations, indent=2)
                    annotation_text += "\n----------------------------\n"
                    
                    text_content += annotation_text
                
                # Add document-specific metadata if available
                if documents and hasattr(documents[0], 'metadata'):
                    metadata["document_metadata"] = documents[0].metadata
                
                # Optional: Chunk text
                if self.config.get("chunk_text", False):
                    chunk_size = self.config.get("chunk_size", 1000)
                    chunk_overlap = self.config.get("chunk_overlap", 200)
                    
                    chunks = doc_loader.split_documents(
                        documents,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap
                    )
                    
                    text_content = [chunk.page_content for chunk in chunks]
                    metadata["num_chunks"] = len(chunks)
                    
                    logger.info(f"✂️ Split into {len(chunks)} chunks")
                
                logger.info(f"✅ Loaded document: {metadata['char_count']} chars, {metadata['word_count']} words (MediaFormat)")
                
                # Output text using TextFormatter for consistency
                text_output = TextFormatter.format(text_content, metadata)
                
                return {
                    "text": text_output,
                    "metadata": metadata
                }
            
            finally:
                # Clean up temporary decrypted file if created
                if temp_decrypted_file:
                    try:
                        Path(temp_decrypted_file).unlink()
                        logger.debug(f"🗑️ Cleaned up temporary decrypted file")
                    except Exception as cleanup_error:
                        logger.warning(f"⚠️ Could not clean up temp file: {cleanup_error}")
            
        except Exception as e:
            logger.error(f"❌ Document loader failed: {e}", exc_info=True)
            raise
    
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
                try:
                    start, end = part.split("-")
                    start = int(start.strip())
                    end = int(end.strip())
                    
                    # Convert to 0-based indices
                    for i in range(start - 1, end):
                        if 0 <= i < total_pages:
                            page_numbers.add(i)
                except ValueError:
                    logger.warning(f"⚠️ Invalid page range: {part}")
                    continue
            else:
                # Single page (e.g., "5")
                try:
                    page_num = int(part) - 1  # Convert to 0-based
                    if 0 <= page_num < total_pages:
                        page_numbers.add(page_num)
                except ValueError:
                    logger.warning(f"⚠️ Invalid page number: {part}")
                    continue
        
        return sorted(list(page_numbers))


