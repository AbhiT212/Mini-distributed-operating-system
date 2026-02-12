"""
Process Agent
Node-level process monitoring using psutil
"""

import psutil
import logging
import threading
import time
from typing import List, Dict, Optional


class ProcessAgent:
    """Monitors processes on the local node"""
    
    def __init__(self, node_name: str, update_interval: int = 2):
        self.node_name = node_name
        self.update_interval = update_interval
        self.logger = logging.getLogger("ProcessAgent")
        
        self.running = False
        self.update_thread: Optional[threading.Thread] = None
        
        self.processes: List[Dict] = []
        self.system_stats: Dict = {}
        self.lock = threading.RLock()
    
    def start(self):
        """Start monitoring processes"""
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        self.logger.info(f"ProcessAgent started for {self.node_name}")
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=2)
        self.logger.info("ProcessAgent stopped")
    
    def _update_loop(self):
        """Periodically update process information"""
        while self.running:
            try:
                self._update_processes()
                self._update_system_stats()
            except Exception as e:
                self.logger.error(f"Error updating processes: {e}")
            
            time.sleep(self.update_interval)
    
    def _update_processes(self):
        """Update process list"""
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    pinfo = proc.info
                    processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'],
                        'username': pinfo['username'],
                        'cpu_percent': round(pinfo['cpu_percent'] or 0, 2),
                        'memory_percent': round(pinfo['memory_percent'] or 0, 2),
                        'status': pinfo['status'],
                        'node': self.node_name
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            with self.lock:
                self.processes = processes
                
        except Exception as e:
            self.logger.error(f"Failed to update processes: {e}")
    
    def _update_system_stats(self):
        """Update system statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            stats = {
                'cpu_percent': round(cpu_percent, 2),
                'memory_percent': round(memory.percent, 2),
                'memory_used': memory.used,
                'memory_total': memory.total,
                'disk_percent': round(disk.percent, 2),
                'disk_used': disk.used,
                'disk_total': disk.total,
                'node': self.node_name
            }
            
            with self.lock:
                self.system_stats = stats
                
        except Exception as e:
            self.logger.error(f"Failed to update system stats: {e}")
    
    def get_processes(self, limit: int = None) -> List[Dict]:
        """Get current process list"""
        with self.lock:
            if limit:
                return self.processes[:limit]
            return self.processes.copy()
    
    def get_system_stats(self) -> Dict:
        """Get current system statistics"""
        with self.lock:
            return self.system_stats.copy()
    
    def get_process_by_pid(self, pid: int) -> Optional[Dict]:
        """Get specific process by PID"""
        with self.lock:
            for proc in self.processes:
                if proc['pid'] == pid:
                    return proc
        return None
    
    def get_top_processes(self, by: str = 'cpu', limit: int = 10) -> List[Dict]:
        """
        Get top processes sorted by resource usage
        by: 'cpu' or 'memory'
        """
        with self.lock:
            if by == 'cpu':
                sorted_procs = sorted(self.processes, key=lambda x: x['cpu_percent'], reverse=True)
            elif by == 'memory':
                sorted_procs = sorted(self.processes, key=lambda x: x['memory_percent'], reverse=True)
            else:
                sorted_procs = self.processes
            
            return sorted_procs[:limit]
    
    def search_processes(self, name_pattern: str) -> List[Dict]:
        """Search processes by name pattern"""
        with self.lock:
            return [p for p in self.processes if name_pattern.lower() in p['name'].lower()]

