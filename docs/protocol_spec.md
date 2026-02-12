# MiniDOS Network Protocol Specification

## Overview

MiniDOS uses a custom JSON-based protocol over TCP for command and data transfer, with UDP broadcast for peer discovery.

## Transport Layer

### TCP Protocol (Ports 9000-9010)

**Purpose**: Main communication between nodes

**Connection Model**: 
- Short-lived connections
- One request per connection
- Client opens connection, sends message, receives response, closes

**Message Format**:
```
[4-byte length prefix][JSON payload]
```

**Length Prefix**:
- Big-endian unsigned 32-bit integer
- Indicates byte count of following JSON payload
- Maximum message size: 4,294,967,295 bytes

**Example**:
```
[0x00, 0x00, 0x01, 0x2F]  # 303 bytes
{"type":"command",...}     # 303-byte JSON
```

### UDP Protocol (Port 9050)

**Purpose**: Peer discovery via broadcast

**Message Format**: Raw JSON (no length prefix)

**Broadcast Address**: 255.255.255.255 (local subnet)

**Frequency**: Every 5 seconds per node

## Message Types

### 1. Command Message

**Purpose**: Execute file operations

**Structure**:
```json
{
    "type": "command",
    "action": "create|read|write|delete|mkdir|list",
    "path": "path/to/file",
    "content": "data or empty",
    "origin": "NODE-01",
    "timestamp": 1731483800.123,
    "checksum": "a1b2c3d4",
    "sequence": 0
}
```

**Fields**:
- `type`: Always "command"
- `action`: Operation to perform
- `path`: Target file/directory path (relative to VFS root)
- `content`: Payload data (file content, empty for read/delete)
- `origin`: Source node name
- `timestamp`: Unix timestamp with milliseconds
- `checksum`: First 16 chars of SHA-256 hash (message integrity)
- `sequence`: Optional sequence number for ordering

**Actions**:
- `create` - Create empty file
- `read` - Read file content
- `write` - Write file content
- `delete` - Delete file/directory
- `mkdir` - Create directory
- `list` - List directory contents

### 2. Sync Message

**Purpose**: Replicate file changes

**Structure**:
```json
{
    "type": "sync",
    "action": "sync_file|sync_metadata|request_file",
    "path": "path/to/file",
    "content": {
        "data": "base64_encoded_or_raw",
        "metadata": {
            "checksum": "full_sha256_hash",
            "size": 12345,
            "operation": "create|modify|delete",
            "version": 5
        }
    },
    "origin": "NODE-02",
    "timestamp": 1731483800.456,
    "checksum": "e5f6g7h8"
}
```

**Actions**:
- `sync_file` - Push file to peer
- `sync_metadata` - Exchange metadata tables
- `request_file` - Pull file from peer

**Metadata Object**:
- `checksum`: Full SHA-256 hash of file
- `size`: File size in bytes
- `operation`: How file was modified
- `version`: Monotonically increasing version number

### 3. Heartbeat Message

**Purpose**: Keep-alive and health monitoring

**Structure**:
```json
{
    "type": "heartbeat",
    "action": "ping",
    "path": "",
    "content": {
        "cpu_percent": 23.5,
        "memory_percent": 45.2,
        "disk_percent": 67.8,
        "files": 142,
        "peers": 2
    },
    "origin": "NODE-03",
    "timestamp": 1731483801.789,
    "checksum": "i9j0k1l2"
}
```

**Response (action="pong")**:
```json
{
    "type": "response",
    "action": "pong",
    "path": "",
    "content": {
        "success": true,
        "message": "Alive",
        "data": { /* node stats */ }
    },
    "origin": "NODE-03",
    "timestamp": 1731483801.890,
    "checksum": "m3n4o5p6"
}
```

### 4. Discovery Message

**Purpose**: Announce presence to LAN

**Transport**: UDP broadcast

**Structure**:
```json
{
    "type": "discovery",
    "action": "announce",
    "path": "",
    "content": {
        "port": 9000,
        "version": "1.0.0"
    },
    "origin": "NODE-04",
    "timestamp": 1731483802.001,
    "checksum": "q7r8s9t0"
}
```

**Broadcast Interval**: 5 seconds

**TTL**: 64 hops (default)

### 5. Response Message

**Purpose**: Acknowledge command/sync operations

**Structure**:
```json
{
    "type": "response",
    "action": "create|read|write|etc",
    "path": "",
    "content": {
        "success": true,
        "message": "Operation completed",
        "data": null
    },
    "origin": "NODE-01",
    "timestamp": 1731483803.234,
    "checksum": "u1v2w3x4"
}
```

**Content Fields**:
- `success`: Boolean operation result
- `message`: Human-readable status
- `data`: Optional return data (e.g., file content for read)

## Checksum Calculation

**Algorithm**: SHA-256

**Input**: JSON message with checksum field set to empty string

**Output**: First 16 hexadecimal characters

**Python Implementation**:
```python
import hashlib
import json

def calculate_checksum(message_dict):
    # Remove checksum field
    data = {k: v for k, v in message_dict.items() if k != 'checksum'}
    
    # Serialize deterministically
    json_str = json.dumps(data, sort_keys=True)
    
    # Hash
    hash_obj = hashlib.sha256(json_str.encode())
    return hash_obj.hexdigest()[:16]
```

## Connection Flow

### Client-Server Pattern

```
Client                          Server
  |                               |
  |--- TCP Connect (port 9000) -->|
  |                               |
  |--- Send Length Prefix ------->|
  |--- Send JSON Message -------->|
  |                               |
  |                               |--- Process Message
  |                               |
  |<-- Send Length Prefix --------|
  |<-- Send JSON Response --------|
  |                               |
  |--- TCP Close ---------------->|
```

### Broadcast Pattern

```
Node A                    Node B                    Node C
  |                         |                         |
  |-- UDP Broadcast ------->|                         |
  |        (discovery)      |-- UDP Broadcast ------->|
  |                         |        (discovery)      |
  |                         |                         |
  |<-- Add to peer list ----|<-- Add to peer list ----|
```

## Error Handling

### Network Errors

**Timeout**: 30 seconds for TCP connections

**Retry Logic**: 
- Command: 3 retries with exponential backoff
- Sync: Retry until success or peer marked dead
- Discovery: Continuous broadcast, no retries

**Error Response**:
```json
{
    "type": "response",
    "action": "error",
    "path": "",
    "content": {
        "success": false,
        "message": "Checksum validation failed",
        "data": null
    },
    "origin": "NODE-01",
    "timestamp": 1731483804.567,
    "checksum": "y5z6a7b8"
}
```

### Message Validation

**Required Checks**:
1. JSON syntax validity
2. Required fields present
3. Checksum matches calculated value
4. Timestamp within reasonable range (±5 minutes)
5. Action is valid for message type

**Invalid Message Handling**:
- Log warning
- Send error response
- Close connection
- Do not process

## Sync Protocol

### Full Resync Procedure

```
Node A (reconnecting)              Node B (active)
    |                                    |
    |--- Request Metadata -------------->|
    |<-- Send Metadata Table ------------|
    |                                    |
    |--- Compare Local Metadata         |
    |                                    |
    |--- Request Missing Files --------->|
    |<-- Send File Data -----------------|
    |                                    |
    |--- Apply Changes                  |
    |--- Update Metadata                |
    |                                    |
    |--- Send Ack ---------------------->|
```

### File Sync Procedure

```
Node A (writer)                   Node B (replica)
    |                                    |
    |--- User writes file               |
    |--- Calculate checksum             |
    |--- Update local metadata          |
    |                                    |
    |--- Broadcast Sync Message ------->|
    |                                    |--- Receive message
    |                                    |--- Validate checksum
    |                                    |--- Write file
    |                                    |--- Update metadata
    |                                    |
    |<-- Send Success Response ----------|
```

### Conflict Resolution

When two nodes modify same file simultaneously:

```
Node A: version=5, timestamp=1000.100
Node B: version=5, timestamp=1000.200

Result: Node B wins (later timestamp)

Both nodes converge to:
  version=6, timestamp=1000.200, source=NODE-B
```

## Security Considerations

### Current Implementation

**Authentication**: None (trusted LAN)

**Encryption**: None (plaintext)

**Integrity**: Checksum only (not cryptographic)

**Authorization**: Peer-to-peer (all nodes equal)

### Threat Model

**Protected Against**:
- Accidental corruption (checksums)
- Path traversal (VFS validation)

**Not Protected Against**:
- Network sniffing (unencrypted)
- Message injection (no HMAC)
- Replay attacks (no nonces)
- Rogue nodes (no authentication)

### Future Enhancements

1. **TLS**: Encrypt all TCP connections
2. **Certificates**: Mutual TLS authentication
3. **HMAC**: Cryptographic message signatures
4. **Nonces**: Prevent replay attacks
5. **Rate Limiting**: Prevent DoS

## Performance Characteristics

### Latency

- **Discovery**: 0-5 seconds (broadcast interval)
- **Command**: 10-50 ms (network + processing)
- **Small file sync**: 50-200 ms (<1MB)
- **Large file sync**: ~100 MB/s (Gigabit LAN)

### Bandwidth

- **Heartbeat**: ~500 bytes every 5s = 100 B/s per peer
- **Discovery**: ~200 bytes every 5s = 40 B/s
- **Idle overhead**: ~150 B/s per peer connection
- **File sync**: Proportional to file size

### Scalability

- **Message overhead**: O(N) where N = peer count
- **Broadcast storms**: Limited by batch size
- **Connection overhead**: Short-lived (no keep-alive)

## Protocol Versioning

**Current Version**: 1.0.0

**Version Field**: In discovery messages

**Compatibility**: 
- Minor versions are compatible
- Major versions may break compatibility

**Negotiation**: Not implemented (all nodes must match)

## Examples

See `examples/` directory for:
- `simple_command.py` - Send a command message
- `file_sync.py` - Sync a file between nodes
- `discovery_test.py` - Test peer discovery
- `stress_test.py` - Performance testing

