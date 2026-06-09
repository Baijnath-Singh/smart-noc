#!/usr/bin/env python3
"""
Test Extreme Networks KB Article Retrieval
Generate EXOS interface flapping scenario
"""

from kafka import KafkaProducer
import json
from datetime import datetime, timedelta
import time

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

print("="*70)
print("🧪 TESTING EXTREME NETWORKS KB ARTICLE RETRIEVAL")
print("="*70)
print("\n📡 Scenario: EXOS Interface Flapping")
print("   Device: exos-switch-01 (Extreme Networks X460-G2)")
print("   Issue: Port 1:5 rapidly flapping")
print("   Expected KB: EXT-001 (EXOS Interface Flapping)")

base_time = datetime.now()

# Generate 4 complete flapping cycles (8 state changes)
events_sent = 0
for i in range(4):
    # DOWN event
    down_event = {
        "timestamp": (base_time + timedelta(seconds=i*2)).isoformat(),
        "device_id": "exos-switch-01",
        "device_type": "switch",
        "vendor": "extreme",
        "platform": "exos",
        "model": "X460-G2",
        "interface": "1:5",
        "event_type": "INTERFACE_STATE_CHANGE",
        "severity": "HIGH",
        "message": f"Port 1:5 state changed to DOWN (transition {i*2+1}/8)",
        "details": {
            "port": "1:5",
            "previous_state": "UP",
            "current_state": "DOWN",
            "transceiver_type": "SFP-1G-SX"
        }
    }
    
    # UP event  
    up_event = {
        "timestamp": (base_time + timedelta(seconds=i*2+1)).isoformat(),
        "device_id": "exos-switch-01",
        "device_type": "switch",
        "vendor": "extreme",
        "platform": "exos",
        "model": "X460-G2",
        "interface": "1:5",
        "event_type": "INTERFACE_STATE_CHANGE",
        "severity": "INFO",
        "message": f"Port 1:5 state changed to UP (transition {i*2+2}/8)",
        "details": {
            "port": "1:5",
            "previous_state": "DOWN",
            "current_state": "UP",
            "transceiver_type": "SFP-1G-SX"
        }
    }
    
    producer.send('network-logs', value=down_event)
    producer.send('network-logs', value=up_event)
    events_sent += 2
    print(f"   ✓ Flap cycle {i+1}/4: DOWN → UP")
    time.sleep(0.2)

producer.flush()
print(f"\n✅ Sent {events_sent} events to Kafka (network-logs topic)")
print("\n⏳ Processing pipeline:")
print("   1. Anomaly Detector detects INTERFACE_FLAPPING")
print("   2. Correlation Engine creates CONNECTIVITY_ISSUE incident")
print("   3. LLM Diagnosis searches KB for vendor=extreme, platform=exos")
print("\n⏳ Waiting 20 seconds for diagnosis...")

time.sleep(20)
print("✅ Processing should be complete!")
