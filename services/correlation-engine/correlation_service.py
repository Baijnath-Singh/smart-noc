"""
Smart NOC - Correlation Engine Service

Consumes anomalies from Kafka, correlates related anomalies into incidents,
stores in PostgreSQL, and publishes incidents back to Kafka.
"""

import json
import yaml
import sys
import time
import signal
from datetime import datetime
from typing import Dict, List
from kafka import KafkaConsumer, KafkaProducer
from loguru import logger

from models.database import DatabaseManager
from models.incident import IncidentManager
from correlators.time_based import TimeBasedCorrelator
from correlators.pattern_based import PatternBasedCorrelator


class CorrelationService:
    """Main correlation engine service"""
    
    def __init__(self, config_path='config.yaml'):
        """Initialize correlation service"""
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Statistics
        self.stats = {
            'anomalies_processed': 0,
            'incidents_created': 0,
            'correlations_found': 0,
            'start_time': datetime.utcnow()
        }
        
        # Initialize database
        logger.info("Connecting to PostgreSQL...")
        self.db_manager = DatabaseManager(self.config)
        self.incident_manager = IncidentManager(self.config)
        
        # Initialize correlators
        logger.info("Initializing correlators...")
        self.time_correlator = TimeBasedCorrelator(self.config)
        self.pattern_correlator = PatternBasedCorrelator(self.config)
        
        # Kafka configuration
        kafka_config = self.config['kafka']
        
        # Initialize Kafka consumer (anomalies)
        logger.info(f"Connecting to Kafka: {kafka_config['bootstrap_servers']}")
        self.consumer = KafkaConsumer(
            kafka_config['input_topic'],
            bootstrap_servers=kafka_config['bootstrap_servers'],
            group_id=kafka_config['consumer_group'],
            auto_offset_reset=kafka_config['auto_offset_reset'],
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            consumer_timeout_ms=1000  # Allow periodic processing even without messages
        )
        
        # Initialize Kafka producer (incidents)
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_config['bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        self.output_topic = kafka_config['output_topic']
        
        # Shutdown flag
        self.shutdown = False
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)
        
        # Last stats time
        self.last_stats_time = time.time()
        self.stats_interval = self.config.get('monitoring', {}).get('stats_interval_seconds', 300)
        
        logger.success("Correlation Engine Service initialized!")
    
    def run(self):
        """Main service loop"""
        logger.success("Correlation Engine Service running!")
        logger.info(f"Consuming from: {self.config['kafka']['input_topic']}")
        logger.info(f"Publishing to: {self.output_topic}")
        logger.info(f"Time window: {self.config['correlation']['time_window_minutes']} minutes")
        
        try:
            while not self.shutdown:
                # Process anomalies from Kafka
                self._process_anomalies()
                
                # Periodically check for correlations
                self._check_correlations()
                
                # Log statistics
                if time.time() - self.last_stats_time >= self.stats_interval:
                    self._log_statistics()
                    self.last_stats_time = time.time()
                
                # No sleep needed - poll timeout handles pacing
        
        except Exception as e:
            logger.error(f"Service error: {e}")
            raise
        finally:
            self._cleanup()
    
    def _process_anomalies(self):
        """Process incoming anomalies from Kafka"""
        try:
            # Poll for messages (more responsive: 500ms timeout, 50 records)
            messages = self.consumer.poll(timeout_ms=500, max_records=50)
            
            for topic, msgs in messages.items():
                for message in msgs:
                    anomaly = message.value
                    self.stats['anomalies_processed'] += 1
                    
                    logger.debug(f"Received anomaly: {anomaly.get('device_id')} - {anomaly.get('anomaly_type')}")
                    
                    # Add to time-based correlator buffer
                    self.time_correlator.add_anomaly(anomaly)
        
        except Exception as e:
            logger.error(f"Error processing anomalies: {e}")
    
    def _check_correlations(self):
        """Check for correlations and create incidents"""
        try:
            # Get time-based correlations
            time_groups = self.time_correlator.find_correlations()
            
            for group in time_groups:
                # Apply pattern-based correlation to each time group
                pattern_correlations = self.pattern_correlator.correlate(group)
                
                if pattern_correlations:
                    # Create incidents from pattern matches
                    for anomalies, incident_type, method in pattern_correlations:
                        self._create_incident(anomalies, incident_type, method)
                        self.stats['correlations_found'] += 1
                elif len(group) >= 2:
                    # Create generic time-based incident if no specific pattern matched
                    self._create_incident(group, 'UNKNOWN', 'TIME_BASED')
                    self.stats['correlations_found'] += 1
                elif len(group) == 1:
                    # Create incident from single high-severity anomaly
                    anomaly = group[0]
                    severity = anomaly.get('severity', 'MEDIUM').upper()
                    if severity in ['HIGH', 'CRITICAL']:
                        anomaly_type = anomaly.get('anomaly_type', 'UNKNOWN')
                        self._create_incident(group, anomaly_type, 'SINGLE_HIGH_SEVERITY')
                        self.stats['correlations_found'] += 1
                        logger.info(f"Single high-severity anomaly incident created: {anomaly_type} ({severity})")
        
        except Exception as e:
            logger.error(f"Error checking correlations: {e}")
    
    def _create_incident(self, anomalies: List[Dict], incident_type: str, correlation_method: str):
        """Create incident from correlated anomalies"""
        try:
            db = self.db_manager.get_session()
            
            try:
                # Create incident in database
                incident = self.incident_manager.create_incident(
                    db=db,
                    anomalies=anomalies,
                    incident_type=incident_type,
                    correlation_method=correlation_method,
                    metadata={
                        'anomaly_count': len(anomalies),
                        'correlation_timestamp': datetime.utcnow().isoformat()
                    }
                )
                
                self.stats['incidents_created'] += 1
                
                # Publish incident to Kafka
                self._publish_incident(incident)
                
                # CRITICAL FIX: Remove anomalies from buffer after creating incident
                # This prevents infinite loop of re-correlating the same anomalies
                self.time_correlator.remove_anomalies(anomalies)
                
                logger.success(
                    f"Incident #{incident.incident_number} created: "
                    f"{incident_type} (severity: {incident.severity}, "
                    f"devices: {incident.affected_device_count}, "
                    f"anomalies: {incident.anomaly_count})"
                )
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"Error creating incident: {e}")
    
    def _publish_incident(self, incident):
        """Publish incident to Kafka"""
        try:
            incident_data = incident.to_dict()
            self.producer.send(self.output_topic, value=incident_data)
            logger.info(f"Incident published to Kafka: {self.output_topic}")
        except Exception as e:
            logger.error(f"Error publishing incident: {e}")
    
    def _log_statistics(self):
        """Log service statistics"""
        uptime = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        
        logger.info("=" * 60)
        logger.info("CORRELATION ENGINE STATISTICS")
        logger.info(f"Uptime: {int(uptime)} seconds")
        logger.info(f"Anomalies processed: {self.stats['anomalies_processed']}")
        logger.info(f"Incidents created: {self.stats['incidents_created']}")
        logger.info(f"Correlations found: {self.stats['correlations_found']}")
        logger.info(f"Buffer size: {self.time_correlator.get_buffer_size()} anomalies")
        logger.info("=" * 60)
    
    def _shutdown_handler(self, signum, frame):
        """Handle shutdown signal"""
        logger.info("Shutdown signal received, stopping service...")
        self.shutdown = True
    
    def _cleanup(self):
        """Cleanup resources"""
        logger.info("Closing connections...")
        self.consumer.close()
        self.producer.close()
        logger.success("Correlation Engine Service stopped gracefully")


def main():
    """Entry point"""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    logger.info("Starting Correlation Engine Service...")
    
    try:
        service = CorrelationService()
        service.run()
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
