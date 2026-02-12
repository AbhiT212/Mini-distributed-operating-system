    """
    Metadata Store
    SQLite-based storage for file versions and sync metadata
    """

    import sqlite3
    import os
    import time
    import threading
    from typing import Dict, List, Optional, Tuple
    from pathlib import Path
    import logging


    class MetadataStore:
        """Manages file metadata and version information"""
        
        def __init__(self, db_path: str):
            self.db_path = db_path
            self.conn: Optional[sqlite3.Connection] = None
            self.lock = threading.RLock()
            self.logger = logging.getLogger("MetadataStore")
            
            self._initialize_db()
        
        def _initialize_db(self):
            """Create database schema"""
            try:
                self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
                
                cursor = self.conn.cursor()
                
                # Files table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filepath TEXT UNIQUE NOT NULL,
                        checksum TEXT NOT NULL,
                        size INTEGER NOT NULL,
                        version INTEGER DEFAULT 1,
                        modified_time REAL NOT NULL,
                        created_time REAL NOT NULL,
                        node_id TEXT,
                        operation_type TEXT,
                        is_deleted INTEGER DEFAULT 0
                    )
                ''')
                
                # Sync log table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sync_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sync_id TEXT NOT NULL,
                        source_node TEXT,
                        target_node TEXT,
                        filepath TEXT,
                        action TEXT,
                        timestamp REAL NOT NULL,
                        status TEXT,
                        error_message TEXT
                    )
                ''')
                
                # Create indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_filepath ON files(filepath)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_timestamp ON sync_log(timestamp)')
                
                self.conn.commit()
                self.logger.info(f"Metadata database initialized: {self.db_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize database: {e}")
                raise
        
        def close(self):
            """Close database connection"""
            if self.conn:
                self.conn.close()
                self.logger.info("Metadata database closed")
        
        def add_file(self, filepath: str, checksum: str, size: int, 
                    node_id: str = None, operation_type: str = "create") -> bool:
            """Add or update file metadata"""
            try:
                with self.lock:
                    cursor = self.conn.cursor()
                    
                    # Check if file exists
                    cursor.execute('SELECT version FROM files WHERE filepath = ?', (filepath,))
                    result = cursor.fetchone()
                    
                    current_time = time.time()
                    
                    if result:
                        # Update existing file
                        new_version = result[0] + 1
                        cursor.execute('''
                            UPDATE files 
                            SET checksum = ?, size = ?, version = ?, 
                                modified_time = ?, node_id = ?, operation_type = ?,
                                is_deleted = 0
                            WHERE filepath = ?
                        ''', (checksum, size, new_version, current_time, node_id, operation_type, filepath))
                    else:
                        # Insert new file
                        cursor.execute('''
                            INSERT INTO files 
                            (filepath, checksum, size, version, modified_time, created_time, node_id, operation_type)
                            VALUES (?, ?, ?, 1, ?, ?, ?, ?)
                        ''', (filepath, checksum, size, current_time, current_time, node_id, operation_type))
                    
                    self.conn.commit()
                    return True
                    
            except Exception as e:
                self.logger.error(f"Failed to add file metadata: {e}")
                return False
        
        def get_file(self, filepath: str) -> Optional[Dict]:
            """Get file metadata"""
            try:
                with self.lock:
                    cursor = self.conn.cursor()
                    cursor.execute('SELECT * FROM files WHERE filepath = ? AND is_deleted = 0', (filepath,))
                    result = cursor.fetchone()
                    
                    if result:
                        return dict(result)
                    return None
                    
            except Exception as e:
                self.logger.error(f"Failed to get file metadata: {e}")
                return None
        
        def get_all_files(self) -> List[Dict]:
            """Get all file metadata"""
            try:
                with self.lock:
                    cursor = self.conn.cursor()
                    cursor.execute('SELECT * FROM files WHERE is_deleted = 0 ORDER BY filepath')
                    results = cursor.fetchall()
                    
                    return [dict(row) for row in results]
                    
            except Exception as e:
                self.logger.error(f"Failed to get all files: {e}")
                return []
        
        def delete_file(self, filepath: str, node_id: str = None) -> bool:
            """Mark file as deleted"""
            try:
                with self.lock:
                    cursor = self.conn.cursor()
                    current_time = time.time()
                    
                    cursor.execute('''
                        UPDATE files 
                        SET is_deleted = 1, modified_time = ?, node_id = ?, operation_type = 'delete'
                        WHERE filepath = ?
                    ''', (current_time, node_id, filepath))
                    
                    self.conn.commit()
                    return True
                    
            except Exception as e:
                self.logger.error(f"Failed to delete file metadata: {e}")
                return False
        
        def get_file_version(self, filepath: str) -> int:
            """Get current version number of a file"""
            metadata = self.get_file(filepath)
            return metadata['version'] if metadata else 0
        
        def compare_metadata(self, other_metadata: List[Dict]) -> Dict[str, List[str]]:
            """
            Compare local metadata with remote metadata
            Returns dict with 'missing', 'outdated', 'newer' file lists
            """
            result = {
                'missing': [],    # Files we don't have
                'outdated': [],   # Files we have but are older
                'newer': []       # Files we have that are newer
            }
            
            try:
                local_files = {f['filepath']: f for f in self.get_all_files()}
                
                for remote_file in other_metadata:
                    filepath = remote_file['filepath']
                    
                    if filepath not in local_files:
                        result['missing'].append(filepath)
                    else:
                        local_file = local_files[filepath]
                        
                        # Compare versions and timestamps
                        if remote_file['version'] > local_file['version']:
                            result['outdated'].append(filepath)
                        elif remote_file['version'] < local_file['version']:
                            result['newer'].append(filepath)
                        elif remote_file['modified_time'] > local_file['modified_time']:
                            result['outdated'].append(filepath)
                        elif remote_file['modified_time'] < local_file['modified_time']:
                            result['newer'].append(filepath)
                
                # Check for files we have that remote doesn't
                remote_paths = {f['filepath'] for f in other_metadata}
                for filepath in local_files:
                    if filepath not in remote_paths:
                        result['newer'].append(filepath)
                
                return result
                
            except Exception as e:
                self.logger.error(f"Failed to compare metadata: {e}")
                return result
        
        def log_sync(self, sync_id: str, source_node: str, target_node: str,
                    filepath: str, action: str, status: str, error: str = None) -> bool:
            """Log a sync operation"""
            try:
                with self.lock:
                    cursor = self.conn.cursor()
                    cursor.execute('''
                        INSERT INTO sync_log 
                        (sync_id, source_node, target_node, filepath, action, timestamp, status, error_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (sync_id, source_node, target_node, filepath, action, time.time(), status, error))
                    
                    self.conn.commit()
                    return True
                    
            except Exception as e:
                self.logger.error(f"Failed to log sync: {e}")
                return False
        
        def get_sync_history(self, limit: int = 100) -> List[Dict]:
            """Get recent sync history"""
            try:
                with self.lock:
                    cursor = self.conn.cursor()
                    cursor.execute('''
                        SELECT * FROM sync_log 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    ''', (limit,))
                    
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
                    
            except Exception as e:
                self.logger.error(f"Failed to get sync history: {e}")
                return []
        
        def get_operation_history(self, limit: int = 100, node_filter: str = None) -> List[Dict]:
            """Get history of all file operations with timestamps"""
            try:
                with self.lock:
                    cursor = self.conn.cursor()
                    
                    if node_filter:
                        cursor.execute('''
                            SELECT 
                                filepath,
                                operation_type,
                                node_id,
                                modified_time as timestamp,
                                version,
                                size
                            FROM files 
                            WHERE node_id = ?
                            ORDER BY modified_time DESC 
                            LIMIT ?
                        ''', (node_filter, limit))
                    else:
                        cursor.execute('''
                            SELECT 
                                filepath,
                                operation_type,
                                node_id,
                                modified_time as timestamp,
                                version,
                                size
                            FROM files 
                            ORDER BY modified_time DESC 
                            LIMIT ?
                        ''', (limit,))
                    
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
                    
            except Exception as e:
                self.logger.error(f"Failed to get operation history: {e}")
                return []
        
        def get_stats(self) -> Dict:
            """Get metadata statistics"""
            try:
                with self.lock:
                    cursor = self.conn.cursor()
                    
                    # Total files
                    cursor.execute('SELECT COUNT(*) FROM files WHERE is_deleted = 0')
                    total_files = cursor.fetchone()[0]
                    
                    # Total size
                    cursor.execute('SELECT SUM(size) FROM files WHERE is_deleted = 0')
                    total_size = cursor.fetchone()[0] or 0
                    
                    # Recent syncs
                    cursor.execute('''
                        SELECT COUNT(*) FROM sync_log 
                        WHERE timestamp > ?
                    ''', (time.time() - 3600,))  # Last hour
                    recent_syncs = cursor.fetchone()[0]
                    
                    return {
                        'total_files': total_files,
                        'total_size': total_size,
                        'recent_syncs': recent_syncs
                    }
                    
            except Exception as e:
                self.logger.error(f"Failed to get stats: {e}")
                return {}
        
        def vacuum(self):
            """Optimize database"""
            try:
                with self.lock:
                    self.conn.execute('VACUUM')
                    self.logger.info("Database vacuumed")
            except Exception as e:
                self.logger.error(f"Failed to vacuum database: {e}")

