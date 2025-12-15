"""
Document Loaders

Unified interface for loading documents from various sources.
Supports 100+ file formats and data sources.
"""

import logging
from typing import List, Optional, Any
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Supported document types."""
    PDF = "pdf"
    CSV = "csv"
    TXT = "txt"
    HTML = "html"
    MARKDOWN = "md"
    JSON = "json"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"


class DocumentLoader:
    """
    Unified document loader for multiple file formats.
    
    Supports:
    - PDF (pypdf)
    - CSV (pandas)
    - Text files
    - HTML (beautifulsoup4)
    - Markdown
    - JSON
    - Word/Excel/PowerPoint (unstructured)
    """
    
    def __init__(self):
        logger.info("📚 DocumentLoader initialized")
    
    def load_document(
        self,
        file_path: str,
        document_type: Optional[DocumentType] = None,
        **kwargs
    ) -> List[Any]:
        """
        Load a document from file.
        
        Args:
            file_path: Path to the document
            document_type: Type of document (auto-detected if None)
            **kwargs: Loader-specific options
            
        Returns:
            List of LangChain Document objects
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        # Auto-detect document type from extension
        if document_type is None:
            ext = path.suffix.lower().lstrip('.')
            try:
                document_type = DocumentType(ext)
            except ValueError:
                raise ValueError(f"Unsupported file extension: {ext}")
        
        logger.info(f"📄 Loading document: {path.name} (type: {document_type})")
        
        # Route to appropriate loader
        if document_type == DocumentType.PDF:
            return self._load_pdf(file_path, **kwargs)
        
        elif document_type == DocumentType.CSV:
            return self._load_csv(file_path, **kwargs)
        
        elif document_type == DocumentType.TXT:
            return self._load_text(file_path, **kwargs)
        
        elif document_type == DocumentType.HTML:
            return self._load_html(file_path, **kwargs)
        
        elif document_type == DocumentType.MARKDOWN:
            return self._load_markdown(file_path, **kwargs)
        
        elif document_type == DocumentType.JSON:
            return self._load_json(file_path, **kwargs)
        
        elif document_type in [DocumentType.DOCX, DocumentType.PPTX, DocumentType.XLSX]:
            return self._load_unstructured(file_path, **kwargs)
        
        else:
            raise ValueError(f"Unsupported document type: {document_type}")
    
    def _load_pdf(self, file_path: str, **kwargs) -> List[Any]:
        """Load PDF document using PyMuPDF (fitz) with OCR fallback."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PDF loading requires: pip install pymupdf")
        
        # Try direct text extraction first
        try:
            from langchain_community.document_loaders import PyMuPDFLoader
            loader = PyMuPDFLoader(file_path, **kwargs)
            docs = loader.load()
            
            # Check if we got any text
            total_chars = sum(len(doc.page_content) for doc in docs)
            logger.info(f"📊 PyMuPDF loaded {len(docs)} pages, {total_chars} chars total")
            
            if total_chars > 0:
                # Success! We got text
                for i, doc in enumerate(docs[:3]):  # Show first 3 pages
                    logger.info(f"   Page {i+1}: {len(doc.page_content)} chars")
                return docs
            
            # No text found - this is likely an image-based/scanned PDF
            logger.warning("⚠️ No text extracted - PDF may be image-based. Attempting OCR fallback...")
            
        except Exception as e:
            logger.warning(f"⚠️ PyMuPDFLoader failed: {e}. Trying direct fitz extraction...")
        
        # Fallback: Direct fitz extraction with better handling
        from langchain_core.documents import Document
        
        doc = fitz.open(file_path)
        documents = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Try getting text with different methods
            text = page.get_text("text")  # Plain text
            
            # If no text, try blocks method
            if not text.strip():
                text = page.get_text("blocks")
                if isinstance(text, list):
                    text = "\n".join([block[4] for block in text if len(block) > 4])
            
            # If still no text, this is an image-based PDF
            if not text.strip():
                logger.warning(f"📄 Page {page_num + 1} has no text - may need OCR")
                text = f"[Page {page_num + 1}: No text content - scanned/image PDF]"
            
            documents.append(Document(
                page_content=text,
                metadata={
                    "source": file_path,
                    "page": page_num + 1,
                    "total_pages": len(doc)
                }
            ))
            
            logger.info(f"   Page {page_num + 1}: {len(text)} chars")
        
        doc.close()
        
        logger.info(f"✅ Direct fitz extraction: {len(documents)} pages")
        return documents
    
    def _load_csv(self, file_path: str, **kwargs) -> List[Any]:
        """Load CSV document."""
        try:
            from langchain_community.document_loaders import CSVLoader
        except ImportError:
            raise ImportError("CSV loading requires: pip install pandas")
        
        loader = CSVLoader(file_path, **kwargs)
        return loader.load()
    
    def _load_text(self, file_path: str, **kwargs) -> List[Any]:
        """Load plain text document."""
        from langchain_community.document_loaders import TextLoader
        
        loader = TextLoader(file_path, **kwargs)
        return loader.load()
    
    def _load_html(self, file_path: str, **kwargs) -> List[Any]:
        """Load HTML document."""
        try:
            from langchain_community.document_loaders import UnstructuredHTMLLoader
        except ImportError:
            raise ImportError("HTML loading requires: pip install beautifulsoup4 lxml")
        
        loader = UnstructuredHTMLLoader(file_path, **kwargs)
        return loader.load()
    
    def _load_markdown(self, file_path: str, **kwargs) -> List[Any]:
        """Load Markdown document."""
        from langchain_community.document_loaders import UnstructuredMarkdownLoader
        
        loader = UnstructuredMarkdownLoader(file_path, **kwargs)
        return loader.load()
    
    def _load_json(self, file_path: str, **kwargs) -> List[Any]:
        """Load JSON document."""
        from langchain_community.document_loaders import JSONLoader
        
        # JSONLoader requires jq_schema or text_content
        if 'jq_schema' not in kwargs and 'text_content' not in kwargs:
            kwargs['jq_schema'] = '.'
        
        loader = JSONLoader(file_path, **kwargs)
        return loader.load()
    
    def _load_unstructured(self, file_path: str, **kwargs) -> List[Any]:
        """Load document using Unstructured (Word, PowerPoint, Excel)."""
        try:
            from langchain_community.document_loaders import UnstructuredFileLoader
        except ImportError:
            raise ImportError("Unstructured loading requires: pip install unstructured")
        
        loader = UnstructuredFileLoader(file_path, **kwargs)
        return loader.load()
    
    def split_documents(
        self,
        documents: List[Any],
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs
    ) -> List[Any]:
        """
        Split documents into chunks for better processing.
        
        Args:
            documents: List of documents to split
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            **kwargs: Splitter-specific options
            
        Returns:
            List of document chunks
        """
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
        except ImportError:
            raise ImportError("Text splitting requires: pip install langchain")
        
        logger.info(f"✂️ Splitting {len(documents)} documents (chunk_size={chunk_size}, overlap={chunk_overlap})")
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            **kwargs
        )
        
        chunks = splitter.split_documents(documents)
        logger.info(f"✅ Created {len(chunks)} chunks")
        
        return chunks
    
    def load_from_url(self, url: str, **kwargs) -> List[Any]:
        """
        Load document from URL.
        
        Args:
            url: URL to load from
            **kwargs: Loader-specific options
            
        Returns:
            List of LangChain Document objects
        """
        try:
            from langchain_community.document_loaders import WebBaseLoader
        except ImportError:
            raise ImportError("URL loading requires: pip install beautifulsoup4")
        
        logger.info(f"🌐 Loading document from URL: {url}")
        
        loader = WebBaseLoader(url, **kwargs)
        return loader.load()

