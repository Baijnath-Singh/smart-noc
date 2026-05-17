"""
Smart NOC - Time-Based Correlation

Groups anomalies that occur within a specified time window
"""

from datetime import datetime, timedelta
from typing import List, Dict
from loguru import logger


class TimeBasedCorrelator:
    """Correlates anomalies based on temporal proximity"""
    
    def __init__(self, config: dict):
        """Initialize time-based correlator"""
        self.config = config
        self.time_window_minutes = config['correlation']['time_window_minutes']
        self.anomaly_buffer = []  # Buffer to store recent anomalies
    
    def add_anomaly(self, anomaly: Dict):
        """Add anomaly to buffer"""
        self.anomaly_buffer.append(anomaly)
        
        # Clean old anomalies outside the time window
        self._clean_old_anomalies()
    
    def find_correlations(self) -> List[List[Dict]]:
        """
        Find groups of anomalies within the time window
        
        Returns:
            List of anomaly groups that should be correlated
        """
        if len(self.anomaly_buffer) < 2:
            return []
        
        self._clean_old_anomalies()
        
        # Sort by timestamp
        sorted_anomalies = sorted(
            self.anomaly_buffer,
            key=lambda x: datetime.fromisoformat(x['timestamp'].replace('Z', '+00:00'))
        )
        
        groups = []
        current_group = [sorted_anomalies[0]]
        reference_time = datetime.fromisoformat(sorted_anomalies[0]['timestamp'].replace('Z', '+00:00'))
        
        for anomaly in sorted_anomalies[1:]:
            anomaly_time = datetime.fromisoformat(anomaly['timestamp'].replace('Z', '+00:00'))
            time_diff = (anomaly_time - reference_time).total_seconds() / 60
            
            if time_diff <= self.time_window_minutes:
                # Within window, add to current group
                current_group.append(anomaly)
            else:
                # Outside window, start new group if current group has multiple anomalies
                if len(current_group) >= 2:
                    groups.append(current_group)
                    logger.debug(f"Time-based group found: {len(current_group)} anomalies")
                
                # Start new group
                current_group = [anomaly]
                reference_time = anomaly_time
        
        # Add last group if it has multiple anomalies
        if len(current_group) >= 2:
            groups.append(current_group)
            logger.debug(f"Time-based group found: {len(current_group)} anomalies")
        
        return groups
    
    def _clean_old_anomalies(self):
        """Remove anomalies older than the time window"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.time_window_minutes * 2)
        
        self.anomaly_buffer = [
            anomaly for anomaly in self.anomaly_buffer
            if datetime.fromisoformat(anomaly['timestamp'].replace('Z', '+00:00')) > cutoff_time
        ]
    
    def get_buffer_size(self) -> int:
        """Get current buffer size"""
        return len(self.anomaly_buffer)
    
    def remove_anomalies(self, anomalies_to_remove: List[Dict]):
        """
        Remove specific anomalies from buffer after they've been correlated
        
        Args:
            anomalies_to_remove: List of anomalies to remove from buffer
        """
        # Build set of anomaly IDs to remove (use timestamp + device_id + anomaly_type as unique key)
        remove_keys = set()
        for anomaly in anomalies_to_remove:
            key = f"{anomaly.get('timestamp')}_{anomaly.get('device_id')}_{anomaly.get('anomaly_type')}"
            remove_keys.add(key)
        
        # Filter out removed anomalies
        self.anomaly_buffer = [
            anomaly for anomaly in self.anomaly_buffer
            if f"{anomaly.get('timestamp')}_{anomaly.get('device_id')}_{anomaly.get('anomaly_type')}" not in remove_keys
        ]
        
        logger.debug(f"Removed {len(anomalies_to_remove)} anomalies from buffer, {len(self.anomaly_buffer)} remaining")
