"""
Node Saver - Save custom node code to filesystem

Handles file system operations for saving custom nodes to the custom/ folder.
Includes filename sanitization and safety checks.
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class NodeSaver:
    """
    Saves custom node code to filesystem.
    
    Security:
    - Filename sanitization (prevents directory traversal)
    - Only writes to custom/ folder
    - Validates node_type format
    """
    
    def __init__(self):
        """Initialize node saver with custom nodes directory"""
        # Get custom nodes directory
        current_file = Path(__file__)
        # node_saver.py lives in: backend/app/services/
        # We want custom nodes in:   backend/app/core/nodes/custom/
        app_dir = current_file.parent.parent  # backend/app
        self.custom_nodes_dir = app_dir / "core" / "nodes" / "custom"
        
        # Ensure directory exists
        self.custom_nodes_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 Custom nodes directory: {self.custom_nodes_dir}")
    
    def save_node(
        self, 
        code: str, 
        node_type: str, 
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Save node code to filesystem.
        
        Args:
            code: Python code to save
            node_type: Node type identifier (becomes filename)
            overwrite: Allow overwriting existing file
        
        Returns:
            Dict with:
            - file_path: Where file was saved
            - message: Success message
        
        Raises:
            FileExistsError: If file exists and overwrite=False
            ValueError: If node_type is invalid
        """
        logger.info(f"💾 Saving node: {node_type}")
        
        # Sanitize node_type
        sanitized_type = self._sanitize_node_type(node_type)
        
        if not sanitized_type:
            raise ValueError(f"Invalid node_type: '{node_type}'. Must contain only letters, numbers, and underscores.")
        
        # Create filename
        filename = f"{sanitized_type}.py"
        file_path = self.custom_nodes_dir / filename
        
        # Check if file exists
        if file_path.exists() and not overwrite:
            raise FileExistsError(
                f"Node file '{filename}' already exists. "
                "Set overwrite=True to replace it."
            )
        
        # Write file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            logger.info(f"✅ Node saved: {file_path}")
            
            return {
                "file_path": str(file_path),
                "message": f"Node saved successfully: {filename}"
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to save node: {e}", exc_info=True)
            raise Exception(f"Failed to save node file: {str(e)}")
    
    def delete_node(self, node_type: str) -> str:
        """
        Delete a custom node file.
        
        Args:
            node_type: Node type identifier
        
        Returns:
            Path of deleted file
        
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        logger.info(f"🗑️ Deleting node: {node_type}")
        
        # Sanitize
        sanitized_type = self._sanitize_node_type(node_type)
        filename = f"{sanitized_type}.py"
        file_path = self.custom_nodes_dir / filename
        
        # Check if file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Node file '{filename}' not found")
        
        # Security: Ensure file is in custom directory
        if not self._is_in_custom_directory(file_path):
            raise ValueError(f"File is not in custom nodes directory")
        
        # Delete file
        try:
            os.remove(file_path)
            logger.info(f"✅ Node deleted: {file_path}")
            return str(file_path)
        
        except Exception as e:
            logger.error(f"❌ Failed to delete node: {e}", exc_info=True)
            raise Exception(f"Failed to delete node file: {str(e)}")
    
    def list_custom_nodes(self) -> List[Dict[str, Any]]:
        """
        List all custom node files.
        
        Returns:
            List of dicts with file info:
            - node_type: Node type from filename
            - file_name: Filename
            - file_path: Full path
            - size_bytes: File size
            - modified_at: Last modified timestamp
        """
        logger.info("📋 Listing custom nodes")
        
        nodes = []
        
        try:
            # List all .py files in custom directory
            for file_path in self.custom_nodes_dir.glob("*.py"):
                # Skip __init__.py and __pycache__
                if file_path.name.startswith('__'):
                    continue
                
                # Get file stats
                stat = file_path.stat()
                
                # Extract node_type from filename
                node_type = file_path.stem  # filename without .py extension
                
                nodes.append({
                    "node_type": node_type,
                    "file_name": file_path.name,
                    "file_path": str(file_path),
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            
            logger.info(f"✅ Found {len(nodes)} custom nodes")
            return nodes
        
        except Exception as e:
            logger.error(f"❌ Failed to list nodes: {e}", exc_info=True)
            return []
    
    def _sanitize_node_type(self, node_type: str) -> str:
        """
        Sanitize node_type to prevent directory traversal.
        
        Only allows: letters, numbers, underscores
        Converts to snake_case
        """
        # Remove any path separators
        node_type = node_type.replace('/', '').replace('\\', '').replace('..', '')
        
        # Only allow alphanumeric and underscores
        sanitized = re.sub(r'[^a-z0-9_]', '', node_type.lower())
        
        # Must start with letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'node_' + sanitized
        
        return sanitized
    
    def _is_in_custom_directory(self, file_path: Path) -> bool:
        """
        Security check: Ensure file is within custom nodes directory.
        """
        try:
            # Resolve to absolute paths
            file_abs = file_path.resolve()
            custom_abs = self.custom_nodes_dir.resolve()
            
            # Check if file is under custom directory
            return str(file_abs).startswith(str(custom_abs))
        
        except Exception:
            return False

