# MiniDOS Architecture

## Overview

MiniDOS is a peer-to-peer distributed operating system designed for Windows LAN networks. It provides a unified filesystem and process monitoring across multiple nodes without requiring a central server.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     MiniDOS Node                        │
├─────────────────────────────────────────────────────────┤
│  CLI Layer                                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  MiniShell  │  Command Parser  │  Formatters     │  │
│  └──────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  Application Layer                                      │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Process Monitor  │  Aggregator  │  Stats        │  │
│  └──────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  Filesystem Layer                                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │  VFS  │  Sync Engine  │  Metadata Store          │  │
│  └──────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  Kernel Layer                                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Node Daemon  │  Peer Manager  │  Protocol       │  │
│  └──────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  Network Layer                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  TCP Server  │  UDP Discovery  │  Message Queue  │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Node Daemon (kernel/node_daemon.py)

The main service running on each node.

**Responsibilities:**
- TCP server for peer communication
- Message routing and processing
- Component coordination
- Service lifecycle management

**Key Features:**
- Multi-threaded connection handling
- Automatic peer reconnection
- Configuration management
- Graceful shutdown

### 2. Peer Manager (kernel/peer_manager.py)

Manages peer discovery and health monitoring.

**Responsibilities:**
- UDP broadcast discovery
- Peer list maintenance
- Heartbeat monitoring
- Connection state tracking

**Discovery Protocol:**
1. Each node broadcasts UDP announcement every 5 seconds
2. Listening nodes add broadcaster to peer list
3. Heartbeat timeout removes unresponsive peers
4. Static peers can be configured manually

### 3. Virtual File System (fs/vfs.py)

Provides unified file operations across the cluster.

**Operations:**
- `create(path)` - Create file
- `write(path, content)` - Write data
- `read(path)` - Read data
- `delete(path)` - Remove file
- `mkdir(path)` - Create directory
- `list(path)` - List contents

**Features:**
- Path validation and security
- Automatic parent directory creation
- Binary and text mode support
- Checksum calculation

### 4. Sync Engine (kernel/sync_engine.py)

Handles file replication and consistency.

**Sync Strategies:**
- **Push Sync**: Broadcasting changes to all peers
- **Pull Sync**: Requesting missing files from peers
- **Full Sync**: Complete metadata comparison

**Conflict Resolution:**
- Timestamp-based (latest wins)
- Version number tracking
- Checksum verification

**Resync Process:**
1. Node reconnects to cluster
2. Exchanges metadata with peers
3. Identifies missing/outdated files
4. Pulls required files in batches
5. Verifies integrity with checksums

### 5. Metadata Store (kernel/metadata_store.py)

SQLite-based storage for file versions.

**Schema:**

```sql
-- File metadata
files (
    id INTEGER PRIMARY KEY,
    filepath TEXT UNIQUE,
    checksum TEXT,
    size INTEGER,
    version INTEGER,
    modified_time REAL,
    created_time REAL,
    node_id TEXT,
    operation_type TEXT,
    is_deleted INTEGER
)

-- Sync history
sync_log (
    id INTEGER PRIMARY KEY,
    sync_id TEXT,
    source_node TEXT,
    target_node TEXT,
    filepath TEXT,
    action TEXT,
    timestamp REAL,
    status TEXT,
    error_message TEXT
)
```

### 6. Process Monitor (procmon/proc_agent.py)

Monitors system processes using psutil.

**Collected Metrics:**
- Process ID, name, status
- CPU usage percentage
- Memory usage percentage
- Running user
- Node assignment

**System Stats:**
- Overall CPU usage
- Memory usage and capacity
- Disk usage and capacity

### 7. CLI Interface (cli/minishell.py)

Interactive command-line shell.

**Features:**
- Colorized output
- Command history
- Error handling
- Remote command execution

## Network Protocol

### Message Format

All messages use JSON over TCP with length prefix:

```
[4 bytes: length][JSON message]
```

**Message Structure:**
```json
{
    "type": "command|sync|heartbeat|discovery|response",
    "action": "create|read|write|delete|...",
    "path": "file/path",
    "content": "...",
    "origin": "NODE-01",
    "timestamp": 1731483800.0,
    "checksum": "abc123...",
    "sequence": 0
}
```

### Communication Patterns

**1. Command Flow:**
```
CLI → Node Daemon → VFS → Sync Engine → Broadcast to Peers
```

**2. File Sync Flow:**
```
Node A: File Modified → Calculate Checksum → Create Sync Message
     ↓
Broadcast to all active peers
     ↓
Node B: Receive → Validate → Write → Update Metadata
```

**3. Discovery Flow:**
```
Node: UDP Broadcast (port 9050) → "I'm here at IP:PORT"
     ↓
Peers: Receive → Add to peer list → Update last_seen
```

## Data Replication

### Full Replication Strategy

Every node maintains a complete copy of the filesystem.

**Advantages:**
- Fast local reads
- High availability
- Simple consistency model
- No single point of failure

**Trade-offs:**
- Storage overhead (N copies)
- Write amplification
- Limited scalability (~10 nodes max)

### Consistency Model

**Eventually Consistent** with timestamp-based ordering:

1. All writes are timestamped
2. Conflicts resolved by latest timestamp
3. Version numbers track change history
4. Checksums verify data integrity

### Failure Scenarios

**Scenario 1: Node Crashes**
- Other nodes continue operating
- Crashed node's data preserved on peers
- On restart, full resync occurs

**Scenario 2: Network Partition**
- Each partition continues independently
- Conflicting writes may occur
- On reconnection, timestamp wins
- Version vectors track history

**Scenario 3: Concurrent Writes**
- Each node writes locally
- Timestamp determines winner
- Loser's version preserved in history
- No data loss, predictable outcome

## Security Model

### Trust Assumptions

- All nodes on LAN are trusted
- No encryption in transit (LAN only)
- Administrator-level permissions required
- No authentication between nodes

### Permission Enforcement

**Windows-specific:**
- UAC elevation required
- NTFS ACL for filesystem access
- Firewall rules for network ports
- Service account for daemon mode

### Attack Surface

**Mitigated:**
- Path traversal (VFS validation)
- Message injection (checksum validation)
- Unauthorized filesystem access (admin-only)

**Not Addressed:**
- Network sniffing (unencrypted)
- Rogue node joining (no auth)
- DoS attacks (no rate limiting)

## Performance Characteristics

### Latency

- Local reads: ~1ms (filesystem)
- Remote commands: ~10-50ms (network + processing)
- File sync: ~100ms per file (LAN)
- Discovery: ~5s (broadcast interval)

### Throughput

- File transfer: ~100 MB/s (Gigabit LAN)
- Metadata sync: ~1000 files/second
- Command processing: ~100 ops/second

### Scalability Limits

- **Nodes**: 2-10 (broadcast domain)
- **Files**: ~10,000 (metadata performance)
- **File size**: Unlimited (chunked transfer)
- **Network**: Single subnet (UDP broadcast)

## Future Enhancements

1. **Partial Replication** - Sharding for scalability
2. **Encryption** - TLS for message security
3. **Authentication** - Certificate-based node identity
4. **Cross-subnet** - Multicast or gossip protocol
5. **Conflict Resolution** - CRDTs for better consistency
6. **Performance** - Delta sync for large files
7. **Monitoring** - Web dashboard for cluster status

