"""
File Listener Node - Poll folder for files and pause workflow

Polls a directory for files matching a pattern, blocks workflow execution
until a file is found. Similar to WhatsApp Listener but for files.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Set
from datetime import datetime
import hashlib

from app.core.nodes.base import Node, NodeExecutionInput
from app.core.nodes.registry import register_node
from app.schemas.workflow import NodeCategory, PortType
from app.utils.timezone import get_local_now

logger = logging.getLogger(__name__)


@register_node(
    node_type="file_listener",
    category=NodeCategory.PROCESSING,
    name="File Listener",
    description="Wait for file to appear in folder (polling mode). Pauses workflow until file found.",
    icon="fa-solid fa-file",
    version="1.0.0"
)
class FileListenerNode(Node):
    """
    File Listener Node - Wait for File in Folder (Polling)
    
    **How It Works:**
    1. Node executes and starts polling folder
    2. Workflow PAUSES (blocks execution)
    3. Polls every X seconds for files matching pattern
    4. When file found:
       - Returns file reference
       - Resumes workflow with file data
    
    **Features:**
    - Configurable polling interval (1-60 seconds)
    - Timeout support (max wait time)
    - File pattern matching (*.pdf, *.csv, etc.)
    - Network share support with credentials
    - Recursive folder scanning
    
    **Use Cases:**
    - Sequential file processing (wait for CSV, then PDF)
    - Password-dependent workflows (extract password, wait for encrypted file)
    - Multi-stage document workflows
    - Coordinated file arrivals
    
    **Differences from File Polling Trigger:**
    - This is a REGULAR NODE (not a trigger)
    - Runs WITHIN a workflow execution
    - Blocks execution until file found
    - Has INPUT PORT for dependency tracking
    - File Polling Trigger = starts workflow from outside
    - File Listener = waits for file from inside workflow
    
    **Requirements:**
    - Input connection (for execution order - can be any upstream node)
    - Watch folder must exist
    - Network credential (if using UNC path)
    
    ⚠️ **Important Notes:**
    - This pauses the workflow - no downstream nodes run while waiting
    - Long polling can tie up execution resources
    - Consider timeout to prevent infinite waiting
    - Use short intervals (5-10s) for near-realtime responsiveness
    - For automatic workflow starts, use File Polling Trigger instead
    """
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Define input ports"""
        return [
            {
                "name": "trigger",
                "type": PortType.SIGNAL,
                "display_name": "Trigger",
                "description": "Signal from upstream node to start listening",
                "required": False
            },
            {
                "name": "context",
                "type": PortType.UNIVERSAL,
                "display_name": "Context",
                "description": "Optional context data to pass through",
                "required": False
            }
        ]
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "file",
                "type": PortType.UNIVERSAL,
                "display_name": "File Reference",
                "description": "Standardized file reference (compatible with loaders)"
            },
            {
                "name": "file_name",
                "type": PortType.TEXT,
                "display_name": "File Name",
                "description": "Name of the detected file"
            },
            {
                "name": "file_path",
                "type": PortType.TEXT,
                "display_name": "File Path",
                "description": "Full path to the detected file"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "watch_folder": {
                "type": "string",
                "label": "Watch Folder",
                "description": "Folder path to monitor for files",
                "required": True,
                "placeholder": "C:\\Users\\YourName\\Desktop\\files or \\\\192.168.1.100\\share\\folder",
                "widget": "folder_picker",
                "help": "Full path to folder. Supports local paths and network shares (\\\\server\\share\\path)"
            },
            "network_credential": {
                "type": "string",
                "label": "Network Share Credential (Optional)",
                "description": "Credential for network share authentication",
                "required": False,
                "widget": "credential",
                "help": "Only needed for UNC network paths that require authentication. Create a Basic Auth credential with username/password."
            },
            "file_pattern": {
                "type": "string",
                "label": "File Pattern",
                "description": "File pattern to match (glob syntax)",
                "required": False,
                "default": "*",
                "placeholder": "*.pdf",
                "widget": "text",
                "help": "Examples: *.pdf, *.jpg, application_*.pdf, *"
            },
            "polling_interval": {
                "type": "integer",
                "label": "Polling Interval (seconds)",
                "description": "How often to check for files",
                "required": False,
                "default": 5,
                "widget": "number",
                "min": 1,
                "max": 3600,
                "help": "Checks folder every N seconds. 5-10s recommended for near-realtime."
            },
            "timeout_seconds": {
                "type": "integer",
                "label": "Timeout (seconds)",
                "description": "Maximum time to wait for file (0 = infinite)",
                "required": False,
                "default": 300,
                "widget": "number",
                "min": 0,
                "max": 86400,
                "help": "Workflow fails if no file found within timeout. 0 = wait forever."
            },
            "recursive": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Recursive Scan",
                "description": "Scan subdirectories recursively",
                "required": False,
                "default": False,
                "help": "Enable to monitor all subfolders"
            },
            "return_first": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Return First Match",
                "description": "Return immediately on first match, or wait for specific file",
                "required": False,
                "default": True,
                "help": "If true, returns first file found. If false, continues polling (useful with filtering)."
            },
            "delete_after_read": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Delete File After Processing",
                "description": "Delete the file after returning it (for one-time processing)",
                "required": False,
                "default": False,
                "help": "⚠️ Use with caution! File will be permanently deleted."
            },
            "ignore_existing": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Ignore Existing Files",
                "description": "Only return files that appear AFTER listener starts",
                "required": False,
                "default": True,
                "help": "Enable to wait for NEW files only. Disable to process any existing file."
            },
            "move_processed_files": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Move Processed Files",
                "description": "Move detected files to a separate folder to prevent reprocessing",
                "required": False,
                "default": False,
                "help": "When enabled, files are moved to a sibling '_processed' folder before workflow continues. Useful for demos or one-time processing scenarios."
            },
            "processed_folder_suffix": {
                "type": "string",
                "label": "Processed Folder Suffix",
                "description": "Suffix to append to watch folder name for processed files",
                "required": False,
                "default": "_processed",
                "placeholder": "_processed",
                "widget": "text",
                "help": "The processed folder will be: {watch_folder}{suffix} (e.g., C:\\Inbox → C:\\Inbox_processed)"
            }
        }
    
    async def execute(self, input_data: NodeExecutionInput) -> Dict[str, Any]:
        """
        Execute file listener - poll folder until file found.
        
        This method blocks workflow execution until a file is found or timeout occurs.
        """
        from app.utils.network_share import NetworkShareAuth
        from app.services.credential_manager import CredentialManager
        from app.database.session import SessionLocal
        
        # Get configuration
        watch_folder = self.resolve_config(input_data, "watch_folder")
        file_pattern = self.resolve_config(input_data, "file_pattern", "*")
        polling_interval = self.resolve_config(input_data, "polling_interval", 5)
        timeout_seconds = self.resolve_config(input_data, "timeout_seconds", 300)
        recursive = self.resolve_config(input_data, "recursive", False)
        return_first = self.resolve_config(input_data, "return_first", True)
        delete_after_read = self.resolve_config(input_data, "delete_after_read", False)
        ignore_existing = self.resolve_config(input_data, "ignore_existing", True)
        credential_id = self.config.get("network_credential")
        move_processed_files = self.resolve_config(input_data, "move_processed_files", False)
        processed_folder_suffix = self.resolve_config(input_data, "processed_folder_suffix", "_processed")
        
        if not watch_folder:
            error_msg = "Watch folder is required"
            logger.error(f"❌ {error_msg}")
            return {
                "file": None,
                "file_name": "",
                "file_path": "",
                "error": error_msg
            }
        
        # Check if network share and mount if needed
        is_network = NetworkShareAuth.is_unc_path(watch_folder)
        if is_network:
            logger.info(f"📡 Detected network share: {watch_folder}")
            
            if credential_id:
                # Load credentials
                db = SessionLocal()
                try:
                    cred_manager = CredentialManager(db)
                    cred_data = cred_manager.get_credential_data(credential_id=int(credential_id))
                    
                    if cred_data:
                        username = cred_data.get('username')
                        password = cred_data.get('password')
                        
                        logger.info(f"🔐 Loaded credentials for user: {username}")
                        
                        # Parse and mount share
                        parsed = NetworkShareAuth.parse_unc_path(watch_folder)
                        if parsed:
                            logger.info(f"🔐 Attempting to mount network share: {parsed['share_path']}")
                            
                            result = NetworkShareAuth.mount_network_share(
                                share_path=parsed['share_path'],
                                username=username,
                                password=password
                            )
                            
                            if not result['success']:
                                error_msg = f"Failed to mount network share: {result.get('error')}"
                                logger.error(f"❌ {error_msg}")
                                return {
                                    "file": None,
                                    "file_name": "",
                                    "file_path": "",
                                    "error": error_msg
                                }
                            else:
                                logger.info(f"✅ Network share mounted successfully")
                        else:
                            error_msg = f"Failed to parse UNC path: {watch_folder}"
                            logger.error(f"❌ {error_msg}")
                            return {
                                "file": None,
                                "file_name": "",
                                "file_path": "",
                                "error": error_msg
                            }
                    else:
                        error_msg = f"Credential ID {credential_id} not found"
                        logger.error(f"❌ {error_msg}")
                        return {
                            "file": None,
                            "file_name": "",
                            "file_path": "",
                            "error": error_msg
                        }
                except Exception as e:
                    error_msg = f"Error loading credentials: {e}"
                    logger.error(f"❌ {error_msg}", exc_info=True)
                    return {
                        "file": None,
                        "file_name": "",
                        "file_path": "",
                        "error": error_msg
                    }
                finally:
                    db.close()
            else:
                logger.warning(f"⚠️  Network share detected but no credential provided")
                logger.warning(f"   Will attempt to access using current Windows credentials")
        
        watch_path = Path(watch_folder)
        
        # Test if path exists
        if not watch_path.exists():
            error_msg = f"Watch folder does not exist: {watch_folder}"
            logger.error(f"❌ {error_msg}")
            return {
                "file": None,
                "file_name": "",
                "file_path": "",
                "error": error_msg
            }
        
        # Test read permissions
        try:
            test_list = list(watch_path.iterdir())
            logger.info(f"✅ Successfully listed directory, found {len(test_list)} items")
        except PermissionError as e:
            error_msg = f"Permission denied accessing folder: {e}"
            logger.error(f"❌ {error_msg}")
            return {
                "file": None,
                "file_name": "",
                "file_path": "",
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Error accessing folder: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                "file": None,
                "file_name": "",
                "file_path": "",
                "error": error_msg
            }
        
        logger.info(
            f"👁️ File Listener started:\n"
            f"  Watching: {watch_path}\n"
            f"  Pattern: {file_pattern}\n"
            f"  Interval: {polling_interval}s\n"
            f"  Timeout: {timeout_seconds}s{'(infinite)' if timeout_seconds == 0 else ''}\n"
            f"  Recursive: {recursive}\n"
            f"  Ignore Existing: {ignore_existing}"
        )
        
        # Track existing files if ignore_existing=True
        existing_files = set()
        if ignore_existing:
            try:
                initial_files = self._scan_folder(watch_path, file_pattern, recursive)
                for file_path in initial_files:
                    file_hash = self._get_file_hash(file_path)
                    existing_files.add(file_hash)
                logger.info(f"📂 Initial scan: {len(initial_files)} existing files will be ignored")
            except Exception as e:
                logger.warning(f"⚠️  Could not scan for existing files: {e}")
        
        # Start polling loop
        start_time = datetime.now()
        file_found = None
        elapsed = 0
        loop_count = 0
        
        while True:
            # Check timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if timeout_seconds > 0 and elapsed >= timeout_seconds:
                error_msg = f"Timeout after {elapsed:.1f}s - no file found matching pattern '{file_pattern}'"
                logger.error(f"⏱️ {error_msg}")
                return {
                    "file": None,
                    "file_name": "",
                    "file_path": "",
                    "error": error_msg,
                    "timeout": True,
                    "elapsed_seconds": elapsed
                }
            
            # Poll for files
            loop_count += 1
            logger.debug(f"🔍 Polling for files... (loop #{loop_count}, elapsed: {elapsed:.1f}s)")
            
            try:
                files = self._scan_folder(watch_path, file_pattern, recursive)
                logger.debug(f"   Found {len(files)} file(s) matching pattern '{file_pattern}'")
                
                # Filter out existing files if ignore_existing=True
                if ignore_existing and files:
                    new_files = []
                    for file_path in files:
                        file_hash = self._get_file_hash(file_path)
                        if file_hash not in existing_files:
                            new_files.append(file_path)
                    files = new_files
                    if files:
                        logger.debug(f"   {len(files)} NEW file(s) after filtering existing")
                
                if files:
                    # Found file(s)!
                    file_found = files[0]  # Get first match
                    logger.info(
                        f"✅ File found: {file_found.name}\n"
                        f"  Path: {file_found}\n"
                        f"  Wait time: {elapsed:.1f}s"
                    )
                    
                    # Move file to processed folder if enabled (before delete_after_read check)
                    if move_processed_files:
                        file_found = self._move_file_to_processed(
                            file_found, 
                            watch_path, 
                            processed_folder_suffix
                        )
                    
                    # Build file reference (with potentially new path)
                    file_ref = self._build_file_reference(file_found)
                    
                    # Delete file if requested (note: this happens after move if both enabled)
                    if delete_after_read:
                        try:
                            file_found.unlink()
                            logger.info(f"🗑️  Deleted file after processing: {file_found.name}")
                        except Exception as e:
                            logger.warning(f"⚠️  Could not delete file: {e}")
                    
                    return {
                        "file": file_ref,
                        "file_name": file_found.name,
                        "file_path": str(file_found.absolute()),
                        "elapsed_seconds": elapsed
                    }
                
            except Exception as e:
                logger.error(f"❌ Error scanning folder: {e}", exc_info=True)
                # Continue polling even if one scan fails
            
            # Not found - wait and try again
            logger.debug(f"   No files found, waiting {polling_interval}s...")
            await asyncio.sleep(polling_interval)
    
    def _get_file_hash(self, file_path: Path) -> str:
        """
        Get unique identifier for file.
        Uses path + size + mtime for identification.
        """
        try:
            stat = file_path.stat()
            identifier = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
            return hashlib.md5(identifier.encode()).hexdigest()
        except Exception as e:
            logger.error(f"❌ Error getting file hash for {file_path}: {e}")
            # Fallback to just path
            return hashlib.md5(str(file_path).encode()).hexdigest()
    
    def _move_file_to_processed(self, file_path: Path, watch_folder: Path, suffix: str = "_processed") -> Path:
        """
        Move a file to the processed folder.
        
        Creates a sibling folder with the given suffix (e.g., Inbox → Inbox_processed)
        and moves the file there. Returns the new file path.
        
        Args:
            file_path: Path to the file to move
            watch_folder: The original watch folder path
            suffix: Suffix to append to create processed folder name
            
        Returns:
            New path of the moved file
        """
        import shutil
        
        try:
            # Create processed folder path (sibling of watch folder)
            # e.g., C:\Inbox → C:\Inbox_processed
            processed_folder = watch_folder.parent / f"{watch_folder.name}{suffix}"
            
            # Create the processed folder if it doesn't exist
            processed_folder.mkdir(parents=True, exist_ok=True)
            
            # Determine new file path
            new_file_path = processed_folder / file_path.name
            
            # Handle name conflicts by adding a counter
            counter = 1
            original_stem = file_path.stem
            original_suffix = file_path.suffix
            while new_file_path.exists():
                new_file_path = processed_folder / f"{original_stem}_{counter}{original_suffix}"
                counter += 1
            
            # Move the file
            shutil.move(str(file_path), str(new_file_path))
            
            logger.info(f"📦 Moved file to processed folder: {file_path.name} → {new_file_path}")
            
            return new_file_path
            
        except Exception as e:
            logger.error(f"❌ Error moving file to processed folder: {e}", exc_info=True)
            # Return original path if move fails - workflow will still work
            return file_path
    
    def _scan_folder(self, folder: Path, pattern: str, recursive: bool) -> List[Path]:
        """Scan folder for files matching pattern"""
        try:
            if recursive:
                # Recursive glob: folder/**/*.pdf
                files = list(folder.rglob(pattern))
            else:
                # Non-recursive glob: folder/*.pdf
                files = list(folder.glob(pattern))
            
            # Filter to only files (not directories)
            files = [f for f in files if f.is_file()]
            
            # Sort by modification time (newest first)
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            return files
        
        except Exception as e:
            logger.error(f"❌ Error scanning folder {folder}: {e}")
            return []
    
    def _build_file_reference(self, file_path: Path) -> Dict[str, Any]:
        """
        Build standardized MediaFormat file reference.
        
        Compatible with Document Loader, Image Loader, Email Composer, etc.
        Uses the proper MediaFormat structure for consistency across all nodes.
        """
        try:
            import mimetypes
            from app.core.nodes.multimodal import (
                ImageFormatter, AudioFormatter, VideoFormatter, DocumentFormatter
            )
            
            stat = file_path.stat()
            
            # Detect MIME type
            mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
            
            # Build metadata for the formatters
            metadata = {
                "filename": file_path.name,
                "mime_type": mime_type,
                "size_bytes": stat.st_size,
                "extension": file_path.suffix,
                "parent_folder": str(file_path.parent),
                "absolute_path": str(file_path.absolute())
            }
            
            # Use appropriate MediaFormat formatter based on MIME type
            file_path_str = str(file_path.absolute())
            
            if mime_type.startswith("image/"):
                return ImageFormatter.from_file_path(file_path_str, metadata=metadata)
            elif mime_type.startswith("audio/"):
                return AudioFormatter.from_file_path(file_path_str, metadata=metadata)
            elif mime_type.startswith("video/"):
                return VideoFormatter.from_file_path(file_path_str, metadata=metadata)
            else:
                # Default to document for PDFs, Office docs, text files, and unknown types
                return DocumentFormatter.from_file_path(file_path_str, metadata=metadata)
        
        except Exception as e:
            logger.error(f"❌ Error building file reference for {file_path}: {e}", exc_info=True)
            # Fallback: still use MediaFormat structure for consistency
            from app.core.nodes.multimodal import DocumentFormatter
            return DocumentFormatter.from_file_path(
                str(file_path),
                metadata={"filename": file_path.name, "error": str(e)}
            )


if __name__ == "__main__":
    print("File Listener Node - Wait for files in folder (polling mode)")

