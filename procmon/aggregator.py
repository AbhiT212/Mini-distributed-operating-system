"""
Process Aggregator
Collects process data from all nodes in the cluster
"""

import logging
from typing import List, Dict, Callable, Optional


class ProcessAggregator:
    """Aggregates process information from multiple nodes"""
    
    def __init__(self):
        self.logger = logging.getLogger("ProcessAggregator")
        self.node_data: Dict[str, Dict] = {}  # node_name -> {processes, stats}
    
    def update_node_data(self, node_name: str, processes: List[Dict], stats: Dict):
        """Update data for a specific node"""
        self.node_data[node_name] = {
            'processes': processes,
            'stats': stats
        }
    
    def get_all_processes(self) -> List[Dict]:
        """Get all processes from all nodes"""
        all_processes = []
        
        for node_name, data in self.node_data.items():
            all_processes.extend(data.get('processes', []))
        
        return all_processes
    
    def get_node_processes(self, node_name: str) -> List[Dict]:
        """Get processes for a specific node"""
        if node_name in self.node_data:
            return self.node_data[node_name].get('processes', [])
        return []
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all nodes"""
        return {
            node: data.get('stats', {})
            for node, data in self.node_data.items()
        }
    
    def get_node_stats(self, node_name: str) -> Optional[Dict]:
        """Get statistics for a specific node"""
        if node_name in self.node_data:
            return self.node_data[node_name].get('stats')
        return None
    
    def get_cluster_summary(self) -> Dict:
        """Get summary statistics for the entire cluster"""
        if not self.node_data:
            return {
                'total_nodes': 0,
                'total_processes': 0,
                'avg_cpu': 0.0,
                'avg_memory': 0.0
            }
        
        total_processes = 0
        total_cpu = 0.0
        total_memory = 0.0
        
        for node_name, data in self.node_data.items():
            stats = data.get('stats', {})
            processes = data.get('processes', [])
            
            total_processes += len(processes)
            total_cpu += stats.get('cpu_percent', 0.0)
            total_memory += stats.get('memory_percent', 0.0)
        
        num_nodes = len(self.node_data)
        
        return {
            'total_nodes': num_nodes,
            'total_processes': total_processes,
            'avg_cpu': round(total_cpu / num_nodes, 2) if num_nodes > 0 else 0.0,
            'avg_memory': round(total_memory / num_nodes, 2) if num_nodes > 0 else 0.0
        }
    
    def search_processes(self, name_pattern: str) -> List[Dict]:
        """Search for processes across all nodes"""
        results = []
        
        for node_name, data in self.node_data.items():
            processes = data.get('processes', [])
            for proc in processes:
                if name_pattern.lower() in proc['name'].lower():
                    results.append(proc)
        
        return results
    
    def get_top_processes_global(self, by: str = 'cpu', limit: int = 10) -> List[Dict]:
        """Get top processes across all nodes"""
        all_processes = self.get_all_processes()
        
        if by == 'cpu':
            sorted_procs = sorted(all_processes, key=lambda x: x.get('cpu_percent', 0), reverse=True)
        elif by == 'memory':
            sorted_procs = sorted(all_processes, key=lambda x: x.get('memory_percent', 0), reverse=True)
        else:
            sorted_procs = all_processes
        
        return sorted_procs[:limit]

