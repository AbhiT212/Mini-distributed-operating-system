"""
MiniDOS Network Protocol
Defines message formats, serialization, and validation
"""

import json
import hashlib
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class Message:
    """Base message structure for all network communication"""
    type: str              # command, sync, heartbeat, discovery, response
    action: str            # create, read, write, delete, mkdir, list, etc.
    path: str              # file/directory path
    content: Any           # payload data
    origin: str            # source node name
    timestamp: float       # Unix timestamp
    checksum: str = ""     # Message integrity check
    sequence: int = 0      # Sequence number for ordering
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Serialize message to JSON"""
        data = self.to_dict()
        # Calculate checksum WITHOUT the checksum field
        data_without_checksum = {k: v for k, v in data.items() if k != 'checksum'}
        content_str = json.dumps(data_without_checksum, sort_keys=True)
        data['checksum'] = self.calculate_checksum(content_str)
        return json.dumps(data)
    
    @staticmethod
    def calculate_checksum(data: str) -> str:
        """Calculate SHA256 checksum"""
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Deserialize message from JSON"""
        data = json.loads(json_str)
        received_checksum = data.pop('checksum', '')
        
        # Verify checksum
        content_str = json.dumps(data, sort_keys=True)
        calculated_checksum = cls.calculate_checksum(content_str)
        
        if received_checksum and received_checksum != calculated_checksum:
            raise ValueError("Message checksum validation failed")
        
        return cls(**data)
    
    def validate(self) -> bool:
        """Validate message structure"""
        required_fields = ['type', 'action', 'origin', 'timestamp']
        return all(hasattr(self, field) and getattr(self, field) for field in required_fields)


class MessageFactory:
    """Factory for creating different types of messages"""
    
    @staticmethod
    def create_command(action: str, path: str, content: Any, origin: str, sequence: int = 0) -> Message:
        """Create a command message"""
        return Message(
            type="command",
            action=action,
            path=path,
            content=content,
            origin=origin,
            timestamp=time.time(),
            sequence=sequence
        )
    
    @staticmethod
    def create_sync(action: str, path: str, content: Any, origin: str, metadata: Dict = None) -> Message:
        """Create a sync message"""
        payload = {
            'data': content,
            'metadata': metadata or {}
        }
        return Message(
            type="sync",
            action=action,
            path=path,
            content=payload,
            origin=origin,
            timestamp=time.time()
        )
    
    @staticmethod
    def create_heartbeat(origin: str, stats: Dict = None) -> Message:
        """Create a heartbeat message"""
        return Message(
            type="heartbeat",
            action="ping",
            path="",
            content=stats or {},
            origin=origin,
            timestamp=time.time()
        )
    
    @staticmethod
    def create_discovery(origin: str, port: int) -> Message:
        """Create a discovery announcement"""
        return Message(
            type="discovery",
            action="announce",
            path="",
            content={'port': port},
            origin=origin,
            timestamp=time.time()
        )
    
    @staticmethod
    def create_response(action: str, success: bool, message: str, origin: str, data: Any = None) -> Message:
        """Create a response message"""
        return Message(
            type="response",
            action=action,
            path="",
            content={
                'success': success,
                'message': message,
                'data': data
            },
            origin=origin,
            timestamp=time.time()
        )


class MessageValidator:
    """Validates incoming messages"""
    
    VALID_TYPES = ['command', 'sync', 'heartbeat', 'discovery', 'response']
    VALID_ACTIONS = [
        'create', 'read', 'write', 'delete', 'mkdir', 'list',
        'sync_file', 'sync_metadata', 'request_sync',
        'ping', 'pong', 'announce', 'nodestats', 'pstree',
        'history', 'loadbal'  # New commands for audit trail and load balancing
    ]
    
    @classmethod
    def validate_message(cls, msg: Message) -> tuple[bool, str]:
        """
        Validate message structure and content
        Returns: (is_valid, error_message)
        """
        if not msg.validate():
            return False, "Missing required fields"
        
        if msg.type not in cls.VALID_TYPES:
            return False, f"Invalid message type: {msg.type}"
        
        if msg.action not in cls.VALID_ACTIONS:
            return False, f"Invalid action: {msg.action}"
        
        if not msg.origin:
            return False, "Missing origin node"
        
        if msg.timestamp <= 0:
            return False, "Invalid timestamp"
        
        return True, ""


def encode_binary(data: bytes) -> str:
    """Encode binary data for transmission"""
    import base64
    return base64.b64encode(data).decode('utf-8')


def decode_binary(encoded: str) -> bytes:
    """Decode binary data from transmission"""
    import base64
    return base64.b64decode(encoded.encode('utf-8'))


def calculate_file_checksum(filepath: str) -> str:
    """Calculate SHA256 checksum of a file"""
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception:
        return ""

