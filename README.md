# Mini DoS: Distributed P2P File System

**Mini DoS** is a loosely coupled, P2P unified file system built in Python. It features a custom CLI and real-time event-driven auto-sync. Designed for seamless networking, it includes LAN auto-discovery with a manual IP configuration fallback, ensuring robust connectivity and data consistency across a distributed environment.

---

##  Prerequisites

Before running the system, ensure you have **Python 3.x** installed. You will also need to adjust your system permissions to allow the automation scripts to run.

### 1. Set Execution Policy

Open PowerShell as an **Administrator** and run the following to allow the installation scripts to execute:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

```

### 2. Install Dependencies

Run the provided installer script to set up the necessary Python libraries and environment:

```powershell
.\tools\installer\install_dependencies.ps1

```

---

##  How to Run

The system is designed to work across multiple nodes in a LAN. Follow these steps to get started:

### Starting a Node

To launch a Mini DoS node and join the P2P network, execute:

```powershell
.\scripts\start_node.bat

```

* **Auto-Discovery:** By default, the node will attempt to find other peers on your local network automatically.
* **Manual Fallback:** If auto-discovery fails, you can manually configure the IP in your `configs/` directory.

### Debugging the Shell

If you need to test commands or inspect the internal state of the kernel and file system, use the debug shell:

```powershell
.\scripts\debug_shell.bat

```

---

##  Project Structure

* **`cli/`**: Custom command-line interface implementation.
* **`kernel/`**: Core logic for process management and system calls.
* **`fs/`**: Distributed file system logic and P2P sync handlers.
* **`procmon/`**: Process monitoring and event-driven synchronization.
* **`configs/`**: Network and system configuration files.
* **`scripts/`**: Automation batch files for starting and debugging the system.

---

## 📖 Open Documentation PDF

For a deep dive into the system design, communication protocols, and P2P logic, please refer to the technical documentation:


---

## 🔐 Troubleshooting

### Administrator Rights

Certain networking features (like modifying firewall rules for P2P) require Administrator privileges. You can verify your current session status with:

```powershell
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

```

### Firewall Rules

If nodes cannot see each other, ensure the Mini DoS traffic is allowed through your firewall. You can check existing rules with:

```powershell
Get-NetFirewallRule | Where-Object {$_.DisplayName -like '*9050*' -or $_.DisplayName -like '*MiniDOS*'} | Select-Object DisplayName, Enabled, Direction, Action

```

---
