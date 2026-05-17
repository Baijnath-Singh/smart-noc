#!/usr/bin/env python3
"""Test consumer connectivity"""
import sys
print("Starting consumer test...", flush=True)

from kafka import KafkaConsumer
print("Imported KafkaConsumer", flush=True)

try:
    print("Creating consumer with bootstrap_servers=kafka:9092...", flush=True)
    consumer = KafkaConsumer(
        'incidents',
        bootstrap_servers='kafka:9092',
        group_id='test-direct-consumer-xyz',
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda x: x.decode('utf-8')
    )
    print(f"Consumer created successfully: {consumer}", flush=True)
    print(f"Consumer subscribed to: {consumer.subscription()}", flush=True)
    
    print("Polling for 10 seconds...", flush=True)
    messages = consumer.poll(timeout_ms=10000, max_records=5)
    print(f"Poll completed. Received {sum(len(records) for records in messages.values())} messages", flush=True)
    
    for topic_partition, records in messages.items():
        print(f"Topic: {topic_partition.topic}, Partition: {topic_partition.partition}, Records: {len(records)}", flush=True)
        for record in records[:2]:  # Print first 2
            print(f"  Offset {record.offset}: {record.value[:100]}...", flush=True)
    
    consumer.close()
    print("Test completed successfully", flush=True)
except Exception as e:
    print(f"ERROR: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
