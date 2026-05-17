"""
Test Scenario Generator - Generate specific anomaly patterns for testing

Simulates various anomaly scenarios:
- Interface flapping
- Authentication brute force
- High CPU sustained
- BGP instability
"""

import time
import random
import json
import argparse
from datetime import datetime
from kafka import KafkaProducer
from loguru import logger
import sys

# Configure logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


class ScenarioGenerator:
    """Generate specific anomaly test scenarios"""
    
    def __init__(self, kafka_broker='localhost:9092', topic='network-logs'):
        self.topic = topic
        logger.info(f"Connecting to Kafka broker: {kafka_broker}")
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_broker,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            max_request_size=1048576,
            compression_type='gzip'
        )
        logger.success("Connected to Kafka")
    
    def _send_log(self, log: dict):
        """Send log to Kafka"""
        self.producer.send(self.topic, value=log)
        logger.debug(f"Sent: {log['event_type']} - {log['device_id']}")
    
    def _timestamp(self):
        """Generate syslog timestamp"""
        return datetime.utcnow().strftime('%b %d %H:%M:%S')
    
    def scenario_interface_flapping(self, count=10, interval=2):
        """
        Generate interface flapping scenario
        
        Args:
            count: Number of flaps
            interval: Seconds between flaps
        """
        logger.info(f"🔥 SCENARIO: Interface Flapping ({count} flaps, {interval}s interval)")
        
        device = "core-router-01"
        interface = "GigabitEthernet0/1"
        
        for i in range(count):
            state = "up" if i % 2 == 0 else "down"
            severity = "INFO" if state == "up" else "ERROR"
            
            log = {
                "timestamp": self._timestamp(),
                "device_id": device,
                "device_type": "router",
                "severity": severity,
                "event_type": f"INTERFACE_{state.upper()}",
                "interface": interface,
                "message": f"%LINK-3-UPDOWN: Interface {interface}, changed state to {state}"
            }
            
            self._send_log(log)
            time.sleep(interval)
        
        self.producer.flush()
        logger.success(f"✅ Scenario complete: {count} interface flaps sent")
    
    def scenario_auth_brute_force(self, count=15, interval=1):
        """
        Generate authentication brute force scenario
        
        Args:
            count: Number of failed attempts
            interval: Seconds between attempts
        """
        logger.info(f"🔥 SCENARIO: Auth Brute Force ({count} attempts, {interval}s interval)")
        
        device = "dist-switch-02"
        attacker_ip = "192.168.100.50"
        usernames = ["admin", "root", "cisco", "operator", "user"]
        
        for i in range(count):
            username = random.choice(usernames)
            
            log = {
                "timestamp": self._timestamp(),
                "device_id": device,
                "device_type": "switch",
                "severity": "WARNING",
                "event_type": "AUTH_FAILURE",
                "username": username,
                "source_ip": attacker_ip,
                "message": f"%SEC_LOGIN-4-LOGIN_FAILED: Login failed for user {username} from {attacker_ip}"
            }
            
            self._send_log(log)
            time.sleep(interval)
        
        self.producer.flush()
        logger.success(f"✅ Scenario complete: {count} brute force attempts sent")
    
    def scenario_high_cpu(self, duration=300, interval=10):
        """
        Generate sustained high CPU scenario
        
        Args:
            duration: Total duration in seconds
            interval: Seconds between reports
        """
        logger.info(f"🔥 SCENARIO: High CPU Sustained ({duration}s duration, {interval}s interval)")
        
        device = "core-router-03"
        iterations = duration // interval
        
        for i in range(iterations):
            cpu = random.randint(85, 98)  # High CPU range
            
            log = {
                "timestamp": self._timestamp(),
                "device_id": device,
                "device_type": "router",
                "severity": "WARNING",
                "event_type": "HIGH_CPU",
                "cpu_utilization": cpu,
                "message": f"%SYS-4-CPU_HIGH: CPU utilization is {cpu}%"
            }
            
            self._send_log(log)
            logger.info(f"CPU report {i+1}/{iterations}: {cpu}%")
            time.sleep(interval)
        
        self.producer.flush()
        logger.success(f"✅ Scenario complete: {iterations} high CPU reports sent")
    
    def scenario_bgp_instability(self, count=5, interval=20):
        """
        Generate BGP session instability scenario
        
        Args:
            count: Number of state changes
            interval: Seconds between changes
        """
        logger.info(f"🔥 SCENARIO: BGP Instability ({count} changes, {interval}s interval)")
        
        device = "core-router-02"
        neighbor = "10.0.1.2"
        states = ["Established", "Idle", "Connect", "Active"]
        
        for i in range(count):
            state = random.choice(states)
            severity = "CRITICAL" if state != "Established" else "INFO"
            
            log = {
                "timestamp": self._timestamp(),
                "device_id": device,
                "device_type": "router",
                "severity": severity,
                "event_type": "BGP_STATE_CHANGE",
                "bgp_neighbor": neighbor,
                "bgp_state": state,
                "message": f"%BGP-5-ADJCHANGE: neighbor {neighbor} changed state to {state}"
            }
            
            self._send_log(log)
            time.sleep(interval)
        
        self.producer.flush()
        logger.success(f"✅ Scenario complete: {count} BGP state changes sent")
    
    def scenario_mixed_chaos(self, duration=120):
        """
        Generate mixed anomaly chaos for ML testing
        
        Args:
            duration: Duration in seconds
        """
        logger.info(f"🔥 SCENARIO: Mixed Chaos ({duration}s of random anomalies)")
        
        # Target ONE device for DEVICE_FAILURE pattern
        target_device = "core-router-01"
        logger.info(f"Targeting device: {target_device} for DEVICE_FAILURE correlation")
        
        start_time = time.time()
        event_count = 0
        
        while (time.time() - start_time) < duration and event_count < 15:
            # Generate different event types on SAME device
            event_types = [
                'interface_up', 'interface_down', 'bgp_down', 
                'high_cpu', 'high_memory', 'packet_loss'
            ]
            
            event_type = random.choice(event_types)
            severity = random.choice(['WARNING', 'ERROR', 'CRITICAL'])
            
            if event_type in ['interface_up', 'interface_down']:
                log = {
                    "timestamp": self._timestamp(),
                    "device_id": target_device,
                    "device_type": "router",
                    "severity": 'ERROR' if event_type == 'interface_down' else 'INFO',
                    "event_type": event_type.upper(),
                    "interface": f"GigabitEthernet0/{random.randint(1,4)}",
                    "message": f"%LINK-3-UPDOWN: Interface changed state to {event_type.split('_')[1]}"
                }
            elif event_type == 'bgp_down':
                log = {
                    "timestamp": self._timestamp(),
                    "device_id": target_device,
                    "device_type": "router",
                    "severity": "CRITICAL",
                    "event_type": "BGP_STATE_CHANGE",
                    "bgp_neighbor": "10.0.1.2",
                    "bgp_state": "Idle",
                    "message": f"%BGP-5-ADJCHANGE: neighbor 10.0.1.2 changed state to Idle"
                }
            elif event_type == 'high_cpu':
                log = {
                    "timestamp": self._timestamp(),
                    "device_id": target_device,
                    "device_type": "router",
                    "severity": "WARNING",
                    "event_type": "HIGH_CPU",
                    "cpu_utilization": random.randint(85, 98),
                    "message": f"%SYS-4-CPU_HIGH: CPU utilization is high"
                }
            elif event_type == 'high_memory':
                log = {
                    "timestamp": self._timestamp(),
                    "device_id": target_device,
                    "device_type": "router",
                    "severity": "WARNING",
                    "event_type": "HIGH_MEMORY",
                    "memory_utilization": random.randint(80, 95),
                    "message": f"%SYS-4-MEM_HIGH: Memory utilization is high"
                }
            else:  # packet_loss
                log = {
                    "timestamp": self._timestamp(),
                    "device_id": target_device,
                    "device_type": "router",
                    "severity": "ERROR",
                    "event_type": "PACKET_LOSS",
                    "packet_loss_percent": random.randint(10, 40),
                    "message": f"%SYS-4-PKT_LOSS: High packet loss detected"
                }
            
            self._send_log(log)
            logger.info(f"Event {event_count+1}: {event_type} on {target_device}")
            event_count += 1
            time.sleep(random.randint(2, 5))
        
        self.producer.flush()
        logger.success(f"✅ Mixed chaos scenario complete: {event_count} events on {target_device}")
    
    def scenario_device_failure(self, count=12, interval=2):
        """
        Generate device failure pattern - multiple anomaly types on SAME device
        
        This creates the pattern that correlation engine detects as DEVICE_FAILURE:
        - Same device (core-router-01)
        - Multiple different anomaly types (interface flapping, CPU, memory, packet loss)
        - Creates at least 3+ anomalies with 2+ different types
        
        Args:
            count: Number of events to generate (default 12)
            interval: Seconds between events (default 2 - faster for quicker anomaly detection)
        """
        logger.info(f"🔥 SCENARIO: Device Failure ({count} events, {interval}s interval)")
        
        target_device = "core-router-01"
        logger.info(f"Target: {target_device} - Simulating hardware/system-level failure")
        
        # Use SAME interface for flapping detection (requires 2+ events on same interface)
        flapping_interface = "GigabitEthernet0/1"
        
        # Event pattern for device failure: multiple symptoms on same device
        event_pattern = [
            # Rapid interface flapping on SAME interface (triggers INTERFACE_FLAPPING anomaly)
            {"type": "INTERFACE_DOWN", "interface": flapping_interface, "severity": "ERROR"},
            {"type": "INTERFACE_UP", "interface": flapping_interface, "severity": "INFO"},
            {"type": "INTERFACE_DOWN", "interface": flapping_interface, "severity": "ERROR"},
            {"type": "INTERFACE_UP", "interface": flapping_interface, "severity": "INFO"},
            {"type": "INTERFACE_DOWN", "interface": flapping_interface, "severity": "CRITICAL"},
            
            # High CPU (triggers ML anomaly or HIGH_CPU rule)
            {"type": "HIGH_CPU", "cpu": 92, "severity": "WARNING"},
            {"type": "HIGH_CPU", "cpu": 95, "severity": "WARNING"},
            {"type": "HIGH_CPU", "cpu": 98, "severity": "CRITICAL"},
            
            # High memory (triggers ML anomaly)
            {"type": "HIGH_MEMORY", "memory": 91, "severity": "CRITICAL"},
            
            # Packet loss (triggers ML anomaly)
            {"type": "PACKET_LOSS", "loss": 35, "severity": "CRITICAL"},
            
            # BGP flapping (triggers BGP_INSTABILITY anomaly - needs 2+ state changes)
            {"type": "BGP_STATE_CHANGE", "state": "Idle", "severity": "CRITICAL"},
            {"type": "BGP_STATE_CHANGE", "state": "Active", "severity": "CRITICAL"},
        ]
        
        # Send events up to count limit
        events_to_send = event_pattern[:count]
        
        for idx, event_spec in enumerate(events_to_send):
            if event_spec["type"] in ["INTERFACE_DOWN", "INTERFACE_UP"]:
                log = {
                    "timestamp": self._timestamp(),
                    "device_id": target_device,
                    "device_type": "router",
                    "severity": event_spec["severity"],
                    "event_type": event_spec["type"],
                    "interface": event_spec["interface"],
                    "message": f"%LINK-3-UPDOWN: Interface {event_spec['interface']}, changed state to {event_spec['type'].split('_')[1].lower()}"
                }
            
            elif event_spec["type"] == "HIGH_CPU":
                log = {
                    "timestamp": self._timestamp(),
                    "device_id": target_device,
                    "device_type": "router",
                    "severity": event_spec["severity"],
                    "event_type": "HIGH_CPU",
                    "cpu_utilization": event_spec["cpu"],
                    "message": f"%SYS-4-CPU_HIGH: CPU utilization is {event_spec['cpu']}%"
                }
            
            elif event_spec["type"] == "HIGH_MEMORY":
                log = {
                    "timestamp": self._timestamp(),
                    "device_id": target_device,
                    "device_type": "router",
                    "severity": event_spec["severity"],
                    "event_type": "HIGH_MEMORY",
                    "memory_utilization": event_spec["memory"],
                    "message": f"%SYS-4-MEM_HIGH: Memory utilization is {event_spec['memory']}%"
                }
            
            elif event_spec["type"] == "PACKET_LOSS":
                log = {
                    "timestamp": self._timestamp(),
                    "device_id": target_device,
                    "device_type": "router",
                    "severity": event_spec["severity"],
                    "event_type": "PACKET_LOSS",
                    "packet_loss_percent": event_spec["loss"],
                    "message": f"%SYS-4-PKT_LOSS: High packet loss detected: {event_spec['loss']}%"
                }
            
            elif event_spec["type"] == "BGP_STATE_CHANGE":
                log = {
                    "timestamp": self._timestamp(),
                    "device_id": target_device,
                    "device_type": "router",
                    "severity": event_spec["severity"],
                    "event_type": "BGP_STATE_CHANGE",
                    "bgp_neighbor": "10.0.1.2",
                    "bgp_state": event_spec["state"],
                    "message": f"%BGP-5-ADJCHANGE: neighbor 10.0.1.2 changed state to {event_spec['state']}"
                }
            
            self._send_log(log)
            logger.info(f"[{idx+1}/{len(events_to_send)}] {event_spec['type']} - {event_spec['severity']}")
            time.sleep(interval)
        
        self.producer.flush()
        logger.success(f"✅ Device failure scenario complete: {len(events_to_send)} events on {target_device}")
        logger.info(f"Expected outcome: Multiple anomalies → DEVICE_FAILURE incident with vector KB search")


def main():
    parser = argparse.ArgumentParser(description="Generate anomaly test scenarios")
    parser.add_argument('--scenario', '-s', 
                       choices=['flapping', 'brute-force', 'high-cpu', 'bgp-unstable', 'chaos', 'device-failure'],
                       default='flapping',
                       help='Anomaly scenario to generate')
    parser.add_argument('--broker', '-b', default='localhost:9092', help='Kafka broker address')
    parser.add_argument('--count', '-c', type=int, default=10, help='Event count for scenario')
    parser.add_argument('--duration', '-d', type=int, default=120, help='Duration in seconds (for time-based scenarios)')
    
    args = parser.parse_args()
    
    generator = ScenarioGenerator(kafka_broker=args.broker)
    
    logger.info("=" * 60)
    
    if args.scenario == 'flapping':
        generator.scenario_interface_flapping(count=args.count, interval=2)
    elif args.scenario == 'brute-force':
        generator.scenario_auth_brute_force(count=args.count, interval=1)
    elif args.scenario == 'high-cpu':
        generator.scenario_high_cpu(duration=args.duration, interval=10)
    elif args.scenario == 'bgp-unstable':
        generator.scenario_bgp_instability(count=args.count, interval=20)
    elif args.scenario == 'chaos':
        generator.scenario_mixed_chaos(duration=args.duration)
    elif args.scenario == 'device-failure':
        generator.scenario_device_failure(count=args.count, interval=3)
    
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
