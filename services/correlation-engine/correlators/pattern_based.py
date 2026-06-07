"""
Smart NOC - Pattern-Based Correlation

Groups anomalies based on patterns:
- Same anomaly type across multiple devices (network-wide issue)
- Same device with multiple anomaly types (device failure)
- Known incident patterns (security breach, connectivity issue)
"""

from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from loguru import logger


class PatternBasedCorrelator:
    """Correlates anomalies based on pattern matching"""
    
    def __init__(self, config: dict):
        """Initialize pattern-based correlator"""
        self.config = config
        self.correlation_config = config['correlation']
        self.patterns = self.correlation_config.get('patterns', {})
    
    def _get_anomaly_type(self, anomaly: Dict) -> str:
        """
        Get the relevant anomaly type for pattern matching.
        Prioritizes event_type over anomaly_type for ML detections.
        """
        # For ML-detected anomalies, use the event_type field
        if anomaly.get('anomaly_type') == 'ML_DETECTED_ANOMALY':
            return anomaly.get('event_type', anomaly.get('anomaly_type'))
        # For rule-based anomalies, use anomaly_type
        return anomaly.get('anomaly_type', '')
    
    def correlate(self, anomalies: List[Dict]) -> List[Tuple[List[Dict], str, str]]:
        """
        Find pattern-based correlations in anomalies
        
        Args:
            anomalies: List of anomaly dictionaries
            
        Returns:
            List of tuples: (anomaly_group, incident_type, correlation_method)
        """
        if len(anomalies) < 2:
            return []
        
        correlations = []
        
        # Try each correlation pattern
        correlations.extend(self._find_network_performance(anomalies))
        correlations.extend(self._find_security_breach(anomalies))
        correlations.extend(self._find_connectivity_issue(anomalies))
        correlations.extend(self._find_device_failure(anomalies))
        
        # Also find same-type and same-device correlations
        correlations.extend(self._find_same_type_multi_device(anomalies))
        correlations.extend(self._find_same_device_multi_type(anomalies))
        
        return correlations
    
    def _find_network_performance(self, anomalies: List[Dict]) -> List[Tuple[List[Dict], str, str]]:
        """Detect network-wide performance issues"""
        pattern = self.patterns.get('NETWORK_PERFORMANCE', {})
        target_types = pattern.get('anomaly_types', ['HIGH_CPU', 'HIGH_MEMORY', 'PACKET_LOSS'])
        min_devices = pattern.get('min_devices', 2)
        
        # Find anomalies matching performance types
        perf_anomalies = [
            a for a in anomalies
            if self._get_anomaly_type(a) in target_types
        ]
        
        if len(perf_anomalies) < min_devices:
            return []
        
        # Group by affected devices
        devices = set(a.get('device_id') for a in perf_anomalies if a.get('device_id'))
        
        if len(devices) >= min_devices:
            logger.info(f"Network performance pattern detected: {len(perf_anomalies)} anomalies across {len(devices)} devices")
            return [(perf_anomalies, 'NETWORK_PERFORMANCE', 'PATTERN_BASED')]
        
        return []
    
    def _find_security_breach(self, anomalies: List[Dict]) -> List[Tuple[List[Dict], str, str]]:
        """Detect security incidents"""
        pattern = self.patterns.get('SECURITY_BREACH', {})
        target_types = pattern.get('anomaly_types', ['AUTH_FAILURE', 'UNAUTHORIZED_ACCESS', 'AUTH_BRUTE_FORCE'])
        min_count = pattern.get('min_count', 2)
        
        # Find security-related anomalies
        security_anomalies = [
            a for a in anomalies
            if self._get_anomaly_type(a) in target_types or
               'AUTH' in self._get_anomaly_type(a) or
               'BRUTE' in self._get_anomaly_type(a)
        ]
        
        if len(security_anomalies) >= min_count:
            logger.warning(f"Security breach pattern detected: {len(security_anomalies)} security anomalies")
            return [(security_anomalies, 'SECURITY_BREACH', 'PATTERN_BASED')]
        
        return []
    
    def _find_connectivity_issue(self, anomalies: List[Dict]) -> List[Tuple[List[Dict], str, str]]:
        """Detect connectivity issues"""
        pattern = self.patterns.get('CONNECTIVITY_ISSUE', {})
        target_types = pattern.get('anomaly_types', ['INTERFACE_DOWN', 'BGP_DOWN', 'LINK_DOWN', 'INTERFACE_FLAPPING'])
        min_devices = pattern.get('min_devices', 2)
        
        # Find connectivity anomalies
        conn_anomalies = [
            a for a in anomalies
            if self._get_anomaly_type(a) in target_types or
               'DOWN' in self._get_anomaly_type(a) or
               'FLAPPING' in self._get_anomaly_type(a)
        ]
        
        if len(conn_anomalies) < min_devices:
            return []
        
        devices = set(a.get('device_id') for a in conn_anomalies if a.get('device_id'))
        
        if len(devices) >= min_devices:
            logger.info(f"Connectivity issue pattern detected: {len(conn_anomalies)} anomalies across {len(devices)} devices")
            return [(conn_anomalies, 'CONNECTIVITY_ISSUE', 'PATTERN_BASED')]
        
        return []
    
    def _find_device_failure(self, anomalies: List[Dict]) -> List[Tuple[List[Dict], str, str]]:
        """Detect device failures (same device, multiple different anomaly types)"""
        pattern = self.patterns.get('DEVICE_FAILURE', {})
        min_count = pattern.get('min_count', 3)
        
        # Group by device
        device_groups = defaultdict(list)
        for anomaly in anomalies:
            device_id = anomaly.get('device_id')
            if device_id:
                device_groups[device_id].append(anomaly)
        
        results = []
        for device_id, device_anomalies in device_groups.items():
            if len(device_anomalies) >= min_count:
                # Check if they are different types
                types = set(a.get('anomaly_type') for a in device_anomalies)
                if len(types) >= 2:  # At least 2 different types
                    logger.warning(f"Device failure pattern detected: {device_id} with {len(device_anomalies)} different anomaly types")
                    results.append((device_anomalies, 'DEVICE_FAILURE', 'PATTERN_BASED'))
        
        return results
    
    def _find_same_type_multi_device(self, anomalies: List[Dict]) -> List[Tuple[List[Dict], str, str]]:
        """Find same anomaly type across multiple devices"""
        threshold = self.correlation_config.get('same_type_threshold', 2)
        
        # Group by anomaly type (using event_type for ML anomalies)
        type_groups = defaultdict(list)
        for anomaly in anomalies:
            anomaly_type = self._get_anomaly_type(anomaly)
            type_groups[anomaly_type].append(anomaly)
        
        results = []
        for anomaly_type, type_anomalies in type_groups.items():
            if len(type_anomalies) >= threshold:
                devices = set(a.get('device_id') for a in type_anomalies if a.get('device_id'))
                if len(devices) >= 2:  # Multiple devices affected
                    logger.debug(f"Same-type pattern: {anomaly_type} on {len(devices)} devices")
                    results.append((type_anomalies, 'UNKNOWN', 'PATTERN_BASED'))
        
        return results
    
    def _find_same_device_multi_type(self, anomalies: List[Dict]) -> List[Tuple[List[Dict], str, str]]:
        """Find multiple anomaly types on same device"""
        threshold = self.correlation_config.get('same_device_threshold', 2)
        
        # Group by device
        device_groups = defaultdict(list)
        for anomaly in anomalies:
            device_id = anomaly.get('device_id')
            if device_id:
                device_groups[device_id].append(anomaly)
        
        results = []
        for device_id, device_anomalies in device_groups.items():
            if len(device_anomalies) >= threshold:
                types = set(self._get_anomaly_type(a) for a in device_anomalies)
                if len(types) >= 2:  # Different types
                    logger.debug(f"Same-device pattern: {device_id} with {len(types)} anomaly types")
                    results.append((device_anomalies, 'DEVICE_FAILURE', 'PATTERN_BASED'))
        
        return results
