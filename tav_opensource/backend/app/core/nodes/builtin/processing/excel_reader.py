"""
Excel Reader Node - Read and parse Excel files into structured data

Converts Excel files (XLSX, XLS) into array of dictionaries for easy data extraction.
"""

import logging
from typing import Dict, Any, List
from pathlib import Path

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import PasswordProtectedFileCapability
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="excel_reader",
    category=NodeCategory.PROCESSING,
    name="Excel Reader",
    description="Read and parse Excel file (XLSX, XLS, XLSM) into structured data (array of objects)",
    icon="fa-solid fa-file-excel",
    version="1.0.0"
)
class ExcelReaderNode(Node, PasswordProtectedFileCapability):
    """
    Excel Reader Node - Parse Excel files into structured data
    
    Input: File reference (from File Polling or Upload node)
    Output: Array of dictionaries (one per row)
    
    Features:
    - Sheet selection
    - Automatic header detection
    - Skip rows option
    - Column filtering
    - Type preservation
    
    Example Output:
    [
        {"name": "John", "age": 30, "city": "New York"},
        {"name": "Jane", "age": 25, "city": "Boston"}
    ]
    
    Use Cases:
    - Process Excel data from file polling
    - Extract specific values from rows
    - Data transformation pipelines
    - Automated report processing
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "file",
                "type": PortType.UNIVERSAL,
                "display_name": "Excel File",
                "description": "Excel file reference from upload or polling node",
                "required": True
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "data",
                "type": PortType.UNIVERSAL,
                "display_name": "Parsed Data",
                "description": "Array of objects (one per Excel row)"
            },
            {
                "name": "headers",
                "type": PortType.UNIVERSAL,
                "display_name": "Headers",
                "description": "List of column headers"
            },
            {
                "name": "metadata",
                "type": PortType.UNIVERSAL,
                "display_name": "Metadata",
                "description": "Excel metadata (row count, columns, sheets, etc.)"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "sheet_name": {
                "type": "string",
                "label": "Sheet Name",
                "description": "Name of sheet to read (leave empty for first sheet)",
                "required": False,
                "default": "",
                "placeholder": "Sheet1",
                "widget": "text",
                "help": "Leave empty to read the first sheet"
            },
            "has_header": {
                "type": "boolean",
                "label": "Has Header Row",
                "description": "First row contains column names",
                "required": False,
                "default": True,
                "widget": "checkbox",
                "help": "Enable if Excel has header row with column names"
            },
            "skip_rows": {
                "type": "integer",
                "label": "Skip Rows",
                "description": "Number of rows to skip from the beginning",
                "required": False,
                "default": 0,
                "widget": "number",
                "min": 0,
                "max": 100,
                "help": "Skip initial rows (useful for files with metadata)"
            },
            "columns_to_extract": {
                "type": "string",
                "label": "Columns to Extract (Optional)",
                "description": "Comma-separated column names to extract (leave empty for all)",
                "required": False,
                "placeholder": "name,age,city",
                "widget": "text",
                "help": "Extract only specific columns. Leave empty to extract all columns."
            }
        }
    
    async def execute(self, inputs: NodeExecutionInput) -> Dict[str, Any]:
        """Execute Excel reader node."""
        try:
            import pandas as pd
            
            file_ref = inputs.ports.get("file")
            
            logger.info(f"📊 Excel Reader received file: {type(file_ref)}")
            
            if not file_ref or not isinstance(file_ref, dict):
                raise ValueError("Invalid file reference. Connect to a File Polling or Upload node.")
            
            # Extract file path from different formats
            file_path_str = None
            
            # Handle MediaFormat
            if file_ref.get("type") == "document":
                file_path_str = file_ref.get("data")
            
            # Handle legacy format (from file polling)
            elif "storage_path" in file_ref:
                file_path_str = file_ref.get("storage_path")
            
            # Handle file_path field (legacy)
            elif "file_path" in file_ref:
                file_path_str = file_ref.get("file_path")
            
            if not file_path_str:
                raise ValueError("File reference missing storage_path or file_path")
            
            # Build full path
            file_path = Path(file_path_str)
            
            # Don't prepend if already absolute
            if not file_path.is_absolute():
                if not file_path_str.startswith("data"):
                    base_path = Path("data")
                    file_path = base_path / file_path_str
            
            if not file_path.exists():
                raise FileNotFoundError(f"Excel file not found: {file_path}")
            
            logger.info(f"📄 Reading Excel file: {file_path}")
            
            # Get config
            sheet_name = self.resolve_config(inputs, "sheet_name", "")
            has_header = self.resolve_config(inputs, "has_header", True)
            skip_rows = self.resolve_config(inputs, "skip_rows", 0)
            columns_str = self.resolve_config(inputs, "columns_to_extract", "")
            
            # Parse columns filter
            columns_filter = None
            if columns_str and columns_str.strip():
                columns_filter = [col.strip() for col in columns_str.split(",")]
                logger.info(f"🔍 Filtering columns: {columns_filter}")
            
            # Handle password-protected files
            password = self.resolve_config(inputs, "file_password", None)
            actual_file_path = file_path
            
            if password:
                logger.info("🔐 Attempting to decrypt password-protected Excel file...")
                try:
                    decrypted_path = await self.decrypt_office_document(
                        str(file_path), 
                        password, 
                        str(file_path.stem)
                    )
                    actual_file_path = Path(decrypted_path)
                    logger.info(f"✅ Excel file decrypted to: {actual_file_path}")
                except Exception as e:
                    raise ValueError(f"Failed to decrypt Excel file: {e}")
            
            # Read Excel file using pandas
            read_kwargs = {
                "skiprows": skip_rows,
                "header": 0 if has_header else None
            }
            
            # Use sheet name if provided
            if sheet_name and sheet_name.strip():
                read_kwargs["sheet_name"] = sheet_name.strip()
            else:
                read_kwargs["sheet_name"] = 0  # First sheet
            
            # Read the Excel file
            df = pd.read_excel(actual_file_path, **read_kwargs)
            
            # Get sheet names for metadata
            with pd.ExcelFile(actual_file_path) as xls:
                all_sheets = xls.sheet_names
            
            # Generate column names if no header
            if not has_header:
                df.columns = [f"col_{i}" for i in range(len(df.columns))]
            
            headers = list(df.columns)
            logger.info(f"📋 Excel Headers: {headers}")
            
            # Apply column filter
            if columns_filter:
                # Validate columns exist
                invalid_cols = [col for col in columns_filter if col not in headers]
                if invalid_cols:
                    logger.warning(f"⚠️ Columns not found in Excel: {invalid_cols}")
                
                # Filter columns
                valid_cols = [col for col in columns_filter if col in headers]
                if valid_cols:
                    df = df[valid_cols]
                    headers = valid_cols
            
            # Convert to list of dictionaries
            # Handle NaN values by converting to None or empty string
            df = df.fillna("")
            data_rows = df.to_dict(orient="records")
            
            # Build metadata
            metadata = {
                "row_count": len(data_rows),
                "column_count": len(headers),
                "columns": headers,
                "file_name": file_path.name,
                "file_path": str(file_path),
                "sheet_name": sheet_name if sheet_name else all_sheets[0] if all_sheets else "Sheet1",
                "all_sheets": all_sheets
            }
            
            logger.info(f"✅ Excel parsed successfully:")
            logger.info(f"   Rows: {len(data_rows)}")
            logger.info(f"   Columns: {len(headers)}")
            logger.info(f"   Headers: {headers}")
            logger.info(f"   Sheets: {all_sheets}")
            
            if data_rows:
                logger.info(f"   First row sample: {str(data_rows[0])[:200]}")
            
            return {
                "data": data_rows,
                "headers": headers,
                "metadata": metadata
            }
        
        except Exception as e:
            logger.error(f"❌ Excel Reader failed: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    print("Excel Reader Node - Parse Excel files into structured data")

