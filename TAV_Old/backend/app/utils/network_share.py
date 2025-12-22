"""
Network Share Authentication Utilities

Provides helpers for accessing Windows network shares with credentials.
"""

import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import tempfile

logger = logging.getLogger(__name__)


class NetworkShareAuth:
    """
    Handle Windows network share authentication.
    
    Supports:
    - UNC path validation
    - Temporary credential mounting
    - Network path access with credentials
    """
    
    @staticmethod
    def is_unc_path(path: str) -> bool:
        r"""Check if path is a UNC network path (\\server\share)"""
        return path.startswith('\\\\') or path.startswith('//')
    
    @staticmethod
    def parse_unc_path(path: str) -> Optional[Dict[str, str]]:
        r"""
        Parse UNC path into components.
        
        Args:
            path: UNC path like \\192.168.108.110\Data\Upload_Data\Medex\V2
            
        Returns:
            Dict with 'server', 'share', 'path' or None if invalid
        """
        if not NetworkShareAuth.is_unc_path(path):
            return None
        
        # Normalize slashes
        path = path.replace('/', '\\')
        
        # Remove leading slashes
        path = path.lstrip('\\')
        
        # Split into parts
        parts = path.split('\\')
        
        if len(parts) < 2:
            return None
        
        return {
            'server': parts[0],
            'share': parts[1],
            'path': '\\'.join(parts[2:]) if len(parts) > 2 else '',
            'share_path': f'\\\\{parts[0]}\\{parts[1]}'
        }
    
    @staticmethod
    def mount_network_share(
        share_path: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        drive_letter: Optional[str] = None
    ) -> Dict[str, Any]:
        r"""
        Mount a network share with credentials (Windows only).
        
        Args:
            share_path: UNC path like \\192.168.108.110\Data
            username: Username (optional if using saved credentials)
            password: Password (optional if using saved credentials)
            drive_letter: Optional drive letter to mount to (e.g., 'Z:')
            
        Returns:
            Dict with 'success', 'message', 'drive_letter' (if mounted)
        """
        if platform.system() != 'Windows':
            return {
                'success': False,
                'error': 'Network share mounting only supported on Windows'
            }
        
        try:
            parsed = NetworkShareAuth.parse_unc_path(share_path)
            if not parsed:
                return {
                    'success': False,
                    'error': f'Invalid UNC path: {share_path}'
                }
            
            share_unc = parsed['share_path']
            
            # Build net use command
            if drive_letter:
                cmd = ['net', 'use', drive_letter, share_unc]
            else:
                cmd = ['net', 'use', share_unc]
            
            if username:
                cmd.extend(['/user:' + username])
                if password:
                    cmd.append(password)
            
            # Execute
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Network share mounted: {share_unc}")
                return {
                    'success': True,
                    'message': f'Successfully mounted {share_unc}',
                    'drive_letter': drive_letter,
                    'share_path': share_unc
                }
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"❌ Failed to mount {share_unc}: {error_msg}")
                return {
                    'success': False,
                    'error': f'Failed to mount: {error_msg}'
                }
        
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Network share mount timeout (30s)'
            }
        except Exception as e:
            logger.error(f"❌ Network share mount error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def write_to_network_path(
        file_content: bytes,
        network_path: str,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write file to network share with authentication.
        
        This method attempts direct write first (if credentials are cached),
        then tries mounting if direct write fails.
        
        Args:
            file_content: File content as bytes
            network_path: Full UNC path including filename
            username: Optional username
            password: Optional password
            
        Returns:
            Dict with 'success', 'message', 'file_path'
        """
        try:
            # Try direct write first (works if credentials are cached)
            try:
                network_path_obj = Path(network_path)
                network_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                with open(network_path_obj, 'wb') as f:
                    f.write(file_content)
                    f.flush()  # Flush Python buffer
                    os.fsync(f.fileno())  # Force OS to write to disk
                
                # Verify file was written
                if network_path_obj.exists():
                    actual_size = network_path_obj.stat().st_size
                    logger.info(f"✅ File written to network path: {network_path} ({actual_size} bytes)")
                else:
                    raise IOError(f"File write reported success but file doesn't exist: {network_path}")
                
                return {
                    'success': True,
                    'message': f'File saved successfully',
                    'file_path': str(network_path),
                    'file_size': len(file_content)
                }
            
            except (PermissionError, OSError) as e:
                # Direct write failed, try mounting
                logger.info(f"Direct write failed ({e}), attempting to mount share...")
                
                if not username or not password:
                    return {
                        'success': False,
                        'error': 'Permission denied. Credentials required for network share access.'
                    }
                
                # Parse path to get share
                parsed = NetworkShareAuth.parse_unc_path(network_path)
                if not parsed:
                    return {
                        'success': False,
                        'error': f'Invalid network path: {network_path}'
                    }
                
                # Mount share
                mount_result = NetworkShareAuth.mount_network_share(
                    share_path=parsed['share_path'],
                    username=username,
                    password=password
                )
                
                if not mount_result['success']:
                    return mount_result
                
                # Try writing again after mount
                network_path_obj = Path(network_path)
                network_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                with open(network_path_obj, 'wb') as f:
                    f.write(file_content)
                    f.flush()  # Flush Python buffer
                    os.fsync(f.fileno())  # Force OS to write to disk
                
                # Verify file was written
                if network_path_obj.exists():
                    actual_size = network_path_obj.stat().st_size
                    logger.info(f"✅ File written to network path after mount: {network_path} ({actual_size} bytes)")
                else:
                    raise IOError(f"File write reported success but file doesn't exist: {network_path}")
                
                return {
                    'success': True,
                    'message': f'File saved successfully (after mounting share)',
                    'file_path': str(network_path),
                    'file_size': len(file_content)
                }
        
        except Exception as e:
            logger.error(f"❌ Network write error: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to write to network path: {str(e)}'
            }

