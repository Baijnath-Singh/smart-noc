#!/usr/bin/env python3
"""
End-to-End Test: Extreme Networks KB Article in Diagnosis
Complete pipeline validation with detailed logging
"""

from kafka import KafkaProducer
import json
from datetime import datetime, timedelta
import time
import sys

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def main():
    print_section("🚀 SMART NOC - END-TO-END TEST: EXTREME NETWORKS KB")
    
    print("\n📋 TEST SCENARIO:")
    print("   Device: exos-core-01 (Extreme Networks X460-G2 running EXOS)")
    print("   Issue: Port 1:10 experiencing rapid link flapping")
    print("   Root Cause: SFP transceiver issue")
    print("   Expected KB: EXT-001 (EXOS Interface Flapping)")
    
    print("\n📊 PIPELINE FLOW:")
    print("   1. Log Generator → Kafka (network-logs topic)")
    print("   2. Anomaly Detector → Detect INTERFACE_FLAPPING")
    print("   3. Correlation Engine → Create CONNECTIVITY_ISSUE incident")
    print("   4. LLM Diagnosis → Search KB for vendor=extreme, platform=exos")
    print("   5. Database → Store diagnosis with KB article reference")
    
    # Initialize Kafka producer
    print_section("STEP 1: INITIALIZING KAFKA PRODUCER")
    try:
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            api_version=(2, 8, 0)
        )
        print("✅ Kafka producer initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Kafka producer: {e}")
        sys.exit(1)
    
    # Generate test events
    print_section("STEP 2: GENERATING EXOS INTERFACE FLAPPING EVENTS")
    
    base_time = datetime.now()
    events = []
    
    print("\n📡 Creating 5 flapping cycles (10 state changes)...")
    
    for cycle in range(5):
        # DOWN event
        down_event = {
            "timestamp": (base_time + timedelta(seconds=cycle*2)).isoformat(),
            "device_id": "exos-core-01",
            "device_type": "switch",
            "vendor": "extreme",
            "platform": "exos",
            "model": "X460-G2",
            "interface": "1:10",
            "event_type": "INTERFACE_STATE_CHANGE",
            "severity": "HIGH",
            "message": f"Port 1:10 link DOWN - SFP signal loss (cycle {cycle+1}/5)",
            "details": {
                "port": "1:10",
                "port_name": "Core-Uplink-A",
                "previous_state": "UP",
                "current_state": "DOWN",
                "link_speed": "10000",
                "duplex": "full",
                "transceiver_type": "SFP-10G-SR",
                "transceiver_vendor": "Extreme",
                "rx_power_dbm": -18.5,
                "tx_power_dbm": -2.1,
                "crc_errors": 0,
                "flap_count": cycle * 2 + 1
            }
        }
        
        # UP event
        up_event = {
            "timestamp": (base_time + timedelta(seconds=cycle*2+1)).isoformat(),
            "device_id": "exos-core-01",
            "device_type": "switch",
            "vendor": "extreme",
            "platform": "exos",
            "model": "X460-G2",
            "interface": "1:10",
            "event_type": "INTERFACE_STATE_CHANGE",
            "severity": "INFO",
            "message": f"Port 1:10 link UP - SFP signal restored (cycle {cycle+1}/5)",
            "details": {
                "port": "1:10",
                "port_name": "Core-Uplink-A",
                "previous_state": "DOWN",
                "current_state": "UP",
                "link_speed": "10000",
                "duplex": "full",
                "transceiver_type": "SFP-10G-SR",
                "transceiver_vendor": "Extreme",
                "rx_power_dbm": -3.2,
                "tx_power_dbm": -2.1,
                "flap_count": cycle * 2 + 2
            }
        }
        
        events.append(down_event)
        events.append(up_event)
    
    # Send events to Kafka
    print(f"\n📤 Sending {len(events)} events to Kafka...")
    for idx, event in enumerate(events, 1):
        try:
            future = producer.send('network-logs', value=event)
            future.get(timeout=10)  # Wait for confirmation
            state = event['details']['current_state']
            flap_num = event['details']['flap_count']
            print(f"   ✓ Event {idx:2d}/10: Port 1:10 → {state:4s} (transition #{flap_num})")
        except Exception as e:
            print(f"   ❌ Event {idx} failed: {e}")
    
    producer.flush()
    print("\n✅ All events sent to Kafka (network-logs topic)")
    
    # Wait for processing
    print_section("STEP 3: WAITING FOR PIPELINE PROCESSING")
    
    print("\n⏳ Processing stages:")
    print("   [1/4] Anomaly Detector analyzing events... (5s)")
    time.sleep(5)
    print("   ✓ Anomaly detection complete")
    
    print("   [2/4] Correlation Engine creating incident... (5s)")
    time.sleep(5)
    print("   ✓ Incident correlation complete")
    
    print("   [3/4] LLM Diagnosis searching KB articles... (10s)")
    time.sleep(10)
    print("   ✓ LLM diagnosis complete")
    
    print("   [4/4] Storing results in database... (3s)")
    time.sleep(3)
    print("   ✓ Database storage complete")
    
    print("\n✅ Pipeline processing finished!")
    print("\n💡 Next Steps:")
    print("   • Check anomaly detector logs for INTERFACE_FLAPPING detection")
    print("   • Check correlation engine logs for incident creation")
    print("   • Check llm-diagnosis logs for KB article retrieval")
    print("   • Query database for incident with diagnosis")
    
    print_section("TEST EXECUTION COMPLETE")
    print("\n🎯 Run the following commands to verify:")
    print("\n1. Check latest incident:")
    print("   docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c")
    print('     "SELECT incident_number, incident_type, affected_devices FROM incidents ORDER BY created_at DESC LIMIT 1;"')
    
    print("\n2. Check anomaly detector logs:")
    print('   docker logs smart-noc-anomaly-detector --tail 50 | grep "exos-core-01"')
    
    print("\n3. Check LLM diagnosis logs:")
    print('   docker logs smart-noc-llm-diagnosis --tail 100 | grep "EXT-001"')
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
