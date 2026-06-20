#!/bin/bash
# Verification script for Smart NOC pipeline

echo "========================================="
echo "SMART NOC PIPELINE VERIFICATION"
echo "========================================="

echo ""
echo "1. KAFKA STATUS"
echo "----------------------------------------"
echo "Total messages in Kafka:"
docker exec smart-noc-kafka /opt/kafka/bin/kafka-run-class.sh kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic network-logs 2>/dev/null | awk -F ":" '{sum += $3} END {print sum " messages"}'

echo ""
echo "2. LOGSTASH CONSUMER STATUS"
echo "----------------------------------------"
docker exec smart-noc-kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group logstash-consumer \
  --describe 2>/dev/null | grep network-logs

echo ""
echo "3. ELASTICSEARCH STATUS"
echo "----------------------------------------"
echo "Documents in Elasticsearch:"
curl -s 'http://localhost:9200/network-logs-*/_count' | jq -r '.count + " documents"'

echo ""
echo "Log Enrichment Breakdown:"
curl -s 'http://localhost:9200/network-logs-*/_search?size=0' \
  -H 'Content-Type: application/json' \
  -d '{"aggs":{"by_criticality":{"terms":{"field":"criticality.keyword"}},"by_role":{"terms":{"field":"device_role.keyword"}},"by_event":{"terms":{"field":"event_type.keyword","size":5}}}}' \
  | jq '.aggregations'

echo ""
echo "4. SAMPLE ENRICHED LOG"
echo "----------------------------------------"
curl -s 'http://localhost:9200/network-logs-*/_search?size=1&sort=@timestamp:desc' \
  | jq '.hits.hits[0]._source | {
      original_device: .device_id,
      enriched_role: .device_role,
      enriched_criticality: .criticality,
      enriched_tags: .tags,
      extracted_link_state: .link_state,
      fingerprint: .event_fingerprint[0:16]
    }'

echo ""
echo "========================================="
echo "VERIFICATION COMPLETE"
echo "========================================="
