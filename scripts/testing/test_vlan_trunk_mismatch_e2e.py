#!/usr/bin/env python3
"""
End-to-End Test: VLAN Trunk Port Native VLAN Mismatch
Scenario: Two VOSS switches with inconsistent native VLAN causing connectivity issues

This test will:
1. Generate VLAN mismatch logs from two VOSS switches
2. Trigger anomaly detection
3. Correlate into VLAN_MISMATCH incident
4. Retrieve EXT-019 KB article via enhanced multi-query search
5. Generate diagnosis with root cause and remediation plan
"""
import json
import time
from datetime import datetime, timedelta
from kafka import KafkaProducer
import random

def send_vlan_mismatch_logs():
    """Send VLAN trunk native VLAN mismatch logs"""
    
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    # Scenario: Trunk link between voss-dist-01 and voss-dist-02
    # Port 1/20 is trunk link
    # voss-dist-01: Native VLAN 1
    # voss-dist-02: Native VLAN 10 (MISMATCH!)
    
    device1 = "voss-dist-switch-01"
    device2 = "voss-dist-switch-02"
    trunk_port_1 = "1/20"
    trunk_port_2 = "1/20"
    
    print("="*80)
    print("🔥 VLAN TRUNK NATIVE VLAN MISMATCH TEST")
    print("="*80)
    print(f"\n📋 Scenario:")
    print(f"   Device 1: {device1} (Native VLAN: 1)")
    print(f"   Device 2: {device2} (Native VLAN: 10)")
    print(f"   Trunk Port: {trunk_port_1} <--> {trunk_port_2}")
    print(f"   Issue: Native VLAN mismatch causing CDP/LLDP warnings and connectivity issues")
    print(f"\n⚠️  Expected Detection:")
    print(f"   - Event Type: VLAN_MISMATCH")
    print(f"   - Incident Type: CONNECTIVITY_ISSUE")
    print(f"   - KB Article: EXT-019 (VOSS VLAN Configuration and Trunking Issues)")
    print("\n" + "="*80)
    
    base_time = datetime.utcnow()
    
    # Event 1: CDP/LLDP Native VLAN mismatch warning on voss-dist-01
    print(f"\n[1/8] Sending: CDP native VLAN mismatch warning (voss-dist-01)")
    log1 = {
        "timestamp": base_time.isoformat() + "Z",
        "device_id": device1,
        "log_level": "WARNING",
        "message": f"CDP: Native VLAN mismatch discovered on port {trunk_port_1}, local VLAN 1, remote VLAN 10",
        "source": "cdp-protocol",
        "event_type": "VLAN_MISMATCH",
        "interface": trunk_port_1,
        "vendor": "extreme",
        "platform": "voss",
        "details": {
            "local_native_vlan": 1,
            "remote_native_vlan": 10,
            "remote_device": device2,
            "trunk_encapsulation": "dot1q"
        }
    }
    producer.send('network-logs', value=log1)
    time.sleep(2)
    
    # Event 2: Same warning from other side (voss-dist-02)
    print(f"[2/8] Sending: CDP native VLAN mismatch warning (voss-dist-02)")
    log2 = {
        "timestamp": (base_time + timedelta(seconds=5)).isoformat() + "Z",
        "device_id": device2,
        "log_level": "WARNING",
        "message": f"CDP: Native VLAN mismatch discovered on port {trunk_port_2}, local VLAN 10, remote VLAN 1",
        "source": "cdp-protocol",
        "event_type": "VLAN_MISMATCH",
        "interface": trunk_port_2,
        "vendor": "extreme",
        "platform": "voss",
        "details": {
            "local_native_vlan": 10,
            "remote_native_vlan": 1,
            "remote_device": device1,
            "trunk_encapsulation": "dot1q"
        }
    }
    producer.send('network-logs', value=log2)
    time.sleep(2)
    
    # Event 3: VLAN membership errors
    print(f"[3/8] Sending: VLAN membership inconsistency (voss-dist-01)")
    log3 = {
        "timestamp": (base_time + timedelta(seconds=15)).isoformat() + "Z",
        "device_id": device1,
        "log_level": "ERROR",
        "message": f"Port {trunk_port_1}: Received untagged frame on trunk with mismatched native VLAN",
        "source": "vlan-manager",
        "event_type": "VLAN_MISMATCH",
        "interface": trunk_port_1,
        "vendor": "extreme",
        "platform": "voss",
        "details": {
            "expected_vlan": 1,
            "received_vlan": 10,
            "frame_count": 1523
        }
    }
    producer.send('network-logs', value=log3)
    time.sleep(2)
    
    # Event 4: Connectivity issues - MAC learning problems
    print(f"[4/8] Sending: MAC address learning issues (voss-dist-01)")
    log4 = {
        "timestamp": (base_time + timedelta(seconds=25)).isoformat() + "Z",
        "device_id": device1,
        "log_level": "WARNING",
        "message": f"MAC table: Inconsistent MAC learning on trunk {trunk_port_1}, addresses appearing in wrong VLAN",
        "source": "mac-manager",
        "event_type": "MAC_LEARNING_ISSUE",
        "interface": trunk_port_1,
        "vendor": "extreme",
        "platform": "voss",
        "details": {
            "macs_in_vlan_1": 45,
            "macs_in_vlan_10": 23,
            "flapping_macs": 12
        }
    }
    producer.send('network-logs', value=log4)
    time.sleep(2)
    
    # Event 5: STP issues due to VLAN mismatch
    print(f"[5/8] Sending: STP topology inconsistency (voss-dist-02)")
    log5 = {
        "timestamp": (base_time + timedelta(seconds=35)).isoformat() + "Z",
        "device_id": device2,
        "log_level": "WARNING",
        "message": f"STP: Inconsistent STP topology detected on port {trunk_port_2}, native VLAN mismatch may cause STP issues",
        "source": "stp-manager",
        "event_type": "STP_INCONSISTENCY",
        "interface": trunk_port_2,
        "vendor": "extreme",
        "platform": "voss",
        "details": {
            "stp_state": "forwarding",
            "native_vlan_local": 10,
            "native_vlan_remote": 1
        }
    }
    producer.send('network-logs', value=log5)
    time.sleep(2)
    
    # Event 6: User connectivity complaints - ping failures
    print(f"[6/8] Sending: Connectivity failure VLAN 10 (voss-dist-01)")
    log6 = {
        "timestamp": (base_time + timedelta(seconds=45)).isoformat() + "Z",
        "device_id": device1,
        "log_level": "ERROR",
        "message": "VLAN 10: Inter-switch connectivity failure, untagged traffic not reaching remote switch",
        "source": "monitoring",
        "event_type": "CONNECTIVITY_FAILURE",
        "vendor": "extreme",
        "platform": "voss",
        "details": {
            "affected_vlan": 10,
            "trunk_port": trunk_port_1,
            "ping_loss": "100%",
            "remote_device": device2
        }
    }
    producer.send('network-logs', value=log6)
    time.sleep(2)
    
    # Event 7: Traffic dropping on mismatched VLAN
    print(f"[7/8] Sending: Traffic drops on trunk (voss-dist-02)")
    log7 = {
        "timestamp": (base_time + timedelta(seconds=55)).isoformat() + "Z",
        "device_id": device2,
        "log_level": "ERROR",
        "message": f"Port {trunk_port_2}: Dropping untagged frames due to native VLAN mismatch (expected VLAN 10, received as VLAN 1)",
        "source": "port-manager",
        "event_type": "TRAFFIC_DROP",
        "interface": trunk_port_2,
        "vendor": "extreme",
        "platform": "voss",
        "details": {
            "dropped_frames": 5234,
            "error_type": "native_vlan_mismatch"
        }
    }
    producer.send('network-logs', value=log7)
    time.sleep(2)
    
    # Event 8: Configuration audit failure
    print(f"[8/8] Sending: Configuration inconsistency alert (monitoring system)")
    log8 = {
        "timestamp": (base_time + timedelta(seconds=65)).isoformat() + "Z",
        "device_id": "monitoring-server",
        "log_level": "CRITICAL",
        "message": f"Network audit: Trunk link {device1}:{trunk_port_1} <-> {device2}:{trunk_port_2} has native VLAN mismatch (1 vs 10)",
        "source": "config-audit",
        "event_type": "CONFIG_MISMATCH",
        "vendor": "extreme",
        "platform": "voss",
        "details": {
            "device1": device1,
            "device1_native_vlan": 1,
            "device2": device2,
            "device2_native_vlan": 10,
            "severity": "high",
            "impact": "connectivity_loss"
        }
    }
    producer.send('network-logs', value=log8)
    
    producer.flush()
    
    print("\n" + "="*80)
    print("✅ Test logs sent successfully!")
    print("="*80)
    print(f"\n📊 Summary:")
    print(f"   Total Events: 8")
    print(f"   Devices: {device1}, {device2}")
    print(f"   Event Types: VLAN_MISMATCH (3), MAC_LEARNING_ISSUE (1), STP_INCONSISTENCY (1)")
    print(f"                CONNECTIVITY_FAILURE (1), TRAFFIC_DROP (1), CONFIG_MISMATCH (1)")
    print(f"\n⏱️  Processing Timeline:")
    print(f"   1. Anomaly Detector: ~5-10 seconds (rule-based detection)")
    print(f"   2. Correlation Engine: ~5 seconds (group related anomalies)")
    print(f"   3. LLM Diagnosis: ~10-15 seconds (multi-query KB search + LLM)")
    print(f"   → Total: ~20-30 seconds")
    print(f"\n🔍 Expected KB Article Match:")
    print(f"   Primary: EXT-019 - VOSS VLAN Configuration and Trunking Issues")
    print(f"   Relevance: 0.70-0.80 (enhanced multi-query search)")
    print(f"   Queries Matched: 3-5 (original, event-focused, vendor-focused, etc.)")
    print(f"\n🎯 Expected Diagnosis:")
    print(f"   Root Cause: Native VLAN mismatch on trunk link")
    print(f"   Affected Devices: voss-dist-switch-01 (VLAN 1), voss-dist-switch-02 (VLAN 10)")
    print(f"   Remediation: Configure consistent native VLAN on both switches")
    print(f"\n📋 Next Steps:")
    print(f"   Run the validation queries (see test output below)")
    print("="*80)

if __name__ == "__main__":
    try:
        send_vlan_mismatch_logs()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
