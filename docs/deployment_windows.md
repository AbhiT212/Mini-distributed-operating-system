# MiniDOS Windows Deployment Guide

## Prerequisites

### System Requirements

- **Operating System**: Windows 10 or Windows 11
- **Python**: Version 3.10 or higher
- **RAM**: 2 GB minimum, 4 GB recommended
- **Disk**: 500 MB for application, additional for data
- **Network**: LAN connectivity (Ethernet or Wi-Fi on same subnet)
- **Permissions**: Administrator access required

### Network Requirements

- **TCP Ports**: 9000-9010 (configurable)
- **UDP Port**: 9050 for peer discovery
- **Firewall**: Allow inbound connections
- **Subnet**: All nodes must be on same broadcast domain

## Installation Steps

### Step 1: Download and Extract

Extract MiniDOS to a permanent location:

```
D:\Mini distributed os\
```

### Step 2: Run Installation Script

Open PowerShell as Administrator and run:

```powershell
cd "D:\Mini distributed os"
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
.\tools\installer\install_dependencies.ps1
```

This script will:
- Verify Python installation
- Install required packages (pyyaml, psutil, colorama)
- Create `C:\MiniDOS_FS` directory
- Set appropriate permissions
- Configure Windows Firewall rules

### Step 3: Configure Node

Edit `configs\default.yaml`:

```yaml
node:
  name: "NODE-01"  # Change for each node (NODE-01, NODE-02, etc.)

network:
  tcp_port: 9000
  discovery_port: 9050
  discovery_enabled: true

filesystem:
  root_path: "C:\\MiniDOS_FS"

# Optional: Add static peers if discovery doesn't work
peers:
  # - "192.168.1.100:9000"
  # - "192.168.1.101:9000"
```

**Important**: Each node must have a unique name!

### Step 4: Start Node Daemon

Run the startup script:

```batch
.\scripts\start_node.bat
```

You should see:
```
========================================
  Starting MiniDOS Node Daemon
========================================

Starting node daemon...
Configuration: configs\default.yaml
Logs: logs\node.log

[timestamp] - NodeDaemon - INFO - NodeDaemon initialized: NODE-01
[timestamp] - PeerManager - INFO - PeerManager started for node NODE-01
[timestamp] - NodeDaemon - INFO - TCP server listening on 0.0.0.0:9000
```

### Step 5: Verify Operation

Open a new PowerShell window and run:

```batch
.\scripts\debug_shell.bat
```

In the shell, try:
```
MiniDOS> help
MiniDOS> create test.txt
MiniDOS> write test.txt "Hello World"
MiniDOS> read test.txt
MiniDOS> ls
```

## Multi-Node Setup

### Scenario: 3-Node Cluster

**Node 1** (192.168.1.100):
```yaml
node:
  name: "NODE-01"
network:
  tcp_port: 9000
```

**Node 2** (192.168.1.101):
```yaml
node:
  name: "NODE-02"
network:
  tcp_port: 9000
```

**Node 3** (192.168.1.102):
```yaml
node:
  name: "NODE-03"
network:
  tcp_port: 9000
```

### Starting the Cluster

1. Start daemon on all three nodes
2. Wait 10-15 seconds for discovery
3. Check logs for "Added new peer" messages
4. Verify with `nodestats` command

### Troubleshooting Discovery

If nodes don't discover each other:

**Option 1: Check Network**
```powershell
.\tools\utilities\net_check.ps1 -RemoteHost 192.168.1.101 -Port 9000
```

**Option 2: Add Static Peers**

Edit `configs\default.yaml` on each node:
```yaml
network:
  discovery_enabled: true  # Keep enabled

peers:
  - "192.168.1.100:9000"
  - "192.168.1.101:9000"
  - "192.168.1.102:9000"
```

**Option 3: Check Firewall**
```powershell
Get-NetFirewallRule -DisplayName "MiniDOS*"
```

Should show two rules with "Enabled: True"

## Service Installation (Optional)

For production deployment, run as Windows service:

### Install Service

```powershell
# Install pywin32 first
pip install pywin32

# Install service
python kernel\service_wrapper.py install
```

### Manage Service

```batch
# Start
net start MiniDOSDaemon

# Stop
net stop MiniDOSDaemon

# Check status
sc query MiniDOSDaemon
```

### Uninstall Service

```powershell
python kernel\service_wrapper.py remove
```

## Configuration Options

### Network Settings

```yaml
network:
  tcp_port: 9000              # Main communication port
  discovery_port: 9050        # UDP broadcast port
  bind_address: "0.0.0.0"     # Listen on all interfaces
  discovery_enabled: true     # Auto peer discovery
  heartbeat_interval: 5       # Seconds between heartbeats
  reconnect_timeout: 30       # Peer timeout threshold
```

### Filesystem Settings

```yaml
filesystem:
  root_path: "C:\\MiniDOS_FS"
  metadata_db: "metadata.db"
  enable_watcher: true        # Watch for local changes
  sync_on_startup: true       # Sync on daemon start
  conflict_resolution: "timestamp"  # Latest wins
```

### Sync Settings

```yaml
sync:
  batch_size: 10              # Files per sync batch
  chunk_size: 1048576         # 1MB chunks for large files
  verify_checksums: true      # Verify integrity
  max_sync_threads: 3         # Parallel operations
  resync_interval: 300        # Full resync every 5 min
```

### Logging Settings

```yaml
logging:
  level: "INFO"               # DEBUG | INFO | WARNING | ERROR
  max_file_size: 10485760     # 10MB per log file
  backup_count: 5             # Keep 5 rotated logs
  console_output: true        # Print to console
```

## Monitoring and Maintenance

### Log Files

- `logs\node.log` - Main daemon logs
- `logs\sync.log` - File synchronization logs (if configured)
- `logs\cli.log` - Shell command logs (if configured)

### Checking Status

```batch
# View real-time logs
powershell Get-Content logs\node.log -Wait -Tail 50

# Check if daemon is running
tasklist | findstr python.exe
```

### Disk Space Management

The metadata database grows over time. To optimize:

```python
# Open Python shell
python

# Connect to metadata DB
from kernel.metadata_store import MetadataStore
meta = MetadataStore("C:\\MiniDOS_FS\\metadata.db")
meta.vacuum()
meta.close()
```

### Performance Tuning

**For many small files:**
- Increase `batch_size` to 20-50
- Increase `max_sync_threads` to 5

**For large files:**
- Increase `chunk_size` to 10MB
- Disable `verify_checksums` (faster but less safe)

**For slow networks:**
- Increase `reconnect_timeout` to 60
- Decrease `resync_interval` to 600 (10 min)

## Backup and Recovery

### Backing Up Data

```powershell
# Stop daemon
.\scripts\stop_node.bat

# Backup filesystem
robocopy C:\MiniDOS_FS D:\Backup\MiniDOS_FS /MIR

# Backup configuration
Copy-Item configs\default.yaml D:\Backup\
```

### Restoring Data

```powershell
# Stop daemon
.\scripts\stop_node.bat

# Restore filesystem
robocopy D:\Backup\MiniDOS_FS C:\MiniDOS_FS /MIR

# Start daemon (it will sync with peers)
.\scripts\start_node.bat
```

### Disaster Recovery

If all nodes fail:

1. Restore filesystem from backup on one node
2. Start that node's daemon
3. Start other nodes (they will sync from first node)
4. Verify with `nodestats` and integrity check

## Upgrading

### Minor Updates

```powershell
# Stop all daemons
.\scripts\stop_node.bat

# Update files (preserve configs and data)
# Keep: configs\, C:\MiniDOS_FS\

# Start daemons
.\scripts\start_node.bat
```

### Major Updates

1. Backup all nodes
2. Test upgrade on one node
3. If successful, upgrade remaining nodes
4. If issues, restore from backup

## Uninstallation

```powershell
# Stop daemon
.\scripts\stop_node.bat

# Remove service (if installed)
python kernel\service_wrapper.py remove

# Remove firewall rules
Remove-NetFirewallRule -DisplayName "MiniDOS TCP"
Remove-NetFirewallRule -DisplayName "MiniDOS UDP"

# Optional: Remove data
Remove-Item -Recurse -Force C:\MiniDOS_FS

# Remove application directory
cd ..
Remove-Item -Recurse -Force "D:\Mini distributed os"
```

## Security Considerations

### Network Isolation

- Deploy only on trusted LAN
- Do not expose to Internet
- Consider VLAN isolation for sensitive data

### Access Control

- Restrict admin access to daemon
- Use Windows ACLs for file permissions
- Audit access through logs

### Data Protection

- No encryption by default (LAN only)
- Implement backup strategy
- Test disaster recovery procedures

## Common Issues

See [troubleshooting.md](troubleshooting.md) for detailed solutions.

