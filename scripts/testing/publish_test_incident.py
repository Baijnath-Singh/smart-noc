#!/usr/bin/env python3
"""
Publish diagnosed incident #10000 to Kafka for remediation testing
"""
import json
from kafka import KafkaProducer

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = 'localhost:19092'
KAFKA_TOPIC = 'incidents-diagnosed'

# Create incident message
incident_message = {
    'incident_number': 10000,
    'incident_type': 'INTERFACE_FLAPPING',
    'severity': 'MEDIUM',
    'primary_device': 'core-router-01',
    'device': 'core-router-01',
    'affected_devices': ['core-router-01'],
    'root_cause': 'Interface flapping on core-router-01 GigabitEthernet0/1 due to faulty SFP module',
    'remediation_plan': [
        {
            'step': 1,
            'action': 'clear_interface_counters',
            'device': 'core-router-01',
            'interface': 'GigabitEthernet0/1'
        },
        {
            'step': 2,
            'action': 'reload_interface',
            'device': 'core-router-01',
            'interface': 'GigabitEthernet0/1'
        }
    ],
    'root_cause_confidence': 0.85,
    'confidence': 0.85,
    'calibrated_confidence': 0.75,
    'confidence_reasoning': 'High confidence - multiple anomalies correlate to interface issues',
    'evidence_direct_count': 3,
    'evidence_indirect_count': 0
}

print(f"📤 Publishing incident #{incident_message['incident_number']} to Kafka topic '{KAFKA_TOPIC}'...")
print(f"   Type: {incident_message['incident_type']}")
print(f"   Severity: {incident_message['severity']}")
print(f"   Confidence: {incident_message['calibrated_confidence']}")

# Create Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Publish message
producer.send(KAFKA_TOPIC, value=incident_message)
producer.flush()

print(f"✅ Published to Kafka topic: {KAFKA_TOPIC}")
print(f"\n📊 Remediation-agent should now:")
print(f"   1. Receive the message from Kafka")
print(f"   2. Perform Safety Framework assessment")
print(f"   3. Execute LangGraph workflow if safe")
print(f"\n🔍 Monitor with:")
print(f"   docker-compose logs -f remediation-agent | grep '#10000'")

producer.close()
