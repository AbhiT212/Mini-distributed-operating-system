"""
Sync Engine
Handles file replication, resync, and conflict resolution
"""

import os
import time
import logging
import threading
import uuid
from typing import List, Dict, Optional, Callable
from pathlib import Path

from kernel.metadata_store import MetadataStore
from fs.vfs import VirtualFileSystem
from kernel.net_protocol import calculate_file_checksum


class SyncEngine:
    """Manages file synchronization across peers"""
    
    def __init__(self, vfs: VirtualFileSystem, metadata: MetadataStore, 
                 node_name: str, batch_size: int = 10, chunk_size: int = 1048576):
        self.vfs = vfs
        self.metadata = metadata
        self.node_name = node_name
        self.batch_size = batch_size
        self.chunk_size = chunk_size
        
        self.logger = logging.getLogger("SyncEngine")
        self.sync_lock = threading.RLock()
        
        # Callbacks for sending data to peers
        self.on_file_created = None
        self.on_file_modified = None
        self.on_file_deleted = None
    
    def sync_file_to_peers(self, filepath: str, operation: str = "create"):
        """Sync a file operation to all peers"""
        try:
            if operation == "delete":
                # Just send delete command
                if self.on_file_deleted:
                    self.on_file_deleted(filepath)
                
                # Update metadata
                self.metadata.delete_file(filepath, self.node_name)
                return True
            
            # Read file content
            content = self.vfs.read(filepath, mode='rb')
            if content is None:
                self.logger.error(f"Cannot read file for sync: {filepath}")
                return False
            
            # Calculate metadata
            checksum = self.vfs.get_checksum(filepath)
            size = len(content)
            
            # Update local metadata
            self.metadata.add_file(filepath, checksum, size, self.node_name, operation)
            
            # Notify peers
            if operation == "create" and self.on_file_created:
                self.on_file_created(filepath, content, checksum, size)
            elif operation == "modify" and self.on_file_modified:
                self.on_file_modified(filepath, content, checksum, size)
            
            self.logger.info(f"Synced file to peers: {filepath} ({operation})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to sync file '{filepath}': {e}")
            return False
    
    def apply_remote_change(self, filepath: str, content: bytes, 
                           checksum: str, size: int, node_id: str, operation: str = "create") -> bool:
        """Apply a change received from a remote peer"""
        try:
            with self.sync_lock:
                # Check if we need to apply this change
                local_meta = self.metadata.get_file(filepath)
                
                if local_meta:
                    # Compare checksums - if same, no need to update
                    if local_meta['checksum'] == checksum:
                        self.logger.debug(f"File already up-to-date: {filepath}")
                        return True
                
                # Write file
                if not self.vfs.write(filepath, content, mode='wb'):
                    return False
                
                # Verify checksum
                actual_checksum = self.vfs.get_checksum(filepath)
                if actual_checksum != checksum:
                    self.logger.error(f"Checksum mismatch for {filepath}")
                    self.vfs.delete(filepath)
                    return False
                
                # Update metadata
                self.metadata.add_file(filepath, checksum, size, node_id, operation)
                
                # Log sync
                sync_id = str(uuid.uuid4())
                self.metadata.log_sync(sync_id, node_id, self.node_name, 
                                      filepath, operation, "success")
                
                self.logger.info(f"Applied remote change: {filepath} from {node_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to apply remote change for '{filepath}': {e}")
            
            # Log failed sync
            sync_id = str(uuid.uuid4())
            self.metadata.log_sync(sync_id, node_id, self.node_name, 
                                  filepath, operation, "failed", str(e))
            return False
    
    def apply_remote_delete(self, filepath: str, node_id: str) -> bool:
        """Apply a delete operation from a remote peer"""
        try:
            with self.sync_lock:
                # Delete file
                if self.vfs.exists(filepath):
                    self.vfs.delete(filepath)
                
                # Update metadata
                self.metadata.delete_file(filepath, node_id)
                
                # Log sync
                sync_id = str(uuid.uuid4())
                self.metadata.log_sync(sync_id, node_id, self.node_name, 
                                      filepath, "delete", "success")
                
                self.logger.info(f"Applied remote delete: {filepath} from {node_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to apply remote delete for '{filepath}': {e}")
            return False
    
    def request_full_sync(self, peer_callback: Callable) -> Dict[str, List[str]]:
        """
        Request full sync with a peer
        peer_callback should return peer's metadata
        """
        try:
            self.logger.info("Starting full sync...")
            
            # Get local metadata
            local_metadata = self.metadata.get_all_files()
            
            # Get remote metadata
            remote_metadata = peer_callback()
            
            # Compare metadata
            diff = self.metadata.compare_metadata(remote_metadata)
            
            self.logger.info(f"Sync diff - Missing: {len(diff['missing'])}, "
                           f"Outdated: {len(diff['outdated'])}, "
                           f"Newer: {len(diff['newer'])}")
            
            return diff
            
        except Exception as e:
            self.logger.error(f"Failed to request full sync: {e}")
            return {'missing': [], 'outdated': [], 'newer': []}
    
    def sync_missing_files(self, file_list: List[str], fetch_callback: Callable) -> int:
        """
        Sync files that are missing locally
        fetch_callback(filepath) should return file data from peer
        """
        synced = 0
        
        try:
            for filepath in file_list[:self.batch_size]:  # Batch limit
                try:
                    # Fetch file from peer
                    file_data = fetch_callback(filepath)
                    
                    if file_data:
                        content = file_data.get('content')
                        checksum = file_data.get('checksum')
                        size = file_data.get('size')
                        node_id = file_data.get('node_id')
                        
                        if self.apply_remote_change(filepath, content, checksum, 
                                                    size, node_id, "sync"):
                            synced += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to sync file '{filepath}': {e}")
            
            self.logger.info(f"Synced {synced} missing files")
            return synced
            
        except Exception as e:
            self.logger.error(f"Failed to sync missing files: {e}")
            return synced
    
    def verify_integrity(self) -> Dict[str, List[str]]:
        """
        Verify integrity of all files
        Returns dict with 'valid', 'corrupted', 'missing' lists
        """
        result = {
            'valid': [],
            'corrupted': [],
            'missing': []
        }
        
        try:
            all_metadata = self.metadata.get_all_files()
            
            for meta in all_metadata:
                filepath = meta['filepath']
                stored_checksum = meta['checksum']
                
                if not self.vfs.exists(filepath):
                    result['missing'].append(filepath)
                    continue
                
                # Calculate current checksum
                current_checksum = self.vfs.get_checksum(filepath)
                
                if current_checksum == stored_checksum:
                    result['valid'].append(filepath)
                else:
                    result['corrupted'].append(filepath)
                    self.logger.warning(f"Corrupted file detected: {filepath}")
            
            self.logger.info(f"Integrity check - Valid: {len(result['valid'])}, "
                           f"Corrupted: {len(result['corrupted'])}, "
                           f"Missing: {len(result['missing'])}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to verify integrity: {e}")
            return result
    
    def scan_local_files(self) -> List[str]:
        """
        Scan local filesystem and update metadata
        Returns list of new/modified files
        """
        changes = []
        
        try:
            # Get all local files
            local_files = self.vfs.get_all_files()
            
            for filepath in local_files:
                try:
                    # Get file info
                    checksum = self.vfs.get_checksum(filepath)
                    size = self.vfs.get_size(filepath)
                    
                    # Check metadata
                    meta = self.metadata.get_file(filepath)
                    
                    if not meta:
                        # New file
                        self.metadata.add_file(filepath, checksum, size, 
                                             self.node_name, "scan")
                        changes.append(filepath)
                    elif meta['checksum'] != checksum:
                        # Modified file
                        self.metadata.add_file(filepath, checksum, size, 
                                             self.node_name, "scan")
                        changes.append(filepath)
                
                except Exception as e:
                    self.logger.error(f"Failed to scan file '{filepath}': {e}")
            
            if changes:
                self.logger.info(f"Scanned and found {len(changes)} changes")
            
            return changes
            
        except Exception as e:
            self.logger.error(f"Failed to scan local files: {e}")
            return changes
    
    def get_sync_stats(self) -> Dict:
        """Get synchronization statistics"""
        try:
            metadata_stats = self.metadata.get_stats()
            vfs_stats = self.vfs.get_stats()
            
            return {
                **metadata_stats,
                **vfs_stats,
                'node_name': self.node_name
            }
        except Exception as e:
            self.logger.error(f"Failed to get sync stats: {e}")
            return {}

