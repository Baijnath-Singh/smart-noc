"""
Rule-Based Anomaly Detectors

Implements deterministic detection rules for known anomaly patterns.
"""

from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
from state_manager import StateManager


class RuleBasedDetector:
    """Rule-based anomaly detection using predefined thresholds"""
    
    def __init__(self, state_manager: StateManager, config: Dict):
        """
        Initialize rule-based detector
        
        Args:
            state_manager: Redis state manager
            config: Detection configuration
        """
        self.state = state_manager
        self.config = config
        self.window_minutes = config['detection']['window_size_minutes']
        logger.info("Rule-based detector initialized")
    
    def _enrich_with_device_fields(self, anomaly: Dict, log: Dict) -> Dict:
        """Add device enrichment fields from log to anomaly if present"""
        for field in ['device_vendor', 'device_family', 'device_model', 'device_os_version', 'device_cli_syntax', 'device_role']:
            if field in log and log[field]:
                anomaly[field] = log[field]
        return anomaly
    
    def detect_interface_flapping(self, log: Dict) -> Optional[Dict]:
        """
        Detect interface flapping: rapid interface up/down transitions
        
        Pattern: >5 state changes in 5 minutes on same interface
        Uses criticality-aware thresholds (from Logstash enrichment)
        """
        if log.get('event_type') not in ['INTERFACE_UP', 'INTERFACE_DOWN']:
            return None
        
        device_id = log.get('device_id')
        interface = log.get('interface')
        
        if not device_id or not interface:
            return None
        
        key = f"interface_events:{device_id}:{interface}"
        
        # Add current event
        event_data = {
            'timestamp': datetime.utcnow().timestamp(),
            'event_type': log['event_type'],
            'link_state': log.get('link_state')
        }
        self.state.add_event(key, event_data, ttl_seconds=self.window_minutes * 60)
        
        # Count events in window
        event_count = self.state.count_events_in_window(key, self.window_minutes)
        
        # Criticality-aware threshold (NEW: uses enriched data from Logstash)
        base_threshold = self.config['detection']['interface_flapping']['threshold']
        criticality = log.get('criticality', 'medium')
        
        # More sensitive for critical devices (lower threshold)
        if criticality == 'high':
            threshold = base_threshold  # Use base threshold (most sensitive)
        elif criticality == 'medium':
            threshold = base_threshold + 1  # Slightly less sensitive
        else:
            threshold = base_threshold + 2  # Least sensitive for low criticality
        
        if event_count >= threshold:
            # Check if we already reported this recently (avoid duplicate alerts)
            alert_key = f"alert:interface_flap:{device_id}:{interface}"
            if self.state.get_counter(alert_key) > 0:
                return None  # Already alerted
            
            # Set alert cooldown (1 minute)
            self.state.increment_counter(alert_key, ttl_seconds=60)
            
            logger.warning(
                f"Interface flapping detected: {device_id} {interface} "
                f"({event_count} events, criticality: {criticality}, threshold: {threshold})"
            )
            
            anomaly = {
                'anomaly_type': 'INTERFACE_FLAPPING',
                'severity': self.config['detection']['interface_flapping']['severity'],
                'device_id': device_id,
                'device_role': log.get('device_role'),  # NEW: Include enriched data
                'criticality': criticality,  # NEW: Include enriched data
                'interface': interface,
                'event_count': event_count,
                'window_minutes': self.window_minutes,
                'detection_method': 'rule',
                'confidence': 1.0,
                'details': f"Interface changed state {event_count} times in {self.window_minutes} minutes (criticality: {criticality})"
            }
            return self._enrich_with_device_fields(anomaly, log)
        
        return None
    
    def detect_auth_brute_force(self, log: Dict) -> Optional[Dict]:
        """
        Detect authentication brute force: repeated login failures
        
        Pattern: >10 auth failures in 2 minutes from same source
        """
        if log.get('event_type') != 'AUTH_FAILURE':
            return None
        
        device_id = log.get('device_id')
        source_ip = log.get('source_ip')
        
        if not device_id or not source_ip:
            return None
        
        # Handle source_ip as list or string
        if isinstance(source_ip, list):
            source_ip = source_ip[0] if source_ip else None
        
        if not source_ip:
            return None
        
        key = f"auth_failures:{device_id}:{source_ip}"
        
        # Add current event
        event_data = {
            'timestamp': datetime.utcnow().timestamp(),
            'username': log.get('failed_username', log.get('username')),
            'source_ip': source_ip
        }
        self.state.add_event(key, event_data, ttl_seconds=120)  # 2 minute window
        
        # Count failures in 2-minute window
        failure_count = self.state.count_events_in_window(key, window_minutes=2)
        
        threshold = self.config['detection']['auth_brute_force']['threshold']
        
        if failure_count >= threshold:
            # Check alert cooldown
            alert_key = f"alert:auth_brute:{device_id}:{source_ip}"
            if self.state.get_counter(alert_key) > 0:
                return None
            
            self.state.increment_counter(alert_key, ttl_seconds=300)  # 5 min cooldown
            
            # Get recent attempts for context
            recent_events = self.state.get_events_in_window(key, window_minutes=2)
            usernames = list(set([e.get('username', 'unknown') for e in recent_events]))
            
            logger.warning(f"Auth brute force detected: {source_ip} → {device_id} ({failure_count} attempts)")
            
            anomaly = {
                'anomaly_type': 'AUTH_BRUTE_FORCE',
                'severity': self.config['detection']['auth_brute_force']['severity'],
                'device_id': device_id,
                'source_ip': source_ip,
                'attempt_count': failure_count,
                'targeted_users': usernames,
                'window_minutes': 2,
                'detection_method': 'rule',
                'confidence': 1.0,
                'details': f"Brute force attack from {source_ip}: {failure_count} failed attempts targeting users {', '.join(usernames[:3])}"
            }
            return self._enrich_with_device_fields(anomaly, log)
        
        return None
    
    def detect_high_cpu(self, log: Dict) -> Optional[Dict]:
        """
        Detect sustained high CPU usage
        
        Pattern: CPU >80% for 10 minutes
        """
        if log.get('event_type') != 'HIGH_CPU':
            return None
        
        device_id = log.get('device_id')
        cpu_percent = log.get('cpu_utilization') or log.get('cpu_percent')
        
        if not device_id or cpu_percent is None:
            return None
        
        try:
            cpu_percent = float(cpu_percent)
        except (TypeError, ValueError):
            return None
        
        threshold_percent = self.config['detection']['high_cpu']['threshold']
        duration_minutes = self.config['detection']['high_cpu']['duration_minutes']
        
        if cpu_percent < threshold_percent:
            # Reset tracking if CPU drops
            key = f"high_cpu_start:{device_id}"
            self.state.redis_client.delete(key)
            return None
        
        # Track when high CPU started
        key = f"high_cpu_start:{device_id}"
        start_time = self.state.get_json(key)
        
        if not start_time:
            # First high CPU event
            self.state.set_json(key, {'start': datetime.utcnow().timestamp()}, ttl_seconds=duration_minutes * 60)
            return None
        
        # Check duration
        elapsed_minutes = (datetime.utcnow().timestamp() - start_time['start']) / 60
        
        if elapsed_minutes >= duration_minutes:
            # Alert only once per episode
            alert_key = f"alert:high_cpu:{device_id}"
            if self.state.get_counter(alert_key) > 0:
                return None
            
            self.state.increment_counter(alert_key, ttl_seconds=600)  # 10 min cooldown
            
            logger.warning(f"Sustained high CPU detected: {device_id} ({cpu_percent}% for {elapsed_minutes:.1f} min)")
            
            anomaly = {
                'anomaly_type': 'HIGH_CPU_SUSTAINED',
                'severity': self.config['detection']['high_cpu']['severity'],
                'device_id': device_id,
                'cpu_percent': cpu_percent,
                'duration_minutes': elapsed_minutes,
                'detection_method': 'rule',
                'confidence': 1.0,
                'details': f"CPU sustained at {cpu_percent}% for {elapsed_minutes:.1f} minutes (threshold: {threshold_percent}%)"
            }
            return self._enrich_with_device_fields(anomaly, log)
        
        return None
    
    def detect_bgp_instability(self, log: Dict) -> Optional[Dict]:
        """
        Detect BGP session instability
        
        Pattern: >3 BGP state changes in 5 minutes
        """
        if log.get('event_type') not in ['BGP_STATE_CHANGE', 'BGP_DOWN', 'BGP_UP']:
            return None
        
        device_id = log.get('device_id')
        neighbor = log.get('bgp_neighbor') or log.get('neighbor')
        
        if not device_id or not neighbor:
            return None
        
        key = f"bgp_events:{device_id}:{neighbor}"
        
        # Add current event
        event_data = {
            'timestamp': datetime.utcnow().timestamp(),
            'bgp_state': log.get('bgp_state'),
            'event_type': log['event_type']
        }
        self.state.add_event(key, event_data, ttl_seconds=self.window_minutes * 60)
        
        # Count state changes
        event_count = self.state.count_events_in_window(key, self.window_minutes)
        
        threshold = self.config['detection']['bgp_instability']['threshold']
        
        if event_count >= threshold:
            alert_key = f"alert:bgp_instability:{device_id}:{neighbor}"
            if self.state.get_counter(alert_key) > 0:
                return None
            
            self.state.increment_counter(alert_key, ttl_seconds=300)
            
            logger.warning(f"BGP instability detected: {device_id} neighbor {neighbor} ({event_count} changes)")
            
            anomaly = {
                'anomaly_type': 'BGP_INSTABILITY',
                'severity': self.config['detection']['bgp_instability']['severity'],
                'device_id': device_id,
                'bgp_neighbor': neighbor,
                'state_change_count': event_count,
                'window_minutes': self.window_minutes,
                'detection_method': 'rule',
                'confidence': 1.0,
                'details': f"BGP session flapping: {event_count} state changes in {self.window_minutes} minutes"
            }
            return self._enrich_with_device_fields(anomaly, log)
        
        return None
    
    def detect_vlan_mismatch(self, log: Dict) -> Optional[Dict]:
        """
        Detect VLAN mismatches and trunk configuration issues
        
        Pattern: VLAN_MISMATCH, CDP/LLDP warnings, trunk inconsistencies
        """
        event_type = log.get('event_type')
        
        # Detect VLAN-related issues
        if event_type not in ['VLAN_MISMATCH', 'CDP_NATIVE_VLAN_MISMATCH', 'TRUNK_MISMATCH']:
            return None
        
        device_id = log.get('device_id')
        if not device_id:
            return None
        
        logger.warning(f"VLAN mismatch detected: {device_id} - {log.get('message', 'No message')[:100]}")
        
        anomaly = {
            'anomaly_type': event_type,
            'device_id': device_id,
            'severity': 'MEDIUM',
            'event_type': event_type,
            'confidence': 1.0,
            'detection_method': 'RULE_BASED',
            'message': f"VLAN configuration mismatch detected on {device_id}",
            'details': log.get('message', '')
        }
        return self._enrich_with_device_fields(anomaly, log)
    
    def detect(self, log: Dict) -> List[Dict]:
        """
        Run all rule-based detectors on a log entry
        
        Args:
            log: Parsed log entry
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Run each detector
        detectors = [
            self.detect_interface_flapping,
            self.detect_auth_brute_force,
            self.detect_high_cpu,
            self.detect_bgp_instability,
            self.detect_vlan_mismatch
        ]
        
        for detector in detectors:
            try:
                result = detector(log)
                if result:
                    # Add common fields
                    result['timestamp'] = datetime.utcnow().isoformat()
                    result['source_log'] = log
                    anomalies.append(result)
            except Exception as e:
                logger.error(f"Error in detector {detector.__name__}: {e}")
        
        return anomalies
