#!/usr/bin/env python3
"""
Generate test logs for Extreme Networks EXOS interface flapping
to validate enhanced multi-query vector search
"""
import json
import time
from datetime import datetime
from kafka import KafkaProducer

def send_exos_flapping_logs():
    """Send EXOS interface flapping logs to Kafka"""
    
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    device_id = "exos-core-switch-01"
    interface = "ge.1.15"
    
    print(f"🔥 Generating EXOS interface flapping incident: {device_id} / {interface}")
    print("="*80)
    
    # Generate 8 flapping events (4 up/down cycles) over 2 minutes
    for i in range(8):
        state = "UP" if i % 2 == 0 else "DOWN"
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "device_id": device_id,
            "log_level": "WARNING" if state == "DOWN" else "INFO",
            "message": f"Interface {interface} state changed to {state}",
            "source": "interface-manager",
            "event_type": "INTERFACE_STATE_CHANGE",
            "interface": interface,
            "state": state,
            "vendor": "extreme",
            "platform": "exos",
            "details": {
                "previous_state": "DOWN" if state == "UP" else "UP",
                "link_speed": "1000Mbps",
                "duplex": "full",
                "admin_status": "enabled",
                "error_count": i * 5
            }
        }
        
        producer.send('network-logs', value=log_entry)
        print(f"  [{i+1}/8] {state:5s} - Interface {interface} @ {log_entry['timestamp']}")
        
        # Sleep between events
        time.sleep(2 if i < 7 else 0)
    
    producer.flush()
    
    print("\n✅ Test logs sent successfully!")
    print(f"   Device: {device_id}")
    print(f"   Interface: {interface}")
    print(f"   Platform: Extreme Networks EXOS")
    print(f"   Expected: INTERFACE_FLAPPING incident classified correctly")
    print(f"   Expected: Enhanced search to retrieve EXT-011 (EXOS SFP flapping) with high relevance")
    print("\n⏱️  Wait ~30 seconds for processing through:")
    print("   1. Anomaly Detector (rule-based)")
    print("   2. Correlation Engine")
    print("   3. LLM Diagnosis (with enhanced multi-query search)")

if __name__ == "__main__":
    send_exos_flapping_logs()
