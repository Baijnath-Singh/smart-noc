"""
Network operation tools for the autonomous agent

These are the "hands" of the agent - tools it uses to interact with devices.
Currently simulated, but designed to be swapped with real SSH/NETCONF connectors.
"""
import time
import random
from typing import Dict, Any, List
from loguru import logger


class NetworkTools:
    """
    Collection of network operation tools
    
    Each tool simulates a real network operation.
    In production, these would connect to actual devices via SSH/NETCONF/REST.
    """
    
    def __init__(self, simulation_mode: bool = True):
        self.simulation_mode = simulation_mode
        logger.info(f"NetworkTools initialized (simulation_mode={simulation_mode})")
    
    # =========================================================================
    # DIAGNOSTIC TOOLS - Gather information
    # =========================================================================
    
    def show_interface_status(self, device: str, interface: str) -> Dict[str, Any]:
        """
        Get interface status and statistics
        Equivalent to: show interface GigabitEthernet0/1
        """
        logger.info(f"[TOOL] show_interface_status: {device} {interface}")
        
        if self.simulation_mode:
            time.sleep(0.2)  # Simulate network delay
            return {
                "device": device,
                "interface": interface,
                "status": "up",
                "protocol": "up",
                "errors": 1250,  # High error count
                "input_drops": 450,
                "output_drops": 20,
                "collisions": 0,
                "speed": "1000Mbps",
                "duplex": "full"
            }
        else:
            # Real implementation would SSH to device
            pass
    
    def show_logging(self, device: str, filter: str = None) -> Dict[str, Any]:
        """
        Get device logs
        Equivalent to: show logging | include Error
        """
        logger.info(f"[TOOL] show_logging: {device} filter={filter}")
        
        if self.simulation_mode:
            time.sleep(0.3)
            return {
                "device": device,
                "logs": [
                    "May 17 07:15:23: %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down",
                    "May 17 07:15:25: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/1, changed state to down",
                    "May 17 07:15:28: %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to up",
                ]
            }
    
    def show_processes_cpu(self, device: str) -> Dict[str, Any]:
        """
        Get CPU utilization
        Equivalent to: show processes cpu sorted
        """
        logger.info(f"[TOOL] show_processes_cpu: {device}")
        
        if self.simulation_mode:
            time.sleep(0.2)
            return {
                "device": device,
                "cpu_5sec": 92,
                "cpu_1min": 85,
                "cpu_5min": 78,
                "top_processes": [
                    {"name": "BGP Scanner", "cpu": 35},
                    {"name": "IP Input", "cpu": 25},
                ]
            }
    
    def show_bgp_summary(self, device: str) -> Dict[str, Any]:
        """
        Get BGP neighbor status
        Equivalent to: show ip bgp summary
        """
        logger.info(f"[TOOL] show_bgp_summary: {device}")
        
        if self.simulation_mode:
            time.sleep(0.3)
            return {
                "device": device,
                "neighbors": [
                    {
                        "ip": "10.1.1.2",
                        "as": 65001,
                        "state": "Established",
                        "prefixes": 250,
                        "uptime": "2d3h"
                    }
                ]
            }
    
    # =========================================================================
    # REMEDIATION TOOLS - Fix problems
    # =========================================================================
    
    def clear_interface_counters(self, device: str, interface: str) -> Dict[str, Any]:
        """
        Clear interface error counters
        Equivalent to: clear counters GigabitEthernet0/1
        """
        logger.info(f"[TOOL] clear_interface_counters: {device} {interface}")
        
        if self.simulation_mode:
            time.sleep(0.5)
            return {
                "device": device,
                "interface": interface,
                "success": True,
                "message": "Counters cleared"
            }
    
    def reload_interface(self, device: str, interface: str) -> Dict[str, Any]:
        """
        Reload interface (shut/no shut)
        Equivalent to: shutdown / no shutdown
        """
        logger.info(f"[TOOL] reload_interface: {device} {interface}")
        
        if self.simulation_mode:
            time.sleep(1.0)  # Takes longer
            return {
                "device": device,
                "interface": interface,
                "success": True,
                "message": "Interface reloaded"
            }
    
    def restart_service(self, device: str, service: str) -> Dict[str, Any]:
        """
        Restart a service/process
        Equivalent to: restart process <name>
        """
        logger.info(f"[TOOL] restart_service: {device} {service}")
        
        if self.simulation_mode:
            time.sleep(2.0)
            # Simulate occasional failures
            success = random.random() > 0.1  # 90% success rate
            return {
                "device": device,
                "service": service,
                "success": success,
                "message": "Service restarted" if success else "Service restart failed"
            }
    
    def apply_configuration(self, device: str, config_lines: List[str]) -> Dict[str, Any]:
        """
        Apply configuration changes
        Equivalent to: configure terminal + config lines
        """
        logger.info(f"[TOOL] apply_configuration: {device} ({len(config_lines)} lines)")
        
        if self.simulation_mode:
            time.sleep(1.5)
            return {
                "device": device,
                "lines_applied": len(config_lines),
                "success": True,
                "message": "Configuration applied"
            }
    
    def clear_arp_cache(self, device: str) -> Dict[str, Any]:
        """
        Clear ARP cache
        Equivalent to: clear arp-cache
        """
        logger.info(f"[TOOL] clear_arp_cache: {device}")
        
        if self.simulation_mode:
            time.sleep(0.5)
            return {
                "device": device,
                "success": True,
                "message": "ARP cache cleared"
            }
    
    # =========================================================================
    # VERIFICATION TOOLS - Check if fix worked
    # =========================================================================
    
    def verify_interface_health(self, device: str, interface: str) -> Dict[str, Any]:
        """
        Check if interface is healthy after remediation
        """
        logger.info(f"[TOOL] verify_interface_health: {device} {interface}")
        
        if self.simulation_mode:
            time.sleep(0.3)
            # Simulate successful fix (90% success rate)
            is_healthy = random.random() > 0.1
            return {
                "device": device,
                "interface": interface,
                "success": is_healthy,
                "healthy": is_healthy,
                "errors": 0 if is_healthy else 5,
                "status": "up/up" if is_healthy else "up/down"
            }
    
    def ping(self, device: str, target: str) -> Dict[str, Any]:
        """
        Test connectivity
        Equivalent to: ping <target>
        """
        logger.info(f"[TOOL] ping: {device} -> {target}")
        
        if self.simulation_mode:
            time.sleep(0.5)
            return {
                "device": device,
                "target": target,
                "success": True,
                "packets_sent": 5,
                "packets_received": 5,
                "loss_percent": 0
            }


# Tool descriptions for LangChain
def get_tool_descriptions():
    """
    Descriptions that help the LLM understand what each tool does
    """
    return {
        "show_interface_status": "Get detailed interface status including errors, drops, speed, duplex. Use this to diagnose interface issues.",
        "show_logging": "View device logs. Use filter parameter to search for specific errors or events.",
        "show_processes_cpu": "Check CPU utilization and identify high-CPU processes. Use when device is slow or unresponsive.",
        "show_bgp_summary": "View BGP neighbor status and routes. Use for routing issues.",
        "clear_interface_counters": "Clear interface error counters. Use after fixing interface issues to reset baseline.",
        "reload_interface": "Reload interface (shutdown + no shutdown). Use to reset interface state.",
        "restart_service": "Restart a network service or process. Use when service is hung or misbehaving.",
        "apply_configuration": "Apply configuration changes to device. Use carefully - verify commands first.",
        "clear_arp_cache": "Clear ARP cache. Use when ARP table is full or stale.",
        "verify_interface_health": "Check if interface is healthy. Use after remediation to verify fix.",
        "ping": "Test network connectivity. Use to verify reachability after fixes."
    }
