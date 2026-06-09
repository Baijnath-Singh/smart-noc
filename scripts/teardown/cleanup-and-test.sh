#!/bin/bash
# Smart NOC - Complete Cleanup and Fresh Test
# This script performs a full cleanup and generates a fresh test incident

set -e  # Exit on error

echo "🧹 Smart NOC - Complete Cleanup & Fresh Test"
echo "============================================="
echo ""

# Step 1: Stop processing services
echo "📍 Step 1/7: Stopping processing services..."
docker compose stop llm-diagnosis correlation-engine anomaly-detector
echo "✅ Services stopped"
echo ""

# Step 2: Clean PostgreSQL database
echo "📍 Step 2/7: Cleaning PostgreSQL database..."
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "TRUNCATE incidents CASCADE;"
echo "✅ Database cleaned"
echo ""

# Step 3: Delete consumer groups (reset Kafka offsets)
echo "📍 Step 3/7: Resetting Kafka consumer groups..."
docker compose exec -T kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --delete --group llm-diagnosis-group 2>&1 || echo "   (Consumer group already deleted or doesn't exist)"
docker compose exec -T kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --delete --group correlation-engine-group 2>&1 || echo "   (Consumer group already deleted or doesn't exist)"
echo "✅ Consumer groups reset"
echo ""

# Step 4: Delete and recreate Kafka topics
echo "📍 Step 4/7: Deleting old Kafka topics..."
docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --delete --topic anomalies 2>&1 | grep -E "Marked for deletion|does not exist" || echo "   (Topic handling in progress)"
docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --delete --topic incidents 2>&1 | grep -E "Marked for deletion|does not exist" || echo "   (Topic handling in progress)"
echo "   Waiting for deletion to complete..."
sleep 8
echo "✅ Topics deletion requested"
echo ""

echo "📍 Step 5/7: Recreating Kafka topics..."
docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --topic anomalies \
  --partitions 3 --replication-factor 1 --if-not-exists 2>&1 | grep -E "Created|already" || echo "   Topic created"
docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --topic incidents \
  --partitions 3 --replication-factor 1 --if-not-exists 2>&1 | grep -E "Created|already" || echo "   Topic created"
echo "✅ Topics ready"
echo ""

# Step 6: Start services
echo "📍 Step 6/7: Starting processing services..."
docker compose start anomaly-detector correlation-engine llm-diagnosis
sleep 10
echo "✅ Services started"
echo ""

# Step 7: Verify service status
echo "📍 Step 7/7: Verifying service status..."
docker compose ps | grep -E "anomaly-detector|correlation-engine|llm-diagnosis"
echo ""

echo "✅ Cleanup complete! System ready for testing."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 Generating test incident..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Generate test scenario
cd services/log-generator
source ../../venv/bin/activate
python generate_scenarios.py --scenario chaos --count 1

echo ""
echo "📊 Test incident generated!"
echo ""
echo "⏳ Waiting 15 seconds for pipeline processing..."
sleep 15
echo ""

# Check results
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Current Incident Status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd ../..
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c \
  "SELECT incident_number, status, 
          CASE WHEN root_cause IS NOT NULL THEN '✅ DIAGNOSED' ELSE '⏳ PENDING' END as diagnosis_status,
          created_at
   FROM incidents 
   ORDER BY created_at DESC 
   LIMIT 2;"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 LLM Diagnosis Service - Last 20 lines:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker logs --tail 20 smart-noc-llm-diagnosis

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ℹ️  Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. If diagnosis shows PENDING, wait 3-5 minutes for phi3 to complete"
echo "2. Monitor in real-time: docker logs -f smart-noc-llm-diagnosis"
echo "3. Check final results with the SQL query shown above"
echo ""
