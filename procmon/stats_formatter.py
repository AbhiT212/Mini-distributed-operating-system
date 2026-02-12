"""
Statistics Formatter
Pretty formatting for process and node statistics
"""

from typing import List, Dict


def format_nodestats(node_stats: Dict[str, Dict], cluster_summary: Dict) -> str:
    """Format node statistics into a pretty table"""
    
    lines = []
    lines.append("-" * 70)
    lines.append(f"{'NODE NAME':<20} {'CPU%':<10} {'MEM%':<10} {'DISK%':<10} {'PROCESSES':<10}")
    lines.append("-" * 70)
    
    for node_name, stats in sorted(node_stats.items()):
        cpu = stats.get('cpu_percent', 0.0)
        mem = stats.get('memory_percent', 0.0)
        disk = stats.get('disk_percent', 0.0)
        
        # Count processes (this would come from aggregator)
        lines.append(f"{node_name:<20} {cpu:<10.1f} {mem:<10.1f} {disk:<10.1f} {'N/A':<10}")
    
    lines.append("-" * 70)
    
    # Cluster summary
    lines.append(f"CLUSTER SUMMARY: {cluster_summary['total_nodes']} nodes, "
                f"{cluster_summary['total_processes']} processes")
    lines.append(f"Average CPU: {cluster_summary['avg_cpu']:.1f}% | "
                f"Average Memory: {cluster_summary['avg_memory']:.1f}%")
    lines.append("-" * 70)
    
    return "\n".join(lines)


def format_pstree(processes: List[Dict], limit: int = 50) -> str:
    """Format process tree"""
    
    lines = []
    lines.append("-" * 90)
    lines.append(f"{'NODE':<15} {'PID':<8} {'NAME':<25} {'CPU%':<8} {'MEM%':<8} {'STATUS':<10}")
    lines.append("-" * 90)
    
    # Sort by node, then by CPU
    sorted_procs = sorted(processes, key=lambda x: (x.get('node', ''), -x.get('cpu_percent', 0)))
    
    for proc in sorted_procs[:limit]:
        node = proc.get('node', 'unknown')[:14]
        pid = proc.get('pid', 0)
        name = proc.get('name', 'unknown')[:24]
        cpu = proc.get('cpu_percent', 0.0)
        mem = proc.get('memory_percent', 0.0)
        status = proc.get('status', 'unknown')[:9]
        
        lines.append(f"{node:<15} {pid:<8} {name:<25} {cpu:<8.1f} {mem:<8.1f} {status:<10}")
    
    lines.append("-" * 90)
    lines.append(f"Showing {min(limit, len(processes))} of {len(processes)} processes")
    lines.append("-" * 90)
    
    return "\n".join(lines)


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def format_system_info(stats: Dict) -> str:
    """Format system information"""
    lines = []
    
    lines.append(f"CPU Usage:    {stats.get('cpu_percent', 0):.1f}%")
    lines.append(f"Memory Usage: {stats.get('memory_percent', 0):.1f}% "
                f"({format_bytes(stats.get('memory_used', 0))} / "
                f"{format_bytes(stats.get('memory_total', 0))})")
    lines.append(f"Disk Usage:   {stats.get('disk_percent', 0):.1f}% "
                f"({format_bytes(stats.get('disk_used', 0))} / "
                f"{format_bytes(stats.get('disk_total', 0))})")
    
    return "\n".join(lines)

