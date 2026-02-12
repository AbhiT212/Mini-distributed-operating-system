"""
Peer Manager
Handles peer discovery, connection management, and heartbeat monitoring
"""

import socket
import threading
import time
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from kernel.net_protocol import Message, MessageFactory


@dataclass
class Peer:
    """Represents a peer node in the network"""
    name: str
    address: str  # IP address
    port: int
    last_seen: float = field(default_factory=time.time)
    status: str = "active"  # active, inactive, disconnected
    latency: float = 0.0  # milliseconds
    
    def __hash__(self):
        return hash(f"{self.address}:{self.port}")
    
    def __eq__(self, other):
        if isinstance(other, Peer):
            return self.address == other.address and self.port == other.port
        return False
    
    def is_alive(self, timeout: int = 30) -> bool:
        """Check if peer is still alive based on last heartbeat"""
        return (time.time() - self.last_seen) < timeout
    
    def update_seen(self):
        """Update last seen timestamp"""
        self.last_seen = time.time()
        self.status = "active"


class PeerManager:
    """Manages peer discovery and connection tracking"""
    
    def __init__(self, node_name: str, tcp_port: int, discovery_port: int, 
                 discovery_enabled: bool = True, reconnect_timeout: int = 30):
        self.node_name = node_name
        self.tcp_port = tcp_port
        self.discovery_port = discovery_port
        self.discovery_enabled = discovery_enabled
        self.reconnect_timeout = reconnect_timeout
        
        self.peers: Dict[str, Peer] = {}  # address:port -> Peer
        self.peers_lock = threading.RLock()
        
        self.discovery_socket: Optional[socket.socket] = None
        self.discovery_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        
        self.running = False
        self.logger = logging.getLogger("PeerManager")
        
        # Callbacks
        self.on_peer_connected = None
        self.on_peer_disconnected = None
    
    def start(self):
        """Start peer discovery and monitoring"""
        self.running = True
        
        if self.discovery_enabled:
            self._start_discovery()
        
        # Start heartbeat monitoring
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        self.logger.info(f"PeerManager started for node {self.node_name}")
    
    def stop(self):
        """Stop all peer management activities"""
        self.running = False
        
        if self.discovery_socket:
            try:
                self.discovery_socket.close()
            except:
                pass
        
        if self.discovery_thread:
            self.discovery_thread.join(timeout=2)
        
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2)
        
        self.logger.info("PeerManager stopped")
    
    def _start_discovery(self):
        """Start UDP broadcast discovery"""
        try:
            self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.discovery_socket.settimeout(1.0)
            
            # Bind to discovery port
            self.discovery_socket.bind(('', self.discovery_port))
            
            # Start listener thread
            self.discovery_thread = threading.Thread(target=self._discovery_listener, daemon=True)
            self.discovery_thread.start()
            
            # Start announcer thread
            announcer_thread = threading.Thread(target=self._discovery_announcer, daemon=True)
            announcer_thread.start()
            
            self.logger.info(f"Discovery service started on port {self.discovery_port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start discovery: {e}")
    
    def _discovery_listener(self):
        """Listen for discovery broadcasts from other nodes"""
        while self.running and self.discovery_socket:
            try:
                data, addr = self.discovery_socket.recvfrom(4096)
                
                # Parse discovery message
                msg = Message.from_json(data.decode('utf-8'))
                
                if msg.type == "discovery" and msg.origin != self.node_name:
                    peer_address = addr[0]
                    peer_port = msg.content.get('port', self.tcp_port)
                    
                    self.add_peer(msg.origin, peer_address, peer_port)
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.debug(f"Discovery listener error: {e}")
    
    def _discovery_announcer(self):
        """Periodically broadcast discovery messages"""
        while self.running:
            try:
                # Create discovery message
                msg = MessageFactory.create_discovery(self.node_name, self.tcp_port)
                
                # Broadcast to LAN
                broadcast_addr = ('<broadcast>', self.discovery_port)
                self.discovery_socket.sendto(msg.to_json().encode('utf-8'), broadcast_addr)
                
                self.logger.debug(f"Sent discovery broadcast")
                
            except Exception as e:
                self.logger.debug(f"Discovery announcer error: {e}")
            
            time.sleep(5)  # Announce every 5 seconds
    
    def _heartbeat_loop(self):
        """Monitor peer health, send pings, and remove dead peers"""
        while self.running:
            try:
                with self.peers_lock:
                    dead_peers = []
                    
                    for key, peer in self.peers.items():
                        # Check if peer is still alive
                        if not peer.is_alive(self.reconnect_timeout):
                            peer.status = "disconnected"
                            dead_peers.append(key)
                            self.logger.warning(f"Peer {peer.name} ({peer.address}) is unresponsive")
                        else:
                            # Send heartbeat ping to keep connection alive
                            self._send_ping_to_peer(peer)
                    
                    # Remove dead peers
                    for key in dead_peers:
                        peer = self.peers.pop(key)
                        if self.on_peer_disconnected:
                            try:
                                self.on_peer_disconnected(peer)
                            except Exception as e:
                                self.logger.error(f"Error in disconnect callback: {e}")
                
            except Exception as e:
                self.logger.error(f"Heartbeat loop error: {e}")
            
            time.sleep(5)
    
    def _send_ping_to_peer(self, peer: Peer):
        """Send a ping message to peer to keep connection alive"""
        try:
            import socket
            from kernel.net_protocol import MessageFactory
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((peer.address, peer.port))
            
            # Send ping message
            msg = MessageFactory.create_heartbeat(self.node_name)
            msg_json = msg.to_json()
            msg_bytes = msg_json.encode('utf-8')
            length = len(msg_bytes).to_bytes(4, 'big')
            sock.sendall(length + msg_bytes)
            
            # Receive pong
            sock.recv(8192)
            sock.close()
            
            self.logger.debug(f"Sent heartbeat ping to {peer.name}")
            
        except Exception as e:
            self.logger.debug(f"Failed to ping {peer.name}: {e}")
    
    def add_peer(self, name: str, address: str, port: int) -> bool:
        """Add or update a peer"""
        try:
            key = f"{address}:{port}"
            
            with self.peers_lock:
                if key in self.peers:
                    # Update existing peer
                    self.peers[key].update_seen()
                    self.logger.debug(f"Updated peer {name} ({address}:{port})")
                else:
                    # Add new peer
                    peer = Peer(name=name, address=address, port=port)
                    self.peers[key] = peer
                    self.logger.info(f"Added new peer {name} ({address}:{port})")
                    
                    # Trigger callback
                    if self.on_peer_connected:
                        try:
                            self.on_peer_connected(peer)
                        except Exception as e:
                            self.logger.error(f"Error in connect callback: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add peer: {e}")
            return False
    
    def remove_peer(self, address: str, port: int):
        """Remove a peer"""
        key = f"{address}:{port}"
        
        with self.peers_lock:
            if key in self.peers:
                peer = self.peers.pop(key)
                self.logger.info(f"Removed peer {peer.name} ({address}:{port})")
                
                if self.on_peer_disconnected:
                    try:
                        self.on_peer_disconnected(peer)
                    except Exception as e:
                        self.logger.error(f"Error in disconnect callback: {e}")
    
    def update_peer_heartbeat(self, address: str, port: int):
        """Update peer's last seen timestamp"""
        key = f"{address}:{port}"
        
        with self.peers_lock:
            if key in self.peers:
                self.peers[key].update_seen()
    
    def get_active_peers(self) -> List[Peer]:
        """Get list of active peers"""
        with self.peers_lock:
            return [p for p in self.peers.values() if p.status == "active"]
    
    def get_all_peers(self) -> List[Peer]:
        """Get list of all known peers"""
        with self.peers_lock:
            return list(self.peers.values())
    
    def get_peer(self, address: str, port: int) -> Optional[Peer]:
        """Get a specific peer"""
        key = f"{address}:{port}"
        with self.peers_lock:
            return self.peers.get(key)
    
    def get_peer_count(self) -> int:
        """Get number of active peers"""
        return len(self.get_active_peers())
    
    def add_static_peer(self, address: str, port: int, name: str = None):
        """Manually add a static peer (for non-discovery scenarios)"""
        if not name:
            name = f"{address}:{port}"
        
        return self.add_peer(name, address, port)
    
    def load_static_peers(self, peer_list: List[str]):
        """
        Load static peers from configuration
        peer_list format: ["192.168.1.100:9000", "192.168.1.101:9000"]
        """
        for peer_str in peer_list:
            try:
                address, port_str = peer_str.split(':')
                port = int(port_str)
                self.add_static_peer(address, port)
            except Exception as e:
                self.logger.error(f"Failed to parse static peer '{peer_str}': {e}")

