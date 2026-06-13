"""
ML-Based Anomaly Detectors

Implements machine learning models for intelligent anomaly detection.
Uses Isolation Forest for unsupervised anomaly detection.
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from loguru import logger
from state_manager import StateManager


class MLBasedDetector:
    """Machine learning-based anomaly detection using Isolation Forest"""
    
    def __init__(self, state_manager: StateManager, config: Dict):
        """
        Initialize ML-based detector
        
        Args:
            state_manager: Redis state manager
            config: Detection configuration
        """
        self.state = state_manager
        self.config = config
        self.ml_config = config['detection']['isolation_forest']
        
        # Initialize Isolation Forest model
        self.model = IsolationForest(
            contamination=self.ml_config['contamination'],
            n_estimators=self.ml_config['n_estimators'],
            random_state=42,
            n_jobs=-1
        )
        
        self.scaler = StandardScaler()
        self.is_trained = False
        self.last_training_time = None
        self.feature_buffer = []
        
        logger.info("ML-based detector initialized (Isolation Forest)")
    
    def extract_features(self, log: Dict) -> Optional[Dict]:
        """
        Extract numerical features from log entry for ML model
        
        Features:
        - Severity level (numerical encoding)
        - Event type (one-hot or hash)
        - Device criticality
        - Hour of day
        - Day of week
        - Log length
        - Has error indicators
        """
        try:
            # Helper function to normalize field values (handle both strings and lists)
            def normalize_field(value, default=''):
                """Convert list/array to string by taking first element"""
                if isinstance(value, list):
                    return str(value[0]) if value else default
                return str(value) if value else default
            
            # Severity mapping
            severity_map = {'INFO': 0, 'WARNING': 1, 'ERROR': 2, 'CRITICAL': 3}
            severity_str = normalize_field(log.get('severity', 'INFO'), 'INFO').upper()
            severity = severity_map.get(severity_str, 0)
            
            # Event type hash (simple method)
            event_type = normalize_field(log.get('event_type', ''), '')
            event_hash = hash(event_type) % 1000  # Bounded hash
            
            # Criticality mapping
            criticality_map = {'low': 0, 'medium': 1, 'high': 2}
            criticality_str = normalize_field(log.get('criticality', 'medium'), 'medium').lower()
            criticality = criticality_map.get(criticality_str, 1)
            
            # Device role mapping
            role_map = {'edge': 0, 'distribution': 1, 'core': 2}
            device_role_str = normalize_field(log.get('device_role', 'edge'), 'edge').lower()
            device_role = role_map.get(device_role_str, 0)
            
            # Temporal features
            timestamp = datetime.utcnow()
            hour_of_day = timestamp.hour
            day_of_week = timestamp.weekday()
            
            # Message analysis
            message = normalize_field(log.get('message', ''), '')
            message_length = len(message)
            has_error_keyword = int(any(kw in message.lower() for kw in ['error', 'fail', 'down', 'critical']))
            
            # Additional features
            has_interface = int(bool(log.get('interface')))
            has_cpu_data = int(bool(log.get('cpu_utilization') or log.get('cpu_percent')))
            has_bgp_data = int(bool(log.get('bgp_neighbor')))
            has_auth_data = int(bool(log.get('failed_username') or log.get('username')))
            
            features = {
                'severity': severity,
                'event_hash': event_hash,
                'criticality': criticality,
                'device_role': device_role,
                'hour_of_day': hour_of_day,
                'day_of_week': day_of_week,
                'message_length': message_length,
                'has_error_keyword': has_error_keyword,
                'has_interface': has_interface,
                'has_cpu_data': has_cpu_data,
                'has_bgp_data': has_bgp_data,
                'has_auth_data': has_auth_data,
                'log': log  # Keep original for reference
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return None
    
    def should_retrain(self) -> bool:
        """Check if model should be retrained"""
        if not self.is_trained:
            return len(self.feature_buffer) >= self.ml_config['min_samples']
        
        if not self.last_training_time:
            return True
        
        minutes_since_training = (datetime.utcnow() - self.last_training_time).total_seconds() / 60
        return minutes_since_training >= self.ml_config['train_interval_minutes']
    
    def train(self):
        """Train the Isolation Forest model"""
        if len(self.feature_buffer) < self.ml_config['min_samples']:
            logger.info(f"Insufficient samples for training ({len(self.feature_buffer)}/{self.ml_config['min_samples']})")
            return
        
        try:
            # Prepare feature matrix
            feature_names = ['severity', 'event_hash', 'criticality', 'device_role',
                           'hour_of_day', 'day_of_week', 'message_length', 'has_error_keyword',
                           'has_interface', 'has_cpu_data', 'has_bgp_data', 'has_auth_data']
            
            X = np.array([[f[fn] for fn in feature_names] for f in self.feature_buffer])
            
            # Fit scaler and transform
            X_scaled = self.scaler.fit_transform(X)
            
            # Train Isolation Forest
            self.model.fit(X_scaled)
            
            self.is_trained = True
            self.last_training_time = datetime.utcnow()
            
            logger.success(f"Isolation Forest trained on {len(self.feature_buffer)} samples")
            
            # Keep only recent samples in buffer (limit memory)
            if len(self.feature_buffer) > 1000:
                self.feature_buffer = self.feature_buffer[-500:]
            
        except Exception as e:
            logger.error(f"Training error: {e}")
    
    def predict(self, features: Dict) -> Optional[Dict]:
        """
        Predict if log entry is anomalous using trained model
        
        Returns:
            Anomaly dict if detected, None otherwise
        """
        if not self.is_trained:
            return None
        
        try:
            # Prepare feature vector
            feature_names = ['severity', 'event_hash', 'criticality', 'device_role',
                           'hour_of_day', 'day_of_week', 'message_length', 'has_error_keyword',
                           'has_interface', 'has_cpu_data', 'has_bgp_data', 'has_auth_data']
            
            X = np.array([[features[fn] for fn in feature_names]])
            X_scaled = self.scaler.transform(X)
            
            # Predict (-1 = anomaly, 1 = normal)
            prediction = self.model.predict(X_scaled)[0]
            
            # Get anomaly score (lower = more anomalous)
            anomaly_score = self.model.score_samples(X_scaled)[0]
            
            # Convert score to confidence (normalize to 0-1 range)
            # Scores typically range from -0.5 to 0 for anomalies
            # More negative = more anomalous = higher confidence
            confidence = max(0, min(1, abs(anomaly_score) * 2))  # 0.5 -> 1.0 (high confidence)
            
            if prediction == -1:
                log = features['log']
                
                # Check cooldown to avoid duplicate alerts
                device_id = log.get('device_id', 'unknown')
                alert_key = f"alert:ml_anomaly:{device_id}"
                
                # Allow more frequent ML alerts than rule-based (30 sec cooldown)
                if self.state.get_counter(alert_key) > 0:
                    return None
                
                self.state.increment_counter(alert_key, ttl_seconds=30)
                
                logger.warning(f"ML anomaly detected: {log.get('device_id')} - {log.get('event_type')} (confidence: {confidence:.2f})")
                
                # Create anomaly with device enrichment fields if available
                anomaly = {
                    'anomaly_type': 'ML_DETECTED_ANOMALY',
                    'severity': 'MEDIUM' if confidence > 0.7 else 'LOW',
                    'device_id': device_id,
                    'event_type': log.get('event_type'),
                    'detection_method': 'ml',
                    'model': 'isolation_forest',
                    'confidence': round(confidence, 3),
                    'anomaly_score': round(anomaly_score, 3),
                    'details': f"ML model detected unusual pattern (confidence: {confidence:.2%})",
                    'features': {
                        'severity': log.get('severity'),
                        'event_type': log.get('event_type'),
                        'criticality': log.get('criticality'),
                        'time_context': f"{features['hour_of_day']}:00 on day {features['day_of_week']}"
                    }
                }
                
                # Add device enrichment fields if present
                for field in ['device_vendor', 'device_family', 'device_model', 'device_os_version', 'device_cli_syntax', 'device_role']:
                    if field in log and log[field]:
                        anomaly[field] = log[field]
                
                return anomaly
            
            return None
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return None
    
    def detect(self, log: Dict) -> List[Dict]:
        """
        Run ML-based detection on log entry
        
        Args:
            log: Parsed log entry
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        try:
            # Extract features
            features = self.extract_features(log)
            if not features:
                return []
            
            # Add to training buffer
            self.feature_buffer.append(features)
            
            # Check if retraining needed
            if self.should_retrain():
                self.train()
            
            # Predict anomaly
            result = self.predict(features)
            if result:
                result['timestamp'] = datetime.utcnow().isoformat()
                result['source_log'] = log
                anomalies.append(result)
            
        except Exception as e:
            logger.error(f"ML detection error: {e}")
        
        return anomalies
    
    def get_model_stats(self) -> Dict:
        """Get model statistics for monitoring"""
        return {
            'is_trained': self.is_trained,
            'training_samples': len(self.feature_buffer),
            'last_training': self.last_training_time.isoformat() if self.last_training_time else None,
            'model_type': 'IsolationForest',
            'n_estimators': self.ml_config['n_estimators'],
            'contamination': self.ml_config['contamination']
        }
