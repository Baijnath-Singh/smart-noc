#!/bin/bash
# Quick script to create all required Kafka topics

echo "Creating Kafka topics..."

docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic network-logs --partitions 3 --replication-factor 1 --if-not-exists
echo "✓ network-logs created"

docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic network-logs-enriched --partitions 3 --replication-factor 1 --if-not-exists
echo "✓ network-logs-enriched created (for enriched logs from Logstash)"

docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic anomalies --partitions 3 --replication-factor 1 --if-not-exists
echo "✓ anomalies created"

docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic incidents --partitions 3 --replication-factor 1 --if-not-exists
echo "✓ incidents created"

docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic incidents-diagnosed --partitions 3 --replication-factor 1 --if-not-exists
echo "✓ incidents-diagnosed created"

echo ""
echo "Verifying topics..."
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list

echo ""
echo "✅ All Kafka topics created successfully!"
