#!/usr/bin/env python3
"""Simple script to publish diagnosed incident to Kafka"""

import json
from kafka import KafkaProducer

incident_data = {
    "incident_number": 20013,
    "incident_type": "CONNECTIVITY_ISSUE",
    "severity": "HIGH",
    "primary_device": "core-sw-02",
    "affected_device_count": 2,
    "anomaly_count": 2,
    "root_cause": "INTERFACE_FLAPPING on GigabitEthernet1/0/10 of core-sw-02 and FastEthernet0/1 of edge-router-03, likely caused by physical layer issues such as faulty cables or transceivers",
    "created_at": "2026-06-11T21:26:31.746914",
    "updated_at": "2026-06-11T21:26:42.510665",
    "confidence": 0.40,
    "status": "DIAGNOSED",
    "resolution_steps": [
        "Check physical connections on GigabitEthernet1/0/10 (core-sw-02)",
        "Check physical connections on FastEthernet0/1 (edge-router-03)",
        "Replace suspect cables or transceivers",
        "Monitor interfaces for stability"
    ]
}

print(f"✅ Publishing incident #20013 to Kafka...")
print(f"   Type: {incident_data['incident_type']}")
print(f"   Root Cause: {incident_data['root_cause'][:80]}...")

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

producer.send('incidents-diagnosed', value=incident_data)
producer.flush()
producer.close()

print(f"✅ Published to incidents-diagnosed topic!")
print(f"   Check remediation agent logs in 5 seconds...")
