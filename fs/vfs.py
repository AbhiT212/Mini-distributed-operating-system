"""
Virtual File System (VFS)
Provides unified interface for file operations
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from kernel.net_protocol import calculate_file_checksum


class VirtualFileSystem:
    """Virtual filesystem abstraction layer"""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.logger = logging.getLogger("VFS")
        
        # Ensure root directory exists
        self._ensure_root()
    
    def _ensure_root(self):
        """Ensure root directory exists"""
        try:
            self.root_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"VFS root: {self.root_path}")
        except Exception as e:
            self.logger.error(f"Failed to create VFS root: {e}")
            raise
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve relative path to absolute path within VFS"""
        # Remove leading slash if present
        path = path.lstrip('/')
        path = path.lstrip('\\')
        
        resolved = self.root_path / path
        
        # Ensure path is within root (security check)
        try:
            resolved.resolve().relative_to(self.root_path.resolve())
        except ValueError:
            raise ValueError(f"Path '{path}' is outside VFS root")
        
        return resolved
    
    def create(self, filepath: str) -> bool:
        """Create an empty file"""
        try:
            abs_path = self._resolve_path(filepath)
            
            # Ensure parent directory exists
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create empty file
            abs_path.touch()
            
            self.logger.info(f"Created file: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create file '{filepath}': {e}")
            return False
    
    def write(self, filepath: str, content: str, mode: str = 'w') -> bool:
        """Write content to a file"""
        try:
            abs_path = self._resolve_path(filepath)
            
            # Ensure parent directory exists
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            if mode == 'wb':
                abs_path.write_bytes(content)
            else:
                abs_path.write_text(content, encoding='utf-8')
            
            self.logger.info(f"Wrote to file: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write file '{filepath}': {e}")
            return False
    
    def read(self, filepath: str, mode: str = 'r') -> Optional[Any]:
        """Read content from a file"""
        try:
            abs_path = self._resolve_path(filepath)
            
            if not abs_path.exists():
                self.logger.warning(f"File not found: {filepath}")
                return None
            
            # Read content
            if mode == 'rb':
                return abs_path.read_bytes()
            else:
                return abs_path.read_text(encoding='utf-8')
            
        except Exception as e:
            self.logger.error(f"Failed to read file '{filepath}': {e}")
            return None
    
    def delete(self, filepath: str) -> bool:
        """Delete a file"""
        try:
            abs_path = self._resolve_path(filepath)
            
            if not abs_path.exists():
                self.logger.warning(f"File not found: {filepath}")
                return False
            
            if abs_path.is_dir():
                shutil.rmtree(abs_path)
            else:
                abs_path.unlink()
            
            self.logger.info(f"Deleted: {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete '{filepath}': {e}")
            return False
    
    def mkdir(self, dirpath: str) -> bool:
        """Create a directory"""
        try:
            abs_path = self._resolve_path(dirpath)
            abs_path.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Created directory: {dirpath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create directory '{dirpath}': {e}")
            return False
    
    def exists(self, path: str) -> bool:
        """Check if path exists"""
        try:
            abs_path = self._resolve_path(path)
            return abs_path.exists()
        except:
            return False
    
    def is_file(self, path: str) -> bool:
        """Check if path is a file"""
        try:
            abs_path = self._resolve_path(path)
            return abs_path.is_file()
        except:
            return False
    
    def is_dir(self, path: str) -> bool:
        """Check if path is a directory"""
        try:
            abs_path = self._resolve_path(path)
            return abs_path.is_dir()
        except:
            return False
    
    def list(self, dirpath: str = "") -> List[Dict[str, Any]]:
        """List contents of a directory"""
        try:
            abs_path = self._resolve_path(dirpath) if dirpath else self.root_path
            
            if not abs_path.exists():
                self.logger.warning(f"Directory not found: {dirpath}")
                return []
            
            if not abs_path.is_dir():
                self.logger.warning(f"Not a directory: {dirpath}")
                return []
            
            items = []
            for item in abs_path.iterdir():
                try:
                    stat = item.stat()
                    items.append({
                        'name': item.name,
                        'type': 'dir' if item.is_dir() else 'file',
                        'size': stat.st_size if item.is_file() else 0,
                        'modified': stat.st_mtime
                    })
                except Exception as e:
                    self.logger.warning(f"Failed to stat {item}: {e}")
            
            return sorted(items, key=lambda x: (x['type'] != 'dir', x['name']))
            
        except Exception as e:
            self.logger.error(f"Failed to list directory '{dirpath}': {e}")
            return []
    
    def get_size(self, filepath: str) -> int:
        """Get file size in bytes"""
        try:
            abs_path = self._resolve_path(filepath)
            if abs_path.is_file():
                return abs_path.stat().st_size
            return 0
        except:
            return 0
    
    def get_checksum(self, filepath: str) -> str:
        """Calculate file checksum"""
        try:
            abs_path = self._resolve_path(filepath)
            return calculate_file_checksum(str(abs_path))
        except:
            return ""
    
    def get_mtime(self, filepath: str) -> float:
        """Get file modification time"""
        try:
            abs_path = self._resolve_path(filepath)
            return abs_path.stat().st_mtime
        except:
            return 0.0
    
    def copy(self, src: str, dst: str) -> bool:
        """Copy a file"""
        try:
            src_path = self._resolve_path(src)
            dst_path = self._resolve_path(dst)
            
            if not src_path.exists():
                return False
            
            # Ensure destination directory exists
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            if src_path.is_file():
                shutil.copy2(src_path, dst_path)
            else:
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            
            self.logger.info(f"Copied {src} to {dst}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to copy '{src}' to '{dst}': {e}")
            return False
    
    def move(self, src: str, dst: str) -> bool:
        """Move/rename a file"""
        try:
            src_path = self._resolve_path(src)
            dst_path = self._resolve_path(dst)
            
            if not src_path.exists():
                return False
            
            # Ensure destination directory exists
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(src_path), str(dst_path))
            
            self.logger.info(f"Moved {src} to {dst}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to move '{src}' to '{dst}': {e}")
            return False
    
    def get_all_files(self, base_path: str = "") -> List[str]:
        """Recursively get all files in directory"""
        try:
            abs_path = self._resolve_path(base_path) if base_path else self.root_path
            
            files = []
            for item in abs_path.rglob('*'):
                if item.is_file():
                    # Get relative path from root
                    rel_path = item.relative_to(self.root_path)
                    files.append(str(rel_path).replace('\\', '/'))
            
            return sorted(files)
            
        except Exception as e:
            self.logger.error(f"Failed to get all files: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get filesystem statistics"""
        try:
            total_files = 0
            total_dirs = 0
            total_size = 0
            
            for item in self.root_path.rglob('*'):
                if item.is_file():
                    total_files += 1
                    total_size += item.stat().st_size
                elif item.is_dir():
                    total_dirs += 1
            
            return {
                'total_files': total_files,
                'total_dirs': total_dirs,
                'total_size': total_size,
                'root_path': str(self.root_path)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}")
            return {}

