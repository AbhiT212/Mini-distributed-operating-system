"""
Node Daemon
Main service that runs on each node
"""

import socket
import threading
import time
import logging
import json
import yaml
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kernel.peer_manager import PeerManager, Peer
from kernel.net_protocol import Message, MessageFactory, MessageValidator
from kernel.metadata_store import MetadataStore
from kernel.sync_engine import SyncEngine
from kernel.permissions_windows import ensure_admin, check_filesystem_permissions
from fs.vfs import VirtualFileSystem


class NodeDaemon:
    """Main daemon process for MiniDOS node"""
    
    def __init__(self, config_path: str = "configs/default.yaml"):
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger("NodeDaemon")
        
        # Node identity
        self.node_name = self.config['node']['name']
        self.tcp_port = self.config['network']['tcp_port']
        self.discovery_port = self.config['network']['discovery_port']
        
        # Initialize components
        self.vfs = VirtualFileSystem(self.config['filesystem']['root_path'])
        
        metadata_path = Path(self.config['filesystem']['root_path']) / self.config['filesystem']['metadata_db']
        self.metadata = MetadataStore(str(metadata_path))
        
        self.sync_engine = SyncEngine(
            self.vfs, 
            self.metadata, 
            self.node_name,
            self.config['sync']['batch_size'],
            self.config['sync']['chunk_size']
        )
        
        self.peer_manager = PeerManager(
            self.node_name,
            self.tcp_port,
            self.discovery_port,
            self.config['network']['discovery_enabled'],
            self.config['network']['reconnect_timeout']
        )
        
        # Network
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.client_threads = []
        
        # Message sequence counter
        self.message_sequence = 0
        self.sequence_lock = threading.Lock()
        
        # Setup callbacks
        self._setup_callbacks()
        
        self.logger.info(f"NodeDaemon initialized: {self.node_name}")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Failed to load config: {e}")
            print("Using default configuration")
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """Return default configuration"""
        return {
            'node': {'name': 'NODE-DEFAULT'},
            'network': {
                'tcp_port': 9000,
                'discovery_port': 9050,
                'bind_address': '0.0.0.0',
                'discovery_enabled': True,
                'heartbeat_interval': 5,
                'reconnect_timeout': 30
            },
            'filesystem': {
                'root_path': 'C:\\MiniDOS_FS',
                'metadata_db': 'metadata.db',
                'sync_on_startup': True
            },
            'sync': {
                'batch_size': 10,
                'chunk_size': 1048576
            },
            'logging': {
                'level': 'INFO',
                'console_output': True
            },
            'peers': []
        }
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config['logging']['level'], logging.INFO)
        
        # Create logs directory
        Path("logs").mkdir(exist_ok=True)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/node.log'),
                logging.StreamHandler() if self.config['logging']['console_output'] else logging.NullHandler()
            ]
        )
    
    def _setup_callbacks(self):
        """Setup callbacks between components"""
        # Peer manager callbacks
        self.peer_manager.on_peer_connected = self._on_peer_connected
        self.peer_manager.on_peer_disconnected = self._on_peer_disconnected
        
        # Sync engine callbacks
        self.sync_engine.on_file_created = self._broadcast_file_create
        self.sync_engine.on_file_modified = self._broadcast_file_modify
        self.sync_engine.on_file_deleted = self._broadcast_file_delete
    
    def _on_peer_connected(self, peer: Peer):
        """Handle new peer connection"""
        self.logger.info(f"Peer connected: {peer.name} ({peer.address}:{peer.port})")
        
        # TODO: Trigger sync with new peer
    
    def _on_peer_disconnected(self, peer: Peer):
        """Handle peer disconnection"""
        self.logger.warning(f"Peer disconnected: {peer.name} ({peer.address}:{peer.port})")
    
    def start(self):
        """Start the node daemon"""
        self.logger.info(f"Starting NodeDaemon: {self.node_name}")
        
        # Check permissions
        if self.config.get('security', {}).get('require_admin', True):
            ensure_admin()
        
        # Check filesystem access
        if not check_filesystem_permissions(self.config['filesystem']['root_path']):
            self.logger.error("Insufficient filesystem permissions")
            return False
        
        self.running = True
        
        # Start peer manager
        self.peer_manager.start()
        
        # Load static peers
        if self.config.get('peers'):
            self.peer_manager.load_static_peers(self.config['peers'])
        
        # Start TCP server
        self._start_tcp_server()
        
        # Sync on startup
        if self.config['filesystem'].get('sync_on_startup', True):
            threading.Thread(target=self._initial_sync, daemon=True).start()
        
        self.logger.info(f"NodeDaemon started on port {self.tcp_port}")
        return True
    
    def stop(self):
        """Stop the node daemon"""
        self.logger.info("Stopping NodeDaemon...")
        
        self.running = False
        
        # Stop peer manager
        self.peer_manager.stop()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        # Wait for client threads
        for thread in self.client_threads:
            thread.join(timeout=2)
        
        # Close metadata database
        self.metadata.close()
        
        self.logger.info("NodeDaemon stopped")
    
    def _start_tcp_server(self):
        """Start TCP server for peer communication"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            bind_address = self.config['network']['bind_address']
            self.server_socket.bind((bind_address, self.tcp_port))
            self.server_socket.listen(10)
            
            # Start accept thread
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()
            
            self.logger.info(f"TCP server listening on {bind_address}:{self.tcp_port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start TCP server: {e}")
            raise
    
    def _accept_connections(self):
        """Accept incoming connections"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                
                self.logger.debug(f"New connection from {address}")
                
                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
                self.client_threads.append(client_thread)
                
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error accepting connection: {e}")
    
    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """Handle client connection"""
        try:
            # Set timeout
            client_socket.settimeout(30)
            
            # Receive message
            data = b""
            while True:
                chunk = client_socket.recv(8192)
                if not chunk:
                    break
                data += chunk
                
                # Check for end of message (simple length-prefixed protocol)
                if len(data) >= 4:
                    msg_len = int.from_bytes(data[:4], 'big')
                    if len(data) >= msg_len + 4:
                        break
            
            if not data:
                return
            
            # Remove length prefix
            msg_data = data[4:]
            
            # Parse message
            msg = Message.from_json(msg_data.decode('utf-8'))
            
            # Validate message
            is_valid, error = MessageValidator.validate_message(msg)
            if not is_valid:
                self.logger.warning(f"Invalid message from {address}: {error}")
                response = MessageFactory.create_response("error", False, error, self.node_name)
                self._send_response(client_socket, response)
                return
            
            # Update peer heartbeat - find peer by IP address
            peer_ip = address[0]
            peer = None
            for p in self.peer_manager.get_all_peers():
                if p.address == peer_ip:
                    peer = p
                    break
            if peer:
                self.peer_manager.update_peer_heartbeat(peer.address, peer.port)
                self.logger.debug(f"Updated heartbeat for {peer.name}")
            else:
                # Fallback: assume standard port
                self.peer_manager.update_peer_heartbeat(peer_ip, self.tcp_port)
                self.logger.debug(f"Updated heartbeat for {peer_ip} (fallback)")
            
            # Process message
            response = self._process_message(msg)
            
            # Send response
            self._send_response(client_socket, response)
            
        except Exception as e:
            self.logger.error(f"Error handling client {address}: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def _send_response(self, sock: socket.socket, msg: Message):
        """Send response message"""
        try:
            msg_json = msg.to_json()
            msg_bytes = msg_json.encode('utf-8')
            
            # Send with length prefix
            length = len(msg_bytes).to_bytes(4, 'big')
            sock.sendall(length + msg_bytes)
            
        except Exception as e:
            self.logger.error(f"Failed to send response: {e}")
    
    def _process_message(self, msg: Message) -> Message:
        """Process incoming message and return response"""
        try:
            if msg.type == "command":
                return self._handle_command(msg)
            elif msg.type == "sync":
                return self._handle_sync(msg)
            elif msg.type == "heartbeat":
                return self._handle_heartbeat(msg)
            else:
                return MessageFactory.create_response(
                    msg.action, False, f"Unknown message type: {msg.type}", self.node_name
                )
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return MessageFactory.create_response(
                msg.action, False, f"Error: {str(e)}", self.node_name
            )
    
    def _handle_command(self, msg: Message) -> Message:
        """Handle command message"""
        action = msg.action
        path = msg.path
        content = msg.content
        is_local = (msg.origin == self.node_name)  # Check if this is a local or remote command
        
        if action == "create":
            success = self.vfs.create(path)
            if success:
                # Update metadata for history tracking
                checksum = self.vfs.get_checksum(path)
                size = self.vfs.get_size(path)
                self.metadata.add_file(path, checksum, size, msg.origin, "create")
                # Only broadcast if this is a LOCAL operation (not from another peer)
                if is_local:
                    file_content = self.vfs.read(path, mode='rb')
                    if file_content:
                        self._broadcast_file_create(path, file_content, checksum, size)
            return MessageFactory.create_response(action, success, 
                                                 "File created" if success else "Failed to create file",
                                                 self.node_name)
        
        elif action == "write":
            success = self.vfs.write(path, content)
            if success:
                # Update metadata for history tracking
                checksum = self.vfs.get_checksum(path)
                size = self.vfs.get_size(path)
                self.metadata.add_file(path, checksum, size, msg.origin, "modify")
                # Only broadcast if this is a LOCAL operation
                if is_local:
                    file_content = self.vfs.read(path, mode='rb')
                    if file_content:
                        self._broadcast_file_modify(path, file_content, checksum, size)
            return MessageFactory.create_response(action, success,
                                                 "File written" if success else "Failed to write file",
                                                 self.node_name)
        
        elif action == "read":
            content = self.vfs.read(path)
            return MessageFactory.create_response(action, content is not None,
                                                 "File read" if content else "Failed to read file",
                                                 self.node_name, content)
        
        elif action == "delete":
            success = self.vfs.delete(path)
            if success:
                # Update metadata for history tracking
                self.metadata.delete_file(path, msg.origin)
                # Only broadcast if this is a LOCAL operation
                if is_local:
                    self._broadcast_file_delete(path)
            return MessageFactory.create_response(action, success,
                                                 "File deleted" if success else "Failed to delete file",
                                                 self.node_name)
        
        elif action == "mkdir":
            success = self.vfs.mkdir(path)
            if success:
                # Update metadata for history tracking
                self.metadata.add_file(path, "", 0, msg.origin, "mkdir")
                # Only broadcast if this is a LOCAL operation
                if is_local:
                    self._broadcast_mkdir(path)
            return MessageFactory.create_response(action, success,
                                                 "Directory created" if success else "Failed to create directory",
                                                 self.node_name)
        
        elif action == "list":
            items = self.vfs.list(path)
            return MessageFactory.create_response(action, True, "Listed directory",
                                                 self.node_name, items)
        
        elif action == "history":
            # Get operation history from metadata
            limit = content.get('limit', 50) if isinstance(content, dict) else 50
            history = self.metadata.get_operation_history(limit=limit)
            return MessageFactory.create_response(action, True, "History retrieved",
                                                 self.node_name, history)
        
        elif action == "loadbal":
            # Get system stats for load balancing
            import psutil
            stats = {
                'node_name': self.node_name,
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'active_peers': len(self.peer_manager.get_active_peers())
            }
            return MessageFactory.create_response(action, True, "Load stats retrieved",
                                                 self.node_name, stats)
        
        else:
            return MessageFactory.create_response(action, False, 
                                                 f"Unknown command: {action}",
                                                 self.node_name)
    
    def _handle_sync(self, msg: Message) -> Message:
        """Handle sync message"""
        action = msg.action
        path = msg.path
        payload = msg.content
        
        if action == "sync_file":
            # Receive file from peer
            import base64
            file_content_b64 = payload['data']
            metadata = payload['metadata']
            
            # Decode base64 to bytes
            file_content = base64.b64decode(file_content_b64)
            
            success = self.sync_engine.apply_remote_change(
                path, file_content, 
                metadata['checksum'], metadata['size'],
                msg.origin, metadata.get('operation', 'sync')
            )
            
            return MessageFactory.create_response(action, success,
                                                 "File synced" if success else "Failed to sync file",
                                                 self.node_name)
        
        elif action == "sync_metadata":
            # Return metadata
            all_metadata = self.metadata.get_all_files()
            return MessageFactory.create_response(action, True, "Metadata sent",
                                                 self.node_name, all_metadata)
        
        elif action == "request_file":
            # Send file to peer
            content = self.vfs.read(path, mode='rb')
            if content:
                metadata = self.metadata.get_file(path)
                data = {
                    'content': content,
                    'checksum': metadata['checksum'] if metadata else '',
                    'size': len(content),
                    'node_id': self.node_name
                }
                return MessageFactory.create_response(action, True, "File sent",
                                                     self.node_name, data)
            else:
                return MessageFactory.create_response(action, False, "File not found",
                                                     self.node_name)
        
        else:
            return MessageFactory.create_response(action, False,
                                                 f"Unknown sync action: {action}",
                                                 self.node_name)
    
    def _handle_heartbeat(self, msg: Message) -> Message:
        """Handle heartbeat message"""
        # Return pong with stats
        stats = self.sync_engine.get_sync_stats()
        return MessageFactory.create_response("pong", True, "Alive",
                                             self.node_name, stats)
    
    def _broadcast_file_create(self, filepath: str, content: bytes, checksum: str, size: int):
        """Broadcast file creation to all peers"""
        import base64
        # Convert bytes to base64 string for JSON serialization
        content_b64 = base64.b64encode(content).decode('utf-8')
        metadata = {
            'checksum': checksum,
            'size': size,
            'operation': 'create'
        }
        msg = MessageFactory.create_sync("sync_file", filepath, content_b64, self.node_name, metadata)
        self._broadcast_message(msg)
    
    def _broadcast_file_modify(self, filepath: str, content: bytes, checksum: str, size: int):
        """Broadcast file modification to all peers"""
        import base64
        # Convert bytes to base64 string for JSON serialization
        content_b64 = base64.b64encode(content).decode('utf-8')
        metadata = {
            'checksum': checksum,
            'size': size,
            'operation': 'modify'
        }
        msg = MessageFactory.create_sync("sync_file", filepath, content_b64, self.node_name, metadata)
        self._broadcast_message(msg)
    
    def _broadcast_file_delete(self, filepath: str):
        """Broadcast file deletion to all peers"""
        msg = MessageFactory.create_command("delete", filepath, "", self.node_name)
        self._broadcast_message(msg)
    
    def _broadcast_mkdir(self, dirpath: str):
        """Broadcast directory creation to all peers"""
        msg = MessageFactory.create_command("mkdir", dirpath, "", self.node_name)
        self._broadcast_message(msg)
    
    def _broadcast_message(self, msg: Message):
        """Broadcast message to all active peers"""
        peers = self.peer_manager.get_active_peers()
        
        if not peers:
            self.logger.warning(f"No peers available to broadcast {msg.action}")
            return
        
        self.logger.info(f"Broadcasting {msg.action} to {len(peers)} peer(s)")
        
        for peer in peers:
            threading.Thread(target=self._send_to_peer, args=(peer, msg), daemon=True).start()
    
    def _send_to_peer(self, peer: Peer, msg: Message):
        """Send message to a specific peer"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((peer.address, peer.port))
            
            msg_json = msg.to_json()
            msg_bytes = msg_json.encode('utf-8')
            
            # Send with length prefix
            length = len(msg_bytes).to_bytes(4, 'big')
            sock.sendall(length + msg_bytes)
            
            # Receive response
            response_data = sock.recv(8192)
            
            sock.close()
            
            self.logger.info(f"Successfully sent {msg.action} to {peer.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to send to peer {peer.name}: {e}")
    
    def _initial_sync(self):
        """Perform initial sync on startup"""
        self.logger.info("Performing initial sync...")
        time.sleep(2)  # Wait for peer discovery
        
        # Scan local files
        self.sync_engine.scan_local_files()
        
        self.logger.info("Initial sync completed")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MiniDOS Node Daemon")
    parser.add_argument('--config', default='configs/default.yaml', help='Configuration file path')
    args = parser.parse_args()
    
    daemon = NodeDaemon(args.config)
    
    try:
        daemon.start()
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        daemon.stop()
    except Exception as e:
        print(f"Fatal error: {e}")
        daemon.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()

