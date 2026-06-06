"""
Autonomous Remediation Agent Service

Consumes diagnosed incidents from Kafka and autonomously remediates them
using a LangGraph-based multi-step workflow.
"""
import json
import time
import os
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import psycopg2
from psycopg2.extras import RealDictCursor
from loguru import logger
import sys

from config import settings
from workflow import RemediationAgent

# Phase 2: Vector Service Integration for Remediation Lessons
try:
    sys.path.append('/vector_service')
    from vector_service import VectorKnowledgeBase
    VECTOR_SERVICE_AVAILABLE = True
    logger.info("Vector service module loaded for remediation lessons")
except ImportError as e:
    logger.warning(f"Vector service not available: {e}")
    VECTOR_SERVICE_AVAILABLE = False


class RemediationService:
    """
    Main service that orchestrates autonomous remediation
    """
    
    def __init__(self):
        logger.info("=" * 80)
        logger.info("🤖 AUTONOMOUS REMEDIATION AGENT")
        logger.info("=" * 80)
        logger.info(f"Service: {settings.SERVICE_NAME}")
        logger.info(f"Simulation Mode: {settings.SIMULATION_MODE}")
        logger.info(f"Auto Execution: {settings.ENABLE_AUTO_EXECUTION}")
        logger.info("=" * 80)
        
        # Initialize agent
        self.agent = RemediationAgent(
            groq_api_key=settings.GROQ_API_KEY,
            simulation_mode=settings.SIMULATION_MODE
        )
        
        # Initialize Kafka consumer
        self.consumer = self._init_kafka_consumer()
        
        # Initialize Kafka producer
        self.producer = self._init_kafka_producer()
        
        # Database connection
        self.db_conn = self._init_database()
        
        # Phase 2: Initialize Vector Service for ChromaDB
        self.vector_kb = None
        if VECTOR_SERVICE_AVAILABLE:
            try:
                self.vector_kb = VectorKnowledgeBase(
                    chromadb_host=os.getenv('CHROMADB_HOST', 'chromadb'),
                    chromadb_port=int(os.getenv('CHROMADB_PORT', '8000'))
                )
                logger.info("✅ Vector KB initialized for remediation lessons storage")
            except Exception as e:
                logger.error(f"Failed to initialize Vector KB: {e}")
                self.vector_kb = None
        
        # Statistics
        self.stats = {
            'processed': 0,
            'succeeded': 0,
            'failed': 0,
            'escalated': 0,
            'total_resolution_time': 0.0
        }
        
        logger.success("✅ Remediation service initialized successfully")
    
    def _init_kafka_consumer(self) -> KafkaConsumer:
        """Initialize Kafka consumer"""
        logger.info(f"Connecting to Kafka: {settings.KAFKA_BOOTSTRAP_SERVERS}")
        logger.info(f"Subscribing to topic: {settings.KAFKA_CONSUME_TOPIC}")
        
        consumer = KafkaConsumer(
            settings.KAFKA_CONSUME_TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_ID,
            auto_offset_reset='latest',
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        
        logger.success("✅ Kafka consumer initialized")
        return consumer
    
    def _init_kafka_producer(self) -> KafkaProducer:
        """Initialize Kafka producer"""
        producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3
        )
        
        logger.success("✅ Kafka producer initialized")
        return producer
    
    def _init_database(self):
        """Initialize PostgreSQL connection"""
        try:
            conn = psycopg2.connect(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                cursor_factory=RealDictCursor
            )
            logger.success("✅ Database connection established")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return None
    
    def _should_auto_execute(self, diagnosis: dict) -> bool:
        """Determine if we should auto-execute or require approval"""
        
        if not settings.ENABLE_AUTO_EXECUTION:
            return False
        
        # Check severity
        severity = diagnosis.get('severity', 'MEDIUM')
        if severity in ['HIGH', 'CRITICAL'] and settings.REQUIRE_APPROVAL_ABOVE_SEVERITY == severity:
            logger.info(f"Severity {severity} requires approval")
            return False
        
        # Check confidence
        confidence = diagnosis.get('confidence', 0.0)
        if confidence < 0.6:
            logger.info(f"Confidence {confidence} too low for auto-execution")
            return False
        
        return True
    
    def _save_remediation_result(self, result: dict):
        """Save remediation result to database"""
        if not self.db_conn:
            return
        
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO remediation_executions (
                        incident_id,
                        incident_number,
                        success,
                        actions_taken,
                        resolution_time_seconds,
                        final_phase,
                        lessons_learned,
                        executed_at
                    ) VALUES (
                        %(incident_id)s,
                        %(incident_number)s,
                        %(success)s,
                        %(actions_taken)s,
                        %(resolution_time)s,
                        %(final_phase)s,
                        %(lessons_learned)s,
                        NOW()
                    )
                """, {
                    'incident_id': result.get('incident_id', ''),
                    'incident_number': result['incident_number'],
                    'success': result['success'],
                    'actions_taken': result.get('actions_taken', 0),
                    'resolution_time': result.get('resolution_time', 0.0),
                    'final_phase': result.get('final_phase', 'unknown'),
                    'lessons_learned': result.get('lessons_learned', '')
                })
                
                self.db_conn.commit()
                logger.debug(f"Remediation result saved to database")
                
                # Phase 2: Also save to ChromaDB for semantic search
                if result['success'] and result.get('lessons_learned'):
                    self._save_to_chromadb(result)
                
        except Exception as e:
            logger.error(f"Failed to save remediation result: {e}")
            self.db_conn.rollback()
    
    def _save_to_chromadb(self, result: dict):
        """Save remediation lessons to ChromaDB for semantic search (Phase 2)"""
        if not self.vector_kb:
            return
        
        try:
            # Build document text for semantic search
            incident_type = result.get('incident_type', 'UNKNOWN')
            device = result.get('device', 'unknown')
            actions = result.get('actions_summary', 'actions taken')
            resolution_time = result.get('resolution_time', 0.0)
            lessons = result.get('lessons_learned', '')
            
            document_text = f"""
Incident Type: {incident_type}
Device: {device}
Actions: {actions}
Resolution Time: {resolution_time:.1f}s
Lesson: {lessons}
""".strip()
            
            # Generate unique ID
            doc_id = f"remediation_{result['incident_number']}_{int(time.time())}"
            
            # Store in ChromaDB remediation_commands collection
            embedding = self.vector_kb.model.encode(document_text).tolist()
            
            self.vector_kb.commands.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[{
                    'incident_type': incident_type,
                    'incident_number': str(result['incident_number']),
                    'device': device,
                    'success': True,
                    'resolution_time_seconds': float(resolution_time),
                    'actions_count': result.get('actions_taken', 0),
                    'stored_at': time.strftime('%Y-%m-%d %H:%M:%S')
                }],
                documents=[document_text]
            )
            
            logger.info(f"✅ Saved remediation lesson to ChromaDB: {doc_id}")
            
        except Exception as e:
            logger.error(f"Failed to save to ChromaDB: {e}")
    
    def _publish_result(self, result: dict):
        """Publish remediation result to Kafka"""
        try:
            self.producer.send(
                settings.KAFKA_PRODUCE_TOPIC,
                value=result
            )
            self.producer.flush()
            logger.debug(f"Result published to {settings.KAFKA_PRODUCE_TOPIC}")
        except Exception as e:
            logger.error(f"Failed to publish result: {e}")
    
    def process_diagnosis(self, message: dict) -> bool:
        """Process a single diagnosed incident"""
        
        # Handle both nested and flattened message formats
        if 'incident' in message and 'diagnosis' in message:
            # Nested format
            incident = message.get('incident', {})
            diagnosis = message.get('diagnosis', {})
        else:
            # Flattened format from llm-diagnosis
            incident = message
            diagnosis = {
                'confidence': message.get('root_cause_confidence', 0.0),
                'root_cause': message.get('root_cause', ''),
                'remediation_plan': message.get('remediation_plan', []),
                'remediation_commands': message.get('remediation_commands', [])
            }
        
        incident_number = incident.get('incident_number', 'unknown')
        
        logger.info("=" * 80)
        logger.info(f"📋 Processing incident #{incident_number}")
        logger.info(f"Type: {incident.get('incident_type', 'UNKNOWN')}")
        logger.info(f"Confidence: {diagnosis.get('confidence', 0.0):.2f}")
        logger.info("=" * 80)
        
        try:
            # Check if we should auto-execute
            if not self._should_auto_execute(diagnosis):
                logger.warning("⏸️  Auto-execution disabled, would require approval")
                return True  # Commit offset anyway
            
            # Run autonomous remediation
            logger.info("🚀 Starting autonomous remediation...")
            result = self.agent.remediate(incident, diagnosis)
            
            # Update statistics
            self.stats['processed'] += 1
            if result['success']:
                self.stats['succeeded'] += 1
                logger.success(f"✅ Remediation succeeded in {result.get('resolution_time', 0):.1f}s")
            elif result.get('final_phase') == 'escalated':
                self.stats['escalated'] += 1
                logger.warning("⚠️  Incident escalated to human")
            else:
                self.stats['failed'] += 1
                logger.error("❌ Remediation failed")
            
            self.stats['total_resolution_time'] += result.get('resolution_time', 0.0)
            
            # Save to database
            result['incident_id'] = incident.get('incident_id')
            self._save_remediation_result(result)
            
            # Publish result
            self._publish_result(result)
            
            # Log statistics every 10 incidents
            if self.stats['processed'] % 10 == 0:
                avg_time = self.stats['total_resolution_time'] / self.stats['processed'] if self.stats['processed'] > 0 else 0
                logger.info(
                    f"📊 Stats: Processed={self.stats['processed']}, "
                    f"Succeeded={self.stats['succeeded']}, "
                    f"Failed={self.stats['failed']}, "
                    f"Escalated={self.stats['escalated']}, "
                    f"Avg Time={avg_time:.1f}s"
                )
            
            return True  # Commit offset
            
        except Exception as e:
            logger.error(f"Error processing incident #{incident_number}: {e}", exc_info=True)
            self.stats['failed'] += 1
            return True  # Commit offset to avoid retry loop
    
    def run(self):
        """Main service loop"""
        logger.success("🚀 Remediation Agent Service running!")
        logger.info(f"Waiting for diagnosed incidents on {settings.KAFKA_CONSUME_TOPIC}...")
        
        try:
            for message in self.consumer:
                try:
                    # Process diagnosis
                    should_commit = self.process_diagnosis(message.value)
                    
                    # Commit offset if successful
                    if should_commit:
                        self.consumer.commit()
                    
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    self.consumer.commit()  # Commit to avoid retry loop
                    
        except KeyboardInterrupt:
            logger.info("Received shutdown signal, closing gracefully...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources...")
        
        if self.consumer:
            self.consumer.close()
        
        if self.producer:
            self.producer.close()
        
        if self.db_conn:
            self.db_conn.close()
        
        logger.info("Cleanup complete")


def main():
    """Entry point"""
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Check required env vars
    if not settings.GROQ_API_KEY:
        logger.error("GROQ_API_KEY not set!")
        sys.exit(1)
    
    # Start service
    service = RemediationService()
    service.run()


if __name__ == "__main__":
    main()
