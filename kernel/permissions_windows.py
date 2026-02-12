"""
Windows Permissions Manager
Ensures proper UAC elevation and access control
"""

import ctypes
import sys
import os
import subprocess
from pathlib import Path


def is_admin() -> bool:
    """Check if current process has administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def request_admin_elevation():
    """Request UAC elevation if not already admin"""
    if not is_admin():
        print("Administrator privileges required. Requesting elevation...")
        try:
            # Re-run the script with admin privileges
            ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                sys.executable, 
                " ".join(sys.argv), 
                None, 
                1  # SW_NORMAL
            )
            sys.exit(0)
        except Exception as e:
            print(f"Failed to elevate privileges: {e}")
            print("Please run this script as Administrator.")
            sys.exit(1)


def ensure_admin():
    """Ensure the process is running with admin privileges"""
    if not is_admin():
        print("ERROR: This application requires Administrator privileges.")
        print("Please right-click and select 'Run as Administrator'")
        sys.exit(1)


def check_filesystem_permissions(path: str) -> bool:
    """Check if we have read/write permissions on a path"""
    try:
        path_obj = Path(path)
        
        # Try to create directory if it doesn't exist
        if not path_obj.exists():
            path_obj.mkdir(parents=True, exist_ok=True)
        
        # Test write permission
        test_file = path_obj / ".permission_test"
        test_file.write_text("test")
        test_file.unlink()
        
        return True
    except PermissionError:
        return False
    except Exception as e:
        print(f"Permission check failed: {e}")
        return False


def setup_filesystem_permissions(path: str) -> bool:
    """
    Grant full permissions to the specified path
    Requires admin privileges
    """
    if not is_admin():
        print("Admin privileges required to set filesystem permissions")
        return False
    
    try:
        # Ensure directory exists
        Path(path).mkdir(parents=True, exist_ok=True)
        
        # Grant full control using icacls
        cmd = f'icacls "{path}" /grant Everyone:(OI)(CI)F /T'
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            print(f"Successfully set permissions on {path}")
            return True
        else:
            print(f"Failed to set permissions: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error setting filesystem permissions: {e}")
        return False


def check_firewall_rules() -> dict:
    """Check if required firewall rules exist"""
    rules = {
        'tcp_9000': False,
        'udp_9050': False
    }
    
    if not is_admin():
        return rules
    
    try:
        # Check for MiniDOS firewall rules
        result = subprocess.run(
            'netsh advfirewall firewall show rule name="MiniDOS TCP"',
            shell=True,
            capture_output=True,
            text=True
        )
        rules['tcp_9000'] = 'MiniDOS TCP' in result.stdout
        
        result = subprocess.run(
            'netsh advfirewall firewall show rule name="MiniDOS UDP"',
            shell=True,
            capture_output=True,
            text=True
        )
        rules['udp_9050'] = 'MiniDOS UDP' in result.stdout
        
    except Exception as e:
        print(f"Error checking firewall rules: {e}")
    
    return rules


def create_firewall_rules() -> bool:
    """Create necessary firewall rules"""
    if not is_admin():
        print("Admin privileges required to create firewall rules")
        return False
    
    try:
        # TCP rule for main communication
        tcp_cmd = (
            'netsh advfirewall firewall add rule '
            'name="MiniDOS TCP" '
            'dir=in action=allow protocol=TCP localport=9000-9010'
        )
        
        result = subprocess.run(tcp_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Failed to create TCP firewall rule: {result.stderr}")
            return False
        
        # UDP rule for discovery
        udp_cmd = (
            'netsh advfirewall firewall add rule '
            'name="MiniDOS UDP" '
            'dir=in action=allow protocol=UDP localport=9050'
        )
        
        result = subprocess.run(udp_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Failed to create UDP firewall rule: {result.stderr}")
            return False
        
        print("Firewall rules created successfully")
        return True
        
    except Exception as e:
        print(f"Error creating firewall rules: {e}")
        return False


def verify_environment() -> dict:
    """
    Verify that the environment is properly set up
    Returns dictionary with status of each check
    """
    status = {
        'is_admin': is_admin(),
        'filesystem_access': False,
        'firewall_tcp': False,
        'firewall_udp': False,
        'python_version': sys.version_info >= (3, 10),
    }
    
    # Check filesystem access
    try:
        fs_path = os.path.join("C:\\", "MiniDOS_FS")
        status['filesystem_access'] = check_filesystem_permissions(fs_path)
    except Exception:
        pass
    
    # Check firewall rules
    if is_admin():
        fw_rules = check_firewall_rules()
        status['firewall_tcp'] = fw_rules['tcp_9000']
        status['firewall_udp'] = fw_rules['udp_9050']
    
    return status


def print_environment_status():
    """Print the current environment status"""
    status = verify_environment()
    
    print("\n" + "="*50)
    print("MiniDOS Environment Status")
    print("="*50)
    
    print(f"Administrator Privileges: {'✓' if status['is_admin'] else '✗'}")
    print(f"Python Version (3.10+):   {'✓' if status['python_version'] else '✗'}")
    print(f"Filesystem Access:        {'✓' if status['filesystem_access'] else '✗'}")
    print(f"Firewall (TCP 9000):      {'✓' if status['firewall_tcp'] else '✗'}")
    print(f"Firewall (UDP 9050):      {'✓' if status['firewall_udp'] else '✗'}")
    
    print("="*50)
    
    all_ok = all(status.values())
    if all_ok:
        print("✓ Environment is properly configured")
    else:
        print("✗ Environment configuration incomplete")
        print("\nRun the installation script as Administrator:")
        print("  .\\tools\\installer\\install_dependencies.ps1")
    
    print("="*50 + "\n")
    
    return all_ok


if __name__ == "__main__":
    print_environment_status()

