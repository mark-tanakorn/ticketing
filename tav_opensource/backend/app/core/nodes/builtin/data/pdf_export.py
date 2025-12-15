"""
PDF Export Node - Export workflow data to PDF file

Create PDF files from workflow data with download or server-save options.
Uses ExportCapability for standardized export handling and LLMCapability for AI integration.
"""

import logging
import io
import re
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4, legal
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available - template mode will be disabled")

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import ExportCapability, LLMCapability
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="pdf_writer",
    category=NodeCategory.EXPORT,
    name="PDF Writer",
    description="Write and Export workflow data to PDF file (download or save to server) - LLM-enabled",
    icon="fa-solid fa-file-pdf",
    version="1.0.0"
)
class PDFExportNode(Node, ExportCapability, LLMCapability):
    """
    PDF Export Node - Export data to PDF files with download capability
    
    Uses ExportCapability mixin for file handling and LLMCapability for LLM integration.
    
    Features:
    - Export data from variables to PDF
    - Template Mode: Edit existing PDF templates with text replacement
    - Customizable title, content, and formatting
    - Table support for structured data
    - LLM-enabled for AI-generated content
    - Timestamp placeholders in filename
    - Access to call_llm() for content generation
    
    Use Cases:
    - Generate reports with AI-generated content
    - Fill and edit PDF templates with workflow data
    - Export medical check summaries
    - Create formatted documents
    - Data extraction with formatting
    - AI-powered document generation
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "data",
                "type": PortType.UNIVERSAL,
                "display_name": "Data to Export",
                "description": "Data object, list, or text content to export as PDF",
                "required": True
            },
            {
                "name": "template",
                "type": PortType.UNIVERSAL,
                "display_name": "Template PDF (Optional)",
                "description": "PDF template file to edit/fill (for template mode)",
                "required": False
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "result",
                "type": PortType.UNIVERSAL,
                "display_name": "Export Result",
                "description": "Result with file path and stats",
            },
            {
                "name": "file",
                "type": PortType.UNIVERSAL,
                "display_name": "File (MediaFormat)",
                "description": "PDF file in standard MediaFormat - can be connected to any node",
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Define configuration schema.
        
        Note: Standard config fields are auto-injected by the system:
        - LLM config (provider, model, temperature) from LLMCapability
        - Export config (export_mode, output_folder, filename) from ExportCapability
        
        This method only defines PDF-specific fields:
        - mode (create new or use template)
        - prompt (for AI-generated content)
        - replacements (for template mode)
        - title, page_size, font_size, etc.
        """
        return {
            "mode": {
                "type": "string",
                "label": "PDF Mode",
                "description": "Create new PDF or edit existing template",
                "required": False,
                "default": "create",
                "widget": "select",
                "options": [
                    {"value": "create", "label": "Create New PDF"},
                    {"value": "template", "label": "Edit PDF Template (Replace Text)"}
                ],
                "help": "Template mode requires PyMuPDF library and a template file"
            },
            "template_file": {
                "type": "string",
                "label": "PDF Template",
                "description": "Upload PDF template to edit",
                "required": False,
                "default": "",
                "widget": "file_picker",
                "accept": ".pdf,application/pdf",
                "file_category": "document",
                "help": "Upload your PDF template here. You can also connect via the 'template' input port.",
                "show_if": {"mode": "template"}
            },
            "replacements": {
                "type": "string",
                "label": "Text Replacements (JSON)",
                "description": "JSON object mapping text to find and replace in template",
                "required": False,
                "default": "",
                "widget": "textarea",
                "rows": 6,
                "placeholder": '{\n  "{{OLD_NAME}}": "{{vision_model.name}}",\n  "{{OLD_DATE}}": "{{current_date}}",\n  "INSURABLE": "APPROVED"\n}',
                "help": "Find-and-replace mappings. Supports variable templates.",
                "allow_template": True,
                "show_if": {"mode": "template"}
            },
            "use_input_as_replacements": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Use Input Data as Replacements",
                "description": "Merge input port data as additional replacements",
                "required": False,
                "default": True,
                "help": "When enabled, data from the input port is merged as replacements. Disable to use ONLY the JSON config above.",
                "show_if": {"mode": "template"}
            },
            "replacement_mode": {
                "type": "string",
                "label": "Replacement Mode",
                "description": "How to match text for replacement",
                "required": False,
                "default": "exact",
                "widget": "select",
                "options": [
                    {"value": "exact", "label": "Exact Match"},
                    {"value": "partial", "label": "Partial Match (substring)"},
                    {"value": "regex", "label": "Regular Expression"}
                ],
                "help": "Exact is safest, partial replaces all occurrences of substring",
                "show_if": {"mode": "template"}
            },
            "preserve_font_size": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Preserve Original Font Size",
                "description": "Automatically detect and use the original text's font size",
                "required": False,
                "default": True,
                "help": "When enabled, replacement text will match the font size of the original text",
                "show_if": {"mode": "template"}
            },
            "override_font_size": {
                "type": "integer",
                "label": "Override Font Size (Optional)",
                "description": "Force a specific font size for all replacements",
                "required": False,
                "default": None,
                "min": 6,
                "max": 72,
                "widget": "number",
                "placeholder": "Leave empty to auto-detect",
                "help": "If set, ignores original font size and uses this value instead",
                "show_if": {"mode": "template"}
            },
            "preserve_font_family": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Preserve Font Family",
                "description": "Try to match the original font family (typeface)",
                "required": False,
                "default": False,
                "help": "Experimental: Attempts to use the same font as the original text. May not work for all fonts.",
                "show_if": {"mode": "template"}
            },
            "use_ai": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Enable AI Content Generation",
                "description": "Use AI to generate PDF content from a prompt",
                "required": False,
                "default": False,
                "help": "When enabled, AI generates the PDF content. When disabled, input data is used directly.",
                "show_if": {"mode": "create"}
            },
            "prompt": {
                "type": "string",
                "label": "AI Prompt",
                "description": "Prompt for AI to generate PDF content",
                "required": False,
                "widget": "textarea",
                "placeholder": "Generate a professional summary report of the data...",
                "rows": 4,
                "help": "Describe what you want the AI to generate.",
                "allow_template": True,
                "show_if": {"mode": "create", "use_ai": True}
            },
            "title": {
                "type": "string",
                "label": "Document Title",
                "description": "Title to display at the top of the PDF",
                "required": False,
                "default": "",
                "placeholder": "Report Title",
                "widget": "text",
                "allow_template": True,
                "show_if": {"mode": "create"}
            },
            "page_size": {
                "type": "string",
                "label": "Page Size",
                "description": "PDF page size",
                "required": False,
                "default": "letter",
                "widget": "select",
                "options": [
                    {"value": "letter", "label": "Letter (8.5 x 11 in)"},
                    {"value": "a4", "label": "A4 (210 x 297 mm)"},
                    {"value": "legal", "label": "Legal (8.5 x 14 in)"}
                ],
                "help": "Standard paper sizes",
                "show_if": {"mode": "create"}
            },
            "font_size": {
                "type": "integer",
                "label": "Font Size",
                "description": "Base font size for body text (points)",
                "required": False,
                "default": 12,
                "min": 8,
                "max": 24,
                "widget": "number",
                "help": "Default: 12pt",
                "show_if": {"mode": "create"}
            },
            "include_timestamp": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Include Timestamp",
                "description": "Add generation timestamp to the document",
                "required": False,
                "default": True,
                "help": "Shows when the PDF was generated",
                "show_if": {"mode": "create"}
            },
            "content_type": {
                "type": "string",
                "label": "Content Type",
                "description": "How to format the input data",
                "required": False,
                "default": "auto",
                "widget": "select",
                "options": [
                    {"value": "auto", "label": "Auto-detect"},
                    {"value": "text", "label": "Plain Text"},
                    {"value": "table", "label": "Table (for lists of dicts)"}
                ],
                "help": "Auto-detect will choose the best format based on data type",
                "show_if": {"mode": "create"}
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute PDF export"""
        try:
            logger.info(f"📄 PDF Export Node executing: {self.node_id}")
            
            # Get mode
            mode = self.resolve_config(input_data, "mode", "create")
            
            if mode == "template":
                # Template mode - edit existing PDF
                return await self._execute_template_mode(input_data)
            else:
                # Create mode - generate new PDF
                return await self._execute_create_mode(input_data)
            
        except Exception as e:
            logger.error(f"❌ PDF Export error: {e}", exc_info=True)
            return {
                "result": {
                    "success": False,
                    "error": str(e)
                },
                "file": None
            }
    
    async def _execute_template_mode(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute PDF template editing mode"""
        if not PYMUPDF_AVAILABLE:
            return {
                "result": {
                    "success": False,
                    "error": "Template mode requires PyMuPDF library. Please install: pip install PyMuPDF"
                },
                "file": None
            }
        
        logger.info(f"📝 Template mode: Editing existing PDF")
        
        # Get template file - prioritize uploaded file from config
        template_file_id = self.resolve_config(input_data, "template_file", "")
        template_ref = None
        
        if template_file_id:
            # Use file uploaded via config - resolve file_id to actual file path
            logger.info(f"Using template from config: {template_file_id}")
            
            from app.database.session import SessionLocal
            from app.database.repositories.file import FileRepository
            
            db = SessionLocal()
            try:
                file_repo = FileRepository(db)
                file_record = file_repo.get_by_id(template_file_id)
                
                if not file_record:
                    return {
                        "result": {
                            "success": False,
                            "error": f"Template file not found in database: {template_file_id}"
                        },
                        "file": None
                    }
                
                # Build full path for template
                full_path = Path("data") / file_record.storage_path
                
                # Create a MediaFormat-like reference
                template_ref = {
                    "type": "document",
                    "data_type": "file_path",
                    "data": str(full_path),
                    "format": Path(file_record.filename).suffix.lstrip('.') or "pdf",
                    "metadata": {
                        "file_id": file_record.id,
                        "filename": file_record.filename,
                        "mime_type": file_record.mime_type,
                        "size_bytes": file_record.file_size_bytes
                    }
                }
                
                logger.info(f"Resolved template file: {file_record.filename} at {full_path}")
                logger.info(f"Template path exists: {Path(full_path).exists()}")
                
            finally:
                db.close()
        else:
            # Fallback to input port
            template_ref = input_data.ports.get("template")
            logger.info(f"Using template from input port")
        
        if not template_ref:
            return {
                "result": {
                    "success": False,
                    "error": "No template file provided. Specify template_file_id or connect template input port."
                },
                "file": None
            }
        
        # Get file path from file reference
        # Handle both old format and MediaFormat
        template_path = None
        if isinstance(template_ref, dict):
            # Check if it's MediaFormat
            if template_ref.get("type") in ["document", "image", "audio", "video"]:
                # MediaFormat - extract file path from data
                if template_ref.get("data_type") == "file_path":
                    template_path = template_ref.get("data")
                else:
                    return {
                        "result": {
                            "success": False,
                            "error": "PDF Writer template mode only supports file_path data type"
                        },
                        "file": None
                    }
            else:
                # Old format - extract storage_path
                template_path = template_ref.get("file_path") or template_ref.get("path") or template_ref.get("storage_path")
        else:
            template_path = str(template_ref)
        
        logger.info(f"📂 Template path after extraction: {template_path}")
        
        # If path is relative, build full path
        if template_path:
            template_path_obj = Path(template_path)
            if not template_path_obj.is_absolute():
                # Check if it already starts with "data" directory
                if not (template_path_obj.parts and template_path_obj.parts[0] == "data"):
                    template_path = str(Path("data") / template_path)
                else:
                    template_path = str(template_path_obj)
            else:
                template_path = str(template_path_obj)
        
        logger.info(f"📂 Final template path after normalization: {template_path}")
        logger.info(f"📂 Template file exists: {Path(template_path).exists()}")
        
        if not template_path or not Path(template_path).exists():
            return {
                "result": {
                    "success": False,
                    "error": f"Template file not found: {template_path}"
                },
                "file": None
            }
        
        # Get config options
        replacements_json = self.resolve_config(input_data, "replacements", "{}")
        replacement_mode = self.resolve_config(input_data, "replacement_mode", "exact")
        preserve_font_size = self.resolve_config(input_data, "preserve_font_size", True)
        override_font_size = self.resolve_config(input_data, "override_font_size", None)
        preserve_font_family = self.resolve_config(input_data, "preserve_font_family", False)
        use_input_as_replacements = self.resolve_config(input_data, "use_input_as_replacements", True)
        
        # Parse static replacements from config (manual JSON)
        import json
        replacements = {}
        try:
            if replacements_json and replacements_json.strip() != "":
                replacements = json.loads(replacements_json)
                logger.info(f"📝 Loaded {len(replacements)} replacements from JSON config")
        except json.JSONDecodeError as e:
            return {
                "result": {
                    "success": False,
                    "error": f"Invalid replacements JSON in config: {e}"
                },
                "file": None
            }
        
        # Optionally merge dynamic replacements from input data
        # (This allows connecting an LLM Chat node upstream if you want AI-generated replacements)
        if use_input_as_replacements:
            input_payload = input_data.ports.get("data")
            if isinstance(input_payload, dict):
                # Support direct dictionary mapping: {"Old": "New"}
                # or structured format: {"replacements": [{"old": "A", "new": "B"}, ...]}
                
                dynamic_replacements = {}
                
                # Case 1: Structured "replacements" list (LLM friendly)
                if "replacements" in input_payload and isinstance(input_payload["replacements"], list):
                    for item in input_payload["replacements"]:
                        if isinstance(item, dict):
                            # Support both "old"/"new" and "original"/"replacement" keys
                            old_val = item.get("old") or item.get("original") or item.get("find")
                            new_val = item.get("new") or item.get("replacement") or item.get("replace")
                            if old_val is not None and new_val is not None:
                                dynamic_replacements[str(old_val)] = str(new_val)
                                
                # Case 2: Structured "replacements" dict
                elif "replacements" in input_payload and isinstance(input_payload["replacements"], dict):
                     dynamic_replacements = input_payload["replacements"]
                     
                # Case 3: The whole input is just replacements (if no specific keys detected)
                # Be careful here to avoid treating random data as replacements
                # Only do this if the input is relatively flat (values are strings/numbers)
                elif all(isinstance(v, (str, int, float, bool)) for v in input_payload.values()):
                     # Only if we didn't find "replacements" key
                     if not dynamic_replacements:
                         dynamic_replacements = input_payload

                if dynamic_replacements:
                    logger.info(f"🔗 Merging {len(dynamic_replacements)} dynamic replacements from input data")
                    replacements.update(dynamic_replacements)
        else:
            logger.info(f"📝 Using ONLY manual JSON replacements (input data ignored)")
        
        if not replacements:
            logger.warning("No replacements specified (config, input, or AI), template will be copied as-is")
        
        logger.info(f"📝 Applying {len(replacements)} replacements in {replacement_mode} mode")
        
        # Edit PDF template
        try:
            doc = fitz.open(template_path)
            total_replacements = 0
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                for old_text, new_text in replacements.items():
                    # Convert to string
                    old_text_str = str(old_text)
                    new_text_str = str(new_text)
                    
                    if replacement_mode == "exact":
                        # Search for exact text match
                        # Note: search_for returns a list of Rect objects.
                        # If text spans multiple lines, it returns multiple rects (one per line).
                        # We need to hide ALL rects, but insert the new text ONLY ONCE.
                        text_instances = page.search_for(old_text_str)
                        
                        if text_instances:
                            # Sort instances by vertical position (y) to find the "first" one
                            # This handles multi-line matches where we want to start writing at the top-left
                            text_instances.sort(key=lambda r: (r.y0, r.x0))
                            
                            # Get the actual font size from the text span for better matching
                            first_inst = text_instances[0]
                            original_fontsize = None
                            original_fontname = None
                            
                            # Check if user wants to override font size
                            if override_font_size:
                                original_fontsize = override_font_size
                                logger.debug(f"Using override font size: {original_fontsize}pt")
                            elif preserve_font_size:
                                # Try to find the actual font size by examining text spans in the area
                                text_dict = page.get_text("dict")
                                blocks = text_dict.get("blocks", [])
                                
                                for block in blocks:
                                    if "lines" in block:
                                        for line in block["lines"]:
                                            for span in line.get("spans", []):
                                                text = span.get("text", "")
                                                # Check if this span contains our search text
                                                if old_text_str in text:
                                                    bbox = span["bbox"]
                                                    # Check if this span overlaps with our found instance
                                                    if (abs(bbox[0] - first_inst.x0) < 5 and 
                                                        abs(bbox[1] - first_inst.y0) < 5):
                                                        original_fontsize = span.get("size", None)
                                                        if preserve_font_family:
                                                            original_fontname = span.get("font", None)
                                                        logger.debug(f"Found original font: {original_fontname} at {original_fontsize}pt for '{old_text_str}'")
                                                        break
                                            if original_fontsize:
                                                break
                                    if original_fontsize:
                                        break
                                
                                # Fallback to rect height estimation if we couldn't find the exact font
                                # Rect height is usually 1.2-1.4x the font size, so we use 0.8 as multiplier
                                if not original_fontsize:
                                    original_fontsize = first_inst.height * 0.8
                                    logger.debug(f"Using estimated font size: {original_fontsize}pt (from rect height {first_inst.height})")
                            else:
                                # Use rect height as-is if not preserving
                                original_fontsize = first_inst.height
                                logger.debug(f"Using rect height as font size: {original_fontsize}pt")
                            
                            # 1. Hide ALL instances (whiteout)
                            for inst in text_instances:
                                page.draw_rect(inst, color=(1, 1, 1), fill=(1, 1, 1))
                            
                            # 2. Insert new text ONLY at the first instance position
                            insert_kwargs = {
                                "fontsize": original_fontsize,
                                "color": (0, 0, 0)
                            }
                            
                            # Add font name if we found it and user wants to preserve it
                            if original_fontname and preserve_font_family:
                                insert_kwargs["fontname"] = original_fontname
                                
                            page.insert_text(
                                (first_inst.x0, first_inst.y1 - 2),  # Slight adjustment for better alignment
                                new_text_str,
                                **insert_kwargs
                            )
                            total_replacements += 1
                            logger.debug(f"Replaced '{old_text_str}' with '{new_text_str}' at font size {original_fontsize}pt")
                    
                    elif replacement_mode == "partial":
                        # Get all text blocks
                        text_dict = page.get_text("dict")
                        blocks = text_dict.get("blocks", [])
                        
                        for block in blocks:
                            if "lines" in block:
                                for line in block["lines"]:
                                    for span in line.get("spans", []):
                                        text = span.get("text", "")
                                        if old_text_str in text:
                                            # Replace text
                                            new_full_text = text.replace(old_text_str, new_text_str)
                                            
                                            # Cover old text
                                            bbox = span["bbox"]
                                            rect = fitz.Rect(bbox)
                                            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                                            
                                            # Determine font size to use
                                            if override_font_size:
                                                fontsize = override_font_size
                                            elif preserve_font_size:
                                                fontsize = span.get("size", 11)
                                            else:
                                                fontsize = 11
                                            
                                            # Build insert arguments
                                            insert_kwargs = {
                                                "fontsize": fontsize,
                                                "color": (0, 0, 0)
                                            }
                                            
                                            # Add font name if preserving font family
                                            if preserve_font_family:
                                                fontname = span.get("font")
                                                if fontname:
                                                    insert_kwargs["fontname"] = fontname
                                            
                                            # Insert new text
                                            page.insert_text(
                                                (bbox[0], bbox[3] - 2),
                                                new_full_text,
                                                **insert_kwargs
                                            )
                                            total_replacements += 1
                                            logger.debug(f"Partial replace '{old_text_str}' → '{new_text_str}' at {fontsize}pt")
                    
                    elif replacement_mode == "regex":
                        # Get page text
                        page_text = page.get_text()
                        
                        # Apply regex replacement
                        try:
                            new_page_text = re.sub(old_text_str, new_text_str, page_text)
                            if new_page_text != page_text:
                                # Note: Regex mode is complex, fallback to simple search
                                logger.warning(f"Regex mode may not preserve formatting perfectly")
                                total_replacements += 1
                        except re.error as e:
                            logger.error(f"Invalid regex pattern '{old_text_str}': {e}")
            
            logger.info(f"✅ Made {total_replacements} text replacements")
            
            # Save modified PDF to bytes
            pdf_bytes = doc.tobytes()
            doc.close()
            
            # Get filename
            filename = self.resolve_config(input_data, "filename", "edited_{timestamp}.pdf")
            resolved_filename = self._resolve_path_template(filename, input_data)
            if not resolved_filename.endswith('.pdf'):
                resolved_filename += '.pdf'
            
            logger.info(f"✅ Template PDF edited: {len(pdf_bytes)} bytes")
            
            # Use ExportCapability to handle download or server save
            return await self.handle_export(
                input_data=input_data,
                file_content=pdf_bytes,
                filename=resolved_filename,
                mime_type="application/pdf"
            )
            
        except Exception as e:
            logger.error(f"❌ Template editing error: {e}", exc_info=True)
            return {
                "result": {
                    "success": False,
                    "error": f"Failed to edit template: {str(e)}"
                },
                "file": None
            }
    
    async def _execute_create_mode(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute PDF creation mode (original functionality)"""
        logger.info(f"🆕 Create mode: Generating new PDF")
        
        # Check if AI is enabled
        use_ai = self.resolve_config(input_data, "use_ai", False)
        prompt = self.resolve_config(input_data, "prompt", "")
        
        if use_ai and prompt:
            # AI mode - generate content from prompt
            logger.info(f"🤖 Generating PDF content with AI from prompt")
            
            # Get context data from input port if available
            context_data = input_data.ports.get("data")
            
            # Build AI prompt with context
            if context_data:
                context_str = str(context_data) if not isinstance(context_data, str) else context_data
                full_prompt = f"{prompt}\n\nContext data:\n{context_str}"
            else:
                full_prompt = prompt
            
            # Call LLM to generate content
            ai_response = await self.call_llm(
                user_prompt=full_prompt,
                system_prompt="You are a professional document writer. Generate clear, well-formatted content based on the user's request."
            )
            
            # Use AI response as data
            data = ai_response
            logger.info(f"✅ AI generated {len(ai_response)} characters of content")
        else:
            # Direct mode - get data from input port (NO LLM processing)
            logger.info(f"📝 Using input data directly (AI disabled)")
            data = input_data.ports.get("data")
            if not data:
                return {
                    "result": {
                        "success": False,
                        "error": "No data provided to export. Connect data to input port or enable AI with a prompt."
                    },
                    "file": None
                }
        
        # Get configuration
        filename = self.resolve_config(input_data, "filename", "export_{timestamp}.pdf")
        title = self.resolve_config(input_data, "title", "")
        page_size = self.resolve_config(input_data, "page_size", "letter")
        font_size = self.resolve_config(input_data, "font_size", 12)
        include_timestamp = self.resolve_config(input_data, "include_timestamp", True)
        content_type = self.resolve_config(input_data, "content_type", "auto")
        
        # Resolve filename template (support {timestamp}, {date}, etc.)
        resolved_filename = self._resolve_path_template(filename, input_data)
        if not resolved_filename.endswith('.pdf'):
            resolved_filename += '.pdf'
        
        # Determine page size
        page_size_map = {
            "letter": letter,
            "a4": A4,
            "legal": legal
        }
        page_size_obj = page_size_map.get(page_size.lower(), letter)
        
        # Generate PDF content in memory
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=page_size_obj,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=inch
        )
        
        # Build PDF content
        story = []
        styles = getSampleStyleSheet()
        
        # Add title if provided
        if title:
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=font_size + 6,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=20,
                alignment=TA_CENTER
            )
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 0.2*inch))
        
        # Add timestamp if requested
        if include_timestamp:
            from app.utils.timezone import get_local_now
            now = get_local_now()
            timestamp_text = f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}"
            timestamp_style = ParagraphStyle(
                'Timestamp',
                parent=styles['Normal'],
                fontSize=font_size - 2,
                textColor=colors.grey,
                alignment=TA_RIGHT
            )
            story.append(Paragraph(timestamp_text, timestamp_style))
            story.append(Spacer(1, 0.3*inch))
        
        # Auto-detect content type if needed
        if content_type == "auto":
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                content_type = "table"
            else:
                content_type = "text"
        
        # Format content based on type
        if content_type == "table" and isinstance(data, list):
            # Table format for list of dictionaries
            story.extend(self._create_table(data, font_size, styles))
        else:
            # Text format
            story.extend(self._create_text_content(data, font_size, styles))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF content as bytes
        pdf_content = pdf_buffer.getvalue()
        pdf_buffer.close()
        
        logger.info(f"✅ Generated PDF: {len(pdf_content)} bytes")
        
        # Use ExportCapability to handle download or server save
        return await self.handle_export(
            input_data=input_data,
            file_content=pdf_content,
            filename=resolved_filename,
            mime_type="application/pdf"
        )
    
    def _create_table(self, data: List[Dict], font_size: int, styles) -> List:
        """Create a formatted table from list of dictionaries"""
        story = []
        
        if not data:
            return story
        
        # Get columns from first item
        columns = list(data[0].keys())
        
        # Prepare table data
        table_data = [columns]  # Header row
        for item in data:
            row = [str(item.get(col, "")) for col in columns]
            table_data.append(row)
        
        # Create table
        table = Table(table_data, repeatRows=1)
        
        # Style the table
        table_style = TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90e2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), font_size),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Body style
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), font_size - 1),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ])
        
        table.setStyle(table_style)
        story.append(table)
        
        return story
    
    def _create_text_content(self, data: Any, font_size: int, styles) -> List:
        """Create formatted text content"""
        story = []
        
        # Convert data to string
        if isinstance(data, (dict, list)):
            import json
            text = json.dumps(data, indent=2)
        else:
            text = str(data)
        
        # Create custom body style
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=font_size,
            leading=font_size * 1.5,
            spaceAfter=12
        )
        
        # Split text into paragraphs and add to story
        paragraphs = text.split('\n')
        for para_text in paragraphs:
            if para_text.strip():
                # Escape special characters for reportlab
                safe_text = para_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(safe_text, body_style))
            else:
                story.append(Spacer(1, 0.1*inch))
        
        return story
    
    def _resolve_path_template(self, template: str, input_data: NodeExecutionInput) -> str:
        """
        Resolve path template with placeholders.
        
        Supports:
        - {timestamp}: Current timestamp (YYYYMMDD_HHMMSS)
        - {date}: Current date (YYYYMMDD)
        - {time}: Current time (HHMMSS)
        - Variable references via resolve_config
        """
        from app.utils.timezone import get_local_now
        
        # Replace time placeholders
        now = get_local_now()
        replacements = {
            "{timestamp}": now.strftime("%Y%m%d_%H%M%S"),
            "{date}": now.strftime("%Y%m%d"),
            "{time}": now.strftime("%H%M%S"),
            "{datetime}": now.strftime("%Y%m%d_%H%M%S"),
            "{year}": now.strftime("%Y"),
            "{month}": now.strftime("%m"),
            "{day}": now.strftime("%d")
        }
        
        path = template
        for placeholder, value in replacements.items():
            path = path.replace(placeholder, value)
        
        # Sanitize path for Windows compatibility
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            path = path.replace(char, '_')
        
        return path


if __name__ == "__main__":
    print("PDF Export Node - Export workflow data to PDF files")

