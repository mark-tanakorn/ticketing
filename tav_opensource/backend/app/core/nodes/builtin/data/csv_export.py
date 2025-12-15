"""
CSV Export Node - Export workflow data to CSV file

Create CSV files from workflow data with download or server-save options.
Uses ExportCapability for standardized export handling.
"""

import csv
import logging
import io
from typing import Dict, Any, List
from datetime import datetime

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.capabilities import ExportCapability
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="csv_writer",
    category=NodeCategory.EXPORT,
    name="CSV Writer",
    description="Write and Export workflow data to CSV file (download or save to server)",
    icon="fa-solid fa-file-csv",
    version="1.0.0"
)
class CSVExportNode(Node, ExportCapability):
    """
    CSV Export Node - Export data to CSV files with download capability
    
    Uses ExportCapability mixin which provides:
    - Download to browser mode (default)
    - Save to server path mode
    - Automatic file handling
    
    Features:
    - Export data from variables to CSV
    - Configurable columns and headers
    - Custom delimiter support
    - Timestamp placeholders in filename
    
    Use Cases:
    - Export medical check cases
    - Save form submissions
    - Generate reports
    - Data extraction
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "data",
                "type": PortType.UNIVERSAL,
                "display_name": "Data to Export",
                "description": "Data object or list of objects to export",
                "required": True
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
                "description": "CSV file in standard MediaFormat - can be connected to any node",
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Define configuration schema.
        
        Note: Export config fields (export_mode, output_folder, filename) 
        are auto-injected by the system because this node has ExportCapability.
        
        This method only defines CSV-specific fields:
        - columns, headers, delimiter, etc.
        """
        return {
            "columns": {
                "type": "array",
                "label": "Columns to Export",
                "description": "List of field names to export (from data object)",
                "required": False,
                "items": {"type": "string"},
                "widget": "tags",
                "help": "Leave empty to export all fields. Example: name, id, risk_factors"
            },
            "headers": {
                "type": "array",
                "label": "Column Headers",
                "description": "Custom headers for columns (optional, same order as columns)",
                "required": False,
                "items": {"type": "string"},
                "widget": "tags",
                "help": "Custom names for CSV headers. If empty, uses field names."
            },
            "delimiter": {
                "type": "string",
                "label": "Delimiter",
                "description": "Column separator character",
                "required": False,
                "default": ",",
                "placeholder": ",",
                "widget": "text",
                "help": "Usually comma (,) or semicolon (;) or tab (\\t)"
            },
            "include_headers": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Include Headers",
                "description": "Write header row with column names",
                "required": False,
                "default": True,
                "help": "First row will contain column names"
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """Execute CSV export"""
        try:
            logger.info(f"📊 CSV Export Node executing: {self.node_id}")
            
            # Get data from input
            data = input_data.ports.get("data")
            if not data:
                return {
                    "result": {
                        "success": False,
                        "error": "No data provided to export"
                    }
                }
            
            # Get configuration
            filename = self.resolve_config(input_data, "filename", "export_{timestamp}.csv")
            columns = self.resolve_config(input_data, "columns", [])
            headers = self.resolve_config(input_data, "headers", [])
            delimiter = self.resolve_config(input_data, "delimiter", ",")
            include_headers = self.resolve_config(input_data, "include_headers", True)
            
            # Resolve filename template (support {timestamp}, {date}, etc.)
            resolved_filename = self._resolve_path_template(filename, input_data)
            if not resolved_filename.endswith('.csv'):
                resolved_filename += '.csv'
            
            # Convert delimiter escapes
            delimiter = delimiter.replace("\\t", "\t").replace("\\n", "\n")
            
            # Ensure data is a list
            if not isinstance(data, list):
                data = [data]
            
            if not data:
                return {
                    "result": {
                        "success": False,
                        "error": "Data is empty"
                    }
                }
            
            # Determine columns if not specified
            if not columns:
                # Use keys from first data item
                first_item = data[0]
                if isinstance(first_item, dict):
                    columns = list(first_item.keys())
                else:
                    return {
                        "result": {
                            "success": False,
                            "error": "Cannot auto-detect columns from non-dict data. Please specify columns."
                        }
                    }
            
            # Use headers if provided, otherwise use column names
            if not headers:
                headers = columns
            
            # Validate headers match columns
            if len(headers) != len(columns):
                logger.warning(f"Headers count ({len(headers)}) != columns count ({len(columns)}), using columns")
                headers = columns
            
            # Generate CSV content in memory
            output = io.StringIO()
            writer = csv.writer(output, delimiter=delimiter)
            
            # Write headers
            if include_headers:
                writer.writerow(headers)
            
            # Write data rows
            rows_written = 0
            for item in data:
                if isinstance(item, dict):
                    row = [item.get(col, "") for col in columns]
                else:
                    row = [str(item)]
                writer.writerow(row)
                rows_written += 1
            
            # Get CSV content as bytes
            csv_content = output.getvalue().encode('utf-8')
            output.close()
            
            logger.info(f"✅ Generated CSV: {rows_written} rows, {len(csv_content)} bytes")
            
            # Use ExportCapability to handle download
            return await self.handle_export(
                input_data=input_data,
                file_content=csv_content,
                filename=resolved_filename,
                mime_type="text/csv"
            )
            
        except Exception as e:
            logger.error(f"❌ CSV Export error: {e}", exc_info=True)
            return {
                "result": {
                    "success": False,
                    "error": str(e)
                }
            }
    
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
        # Replace characters that are invalid in Windows filenames: < > : " / \ | ? *
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            path = path.replace(char, '_')
        
        # Resolve any variable references (handled by resolve_config/template system)
        # This is already done if the template came through resolve_config
        
        return path


if __name__ == "__main__":
    print("CSV Export Node - Export workflow data to CSV files")

