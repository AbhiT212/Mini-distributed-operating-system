# MiniDOS Troubleshooting Guide

## Common Issues and Solutions

### 1. Node Daemon Won't Start

#### Symptom
```
ERROR: This application requires Administrator privileges.
```

**Solution:**
- Right-click `start_node.bat` and select "Run as Administrator"
- Or open PowerShell as Administrator first, then run the script

#### Symptom
```
Failed to start TCP server: [WinError 10048] Only one usage of each socket address
```

**Cause:** Port 9000 is already in use.

**Solution:**
```powershell
# Check what's using the port
netstat -ano | findstr :9000

# Stop the conflicting process
taskkill /PID <process_id> /F

# Or change port in configs\default.yaml
```

#### Symptom
```
Failed to create VFS root: [WinError 5] Access is denied
```

**Cause:** Insufficient permissions on `C:\MiniDOS_FS`

**Solution:**
```powershell
# Run as Administrator
icacls "C:\MiniDOS_FS" /grant Everyone:(OI)(CI)F /T
```

### 2. Nodes Can't Discover Each Other

#### Symptom
No "Added new peer" messages in logs after 30 seconds.

**Diagnosis:**
```powershell
.\tools\utilities\net_check.ps1 -RemoteHost <peer_ip> -Port 9000
```

**Common Causes:**

**A. Firewall Blocking**

Check firewall rules:
```powershell
Get-NetFirewallRule -DisplayName "MiniDOS*"
```

If missing or disabled:
```powershell
.\tools\installer\install_dependencies.ps1
```

**B. Different Subnets**

Nodes must be on same subnet for UDP broadcast.

Check your IP:
```powershell
ipconfig
```

All nodes should have IPs like `192.168.1.x` (same subnet).

**C. Discovery Disabled**

Check `configs\default.yaml`:
```yaml
network:
  discovery_enabled: true  # Must be true
```

**Workaround: Static Peers**

Add to `configs\default.yaml`:
```yaml
peers:
  - "192.168.1.100:9000"
  - "192.168.1.101:9000"
```

### 3. File Sync Issues

#### Symptom
File created on Node A doesn't appear on Node B.

**Check connectivity:**
```powershell
# On Node B, check logs for sync messages
Get-Content logs\node.log -Tail 50
```

Look for:
- "Applied remote change: <filename>"
- "Synced file to peers: <filename>"

**Check metadata:**
```python
# On both nodes
python
from kernel.metadata_store import MetadataStore
meta = MetadataStore("C:\\MiniDOS_FS\\metadata.db")
files = meta.get_all_files()
print(f"Total files: {len(files)}")
for f in files[:5]:
    print(f"{f['filepath']} - v{f['version']} - {f['checksum'][:8]}")
```

**Force resync:**
```powershell
# Stop daemon
.\scripts\stop_node.bat

# Delete metadata (will trigger full resync)
Remove-Item C:\MiniDOS_FS\metadata.db

# Start daemon
.\scripts\start_node.bat
```

#### Symptom
Checksum mismatch errors in logs.

**Solution:**
```
Checksum mismatch for <file>
```

This indicates file corruption during transfer.

1. Delete the corrupted file
2. Restart daemon (will resync from peers)
3. If persistent, check network quality

### 4. CLI Connection Issues

#### Symptom
```
Failed to send command: [WinError 10061] No connection could be made
```

**Cause:** Node daemon not running or wrong port.

**Solution:**
```powershell
# Check if daemon is running
tasklist | findstr python.exe

# Check daemon logs
Get-Content logs\node.log -Tail 20

# Verify port in config
Get-Content configs\default.yaml | Select-String "tcp_port"
```

#### Symptom
Commands time out or hang.

**Solution:**
```powershell
# Check daemon responsiveness
Test-NetConnection -ComputerName localhost -Port 9000

# If no response, restart daemon
.\scripts\stop_node.bat
.\scripts\start_node.bat
```

### 5. Performance Issues

#### Symptom
Slow file operations or high CPU usage.

**Check system resources:**
```powershell
# Monitor daemon
Get-Process python | Format-Table Name, CPU, WS -AutoSize

# Check disk I/O
Get-Counter "\PhysicalDisk(*)\% Disk Time"
```

**Optimization:**

For high CPU:
```yaml
# In configs\default.yaml
sync:
  max_sync_threads: 2  # Reduce from 3
  
monitoring:
  update_interval: 5  # Increase from 2
```

For slow network:
```yaml
sync:
  chunk_size: 524288  # Reduce to 512KB
  batch_size: 5       # Reduce from 10
```

### 6. Process Monitoring Issues

#### Symptom
`nodestats` or `pstree` show incomplete data.

**Cause:** Insufficient permissions to access process information.

**Solution:**
Ensure daemon runs as Administrator.

#### Symptom
High memory usage from process monitoring.

**Solution:**
```yaml
# In configs\default.yaml
monitoring:
  enabled: true
  update_interval: 10  # Increase from 2 seconds
```

### 7. Database Issues

#### Symptom
```
sqlite3.OperationalError: database is locked
```

**Cause:** Multiple processes accessing same database.

**Solution:**
```powershell
# Ensure only one daemon per node
.\scripts\stop_node.bat
taskkill /F /IM python.exe
.\scripts\start_node.bat
```

#### Symptom
Database corruption.

**Recovery:**
```powershell
# Stop daemon
.\scripts\stop_node.bat

# Backup current database
Copy-Item C:\MiniDOS_FS\metadata.db C:\MiniDOS_FS\metadata.db.backup

# Delete corrupted database
Remove-Item C:\MiniDOS_FS\metadata.db

# Start daemon (will create new database and sync)
.\scripts\start_node.bat
```

### 8. Peer Disconnection Issues

#### Symptom
Peers frequently disconnect and reconnect.

**Check network stability:**
```powershell
# Ping test
ping -t <peer_ip>
```

If high packet loss or latency:
```yaml
# Increase timeout
network:
  reconnect_timeout: 60  # Increase from 30
  heartbeat_interval: 10 # Increase from 5
```

### 9. Windows-Specific Issues

#### Symptom
```
'python' is not recognized as an internal or external command
```

**Solution:**
Add Python to PATH:
1. Search "Environment Variables" in Windows
2. Edit "Path" in User or System variables
3. Add Python installation directory
4. Restart PowerShell

#### Symptom
PowerShell execution policy error.

**Solution:**
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Symptom
UAC prompts appear repeatedly.

**Solution:**
Run scripts from Administrator PowerShell, or install as service.

### 10. Logging Issues

#### Symptom
No logs being created.

**Check:**
```powershell
# Verify logs directory exists
Test-Path logs

# If not, create it
New-Item -ItemType Directory -Path logs

# Check logging configuration
Get-Content configs\default.yaml | Select-String -Context 2 "logging"
```

#### Symptom
Log files growing too large.

**Solution:**
```yaml
# In configs\default.yaml
logging:
  max_file_size: 5242880  # Reduce to 5MB
  backup_count: 3         # Keep fewer rotations
```

**Manual cleanup:**
```powershell
# Archive old logs
Compress-Archive -Path logs\*.log -DestinationPath logs\archive.zip
Remove-Item logs\*.log
```

## Diagnostic Commands

### Check System Status

```powershell
# Daemon status
tasklist | findstr python.exe

# Port status
netstat -ano | findstr "9000 9050"

# Firewall rules
Get-NetFirewallRule -DisplayName "MiniDOS*" | Format-Table

# File system access
Test-Path C:\MiniDOS_FS -PathType Container

# Recent logs
Get-Content logs\node.log -Tail 50
```

### Network Diagnostics

```powershell
# Test connectivity
.\tools\utilities\net_check.ps1 -RemoteHost <peer_ip> -Port 9000

# Check local IP
ipconfig | findstr IPv4

# Test UDP broadcast
# (Requires third-party tools like Wireshark)
```

### Database Inspection

```python
python
from kernel.metadata_store import MetadataStore
meta = MetadataStore("C:\\MiniDOS_FS\\metadata.db")

# Check stats
print(meta.get_stats())

# List recent syncs
syncs = meta.get_sync_history(10)
for s in syncs:
    print(f"{s['timestamp']}: {s['action']} - {s['filepath']} - {s['status']}")

# Check for corruption
all_files = meta.get_all_files()
print(f"Total files in metadata: {len(all_files)}")
```

### File System Check

```python
python
from fs.vfs import VirtualFileSystem
vfs = VirtualFileSystem("C:\\MiniDOS_FS")

# Get stats
stats = vfs.get_stats()
print(f"Files: {stats['total_files']}")
print(f"Dirs: {stats['total_dirs']}")
print(f"Size: {stats['total_size']} bytes")

# List all files
files = vfs.get_all_files()
for f in files[:10]:
    print(f)
```

## Getting Help

### Enable Debug Logging

```yaml
# In configs\default.yaml
logging:
  level: "DEBUG"
  console_output: true
```

Restart daemon and reproduce issue. Check logs for detailed information.

### Collecting Diagnostic Information

```powershell
# Create diagnostic report
$report = @"
MiniDOS Diagnostic Report
Generated: $(Get-Date)

System:
$(systeminfo | Select-String "OS Name|OS Version|System Type")

Python:
$(python --version)

Network:
$(ipconfig | Select-String "IPv4")

Processes:
$(tasklist | findstr python.exe)

Firewall:
$(Get-NetFirewallRule -DisplayName "MiniDOS*" | Format-Table -AutoSize | Out-String)

Ports:
$(netstat -ano | findstr "9000 9050")

Recent Logs:
$(Get-Content logs\node.log -Tail 30)
"@

$report | Out-File diagnostic_report.txt
Write-Host "Report saved to diagnostic_report.txt"
```

### Resetting Everything

Last resort - complete reset:

```powershell
# Stop daemon
.\scripts\stop_node.bat

# Remove all data
Remove-Item -Recurse -Force C:\MiniDOS_FS
Remove-Item -Recurse -Force logs

# Reinstall
.\tools\installer\install_dependencies.ps1

# Start fresh
.\scripts\start_node.bat
```

## Known Limitations

1. **Subnet Limitation**: Nodes must be on same broadcast domain
2. **File Size**: Very large files (>1GB) may cause timeouts
3. **Concurrent Writes**: No locking - last write wins
4. **Scalability**: Not tested beyond 10 nodes
5. **Windows Only**: No Linux/Mac support currently

## Reporting Issues

When reporting issues, include:

1. Windows version
2. Python version
3. Configuration file (`configs\default.yaml`)
4. Recent logs (`logs\node.log`)
5. Diagnostic report (see above)
6. Steps to reproduce

