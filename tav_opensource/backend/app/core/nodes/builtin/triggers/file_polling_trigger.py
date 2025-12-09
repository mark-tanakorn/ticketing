"""
File Polling Trigger Node

Monitors a folder for new files and triggers workflow when files are detected.
Uses polling mechanism (checks periodically) instead of real-time watching.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Callable, Awaitable, Set, List
import hashlib

from app.utils.timezone import get_local_now

from app.core.nodes import Node, NodeExecutionInput, TriggerCapability, register_node
from app.schemas.workflow import NodeCategory, PortType

logger = logging.getLogger(__name__)


@register_node(
    node_type="file_polling_trigger",
    category=NodeCategory.TRIGGERS,
    name="File Polling Trigger",
    description="Monitors folder for new files and triggers workflow (polling-based)",
    icon="fa-solid fa-folder-open",
    version="1.0.0"
)
class FilePollingTriggerNode(Node, TriggerCapability):
    """
    File Polling Trigger - Monitor folder for new files
    
    Polls a directory at regular intervals and triggers workflow when new files are detected.
    
    Features:
    - Periodic polling (configurable interval)
    - File pattern matching (*.pdf, *.jpg, etc.)
    - Track processed files to avoid duplicates
    - Pass file path and metadata to workflow
    - Optional recursive scanning
    
    How it works:
    1. Every N seconds, scans the target folder
    2. Identifies new files (not seen before)
    3. Triggers workflow with file information
    4. Marks file as processed
    
    Use Cases:
    - Document processing workflows
    - File ingestion pipelines
    - Automatic form processing
    - Scanned document handling
    """
    
    trigger_type = "file_polling"  # Used for execution_source tracking
    
    # Class-level storage for processed files (per node instance)
    # In production, this should be persisted to DB for multi-instance deployments
    _processed_files: Dict[str, Set[str]] = {}  # node_id -> set of file hashes
    
    @classmethod
    def get_input_ports(cls) -> List[Dict[str, Any]]:
        """Triggers typically have NO input ports - they start the workflow"""
        return []
    
    @classmethod
    def get_output_ports(cls) -> List[Dict[str, Any]]:
        """Define output ports"""
        return [
            {
                "name": "file",
                "type": PortType.UNIVERSAL,
                "display_name": "File Reference",
                "description": "Standardized file reference (for Document/Image/Audio loaders)"
            },
            {
                "name": "file_name",
                "type": PortType.UNIVERSAL,
                "display_name": "File Name",
                "description": "Name of the detected file"
            }
        ]
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define configuration schema"""
        return {
            "watch_folder": {
                "type": "string",
                "label": "Watch Folder",
                "description": "Folder path to monitor for new files (supports UNC paths like \\\\server\\share\\path)",
                "required": True,
                "placeholder": "C:\\Users\\YourName\\Desktop\\uploads or \\\\192.168.1.100\\shared\\folder",
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
                "description": "How often to check for new files",
                "required": False,
                "default": 10,
                "widget": "number",
                "min": 1,
                "max": 3600,
                "help": "Checks folder every N seconds"
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
            "trigger_mode": {
                "type": "select",
                "widget": "select",
                "label": "Trigger Mode",
                "description": "When to trigger workflow",
                "required": False,
                "default": "per_file",
                "options": [
                    {"label": "Per File (separate execution for each file)", "value": "per_file"},
                    {"label": "Batch (single execution for all new files)", "value": "batch"}
                ],
                "help": "Per file = one workflow per file, Batch = one workflow for multiple files"
            },
            "ignore_existing": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Ignore Existing Files",
                "description": "Only trigger on files created after trigger starts",
                "required": False,
                "default": True,
                "help": "Enable to skip files that already exist when trigger starts"
            },
            "move_processed_files": {
                "type": "boolean",
                "widget": "checkbox",
                "label": "Move Processed Files",
                "description": "Move detected files to a separate folder to prevent reprocessing",
                "required": False,
                "default": False,
                "help": "When enabled, files are moved to a sibling '_processed' folder before workflow runs. Useful for demos or one-time processing scenarios."
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
        Execute trigger - returns trigger data that was injected into execution context.
        
        When a trigger fires via fire_trigger(), the trigger data is injected into the
        execution context under "trigger_data" key.
        
        Returns output in the format expected by downstream nodes.
        """
        logger.info(f"📤 File polling trigger execute() - extracting trigger data")
        
        # The trigger data was injected into variables["trigger_data"] by the orchestrator
        trigger_data = input_data.variables.get("trigger_data", {})
        
        logger.info(f"   Available variables: {list(input_data.variables.keys())}")
        logger.info(f"   Trigger data keys: {list(trigger_data.keys())}")
        logger.info(f"   File data: {trigger_data.get('file')}")
        
        # Return the trigger data fields as our output ports
        return {
            "file": trigger_data.get("file"),
            "file_name": trigger_data.get("file_name"),
            "signal": trigger_data.get("signal", "file_detected")
        }
    
    async def start_monitoring(
        self,
        workflow_id: str,
        executor_callback: Callable[[str, Dict[str, Any], str], Awaitable[None]]
    ):
        """
        Start monitoring - required by TriggerCapability.
        
        This method is called by the trigger manager to start monitoring.
        It runs in a background task and calls executor_callback when files are detected.
        
        Args:
            workflow_id: ID of the workflow being monitored
            executor_callback: Async function to call when trigger fires
        """
        self._workflow_id = workflow_id
        self._executor_callback = executor_callback
        self._is_monitoring = True
        
        # Start polling loop in background
        self._monitoring_task = asyncio.create_task(self._polling_loop())
        
        logger.info(f"✅ File polling trigger monitoring started: {self.node_id}")
    
    async def stop_monitoring(self):
        """
        Stop monitoring - required by TriggerCapability.
        
        Called by trigger manager to stop this trigger.
        """
        self._is_monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        logger.info(f"⏹️ File polling trigger monitoring stopped: {self.node_id}")
    
    async def _polling_loop(self):
        """
        Internal polling loop that monitors the folder.
        
        This runs continuously until stop_monitoring() is called.
        """
        from app.utils.network_share import NetworkShareAuth
        from app.services.credential_manager import CredentialManager
        from app.database.session import SessionLocal
        
        # Get configuration
        watch_folder = self.config.get("watch_folder")
        file_pattern = self.config.get("file_pattern", "*")
        polling_interval = self.config.get("polling_interval", 10)
        recursive = self.config.get("recursive", False)
        trigger_mode = self.config.get("trigger_mode", "per_file")
        ignore_existing = self.config.get("ignore_existing", True)
        credential_id = self.config.get("network_credential")
        move_processed_files = self.config.get("move_processed_files", False)
        processed_folder_suffix = self.config.get("processed_folder_suffix", "_processed")
        
        if not watch_folder:
            logger.error(f"❌ File polling trigger {self.node_id}: watch_folder not configured")
            return
        
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
                            logger.info(f"   Server: {parsed['server']}")
                            logger.info(f"   Share: {parsed['share']}")
                            logger.info(f"   Path: {parsed.get('path', '(root)')}")
                            
                            result = NetworkShareAuth.mount_network_share(
                                share_path=parsed['share_path'],
                                username=username,
                                password=password
                            )
                            
                            if not result['success']:
                                logger.error(f"❌ Failed to mount network share: {result.get('error')}")
                                logger.error(f"   This could be due to:")
                                logger.error(f"   - Invalid credentials (wrong username/password)")
                                logger.error(f"   - Network connectivity issues (server unreachable)")
                                logger.error(f"   - Share permissions (user not authorized)")
                                logger.error(f"   - Share path incorrect or doesn't exist")
                                return
                            else:
                                logger.info(f"✅ Network share mounted successfully")
                        else:
                            logger.error(f"❌ Failed to parse UNC path: {watch_folder}")
                            return
                    else:
                        logger.error(f"❌ Credential ID {credential_id} not found or has no data")
                        return
                except Exception as e:
                    logger.error(f"❌ Error loading credentials: {e}", exc_info=True)
                    return
                finally:
                    db.close()
            else:
                logger.warning(f"⚠️  Network share detected but no credential provided")
                logger.warning(f"   Will attempt to access using current Windows credentials")
                logger.warning(f"   If access fails, please configure a network credential")
        
        watch_path = Path(watch_folder)
        
        # Test if path exists and log details
        if not watch_path.exists():
            logger.error(f"❌ File polling trigger {self.node_id}: folder does not exist: {watch_folder}")
            logger.error(f"   Absolute path attempted: {watch_path.absolute()}")
            logger.error(f"   Is network path: {is_network}")
            if is_network:
                logger.error(f"   Troubleshooting steps:")
                logger.error(f"   1. Verify the network path is correct and accessible")
                logger.error(f"   2. Test access manually: Open Windows Explorer and navigate to {watch_folder}")
                logger.error(f"   3. Check if credentials are correct (username/password)")
                logger.error(f"   4. Ensure the TAV Engine backend has network access to the server")
                logger.error(f"   5. Try mapping the network drive manually first (net use command)")
            return
        
        # Log successful path access
        logger.info(f"✅ Watch folder exists and is accessible: {watch_path}")
        try:
            # Test read permissions by attempting to list directory
            test_list = list(watch_path.iterdir())
            logger.info(f"✅ Successfully listed directory, found {len(test_list)} items")
        except PermissionError as e:
            logger.error(f"❌ Permission denied accessing folder: {e}")
            logger.error(f"   The folder exists but TAV Engine doesn't have permission to read it")
            return
        except Exception as e:
            logger.error(f"❌ Error accessing folder: {e}", exc_info=True)
            return
        
        logger.info(f"👁️ File polling trigger started: {self.node_id}")
        logger.info(f"   Watching: {watch_path}")
        logger.info(f"   Pattern: {file_pattern}")
        logger.info(f"   Interval: {polling_interval}s")
        logger.info(f"   Recursive: {recursive}")
        
        # Initialize processed files set for this node
        if self.node_id not in self._processed_files:
            self._processed_files[self.node_id] = set()
        
        # Initial scan handling based on ignore_existing setting
        if ignore_existing:
            # Mark existing files as processed so they won't trigger
            initial_files = self._scan_folder(watch_path, file_pattern, recursive)
            for file_path in initial_files:
                file_hash = self._get_file_hash(file_path)
                self._processed_files[self.node_id].add(file_hash)
            logger.info(f"📂 Initial scan: {len(initial_files)} existing files marked as processed (will be skipped)")
        else:
            # Clear the processed files set to allow processing ALL files including existing ones
            self._processed_files[self.node_id] = set()
            logger.info(f"📂 ignore_existing=False: Cleared processed files set - will trigger on ALL files including existing ones")
        
        # Start polling loop
        try:
            loop_count = 0
            while self._is_monitoring:
                await asyncio.sleep(polling_interval)
                
                # Check if still monitoring
                if not self._is_monitoring:
                    break
                
                loop_count += 1
                # Log every 10 polls at INFO level, otherwise DEBUG
                log_level = logging.INFO if loop_count % 10 == 0 else logging.DEBUG
                logger.log(log_level, f"🔍 Polling folder (loop #{loop_count}): {watch_path}")
                
                # Scan for files
                try:
                    current_files = self._scan_folder(watch_path, file_pattern, recursive)
                    logger.log(log_level, f"   Found {len(current_files)} total files matching pattern '{file_pattern}'")
                except Exception as e:
                    logger.error(f"❌ Error scanning folder: {e}", exc_info=True)
                    # Continue polling even if one scan fails
                    continue
                
                # Build set of current file hashes
                current_hashes = set()
                for file_path in current_files:
                    file_hash = self._get_file_hash(file_path)
                    current_hashes.add(file_hash)
                
                # Remove hashes for files that no longer exist (allows reprocessing if file is deleted and re-uploaded)
                removed_hashes = self._processed_files[self.node_id] - current_hashes
                if removed_hashes:
                    self._processed_files[self.node_id] -= removed_hashes
                    logger.debug(f"   Removed {len(removed_hashes)} file(s) from processed set (no longer present)")
                
                # Find new files
                new_files = []
                for file_path in current_files:
                    file_hash = self._get_file_hash(file_path)
                    if file_hash not in self._processed_files[self.node_id]:
                        new_files.append(file_path)
                        self._processed_files[self.node_id].add(file_hash)
                
                if len(new_files) > 0:
                    logger.info(f"📁 Detected {len(new_files)} new file(s)!")
                else:
                    logger.log(log_level, f"   No new files detected")
                
                if new_files:
                    if trigger_mode == "per_file":
                        # Trigger once per file
                        for file_path in new_files:
                            # Move file to processed folder if enabled
                            if move_processed_files:
                                file_path = self._move_file_to_processed(
                                    file_path, 
                                    watch_path, 
                                    processed_folder_suffix
                                )
                            
                            trigger_data = self._build_trigger_data(file_path)
                            logger.info(f"🔔 Triggering workflow for: {file_path.name}")
                            logger.debug(f"   Trigger data keys: {list(trigger_data.keys())}")
                            logger.debug(f"   File data: {trigger_data.get('file', {})}")
                            await self.fire_trigger(trigger_data)
                    else:
                        # Batch mode - trigger once with all files
                        # Move files to processed folder if enabled
                        if move_processed_files:
                            new_files = [
                                self._move_file_to_processed(f, watch_path, processed_folder_suffix)
                                for f in new_files
                            ]
                        
                        trigger_data = self._build_batch_trigger_data(new_files)
                        logger.info(f"🔔 Triggering workflow with {len(new_files)} files")
                        await self.fire_trigger(trigger_data)
        
        except asyncio.CancelledError:
            logger.info(f"⏹️ File polling loop cancelled: {self.node_id}")
            raise
        except Exception as e:
            logger.error(f"❌ Error in file polling loop {self.node_id}: {e}", exc_info=True)
    
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
            
            return files
        
        except Exception as e:
            logger.error(f"❌ Error scanning folder {folder}: {e}")
            return []
    
    def _get_file_hash(self, file_path: Path) -> str:
        """
        Get unique identifier for file.
        
        For network shares, uses path + size only (mtime can be unstable).
        For local files, includes mtime to detect modifications.
        """
        try:
            stat = file_path.stat()
            
            # Check if this is a network path
            from app.utils.network_share import NetworkShareAuth
            is_network = NetworkShareAuth.is_unc_path(str(file_path))
            
            if is_network:
                # Network shares: Use path + size only (mtime unstable)
                # This prevents re-triggering on same file due to clock drift
                identifier = f"{file_path}:{stat.st_size}"
            else:
                # Local files: Include mtime to detect modifications
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
    
    def _build_trigger_data(self, file_path: Path) -> Dict[str, Any]:
        """
        Build trigger data dict for single file.
        
        Outputs standardized MediaFormat that works with:
        - Document Loader (for PDFs, DOCX, TXT)
        - Image Loader (for JPG, PNG, etc.)
        - Audio Loader (for MP3, WAV, etc.)
        - Video Loader (for MP4, AVI, etc.)
        - Email Composer (for attachments)
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
                file_ref = ImageFormatter.from_file_path(file_path_str, metadata=metadata)
            elif mime_type.startswith("audio/"):
                file_ref = AudioFormatter.from_file_path(file_path_str, metadata=metadata)
            elif mime_type.startswith("video/"):
                file_ref = VideoFormatter.from_file_path(file_path_str, metadata=metadata)
            else:
                # Default to document for PDFs, Office docs, text files, and unknown types
                file_ref = DocumentFormatter.from_file_path(file_path_str, metadata=metadata)
            
            return {
                "file": file_ref,  # ✅ Standardized MediaFormat for all nodes
                "file_path": file_path_str,  # Legacy field for backward compatibility
                "file_name": file_path.name,  # Legacy field for backward compatibility
                "signal": "file_detected"
            }
        
        except Exception as e:
            logger.error(f"❌ Error building trigger data for {file_path}: {e}", exc_info=True)
            return {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_info": {},
                "signal": "file_detected"
            }
    
    def _build_batch_trigger_data(self, files: List[Path]) -> Dict[str, Any]:
        """Build trigger data dict for batch of files"""
        return {
            "files": [self._build_trigger_data(f) for f in files],
            "file_count": len(files),
            "signal": "files_detected"
        }


if __name__ == "__main__":
    print("File Polling Trigger Node - Monitor folders for new files")

