"""
Node Reloader - Hot-reload custom nodes without server restart

Dynamically reloads custom node modules and re-registers them in NodeRegistry.
Allows users to see new nodes immediately without restarting the backend.
"""

import logging
import sys
import importlib
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class NodeReloader:
    """
    Hot-reloads custom nodes without server restart.
    
    Process:
    1. Clear cached custom node modules from sys.modules
    2. Re-import all .py files from custom/ folder
    3. Modules auto-register themselves via @register_node decorator
    4. Return statistics
    """
    
    def __init__(self):
        """Initialize reloader"""
        # Get custom nodes directory
        current_file = Path(__file__)
        # node_reloader.py lives in: backend/app/services/
        # We want custom nodes in:   backend/app/core/nodes/custom/
        app_dir = current_file.parent.parent  # backend/app
        self.custom_nodes_dir = app_dir / "core" / "nodes" / "custom"
        
        logger.info(f"🔄 Node reloader initialized: {self.custom_nodes_dir}")
    
    async def reload_custom_nodes(self) -> Dict[str, Any]:
        """
        Reload all custom nodes.
        
        Returns:
            Dict with:
            - nodes_reloaded: Number of modules reloaded
            - errors: List of errors if any
        """
        logger.info("♻️ Starting custom nodes hot-reload...")
        
        errors = []
        reloaded_count = 0
        
        try:
            # Step 1: Clear cached custom node modules
            modules_to_clear = [
                mod_name for mod_name in sys.modules.keys()
                if mod_name.startswith('app.core.nodes.custom.') and not mod_name.endswith('__init__')
            ]
            
            for mod_name in modules_to_clear:
                try:
                    del sys.modules[mod_name]
                    logger.debug(f"  Cleared module: {mod_name}")
                except Exception as e:
                    logger.warning(f"  Could not clear {mod_name}: {e}")
            
            logger.info(f"  Cleared {len(modules_to_clear)} cached modules")
            
            # Step 2: Re-import all custom node files
            if not self.custom_nodes_dir.exists():
                logger.warning(f"⚠️ Custom nodes directory not found: {self.custom_nodes_dir}")
                return {
                    "nodes_reloaded": 0,
                    "errors": ["Custom nodes directory not found"]
                }
            
            # Import each .py file (excluding __init__.py)
            for py_file in self.custom_nodes_dir.glob("*.py"):
                if py_file.name.startswith('__'):
                    continue
                
                module_name = f"app.core.nodes.custom.{py_file.stem}"
                
                try:
                    # Import module (this triggers @register_node decorator)
                    importlib.import_module(module_name)
                    reloaded_count += 1
                    logger.debug(f"  ✅ Reloaded: {module_name}")
                
                except Exception as e:
                    error_msg = f"Failed to reload {module_name}: {str(e)}"
                    logger.error(f"  ❌ {error_msg}")
                    errors.append(error_msg)
            
            # Step 3: Get registry status
            from app.core.nodes.registry import NodeRegistry
            total_nodes = len(NodeRegistry.list_types())
            
            logger.info(f"✅ Hot-reload complete: {reloaded_count} modules reloaded, {total_nodes} nodes in registry")
            
            return {
                "nodes_reloaded": reloaded_count,
                "total_nodes_in_registry": total_nodes,
                "errors": errors
            }
        
        except Exception as e:
            logger.error(f"❌ Hot-reload failed: {e}", exc_info=True)
            errors.append(f"Hot-reload failed: {str(e)}")
            
            return {
                "nodes_reloaded": reloaded_count,
                "errors": errors
            }
    
    def get_custom_node_count(self) -> int:
        """
        Get count of custom node files.
        
        Returns:
            Number of .py files in custom/ folder (excluding __init__.py)
        """
        if not self.custom_nodes_dir.exists():
            return 0
        
        count = 0
        for py_file in self.custom_nodes_dir.glob("*.py"):
            if not py_file.name.startswith('__'):
                count += 1
        
        return count

