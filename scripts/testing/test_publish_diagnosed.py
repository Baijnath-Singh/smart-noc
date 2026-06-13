#!/usr/bin/env python3
"""
Test script to manually publish diagnosed incident to Kafka
"""

import json
import psycopg2
from kafka import KafkaProducer

# Database connection
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="smart_noc",
    user="noc_admin",
    password="noc_password"
)

# Get incident from database
cur = conn.cursor()
cur.execute("""
    SELECT 
        incident_number,
        incident_type,
        severity,
        primary_device,
        affected_device_count,
        anomaly_count,
        root_cause,
        created_at,
        updated_at
    FROM incidents 
    WHERE incident_number = 20013
""")

row = cur.fetchone()
if not row:
    print("❌ Incident #20013 not found")
    exit(1)

# Build incident message
incident_data = {
    "incident_number": row[0],
    "incident_type": row[1],
    "severity": row[2],
    "primary_device": row[3],
    "affected_device_count": row[4],
    "anomaly_count": row[5],
    "root_cause": row[6],
    "created_at": row[7].isoformat() if row[7] else None,
    "updated_at": row[8].isoformat() if row[8] else None,
    "confidence": 0.40,  # From logs
    "status": "DIAGNOSED"
}

print(f"✅ Loaded incident #20013 from database")
print(f"   Type: {incident_data['incident_type']}")
print(f"   Root Cause: {incident_data['root_cause'][:100]}...")

# Publish to Kafka
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

producer.send('incidents-diagnosed', value=incident_data)
producer.flush()

print(f"✅ Published incident #20013 to incidents-diagnosed topic")
print(f"   Waiting for remediation agent to process...")

cur.close()
conn.close()
producer.close()
