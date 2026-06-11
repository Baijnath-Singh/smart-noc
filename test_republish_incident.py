#!/usr/bin/env python3
"""Republish incident #20014 to trigger diagnosis with the fix"""

import json
from kafka import KafkaProducer

incident_data = {
    "incident_number": 20014,
    "incident_type": "UNKNOWN",
    "severity": "HIGH",
    "primary_device": "core-sw-02",
    "affected_device_count": 2,
    "anomaly_count": 2,
    "created_at": "2026-06-11T21:26:31.000000",
    "status": "ACTIVE"
}

print(f"📤 Publishing incident #20014 for diagnosis test...")

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

producer.send('incidents', value=incident_data)
producer.flush()
producer.close()

print(f"✅ Published! Check llm-diagnosis logs in ~10 seconds")
