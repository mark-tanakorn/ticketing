"""
CSV Reader Node - Read and parse CSV files into structured data

Converts CSV files into array of dictionaries for easy data extraction.
"""

import csv
import logging
from typing import Dict, Any, List
from pathlib import Path

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import PasswordProtectedFileCapability
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="csv_reader",
    category=NodeCategory.PROCESSING,
    name="CSV Reader",
    description="Read and parse CSV file into structured data (array of objects)",
    icon="fa-solid fa-table",
    version="1.0.0"
)
class CSVReaderNode(Node, PasswordProtectedFileCapability):
    """
    CSV Reader Node - Parse CSV files into structured data
    
    Input: File reference (from File Polling or Upload node)
    Output: Array of dictionaries (one per row)
    
    Features:
    - Automatic header detection
    - Custom delimiter support
    - Skip rows option
    - Column filtering
    - Type preservation
    
    Example Output:
    [
        {"name": "John", "age": "30", "city": "New York"},
        {"name": "Jane", "age": "25", "city": "Boston"}
    ]
    
    Use Cases:
    - Process CSV data from file polling
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
                "display_name": "CSV File",
                "description": "CSV file reference from upload or polling node",
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
                "description": "Array of objects (one per CSV row)"
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
                "description": "CSV metadata (row count, columns, etc.)"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "delimiter": {
                "type": "string",
                "label": "Delimiter",
                "description": "Column delimiter character",
                "required": False,
                "default": ",",
                "placeholder": ",",
                "widget": "text",
                "help": "Common: comma (,), semicolon (;), tab (\\t), pipe (|)"
            },
            "has_header": {
                "type": "boolean",
                "label": "Has Header Row",
                "description": "First row contains column names",
                "required": False,
                "default": True,
                "widget": "checkbox",
                "help": "Enable if CSV has header row with column names"
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
            },
            "encoding": {
                "type": "select",
                "label": "File Encoding",
                "description": "Character encoding of the CSV file",
                "required": False,
                "default": "utf-8",
                "widget": "select",
                "options": [
                    {"label": "UTF-8", "value": "utf-8"},
                    {"label": "UTF-8-SIG (with BOM)", "value": "utf-8-sig"},
                    {"label": "Windows-1252 (Latin-1)", "value": "windows-1252"},
                    {"label": "ISO-8859-1", "value": "iso-8859-1"},
                    {"label": "ASCII", "value": "ascii"}
                ],
                "help": "Choose encoding based on file source. UTF-8 is most common."
            }
        }
    
    async def execute(self, inputs: NodeExecutionInput) -> Dict[str, Any]:
        """Execute CSV reader node."""
        try:
            file_ref = inputs.ports.get("file")
            
            logger.info(f"📊 CSV Reader received file: {type(file_ref)}")
            
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
                raise FileNotFoundError(f"CSV file not found: {file_path}")
            
            logger.info(f"📄 Reading CSV file: {file_path}")
            
            # Get config
            delimiter = self.resolve_config(inputs, "delimiter", ",")
            has_header = self.resolve_config(inputs, "has_header", True)
            skip_rows = self.resolve_config(inputs, "skip_rows", 0)
            columns_str = self.resolve_config(inputs, "columns_to_extract", "")
            encoding = self.resolve_config(inputs, "encoding", "utf-8")
            
            # Parse columns filter
            columns_filter = None
            if columns_str and columns_str.strip():
                columns_filter = [col.strip() for col in columns_str.split(",")]
                logger.info(f"🔍 Filtering columns: {columns_filter}")
            
            # Handle tab delimiter
            if delimiter == "\\t":
                delimiter = "\t"
            
            # Read CSV file
            data_rows = []
            headers = []
            
            with open(file_path, 'r', encoding=encoding, newline='') as csvfile:
                # Skip initial rows if configured
                for _ in range(skip_rows):
                    next(csvfile, None)
                
                reader = csv.reader(csvfile, delimiter=delimiter)
                
                # Read headers
                if has_header:
                    headers = next(reader, [])
                    logger.info(f"📋 CSV Headers: {headers}")
                else:
                    # Generate column names: col_0, col_1, etc.
                    first_row = next(reader, [])
                    if first_row:
                        headers = [f"col_{i}" for i in range(len(first_row))]
                        # Process first row as data
                        row_dict = dict(zip(headers, first_row))
                        if columns_filter:
                            row_dict = {k: v for k, v in row_dict.items() if k in columns_filter}
                        data_rows.append(row_dict)
                
                # Apply column filter to headers if specified
                if columns_filter:
                    # Validate columns exist
                    invalid_cols = [col for col in columns_filter if col not in headers]
                    if invalid_cols:
                        logger.warning(f"⚠️ Columns not found in CSV: {invalid_cols}")
                    
                    filtered_headers = [h for h in headers if h in columns_filter]
                else:
                    filtered_headers = headers
                
                # Read data rows
                for row in reader:
                    if len(row) == 0:
                        continue  # Skip empty rows
                    
                    # Create dict from row
                    row_dict = dict(zip(headers, row))
                    
                    # Apply column filter
                    if columns_filter:
                        row_dict = {k: v for k, v in row_dict.items() if k in columns_filter}
                    
                    data_rows.append(row_dict)
            
            # Build metadata
            metadata = {
                "row_count": len(data_rows),
                "column_count": len(filtered_headers),
                "columns": filtered_headers,
                "file_name": file_path.name,
                "file_path": str(file_path),
                "delimiter": delimiter,
                "encoding": encoding
            }
            
            logger.info(f"✅ CSV parsed successfully:")
            logger.info(f"   Rows: {len(data_rows)}")
            logger.info(f"   Columns: {len(filtered_headers)}")
            logger.info(f"   Headers: {filtered_headers}")
            
            if data_rows:
                logger.info(f"   First row sample: {str(data_rows[0])[:200]}")
            
            return {
                "data": data_rows,
                "headers": filtered_headers,
                "metadata": metadata
            }
        
        except Exception as e:
            logger.error(f"❌ CSV Reader failed: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    print("CSV Reader Node - Parse CSV files into structured data")

