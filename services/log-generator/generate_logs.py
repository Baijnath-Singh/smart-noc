"""
Smart NOC - Network Log Generator

Simulates network devices (routers, switches, firewalls) generating syslog messages.
Sends logs to Kafka for processing.

Usage:
    python generate_logs.py                    # Normal traffic
    python generate_logs.py --scenario flap    # Interface flapping
    python generate_logs.py --rate 100         # 100 logs/sec
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

class NetworkLogGenerator:
    """Generate realistic network device logs"""
    
    def __init__(self, kafka_broker='localhost:9092', topic='network-logs'):
        """Initialize log generator"""
        self.topic = topic
        self.devices = self._create_devices()
        
        # Connect to Kafka
        logger.info(f"Connecting to Kafka broker: {kafka_broker}")
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=kafka_broker,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                max_request_size=1048576,
                compression_type='gzip'
            )
            logger.success("Connected to Kafka successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    def _create_devices(self):
        """Create simulated network devices"""
        devices = []
        
        # Core Routers
        for i in range(1, 4):
            devices.append({
                'id': f'core-router-{i:02d}',
                'type': 'router',
                'location': f'DC-{i}',
                'interfaces': [f'GigabitEthernet0/{j}' for j in range(1, 9)]
            })
        
        # Distribution Switches
        for i in range(1, 6):
            devices.append({
                'id': f'dist-switch-{i:02d}',
                'type': 'switch',
                'location': f'Floor-{i}',
                'interfaces': [f'GigabitEthernet1/0/{j}' for j in range(1, 25)]
            })
        
        # Edge Firewalls
        for i in range(1, 3):
            devices.append({
                'id': f'edge-firewall-{i:02d}',
                'type': 'firewall',
                'location': f'DMZ-{i}',
                'interfaces': [f'Ethernet0/{j}' for j in range(1, 5)]
            })
        
        return devices
    
    def _generate_syslog_timestamp(self):
        """Generate syslog timestamp format (UTC)"""
        return datetime.utcnow().strftime('%b %d %H:%M:%S')
    
    def _select_weighted_severity(self):
        """Select severity with realistic distribution"""
        return random.choices(
            ['INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            weights=[70, 20, 8, 2],  # 70% INFO, 20% WARNING, 8% ERROR, 2% CRITICAL
            k=1
        )[0]
    
    def generate_interface_event(self, device):
        """Generate interface up/down events"""
        interface = random.choice(device['interfaces'])
        state = random.choice(['up', 'down'])
        severity = 'ERROR' if state == 'down' else 'INFO'
        
        return {
            'timestamp': self._generate_syslog_timestamp(),
            'device_id': device['id'],
            'device_type': device['type'],
            'severity': severity,
            'event_type': f'INTERFACE_{state.upper()}',
            'interface': interface,
            'message': f"%LINK-3-UPDOWN: Interface {interface}, changed state to {state}",
        }
    
    def generate_bgp_event(self, device):
        """Generate BGP session events"""
        if device['type'] != 'router':
            return None
        
        neighbor_ip = f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        state = random.choice(['up', 'down', 'idle', 'established'])
        severity = 'CRITICAL' if state == 'down' else 'INFO'
        
        return {
            'timestamp': self._generate_syslog_timestamp(),
            'device_id': device['id'],
            'device_type': device['type'],
            'severity': severity,
            'event_type': f'BGP_{state.upper()}',
            'neighbor': neighbor_ip,
            'message': f"%BGP-5-ADJCHANGE: neighbor {neighbor_ip} {state}",
        }
    
    def generate_cpu_alert(self, device):
        """Generate CPU utilization alerts"""
        cpu_percent = random.randint(70, 99)
        severity = 'CRITICAL' if cpu_percent > 90 else 'WARNING'
        
        return {
            'timestamp': self._generate_syslog_timestamp(),
            'device_id': device['id'],
            'device_type': device['type'],
            'severity': severity,
            'event_type': 'HIGH_CPU',
            'cpu_percent': cpu_percent,
            'message': f"%SYS-4-CPU_HOG: CPU utilization is {cpu_percent}%",
        }
    
    def generate_auth_failure(self, device):
        """Generate authentication failure events"""
        username = random.choice(['admin', 'operator', 'monitor', 'root'])
        source_ip = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        
        return {
            'timestamp': self._generate_syslog_timestamp(),
            'device_id': device['id'],
            'device_type': device['type'],
            'severity': 'WARNING',
            'event_type': 'AUTH_FAILURE',
            'username': username,
            'source_ip': source_ip,
            'message': f"%SEC_LOGIN-4-LOGIN_FAILED: Login failed for user {username} from {source_ip}",
        }
    
    def generate_spanning_tree_event(self, device):
        """Generate spanning tree events"""
        if device['type'] != 'switch':
            return None
        
        interface = random.choice(device['interfaces'])
        state = random.choice(['blocking', 'forwarding', 'learning'])
        
        return {
            'timestamp': self._generate_syslog_timestamp(),
            'device_id': device['id'],
            'device_type': device['type'],
            'severity': 'INFO',
            'event_type': 'STP_STATE_CHANGE',
            'interface': interface,
            'message': f"%SPANTREE-7-PORT_STATE: {interface} moved to {state} state",
        }
    
    def generate_log(self):
        """Generate a random log message"""
        device = random.choice(self.devices)
        
        # Select log type based on weights
        log_types = [
            (self.generate_interface_event, 30),
            (self.generate_bgp_event, 15),
            (self.generate_cpu_alert, 10),
            (self.generate_auth_failure, 5),
            (self.generate_spanning_tree_event, 40),
        ]
        
        log_func = random.choices(
            [lt[0] for lt in log_types],
            weights=[lt[1] for lt in log_types],
            k=1
        )[0]
        
        log = log_func(device)
        
        # Some log functions return None (device type mismatch)
        if log is None:
            return self.generate_log()
        
        return log
    
    def generate_scenario_interface_flap(self, device_id=None):
        """Generate interface flapping scenario"""
        device = random.choice([d for d in self.devices if d['id'] == device_id]) if device_id else random.choice(self.devices)
        interface = random.choice(device['interfaces'])
        
        logs = []
        for _ in range(10):
            state = 'down' if _ % 2 == 0 else 'up'
            logs.append({
                'timestamp': self._generate_syslog_timestamp(),
                'device_id': device['id'],
                'device_type': device['type'],
                'severity': 'ERROR',
                'event_type': f'INTERFACE_{state.upper()}',
                'interface': interface,
                'message': f"%LINK-3-UPDOWN: Interface {interface}, changed state to {state}",
            })
            time.sleep(0.5)
        
        return logs
    
    def send_log(self, log):
        """Send log to Kafka"""
        try:
            self.producer.send(self.topic, value=log)
            logger.debug(f"Sent: {log['device_id']} - {log['event_type']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send log: {e}")
            return False
    
    def run(self, rate=10, duration=None, scenario=None):
        """
        Run log generator
        
        Args:
            rate: Logs per second
            duration: Run duration in seconds (None = infinite)
            scenario: Special scenario ('flap', 'bgp_failure', 'high_cpu')
        """
        logger.info(f"Starting log generation: {rate} logs/sec")
        if duration:
            logger.info(f"Duration: {duration} seconds")
        
        start_time = time.time()
        log_count = 0
        
        try:
            while True:
                # Check duration
                if duration and (time.time() - start_time) > duration:
                    break
                
                # Generate logs based on scenario
                if scenario == 'flap':
                    logs = self.generate_scenario_interface_flap()
                    for log in logs:
                        self.send_log(log)
                        log_count += 1
                    time.sleep(5)  # Pause between flap scenarios
                else:
                    # Normal operation
                    log = self.generate_log()
                    self.send_log(log)
                    log_count += 1
                    
                    # Sleep to maintain rate
                    time.sleep(1.0 / rate)
                
                # Progress update every 100 logs
                if log_count % 100 == 0:
                    elapsed = time.time() - start_time
                    actual_rate = log_count / elapsed if elapsed > 0 else 0
                    logger.info(f"Generated {log_count} logs | Rate: {actual_rate:.1f} logs/sec")
        
        except KeyboardInterrupt:
            logger.warning("Interrupted by user")
        finally:
            self.producer.flush()
            self.producer.close()
            logger.success(f"Finished. Total logs sent: {log_count}")


def main():
    parser = argparse.ArgumentParser(description='Smart NOC Network Log Generator')
    parser.add_argument('--broker', default='localhost:9092', help='Kafka broker address')
    parser.add_argument('--topic', default='network-logs', help='Kafka topic name')
    parser.add_argument('--rate', type=int, default=10, help='Logs per second')
    parser.add_argument('--duration', type=int, help='Run duration in seconds')
    parser.add_argument('--scenario', choices=['flap', 'bgp_failure', 'high_cpu'], help='Special scenario')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Configure log level
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    # Create and run generator
    generator = NetworkLogGenerator(kafka_broker=args.broker, topic=args.topic)
    generator.run(rate=args.rate, duration=args.duration, scenario=args.scenario)


if __name__ == '__main__':
    main()
