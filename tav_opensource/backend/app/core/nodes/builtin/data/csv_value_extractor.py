"""
Value Extractor Node - Extract specific values from structured data

Extract cells, rows, columns, or multiple values from arrays/objects.
Outputs can be used as variables in downstream nodes.
"""

import logging
from typing import Dict, Any, List, Union

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="csv_value_extractor",
    category=NodeCategory.PROCESSING,
    name="CSV Value Extractor",
    description="Extract specific values, rows, or columns from structured data",
    icon="fa-solid fa-filter",
    version="1.0.0"
)
class CSVValueExtractorNode(Node):
    """
    Value Extractor Node - Extract data from arrays and objects
    
    Input: Structured data (array of objects from CSV Reader, JSON Parser, etc.)
    Output: Extracted value(s) based on configuration
    
    Extraction Modes:
    1. **Cell** - Extract specific value (row + column)
       - Input: [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
       - Config: row=0, column="name"
       - Output: "John"
    
    2. **Row** - Extract entire row as object
       - Input: [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
       - Config: row=0
       - Output: {"name": "John", "age": 30}
    
    3. **Column** - Extract entire column as array
       - Input: [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
       - Config: column="name"
       - Output: ["John", "Jane"]
    
    4. **Multiple Values** - Extract several specific values
       - Config: Multiple row+column pairs
       - Output: {"value1": "John", "value2": 25, ...}
    
    Variable Reference Guide:
    When "Share output to variables" is enabled, reference specific output ports:
    - ${node_name.value} - Main extracted value (cell, row, or column)
    - ${node_name.row_data} - Full row object (when extracting row/cell)
    - ${node_name.row_data.column_name} - Specific field from row
    - ${node_name.column_data} - Full column array (when extracting column)
    - ${node_name.column_data[0]} - First value in column
    - ${node_name.metadata} - Extraction metadata
    
    Example: ${CSV_Extractor.value} → "John"
             ${CSV_Extractor.row_data.age} → "30"
    
    Use Cases:
    - Extract specific values from CSV for variables
    - Get user data from specific rows
    - Extract column for batch processing
    - Build custom data structures
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "data",
                "type": PortType.UNIVERSAL,
                "display_name": "Data",
                "description": "Structured data (array of objects)",
                "required": True
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "value",
                "type": PortType.UNIVERSAL,
                "display_name": "Extracted Value",
                "description": "Primary extracted value (cell, row, or column)"
            },
            {
                "name": "row_data",
                "type": PortType.UNIVERSAL,
                "display_name": "Row Data",
                "description": "Full row object (if row extraction)"
            },
            {
                "name": "column_data",
                "type": PortType.UNIVERSAL,
                "display_name": "Column Data",
                "description": "Full column array (if column extraction)"
            },
            {
                "name": "all_values",
                "type": PortType.UNIVERSAL,
                "display_name": "All Values",
                "description": "All extracted values (for multiple extraction mode)"
            },
            {
                "name": "metadata",
                "type": PortType.UNIVERSAL,
                "display_name": "Metadata",
                "description": "Extraction metadata and statistics"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "extraction_mode": {
                "type": "select",
                "label": "Extraction Mode",
                "description": "What to extract from the data",
                "required": True,
                "default": "cell",
                "widget": "select",
                "options": [
                    {"label": "Cell (specific row + column)", "value": "cell"},
                    {"label": "Row (entire row)", "value": "row"},
                    {"label": "Column (entire column)", "value": "column"},
                    {"label": "First Row", "value": "first_row"},
                    {"label": "Last Row", "value": "last_row"},
                    {"label": "All Data (pass through)", "value": "all"}
                ],
                "help": "Choose what type of data to extract"
            },
            "row_index": {
                "type": "integer",
                "label": "Row Index",
                "description": "Row number to extract (0-based, first row = 0)",
                "required": False,
                "default": 0,
                "widget": "number",
                "min": 0,
                "help": "For cell or row extraction. 0 = first row, 1 = second row, etc."
            },
            "column_name": {
                "type": "string",
                "label": "Column Name",
                "description": "Column/field name to extract",
                "required": False,
                "placeholder": "name",
                "widget": "text",
                "help": "For cell or column extraction. Use exact column name from CSV headers."
            },
            "default_value": {
                "type": "string",
                "label": "Default Value (Optional)",
                "description": "Value to return if extraction fails or data not found",
                "required": False,
                "placeholder": "(empty)",
                "widget": "text",
                "help": "Leave empty to return null on failure, or provide a default value"
            },
            "fail_on_missing": {
                "type": "boolean",
                "label": "Fail on Missing Data",
                "description": "Throw error if requested data doesn't exist",
                "required": False,
                "default": False,
                "widget": "checkbox",
                "help": "Enable to fail workflow if data not found. Disable to use default value."
            }
        }
    
    async def execute(self, inputs: NodeExecutionInput) -> Dict[str, Any]:
        """Execute value extractor node."""
        try:
            # Get input data
            data = inputs.ports.get("data")
            
            logger.info(f"🔍 Value Extractor received data type: {type(data)}")
            
            if data is None:
                if self.resolve_config(inputs, "fail_on_missing", False):
                    raise ValueError("No data provided to extract from")
                return self._return_default(inputs, "No data provided")
            
            # Get config
            mode = self.resolve_config(inputs, "extraction_mode", "cell")
            row_index = self.resolve_config(inputs, "row_index", 0)
            column_name = self.resolve_config(inputs, "column_name", "")
            fail_on_missing = self.resolve_config(inputs, "fail_on_missing", False)
            
            logger.info(f"🔧 Extraction mode: {mode}, row: {row_index}, column: {column_name}")
            
            # Ensure data is a list
            if not isinstance(data, list):
                # Try to convert single object to list
                if isinstance(data, dict):
                    data = [data]
                else:
                    if fail_on_missing:
                        raise ValueError(f"Expected array/list data, got {type(data)}")
                    return self._return_default(inputs, f"Invalid data type: {type(data)}")
            
            if len(data) == 0:
                if fail_on_missing:
                    raise ValueError("Data array is empty")
                return self._return_default(inputs, "Empty data array")
            
            # Execute extraction based on mode
            if mode == "cell":
                return self._extract_cell(data, row_index, column_name, inputs, fail_on_missing)
            
            elif mode == "row":
                return self._extract_row(data, row_index, inputs, fail_on_missing)
            
            elif mode == "column":
                return self._extract_column(data, column_name, inputs, fail_on_missing)
            
            elif mode == "first_row":
                return self._extract_row(data, 0, inputs, fail_on_missing)
            
            elif mode == "last_row":
                return self._extract_row(data, len(data) - 1, inputs, fail_on_missing)
            
            elif mode == "all":
                return {
                    "value": data,
                    "all_values": data,
                    "metadata": {
                        "mode": "all",
                        "row_count": len(data),
                        "success": True
                    }
                }
            
            else:
                raise ValueError(f"Unknown extraction mode: {mode}")
        
        except Exception as e:
            logger.error(f"❌ Value Extractor failed: {e}", exc_info=True)
            raise
    
    def _extract_cell(
        self,
        data: List[Dict[str, Any]],
        row_index: int,
        column_name: str,
        inputs: NodeExecutionInput,
        fail_on_missing: bool
    ) -> Dict[str, Any]:
        """Extract specific cell value (row + column)"""
        
        if not column_name or not column_name.strip():
            if fail_on_missing:
                raise ValueError("Column name is required for cell extraction")
            return self._return_default(inputs, "No column name provided")
        
        # Check row exists
        if row_index < 0 or row_index >= len(data):
            if fail_on_missing:
                raise ValueError(f"Row index {row_index} out of range (0-{len(data)-1})")
            return self._return_default(inputs, f"Row {row_index} not found")
        
        row = data[row_index]
        
        if not isinstance(row, dict):
            if fail_on_missing:
                raise ValueError(f"Row {row_index} is not a dictionary/object")
            return self._return_default(inputs, f"Invalid row type: {type(row)}")
        
        # Extract value
        if column_name not in row:
            if fail_on_missing:
                raise ValueError(f"Column '{column_name}' not found in row {row_index}")
            return self._return_default(inputs, f"Column '{column_name}' not found")
        
        cell_value = row[column_name]
        
        logger.info(f"✅ Extracted cell [row {row_index}]['{column_name}']: {repr(cell_value)}")
        
        return {
            "value": cell_value,
            "row_data": row,
            "all_values": {
                "cell_value": cell_value,
                "row_index": row_index,
                "column_name": column_name
            },
            "metadata": {
                "mode": "cell",
                "row_index": row_index,
                "column_name": column_name,
                "value_type": type(cell_value).__name__,
                "success": True
            }
        }
    
    def _extract_row(
        self,
        data: List[Dict[str, Any]],
        row_index: int,
        inputs: NodeExecutionInput,
        fail_on_missing: bool
    ) -> Dict[str, Any]:
        """Extract entire row as object"""
        
        # Check row exists
        if row_index < 0 or row_index >= len(data):
            if fail_on_missing:
                raise ValueError(f"Row index {row_index} out of range (0-{len(data)-1})")
            return self._return_default(inputs, f"Row {row_index} not found")
        
        row = data[row_index]
        
        logger.info(f"✅ Extracted row {row_index}: {str(row)[:200]}")
        
        return {
            "value": row,
            "row_data": row,
            "all_values": row,
            "metadata": {
                "mode": "row",
                "row_index": row_index,
                "column_count": len(row) if isinstance(row, dict) else 1,
                "columns": list(row.keys()) if isinstance(row, dict) else [],
                "success": True
            }
        }
    
    def _extract_column(
        self,
        data: List[Dict[str, Any]],
        column_name: str,
        inputs: NodeExecutionInput,
        fail_on_missing: bool
    ) -> Dict[str, Any]:
        """Extract entire column as array"""
        
        if not column_name or not column_name.strip():
            if fail_on_missing:
                raise ValueError("Column name is required for column extraction")
            return self._return_default(inputs, "No column name provided")
        
        # Extract column values from all rows
        column_values = []
        missing_count = 0
        
        for i, row in enumerate(data):
            if isinstance(row, dict):
                if column_name in row:
                    column_values.append(row[column_name])
                else:
                    missing_count += 1
                    column_values.append(None)  # Add None for missing values
            else:
                missing_count += 1
                column_values.append(None)
        
        if missing_count == len(data):
            # Column doesn't exist in any row
            if fail_on_missing:
                raise ValueError(f"Column '{column_name}' not found in any row")
            return self._return_default(inputs, f"Column '{column_name}' not found")
        
        logger.info(f"✅ Extracted column '{column_name}': {len(column_values)} values")
        if missing_count > 0:
            logger.warning(f"⚠️ Column '{column_name}' missing in {missing_count} rows")
        
        return {
            "value": column_values,
            "column_data": column_values,
            "all_values": {
                "column_name": column_name,
                "values": column_values,
                "count": len(column_values)
            },
            "metadata": {
                "mode": "column",
                "column_name": column_name,
                "value_count": len(column_values),
                "missing_count": missing_count,
                "success": True
            }
        }
    
    def _return_default(self, inputs: NodeExecutionInput, reason: str) -> Dict[str, Any]:
        """Return default value when extraction fails"""
        default_value = self.resolve_config(inputs, "default_value", None)
        
        logger.warning(f"⚠️ Using default value: {reason}")
        
        return {
            "value": default_value,
            "metadata": {
                "success": False,
                "reason": reason,
                "used_default": True,
                "default_value": default_value
            }
        }


if __name__ == "__main__":
    print("Value Extractor Node - Extract specific values from structured data")

