"""
CLI Commands
Implementation of all available commands
"""

import socket
import logging
from typing import Optional, Dict, Any, List
from kernel.net_protocol import Message, MessageFactory


class CommandExecutor:
    """Executes commands on the local or remote nodes"""
    
    def __init__(self, local_node_address: str, local_node_port: int):
        self.local_address = local_node_address
        self.local_port = local_node_port
        self.logger = logging.getLogger("CommandExecutor")
        self.current_dir = ""  # Current working directory
        # Get actual node name from daemon
        self.node_name = self._get_daemon_node_name()
    
    def _get_daemon_node_name(self) -> str:
        """Get the actual node name from the daemon"""
        try:
            msg = MessageFactory.create_command("nodestats", "", {}, "CLI")
            response = self._send_command(msg)
            if response and response.origin:
                return response.origin
        except:
            pass
        return "CLI"  # Fallback if daemon not reachable
    
    def _resolve_path(self, path: str) -> str:
        """Resolve path relative to current directory"""
        if not path:
            return self.current_dir if self.current_dir else ""
        
        # Absolute path
        if path.startswith("/"):
            return path.lstrip("/")
        
        # Relative path
        if self.current_dir:
            return f"{self.current_dir}/{path}"
        return path
    
    def execute(self, command: str, args: List[str], current_dir: str = "") -> tuple[bool, str, Any]:
        """
        Execute a command
        Returns: (success, message, data)
        current_dir: Current working directory for relative paths
        """
        # Store current directory for path resolution
        self.current_dir = current_dir
        
        try:
            if command == "create":
                return self._cmd_create(args)
            elif command == "write":
                return self._cmd_write(args)
            elif command == "read":
                return self._cmd_read(args)
            elif command == "delete":
                return self._cmd_delete(args)
            elif command == "mkdir":
                return self._cmd_mkdir(args)
            elif command == "ls":
                return self._cmd_ls(args)
            elif command == "nodestats":
                return self._cmd_nodestats(args)
            elif command == "pstree":
                return self._cmd_pstree(args)
            elif command == "history":
                return self._cmd_history(args)
            elif command == "loadbal":
                return self._cmd_loadbal(args)
            elif command == "help":
                return self._cmd_help(args)
            else:
                return False, f"Unknown command: {command}", None
                
        except Exception as e:
            self.logger.error(f"Command execution error: {e}")
            return False, f"Error: {str(e)}", None
    
    def _send_command(self, msg: Message) -> Optional[Message]:
        """Send command to local node daemon"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.local_address, self.local_port))
            
            # Send message
            msg_json = msg.to_json()
            msg_bytes = msg_json.encode('utf-8')
            length = len(msg_bytes).to_bytes(4, 'big')
            sock.sendall(length + msg_bytes)
            
            # Receive response
            response_len_bytes = sock.recv(4)
            if not response_len_bytes:
                return None
            
            response_len = int.from_bytes(response_len_bytes, 'big')
            response_data = b""
            
            while len(response_data) < response_len:
                chunk = sock.recv(min(8192, response_len - len(response_data)))
                if not chunk:
                    break
                response_data += chunk
            
            sock.close()
            
            # Parse response
            response = Message.from_json(response_data.decode('utf-8'))
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to send command: {e}")
            return None
    
    def _cmd_create(self, args: List[str]) -> tuple[bool, str, Any]:
        """Create a new file"""
        if len(args) < 1:
            return False, "Usage: create <filename>", None
        
        filepath = self._resolve_path(args[0])
        msg = MessageFactory.create_command("create", filepath, "", self.node_name)
        response = self._send_command(msg)
        
        if response and response.content.get('success'):
            return True, f"Created: {args[0]}", None
        else:
            error = response.content.get('message', 'Unknown error') if response else 'No response'
            return False, f"Failed to create file: {error}", None
    
    def _cmd_write(self, args: List[str]) -> tuple[bool, str, Any]:
        """Write content to a file"""
        if len(args) < 2:
            return False, "Usage: write <filename> <content>", None
        
        filepath = self._resolve_path(args[0])
        content = ' '.join(args[1:])
        
        # Remove quotes if present
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        
        msg = MessageFactory.create_command("write", filepath, content, self.node_name)
        response = self._send_command(msg)
        
        if response and response.content.get('success'):
            return True, f"Written to: {args[0]}", None
        else:
            error = response.content.get('message', 'Unknown error') if response else 'No response'
            return False, f"Failed to write file: {error}", None
    
    def _cmd_read(self, args: List[str]) -> tuple[bool, str, Any]:
        """Read file content"""
        if len(args) < 1:
            return False, "Usage: read <filename>", None
        
        filepath = self._resolve_path(args[0])
        msg = MessageFactory.create_command("read", filepath, "", self.node_name)
        response = self._send_command(msg)
        
        if response and response.content.get('success'):
            content = response.content.get('data', '')
            return True, content, None
        else:
            error = response.content.get('message', 'Unknown error') if response else 'No response'
            return False, f"Failed to read file: {error}", None
    
    def _cmd_delete(self, args: List[str]) -> tuple[bool, str, Any]:
        """Delete a file"""
        if len(args) < 1:
            return False, "Usage: delete <filename>", None
        
        filepath = self._resolve_path(args[0])
        msg = MessageFactory.create_command("delete", filepath, "", self.node_name)
        response = self._send_command(msg)
        
        if response and response.content.get('success'):
            return True, f"Deleted: {args[0]}", None
        else:
            error = response.content.get('message', 'Unknown error') if response else 'No response'
            return False, f"Failed to delete file: {error}", None
    
    def _cmd_mkdir(self, args: List[str]) -> tuple[bool, str, Any]:
        """Create a directory"""
        if len(args) < 1:
            return False, "Usage: mkdir <dirname>", None
        
        dirpath = self._resolve_path(args[0])
        msg = MessageFactory.create_command("mkdir", dirpath, "", self.node_name)
        response = self._send_command(msg)
        
        if response and response.content.get('success'):
            return True, f"Created directory: {args[0]}", None
        else:
            error = response.content.get('message', 'Unknown error') if response else 'No response'
            return False, f"Failed to create directory: {error}", None
    
    def _cmd_ls(self, args: List[str]) -> tuple[bool, str, Any]:
        """List directory contents"""
        dirpath = self._resolve_path(args[0]) if args else self.current_dir
        
        msg = MessageFactory.create_command("list", dirpath, "", self.node_name)
        response = self._send_command(msg)
        
        if response and response.content.get('success'):
            items = response.content.get('data', [])
            
            if not items:
                return True, "Directory is empty", None
            
            # Format output
            lines = []
            for item in items:
                item_type = item['type']
                name = item['name']
                size = item['size']
                
                if item_type == 'dir':
                    lines.append(f"[DIR]  {name}")
                else:
                    lines.append(f"[FILE] {name:<30} {self._format_size(size)}")
            
            return True, "\n".join(lines), None
        else:
            error = response.content.get('message', 'Unknown error') if response else 'No response'
            return False, f"Failed to list directory: {error}", None
    
    def _cmd_nodestats(self, args: List[str]) -> tuple[bool, str, Any]:
        """Show node statistics"""
        # This would query all nodes for their stats
        # For now, just query the local node
        msg = MessageFactory.create_heartbeat(self.node_name)
        response = self._send_command(msg)
        
        if response and response.content.get('success'):
            stats = response.content.get('data', {})
            
            lines = []
            lines.append("-" * 60)
            lines.append(f"Node: {stats.get('node_name', 'Unknown')}")
            lines.append("-" * 60)
            lines.append(f"Files:     {stats.get('total_files', 0)}")
            lines.append(f"Size:      {self._format_size(stats.get('total_size', 0))}")
            lines.append(f"Syncs:     {stats.get('recent_syncs', 0)} (last hour)")
            lines.append("-" * 60)
            
            return True, "\n".join(lines), None
        else:
            return False, "Failed to get node statistics", None
    
    def _cmd_pstree(self, args: List[str]) -> tuple[bool, str, Any]:
        """Show process tree"""
        # This would aggregate from all nodes
        # For now, show message
        return True, "Use 'history' to see file operations or 'loadbal' for system stats", None
    
    def _cmd_history(self, args: List[str]) -> tuple[bool, str, Any]:
        """Show history of file operations"""
        limit = int(args[0]) if args and args[0].isdigit() else 50
        
        msg = MessageFactory.create_command("history", "", {'limit': limit}, self.node_name)
        response = self._send_command(msg)
        
        if response and response.content.get('success'):
            history = response.content.get('data', [])
            
            if not history:
                return True, "No operations in history yet", None
            
            # Format output
            from datetime import datetime
            lines = []
            lines.append("=" * 100)
            lines.append(f"{'TIMESTAMP':<20} {'NODE':<20} {'OPERATION':<12} {'FILE':<35} {'SIZE':<10}")
            lines.append("=" * 100)
            
            for item in history:
                timestamp = datetime.fromtimestamp(item['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                node = (item['node_id'] or 'Unknown')[:19]
                operation = (item['operation_type'] or 'unknown')[:11]
                filepath = item['filepath'][:34]
                size = self._format_size(item['size'])
                
                lines.append(f"{timestamp:<20} {node:<20} {operation:<12} {filepath:<35} {size:<10}")
            
            lines.append("=" * 100)
            lines.append(f"Showing {len(history)} most recent operations")
            lines.append("=" * 100)
            
            return True, "\n".join(lines), None
        else:
            return False, "Failed to get operation history", None
    
    def _cmd_loadbal(self, args: List[str]) -> tuple[bool, str, Any]:
        """Show load balancing stats across all nodes"""
        
        
        msg = MessageFactory.create_command("loadbal", "", {}, self.node_name)
        response = self._send_command(msg)
        
        if response and response.content.get('success'):
            local_stats = response.content.get('data', {})
            
            lines = []
            lines.append("=" * 70)
            lines.append(f"{'NODE NAME':<25} {'CPU%':<10} {'MEMORY%':<12} {'DISK%':<10} {'PEERS':<8}")
            lines.append("=" * 70)
            
            node_name = local_stats.get('node_name', 'Unknown')[:24]
            cpu = local_stats.get('cpu_percent', 0.0)
            mem = local_stats.get('memory_percent', 0.0)
            disk = local_stats.get('disk_percent', 0.0)
            peers = local_stats.get('active_peers', 0)
            
            lines.append(f"{node_name:<25} {cpu:<10.1f} {mem:<12.1f} {disk:<10.1f} {peers:<8}")
            
            # Add note about peer stats
            if peers > 0:
                lines.append("=" * 70)
                lines.append(f"Note: Connected to {peers} peer(s)")
                lines.append("(Future update will show stats from all peers)")
            
            lines.append("=" * 70)
            lines.append(f"Load Status: {'🟢 Normal' if cpu < 70 and mem < 80 else '🟡 High' if cpu < 90 and mem < 90 else '🔴 Critical'}")
            lines.append("=" * 70)
            
            return True, "\n".join(lines), None
        else:
            return False, "Failed to get load balancing stats", None
    
    def _cmd_help(self, args: List[str]) -> tuple[bool, str, Any]:
        """Show help information"""
        help_text = """
MiniDOS Commands:

File Operations:
  create <filename>           - Create a new empty file
  write <filename> <content>  - Write content to a file
  read <filename>             - Read and display file content
  delete <filename>           - Delete a file
  mkdir <dirname>             - Create a directory
  ls [path]                   - List files and directories

Navigation:
  cd <directory>              - Change current directory
  cd ..                       - Go to parent directory
  cd /                        - Go to root directory
  pwd                         - Print current working directory

System Monitoring:
  nodestats                   - Show node statistics
  history [limit]             - Show file operation history (default: 50)
  loadbal                     - Show load balancing stats (CPU, Memory, Disk)
  

General:
  help                        - Show this help message
  exit                        - Exit the shell

Examples:
  mkdir projects
  cd projects                 - Enter directory
  create test.txt             - Create file in current dir
  write test.txt "Hello World"
  read test.txt
  cd ..                       - Go back to parent
  ls                          - List current directory
  history 20                  - Show last 20 operations
  loadbal                     - Check system load
"""
        return True, help_text, None
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

