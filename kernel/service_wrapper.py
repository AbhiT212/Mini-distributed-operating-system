"""
Service Wrapper
Runs node daemon as a Windows service (optional)
"""

import sys
import time
import logging
from pathlib import Path

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    HAS_PYWIN32 = True
except ImportError:
    HAS_PYWIN32 = False
    print("Warning: pywin32 not installed. Service mode not available.")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kernel.node_daemon import NodeDaemon


if HAS_PYWIN32:
    class MiniDOSService(win32serviceutil.ServiceFramework):
        """Windows service for MiniDOS node daemon"""
        
        _svc_name_ = "MiniDOSDaemon"
        _svc_display_name_ = "MiniDOS Node Daemon"
        _svc_description_ = "Peer-to-peer distributed operating system node service"
        
        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.daemon = None
            
            # Setup logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler('logs/service.log')
                ]
            )
            self.logger = logging.getLogger("MiniDOSService")
        
        def SvcStop(self):
            """Stop the service"""
            self.logger.info("Service stop requested")
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            
            if self.daemon:
                self.daemon.stop()
        
        def SvcDoRun(self):
            """Run the service"""
            self.logger.info("Service starting")
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            
            try:
                # Start daemon
                self.daemon = NodeDaemon()
                self.daemon.start()
                
                # Wait for stop event
                win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
                
            except Exception as e:
                self.logger.error(f"Service error: {e}")
                servicemanager.LogErrorMsg(f"MiniDOS Service error: {e}")
            
            self.logger.info("Service stopped")


def install_service():
    """Install the service"""
    if not HAS_PYWIN32:
        print("Error: pywin32 is required for service installation")
        print("Install with: pip install pywin32")
        return False
    
    try:
        win32serviceutil.HandleCommandLine(MiniDOSService, argv=['', 'install'])
        print("Service installed successfully")
        print("Start with: net start MiniDOSDaemon")
        return True
    except Exception as e:
        print(f"Failed to install service: {e}")
        return False


def uninstall_service():
    """Uninstall the service"""
    if not HAS_PYWIN32:
        print("Error: pywin32 is required")
        return False
    
    try:
        win32serviceutil.HandleCommandLine(MiniDOSService, argv=['', 'remove'])
        print("Service uninstalled successfully")
        return True
    except Exception as e:
        print(f"Failed to uninstall service: {e}")
        return False


def main():
    """Main entry point for service management"""
    if len(sys.argv) == 1:
        if HAS_PYWIN32:
            # Called by Windows Service Manager
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(MiniDOSService)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            print("Usage: python service_wrapper.py [install|remove|start|stop]")
    else:
        if HAS_PYWIN32:
            win32serviceutil.HandleCommandLine(MiniDOSService)
        else:
            print("Error: pywin32 is required for service management")
            print("Install with: pip install pywin32")


if __name__ == "__main__":
    main()

