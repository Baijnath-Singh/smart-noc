#!/usr/bin/env python3
"""
Re-trigger LLM Diagnosis for Existing Incident
Publishes an undiagnosed incident to Kafka for the improved LLM system to process
"""

import sys
import json
import time
sys.path.insert(0, '/app')

from confluent_kafka import Producer
from sqlalchemy import create_engine, text
import config

def get_incident(incident_number: int):
    """Fetch incident from database"""
    engine = create_engine(config.DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT 
                    id::text,
                    incident_number,
                    incident_type,
                    severity,
                    status,
                    affected_device_count,
                    affected_devices::text,
                    primary_device,
                    anomaly_count,
                    start_time::text,
                    end_time::text,
                    duration_seconds,
                    correlation_method,
                    correlation_confidence,
                    impact_score,
                    incident_metadata::text,
                    created_at::text
                FROM incidents 
                WHERE incident_number = :incident_number
            """),
            {"incident_number": incident_number}
        ).fetchone()
    
    if not result:
        print(f"❌ Incident #{incident_number} not found")
        return None
    
    incident = {
        'id': result[0],
        'incident_number': result[1],
        'incident_type': result[2],
        'severity': result[3],
        'status': result[4],
        'affected_device_count': result[5],
        'affected_devices': json.loads(result[6]) if result[6] else [],
        'primary_device': result[7],
        'anomaly_count': result[8],
        'start_time': result[9],
        'end_time': result[10],
        'duration_seconds': result[11],
        'correlation_method': result[12],
        'correlation_confidence': float(result[13]) if result[13] else None,
        'impact_score': float(result[14]) if result[14] else None,
        'incident_metadata': json.loads(result[15]) if result[15] else {},
        'created_at': result[16]
    }
    
    return incident

def publish_to_kafka(incident: dict):
    """Publish incident to Kafka"""
    producer = Producer({
        'bootstrap.servers': config.KAFKA_BOOTSTRAP_SERVERS,
        'client.id': 'incident-republisher'
    })
    
    message = json.dumps(incident)
    
    producer.produce(
        'incidents',
        key=str(incident['incident_number']).encode('utf-8'),
        value=message.encode('utf-8'),
        callback=lambda err, msg: print(f"✅ Published to Kafka: {msg.topic()}") if not err else print(f"❌ Kafka error: {err}")
    )
    
    producer.flush()

def main():
    if len(sys.argv) > 1:
        incident_number = int(sys.argv[1])
    else:
        # Default to incident 65 (undiagnosed)
        incident_number = 65
    
    print(f"🔄 Re-triggering diagnosis for incident #{incident_number}...")
    print()
    
    # Fetch incident
    incident = get_incident(incident_number)
    if not incident:
        sys.exit(1)
    
    print(f"📋 Incident Details:")
    print(f"   Type: {incident['incident_type']}")
    print(f"   Severity: {incident['severity']}")
    print(f"   Devices: {incident['affected_device_count']}")
    print(f"   Anomalies: {incident['anomaly_count']}")
    print()
    
    # Publish to Kafka
    print(f"📤 Publishing to Kafka topic 'incidents'...")
    publish_to_kafka(incident)
    
    time.sleep(1)
    
    print()
    print("✅ Incident published to Kafka!")
    print()
    print("📊 The LLM diagnosis service will process it with:")
    print("   Layer 1: Confidence Reasoning (forces LLM to explain)")
    print("   Layer 2: Historical Feedback (shows past overconfidence)")
    print("   Layer 3: Calibration Mapping (final correction)")
    print()
    print("⏳ Diagnosis typically takes 30-60 seconds...")
    print()
    print("🔍 Monitor progress:")
    print(f"   docker-compose logs -f llm-diagnosis | grep -E '#{incident_number}|Confidence'")
    print()
    print("📈 Check results:")
    print(f"   docker-compose exec postgres psql -U noc_admin -d smart_noc -c \"SELECT * FROM confidence_analysis WHERE incident_number = {incident_number};\"")

if __name__ == '__main__':
    main()
