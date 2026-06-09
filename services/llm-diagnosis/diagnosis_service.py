"""
LLM Diagnosis Service - Main Service
Phase 4: AI-Powered Root Cause Analysis and Remediation

Consumes incidents from Kafka, generates LLM diagnosis, updates PostgreSQL
"""

import sys
import json
import time
import signal
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from confluent_kafka import Consumer, Producer, KafkaError, TopicPartition
from sqlalchemy import create_engine, text, bindparam
from sqlalchemy.orm import sessionmaker
from loguru import logger

import config
from llm_client import LLMClient
from context_builder import ContextBuilder
from confidence_calibrator import ConfidenceCalibrator
from prompts.system_prompts import SYSTEM_PROMPT, get_prompt_template


class DiagnosisService:
    """Main LLM Diagnosis Service"""
    
    def __init__(self):
        # Configure logging
        logger.remove()
        if config.LOG_FORMAT == 'json':
            logger.add(
                sys.stderr,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
                level=config.LOG_LEVEL
            )
        else:
            logger.add(sys.stderr, level=config.LOG_LEVEL)
        
        logger.info("=== Smart NOC LLM Diagnosis Service ===")
        logger.info(f"Provider: {config.LLM_PROVIDER}/{config.LLM_MODEL}")
        logger.info(f"Min Confidence: {config.DIAGNOSIS_MIN_CONFIDENCE}")
        
        # Validate configuration
        try:
            config.validate_config()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
        
        # Initialize components
        self.llm_client = LLMClient()
        self.context_builder = ContextBuilder()
        
        # Initialize database
        self.engine = create_engine(config.DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)
        
        # Initialize confidence calibrator
        try:
            self.calibrator = ConfidenceCalibrator(engine=self.engine)
            logger.info("✓ Confidence calibrator initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize calibrator: {e}, will use uncalibrated confidence")
            self.calibrator = None
        
        # Initialize Kafka
        self.consumer = self._create_consumer()
        self.producer = self._create_producer()
        
        # State
        self.running = True
        self.stats = {
            'processed': 0,
            'diagnosed': 0,
            'failed': 0,
            'skipped': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'start_time': time.time()
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.success("Diagnosis service initialized successfully")
    
    def _create_consumer(self) -> Consumer:
        """Create Kafka consumer using confluent-kafka (actively maintained, KRaft compatible)"""
        consumer_config = {
            'bootstrap.servers': config.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': config.KAFKA_CONSUMER_GROUP,
            'auto.offset.reset': config.KAFKA_AUTO_OFFSET_RESET,
            'enable.auto.commit': False,  # Manual commit to re-process "too recent" incidents
            'session.timeout.ms': 30000,
            'max.poll.interval.ms': 600000,  # 10 minutes (phi3 can take 5+ min per diagnosis)
        }
        
        consumer = Consumer(consumer_config)
        consumer.subscribe([config.KAFKA_INPUT_TOPIC])
        
        logger.info(f"✓ Kafka consumer created with confluent-kafka")
        logger.info(f"  Topic: {config.KAFKA_INPUT_TOPIC}")
        logger.info(f"  Group: {config.KAFKA_CONSUMER_GROUP}")
        logger.info(f"  Offset reset: {config.KAFKA_AUTO_OFFSET_RESET}")
        
        return consumer
    
    def _create_producer(self) -> Producer:
        """Create Kafka producer using confluent-kafka"""
        producer_config = {
            'bootstrap.servers': config.KAFKA_BOOTSTRAP_SERVERS,
            'compression.type': 'gzip',
            'linger.ms': 10,
        }
        
        producer = Producer(producer_config)
        logger.info(f"✓ Kafka producer created: {config.KAFKA_OUTPUT_TOPIC}")
        return producer
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.warning(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def run(self):
        """Main service loop - EXACT COPY of correlation-engine pattern"""
        logger.success("Diagnosis Service running!")
        logger.info(f"Consuming from: {config.KAFKA_INPUT_TOPIC}")
        logger.info(f"Publishing to: {config.KAFKA_OUTPUT_TOPIC}")
        
        try:
            while self.running:
                # Process incidents from Kafka (matching correlation-engine pattern)
                self._process_incidents_from_kafka()
                
                # Log statistics periodically
                if self.stats['processed'] > 0 and self.stats['processed'] % 10 == 0:
                    self._log_statistics()
                
                time.sleep(0.1)  # Brief pause between polls (100ms for faster retries)
        
        except Exception as e:
            logger.error(f"Service error: {e}")
            raise
        finally:
            self._cleanup()
    
    def _process_incidents_from_kafka(self):
        """Process incoming incidents from Kafka using confluent-kafka API"""
        try:
            # Poll for a single message (confluent-kafka returns one message at a time)
            msg = self.consumer.poll(timeout=0.1)  # 100ms timeout
            
            if msg is None:
                # No message available
                return
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition - not an error
                    logger.debug(f"Reached end of partition {msg.partition()}")
                else:
                    logger.error(f"Kafka error: {msg.error()}")
                return
            
            # Successfully received a message
            try:
                incident = json.loads(msg.value().decode('utf-8'))
                
                if self.stats['processed'] == 0:
                    logger.success(f"🎉 FIRST MESSAGE RECEIVED! Processing incident...")
                
                self.stats['processed'] += 1
                logger.debug(f"Received incident: {incident.get('incident_id')} from partition {msg.partition()} offset {msg.offset()}")
                
                # Process the incident
                processed = self._process_incident(incident)
                
                # Only commit offset if incident was actually processed (not skipped as "too recent")
                if processed:
                    self.consumer.commit(msg)
                    logger.debug(f"Committed offset {msg.offset()} for incident {incident.get('incident_number')}")
                else:
                    # Don't commit - seek back to this offset so next poll returns the same message
                    logger.debug(f"Skipped commit for incident {incident.get('incident_number')}, seeking back to retry")
                    from confluent_kafka import TopicPartition
                    tp = TopicPartition(msg.topic(), msg.partition(), msg.offset())
                    self.consumer.seek(tp)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode incident message: {e}")
        
        except Exception as e:
            logger.error(f"Error processing incidents: {e}", exc_info=True)
    
    def _cleanup(self):
        """Cleanup resources"""
        logger.info("Service shutting down...")
        self.consumer.close()
        self.producer.close()
    
    def _is_already_diagnosed(self, incident_id: str) -> bool:
        """Check if incident already has diagnosis in database"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT root_cause FROM incidents WHERE id = :incident_id"),
                    {"incident_id": incident_id}
                ).fetchone()
                return result is not None and result[0] is not None
        except Exception as e:
            logger.error(f"Error checking diagnosis status: {e}")
            return False  # On error, assume not diagnosed to avoid skipping
    
    def _process_incident(self, incident: Dict[str, Any]):
        """Process a single incident"""
        incident_number = incident.get('incident_number', 'unknown')
        incident_id = incident.get('id')
        
        try:
            logger.info(f"Processing incident #{incident_number}")
            
            # Check if already diagnosed (must check database, not Kafka message)
            if self._is_already_diagnosed(incident_id):
                logger.debug(f"Incident #{incident_number} already has diagnosis, skipping")
                self.stats['skipped'] += 1
                return True  # Return True so offset gets committed (don't re-process diagnosed incidents)
            
            # Check if incident is too recent (avoid diagnosing before fully correlated)
            if config.DIAGNOSIS_DELAY_SECONDS > 0:
                created_at = incident.get('created_at')
                if created_at:
                    try:
                        created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        age_seconds = (datetime.utcnow() - created_time.replace(tzinfo=None)).total_seconds()
                        if age_seconds < config.DIAGNOSIS_DELAY_SECONDS:
                            logger.debug(f"Incident #{incident_number} too recent ({age_seconds:.0f}s), will retry")
                            self.stats['skipped'] += 1
                            return False  # Return False so offset is NOT committed (message will be re-delivered)
                    except:
                        pass
            
            # Build context
            logger.debug("Building context...")
            context = self.context_builder.build_context(incident)
            
            # Generate diagnosis
            logger.debug("Generating diagnosis...")
            diagnosis_result = self._generate_diagnosis(incident, context)
            
            if not diagnosis_result:
                logger.warning(f"Diagnosis failed for incident #{incident_number}")
                self.stats['failed'] += 1
                return True  # Commit offset for generation failure
            
            diagnosis, metadata = diagnosis_result
            
            # Validate diagnosis
            if not self.llm_client.validate_diagnosis(diagnosis):
                logger.warning(f"Diagnosis validation failed for incident #{incident_number}")
                self.stats['failed'] += 1
                return True  # Commit offset for failed validation
            
            # Calibrate confidence score based on historical accuracy
            raw_confidence = diagnosis.get('confidence', 0.0)
            incident_type = incident.get('incident_type', 'UNKNOWN')
            
            if self.calibrator:
                calibrated_confidence, calibration_method = self.calibrator.calibrate(
                    raw_confidence,
                    incident_type
                )
                diagnosis['calibrated_confidence'] = calibrated_confidence
                diagnosis['raw_confidence'] = raw_confidence
                diagnosis['calibration_method'] = calibration_method
                
                logger.info(
                    f"📊 Confidence Calibration: "
                    f"{raw_confidence:.3f} → {calibrated_confidence:.3f} "
                    f"({calibration_method})"
                )
            else:
                # No calibrator available, use raw confidence
                diagnosis['calibrated_confidence'] = raw_confidence
                diagnosis['raw_confidence'] = raw_confidence
                diagnosis['calibration_method'] = 'uncalibrated'
            
            # Update database
            logger.debug("Updating database...")
            self._update_incident_diagnosis(incident, incident_id, diagnosis, metadata)
            
            # Publish enriched incident
            logger.debug("Publishing to Kafka...")
            self._publish_diagnosis(incident, diagnosis, metadata)
            
            self.stats['diagnosed'] += 1
            self.stats['total_tokens'] += metadata.get('total_tokens', 0)
            self.stats['total_cost'] += metadata.get('estimated_cost_usd', 0.0)
            
            # Enhanced logging for diagnosis details
            logger.info("=" * 80)
            logger.success(f"✅ INCIDENT #{incident_number} DIAGNOSIS COMPLETE")
            logger.info("=" * 80)
            logger.info(f"📊 INCIDENT TYPE: {incident.get('incident_type', 'UNKNOWN')}")
            logger.info(f"🎯 SEVERITY: {incident.get('severity', 'N/A')}")
            logger.info(f"🖥️  AFFECTED DEVICES: {', '.join(incident.get('affected_devices', []))}")
            logger.info(f"📈 RAW CONFIDENCE: {diagnosis.get('raw_confidence', 0):.2f}")
            logger.info(f"📊 CALIBRATED CONFIDENCE: {diagnosis.get('calibrated_confidence', 0):.2f} ({diagnosis.get('calibration_method', 'unknown')})")
            logger.info("-" * 80)
            
            # Log Chain-of-Thought reasoning
            reasoning = diagnosis.get('reasoning', '')
            if reasoning:
                logger.info("🧠 CHAIN-OF-THOUGHT REASONING:")
                # Format reasoning for better readability
                for line in reasoning.split('\n'):
                    if line.strip():
                        logger.info(f"   {line.strip()}")
                logger.info("-" * 80)
            
            logger.info("🔍 ROOT CAUSE:")
            logger.info(f"   {diagnosis.get('root_cause', 'Unknown')}")
            logger.info("-" * 80)
            
            # Log remediation plan if present
            remediation_plan = diagnosis.get('remediation_plan', [])
            if remediation_plan:
                logger.info("🔧 REMEDIATION PLAN:")
                for i, step in enumerate(remediation_plan, 1):
                    if isinstance(step, dict):
                        logger.info(f"   Step {i}: {step.get('action', 'N/A')}")
                        logger.info(f"           {step.get('description', '')}")
                    elif isinstance(step, str):
                        logger.info(f"   Step {i}: {step}")
                logger.info("-" * 80)
            
            # Log KB articles used
            kb_articles = context.get('vector_kb_articles', '')
            if kb_articles and 'KB Article' in kb_articles:
                logger.info("📚 KNOWLEDGE BASE ARTICLES USED:")
                for line in kb_articles.split('\n')[:10]:  # Show first 10 lines
                    if line.strip() and ('KB Article' in line or 'EXT-' in line or 'relevance' in line.lower()):
                        logger.info(f"   {line.strip()}")
                logger.info("-" * 80)
            
            logger.info(f"⏱️  LLM Tokens: {metadata.get('total_tokens', 0)}, Cost: ${metadata.get('estimated_cost_usd', 0):.4f}")
            logger.info("=" * 80)
            
            return True  # Commit offset for successful diagnosis
            
        except Exception as e:
            logger.error(f"Error processing incident #{incident_number}: {e}", exc_info=True)
            self.stats['failed'] += 1
            return True  # Commit offset for errors (don't retry failed incidents indefinitely)
    
    def _generate_diagnosis(
        self, 
        incident: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Optional[tuple]:
        """Generate diagnosis using LLM"""
        incident_type = incident.get('incident_type', 'UNKNOWN')
        
        # Get prompt template for incident type
        user_prompt_template = get_prompt_template(incident_type)
        
        # Format user message with context
        user_message = user_prompt_template.format(
            incident_number=incident.get('incident_number', 'N/A'),
            primary_device=incident.get('primary_device', 'N/A'),
            affected_devices=', '.join(incident.get('affected_devices', [])),
            affected_device_count=incident.get('affected_device_count', 0),
            severity=incident.get('severity', 'N/A'),
            anomaly_count=incident.get('anomaly_count', 0),
            impact_score=incident.get('impact_score', 0.0),
            start_time=incident.get('start_time', 'N/A'),
            end_time=incident.get('end_time', 'N/A'),
            correlation_method=incident.get('correlation_method', 'N/A'),
            anomalies_summary=context.get('anomaly_summary', 'No anomalies'),
            anomaly_types=context.get('anomaly_types_distribution', 'N/A'),
            device_history=context.get('device_history', 'No history'),
            historical_incidents=context.get('similar_incidents', 'No similar incidents'),
            remediation_lessons=context.get('remediation_lessons', 'No remediation history yet'),  # Phase 1
            temporal_pattern=context.get('temporal_pattern', 'N/A'),
            # Week 2: Vector search results from semantic similarity
            vector_similar_incidents=context.get('vector_similar_incidents', ''),
            vector_kb_articles=context.get('vector_kb_articles', ''),
            # Additional fields for specific templates
            primary_anomaly_type=incident.get('primary_anomaly_type', 'N/A'),
            duration_minutes=(incident.get('duration_seconds', 0) / 60) if incident.get('duration_seconds') else 'N/A',
            device_relationships='N/A',  # TODO: Add topology context
            recent_configuration_changes='None detected',
            source_ip_summary='N/A',
            attack_pattern='N/A',
            security_history='N/A',
            topology_context='N/A',
            redundancy_status='N/A',
        )
        
        # Generate diagnosis
        try:
            diagnosis, metadata = self.llm_client.generate_diagnosis(SYSTEM_PROMPT, user_message)
            return (diagnosis, metadata)
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return None
    
    def _update_incident_diagnosis(
        self,
        incident: Dict[str, Any],
        incident_id: str, 
        diagnosis: Dict[str, Any],
        metadata: Dict[str, Any]
    ):
        """Update incidents table with diagnosis"""
        try:
            logger.debug(f"Diagnosis type: {type(diagnosis)}, keys: {list(diagnosis.keys()) if isinstance(diagnosis, dict) else 'NOT A DICT'}")
            logger.debug(f"Remediation plan type: {type(diagnosis.get('remediation_plan'))}")
            
            remediation = diagnosis.get('remediation_plan', [])
            remediation_json = json.dumps(remediation) if isinstance(remediation, (list, dict)) else json.dumps([])
            
            params = {
                'incident_id': incident_id,
                'root_cause': diagnosis.get('root_cause', ''),
                'confidence': diagnosis.get('calibrated_confidence', 0.0),  # Use calibrated confidence
                'remediation_plan': remediation_json,
                'llm_model': config.LLM_MODEL,
                'diagnosis_metadata': json.dumps(metadata)
            }
            logger.debug(f"SQL params keys: {list(params.keys())}")
            
            with self.Session() as session:
                # Update main incidents table (only columns that exist in schema)
                # remediation_plan is TEXT column, reasoning stored in incident_metadata
                try:
                    # Prepare incident metadata with reasoning and calibration info
                    incident_metadata = {
                        'reasoning': diagnosis.get('reasoning', ''),
                        'llm_model': config.LLM_MODEL,
                        'llm_metadata': metadata,
                        'affected_components': diagnosis.get('affected_components', []),
                        'escalation_needed': diagnosis.get('escalation_needed', False),
                        'estimated_resolution_minutes': diagnosis.get('estimated_resolution_minutes'),
                        'raw_confidence': diagnosis.get('raw_confidence', 0.0),
                        'calibrated_confidence': diagnosis.get('calibrated_confidence', 0.0),
                        'calibration_method': diagnosis.get('calibration_method', 'uncalibrated')
                    }
                    
                    session.execute(
                        text("""
                            UPDATE incidents
                            SET root_cause = :root_cause,
                                remediation_plan = :remediation_plan,
                                incident_metadata = COALESCE(incident_metadata, '{}'::jsonb) || CAST(:metadata AS jsonb),
                                updated_at = NOW()
                            WHERE id = CAST(:incident_id AS uuid)
                        """),
                        {
                            'incident_id': incident_id,
                            'root_cause': diagnosis.get('root_cause', ''),
                            'remediation_plan': remediation_json,
                            'metadata': json.dumps(incident_metadata)
                        }
                    )
                    logger.debug("✓ Incidents table updated (with reasoning in metadata)")
                except Exception as e:
                    logger.error(f"Failed to update incidents table: {e}")
                    raise
                
                # Insert into diagnosis history using CAST syntax                try:
                    session.execute(
                        text("""
                            INSERT INTO incident_diagnosis_history (
                                incident_id, diagnosis_version, root_cause, root_cause_confidence,
                                remediation_plan, llm_model, tokens_used,
                                diagnosis_duration_ms, diagnosis_metadata
                            )
                            VALUES (
                                CAST(:incident_id AS uuid), 
                                COALESCE((SELECT MAX(diagnosis_version) + 1 FROM incident_diagnosis_history WHERE incident_id = CAST(:incident_id AS uuid)), 1),
                                :root_cause, :confidence, CAST(:remediation_plan AS jsonb), :llm_model,
                                :tokens_used, :duration_ms, CAST(:diagnosis_metadata AS jsonb)
                            )
                        """),
                        {
                            'incident_id': incident_id,
                            'root_cause': diagnosis.get('root_cause', ''),
                            'confidence': diagnosis.get('calibrated_confidence', 0.0),  # Use calibrated confidence
                            'remediation_plan': remediation_json,
                            'llm_model': config.LLM_MODEL,
                            'tokens_used': metadata.get('total_tokens', 0),
                            'duration_ms': metadata.get('duration_ms', 0),
                            'diagnosis_metadata': json.dumps(metadata)
                        }
                    )
                    logger.debug("✓ History table updated")
                except Exception as e:
                    logger.error(f"Failed to insert into history table: {e}")
                    raise
                
                session.commit()
                logger.debug(f"Updated database for incident {incident_id}")
                
                # AUTO-LEARNING: Store this diagnosis in ChromaDB for future incident similarity search
                try:
                    self._store_in_vector_db(incident, diagnosis)
                except Exception as ve:
                    logger.warning(f"Failed to store in vector DB (non-critical): {ve}")
                
        except Exception as e:
            logger.error(f"Database update error: {e}", exc_info=True)
            raise
    
    def _store_in_vector_db(
        self,
        incident: Dict[str, Any],
        diagnosis: Dict[str, Any]
    ):
        """
        Store diagnosed incident in ChromaDB for future similarity search
        
        This creates the learning loop:
        1. Incident gets diagnosed
        2. Store diagnosis in ChromaDB with embeddings
        3. Future similar incidents will find this case
        4. LLM learns from past resolutions
        
        Args:
            incident: Incident data
            diagnosis: Diagnosis results with root cause and remediation
        """
        if not self.context_builder.vector_kb:
            return
        
        try:
            # Create searchable text from incident and diagnosis
            incident_type = incident.get('incident_type', 'UNKNOWN')
            severity = incident.get('severity', 'MEDIUM')
            primary_device = incident.get('primary_device', 'unknown')
            anomaly_count = incident.get('anomaly_count', 0)
            root_cause = diagnosis.get('root_cause', '')
            
            # Format text for embedding
            search_text = f"""
Incident Type: {incident_type}
Severity: {severity}
Device: {primary_device}
Anomalies: {anomaly_count}
Root Cause: {root_cause}
            """.strip()
            
            # Create metadata
            metadata = {
                "incident_number": incident.get('incident_number'),
                "incident_type": incident_type,
                "severity": severity,
                "vendor": "cisco",  # Default, would extract from device type in real scenario
                "primary_device": primary_device,
                "anomaly_count": anomaly_count or 0,
                "duration_seconds": incident.get('duration_seconds', 0) or 0,
                "correlation_confidence": float(incident.get('correlation_confidence', 0.0) or 0.0),
                "impact_score": float(incident.get('impact_score', 0.0) or 0.0),
                "diagnosis_confidence": float(diagnosis.get('confidence', 0.0)),
                "root_cause": root_cause[:200],  # Truncate for metadata
            }
            
            # Store in ChromaDB
            incident_id = f"incident-{incident.get('incident_number')}"
            self.context_builder.vector_kb.incidents.add(
                ids=[incident_id],
                documents=[search_text],
                metadatas=[metadata]
            )
            
            logger.info(f"✓ Stored incident #{incident.get('incident_number')} in vector DB for future learning")
            
        except Exception as e:
            # Don't fail the diagnosis if vector storage fails
            logger.error(f"Failed to store in vector DB: {e}")
            raise
    
    def _publish_diagnosis(
        self,
        incident: Dict[str, Any],
        diagnosis: Dict[str, Any],
        metadata: Dict[str, Any]
    ):
        """Publish diagnosed incident to Kafka"""
        try:
            # Enrich incident with diagnosis
            enriched_incident = {
                **incident,
                'root_cause': diagnosis.get('root_cause', ''),
                'root_cause_confidence': diagnosis.get('confidence', 0.0),
                'remediation_plan': diagnosis.get('remediation_plan', []),
                'diagnosis_timestamp': datetime.utcnow().isoformat() + 'Z',
                'llm_model': config.LLM_MODEL,
                'diagnosis_metadata': metadata
            }
            
            # Publish using confluent-kafka API
            self.producer.produce(
                config.KAFKA_OUTPUT_TOPIC,
                value=json.dumps(enriched_incident).encode('utf-8'),
                callback=lambda err, msg: logger.error(f"Delivery failed: {err}") if err else None
            )
            self.producer.flush()
            
        except Exception as e:
            logger.error(f"Kafka publish error: {e}")
    
    def _log_statistics(self):
        """Log service statistics"""
        uptime = time.time() - self.stats['start_time']
        rate = self.stats['processed'] / max(uptime, 1) * 60  # per minute
        
        logger.info(
            f"Stats: Processed={self.stats['processed']}, "
            f"Diagnosed={self.stats['diagnosed']}, "
            f"Failed={self.stats['failed']}, "
            f"Skipped={self.stats['skipped']}, "
            f"Rate={rate:.2f}/min, "
            f"Tokens={self.stats['total_tokens']}, "
            f"Cost=${self.stats['total_cost']:.4f}"
        )
    
    def _shutdown(self):
        """Cleanup on shutdown"""
        logger.info("Shutting down diagnosis service...")
        
        self._log_statistics()
        
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()
        
        logger.success("Shutdown complete")


def main():
    """Entry point"""
    try:
        service = DiagnosisService()
        service.run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
