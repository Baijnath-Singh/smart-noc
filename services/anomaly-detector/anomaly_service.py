"""
Smart NOC - Anomaly Detection Service

Consumes network logs, detects anomalies using hybrid approach (rule-based + ML),
and publishes anomalies to Kafka for downstream processing.
"""

import json
import yaml
import sys
import time
import signal
from typing import Dict, List
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from loguru import logger

from state_manager import StateManager
from detectors.rule_based import RuleBasedDetector
from detectors.ml_based import MLBasedDetector


class AnomalyDetectionService:
    """Main anomaly detection service orchestrating rule-based and ML detectors"""
    
    def __init__(self, config_path='config.yaml'):
        """Initialize anomaly detection service"""
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        logger.info("Anomaly Detection Service starting...")
        
        # Initialize state manager (Redis)
        redis_config = self.config['redis']
        self.state = StateManager(
            redis_host=redis_config['host'],
            redis_port=redis_config['port'],
            redis_db=redis_config['db']
        )
        
        # Initialize detectors
        self.rule_detector = RuleBasedDetector(self.state, self.config)
        self.ml_detector = MLBasedDetector(self.state, self.config)
        
        # Initialize Kafka consumer
        kafka_config = self.config['kafka']
        self.consumer = KafkaConsumer(
            kafka_config['input_topic'],
            bootstrap_servers=kafka_config['bootstrap_servers'],
            group_id=kafka_config['group_id'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',  # Start from latest for new consumers
            enable_auto_commit=True,
            max_poll_records=100
        )
        
        logger.info(f"Connected to Kafka, consuming from: {kafka_config['input_topic']}")
        
        # Initialize Kafka producer for anomalies
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_config['bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            max_request_size=1048576,
            compression_type='gzip'
        )
        
        self.output_topic = kafka_config['output_topic']
        logger.info(f"Publishing anomalies to: {self.output_topic}")
        
        # Statistics
        self.stats = {
            'logs_processed': 0,
            'anomalies_detected': 0,
            'rule_based_alerts': 0,
            'ml_based_alerts': 0,
            'start_time': datetime.utcnow()
        }
        
        # Graceful shutdown handling
        self.running = True
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
    
    def shutdown(self, signum, frame):
        """Graceful shutdown handler"""
        logger.info("Shutdown signal received, stopping service...")
        self.running = False
    
    def process_log(self, log: Dict) -> List[Dict]:
        """
        Process a single log entry through all detectors
        
        Args:
            log: Network log entry
            
        Returns:
            List of detected anomalies
        """
        all_anomalies = []
        
        try:
            # Log each incoming log at DEBUG level
            device_id = log.get('device_id', 'unknown')
            # Handle both string and list device_id
            if isinstance(device_id, list):
                device_id = device_id[0] if device_id else 'unknown'
            event_type = log.get('event_type', 'unknown')
            logger.debug(f"Processing: {device_id} - {event_type}")
            
            # Run rule-based detection
            rule_anomalies = self.rule_detector.detect(log)
            if rule_anomalies:
                all_anomalies.extend(rule_anomalies)
                self.stats['rule_based_alerts'] += len(rule_anomalies)
            
            # Run ML-based detection
            ml_anomalies = self.ml_detector.detect(log)
            if ml_anomalies:
                all_anomalies.extend(ml_anomalies)
                self.stats['ml_based_alerts'] += len(ml_anomalies)
            
            # Add metadata to all anomalies
            for anomaly in all_anomalies:
                anomaly['detected_at'] = datetime.utcnow().isoformat()
                anomaly['detector_version'] = '1.0.0'
            
        except Exception as e:
            logger.error(f"Error processing log: {e}")
        
        return all_anomalies
    
    def publish_anomaly(self, anomaly: Dict):
        """Publish anomaly to Kafka topic"""
        try:
            self.producer.send(self.output_topic, value=anomaly)
            logger.info(f"Anomaly published: {anomaly['anomaly_type']} - {anomaly.get('device_id', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to publish anomaly: {e}")
    
    def print_stats(self):
        """Print service statistics"""
        uptime = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        rate = self.stats['logs_processed'] / uptime if uptime > 0 else 0
        
        logger.info("=" * 60)
        logger.info("ANOMALY DETECTION SERVICE STATISTICS")
        logger.info(f"Uptime: {uptime:.0f} seconds")
        logger.info(f"Logs processed: {self.stats['logs_processed']} ({rate:.1f}/sec)")
        logger.info(f"Total anomalies: {self.stats['anomalies_detected']}")
        logger.info(f"  ├─ Rule-based: {self.stats['rule_based_alerts']}")
        logger.info(f"  └─ ML-based: {self.stats['ml_based_alerts']}")
        
        # ML model stats
        ml_stats = self.ml_detector.get_model_stats()
        logger.info(f"ML Model: {ml_stats['model_type']}")
        logger.info(f"  ├─ Trained: {ml_stats['is_trained']}")
        logger.info(f"  ├─ Training samples: {ml_stats['training_samples']}")
        logger.info(f"  └─ Last training: {ml_stats['last_training'] or 'Never'}")
        logger.info("=" * 60)
    
    def run(self):
        """Main service loop"""
        logger.success("Anomaly Detection Service running!")
        
        last_stats_time = time.time()
        stats_interval = 60  # Print stats every 60 seconds
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                log = message.value
                self.stats['logs_processed'] += 1
                
                # Process log through detectors
                anomalies = self.process_log(log)
                
                # Publish detected anomalies
                for anomaly in anomalies:
                    self.publish_anomaly(anomaly)
                    self.stats['anomalies_detected'] += 1
                
                # Periodic stats
                if time.time() - last_stats_time > stats_interval:
                    self.print_stats()
                    last_stats_time = time.time()
        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources...")
        
        # Print final stats
        self.print_stats()
        
        # Close Kafka connections
        self.consumer.close()
        self.producer.flush()
        self.producer.close()
        
        logger.success("Anomaly Detection Service stopped gracefully")


def main():
    """Entry point"""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG"  # Changed from INFO to DEBUG for more detailed logging
    )
    
    try:
        service = AnomalyDetectionService()
        service.run()
    except Exception as e:
        logger.error(f"Service failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
