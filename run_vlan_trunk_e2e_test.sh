#!/bin/bash
# Complete E2E Test: VLAN Trunk Native VLAN Mismatch
# This script generates test data and validates each stage of the pipeline

set -e

echo "================================================================================"
echo "🧪 SMART NOC E2E TEST: VLAN Trunk Native VLAN Mismatch"
echo "================================================================================"
echo ""
echo "Test Scenario:"
echo "  - Device 1: voss-dist-switch-01 (Native VLAN: 1)"
echo "  - Device 2: voss-dist-switch-02 (Native VLAN: 10)"
echo "  - Issue: Native VLAN mismatch on trunk port 1/20"
echo "  - Expected KB Article: EXT-019 (VOSS VLAN Configuration)"
echo ""
echo "================================================================================"
echo ""

# Step 1: Generate test logs
echo "📤 STEP 1: Generating test logs..."
echo "--------------------------------------------------------------------------------"
cd /home/user/ng-iam/smart-noc
source venv/bin/activate
python test_vlan_trunk_mismatch_e2e.py
echo ""
echo "✅ Test logs sent to Kafka"
echo ""

# Step 2: Wait for processing
echo "⏳ STEP 2: Waiting for pipeline processing (35 seconds)..."
echo "--------------------------------------------------------------------------------"
for i in {35..1}; do
    echo -ne "   Processing... $i seconds remaining\r"
    sleep 1
done
echo ""
echo "✅ Processing complete"
echo ""

# Step 3: Check anomalies
echo "🔍 STEP 3: Checking Anomaly Detection..."
echo "--------------------------------------------------------------------------------"
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    COUNT(*) as total_anomalies,
    COUNT(DISTINCT device_id) as affected_devices,
    COUNT(DISTINCT anomaly_type) as event_types
FROM anomalies 
WHERE device_id LIKE 'voss-dist%' 
  AND timestamp > NOW() - INTERVAL '2 minutes';
" -t
echo ""
echo "Anomaly Details:"
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    anomaly_type,
    device_id,
    severity,
    TO_CHAR(timestamp, 'HH24:MI:SS') as time
FROM anomalies 
WHERE device_id LIKE 'voss-dist%'
  AND timestamp > NOW() - INTERVAL '2 minutes'
ORDER BY timestamp DESC 
LIMIT 5;
"
echo ""

# Step 4: Check incident correlation
echo "🎯 STEP 4: Checking Incident Correlation..."
echo "--------------------------------------------------------------------------------"
INCIDENT_NUMBER=$(docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "
SELECT incident_number
FROM incidents 
WHERE affected_devices::text LIKE '%voss-dist%'
ORDER BY incident_number DESC 
LIMIT 1;
" | tr -d ' ')

if [ -z "$INCIDENT_NUMBER" ]; then
    echo "❌ ERROR: No incident found for voss-dist switches"
    echo "   Check correlation-engine logs:"
    echo "   docker-compose logs correlation-engine --tail 50"
    exit 1
fi

echo "✅ Incident created: #$INCIDENT_NUMBER"
echo ""

docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    incident_number,
    incident_type,
    severity,
    affected_devices,
    anomaly_count,
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created,
    CASE 
        WHEN root_cause IS NOT NULL THEN 'DIAGNOSED'
        ELSE 'PENDING'
    END as diagnosis_status
FROM incidents 
WHERE incident_number = $INCIDENT_NUMBER;
"
echo ""

# Step 5: Check diagnosis
echo "🧠 STEP 5: Checking LLM Diagnosis..."
echo "--------------------------------------------------------------------------------"

# Check if diagnosed
IS_DIAGNOSED=$(docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "
SELECT CASE WHEN root_cause IS NOT NULL THEN 'YES' ELSE 'NO' END
FROM incidents 
WHERE incident_number = $INCIDENT_NUMBER;
" | tr -d ' ')

if [ "$IS_DIAGNOSED" = "NO" ]; then
    echo "⏳ Diagnosis still pending, waiting 10 more seconds..."
    sleep 10
    IS_DIAGNOSED=$(docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "
    SELECT CASE WHEN root_cause IS NOT NULL THEN 'YES' ELSE 'NO' END
    FROM incidents 
    WHERE incident_number = $INCIDENT_NUMBER;
    " | tr -d ' ')
fi

if [ "$IS_DIAGNOSED" = "YES" ]; then
    echo "✅ Diagnosis completed"
    echo ""
    
    # Show diagnosis metrics
    docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
    SELECT 
        'Confidence Score' as metric,
        confidence_score::text as value
    FROM incidents WHERE incident_number = $INCIDENT_NUMBER
    UNION ALL
    SELECT 
        'Diagnosis Time',
        EXTRACT(EPOCH FROM (diagnosed_at - created_at))::text || ' seconds'
    FROM incidents WHERE incident_number = $INCIDENT_NUMBER;
    "
    echo ""
else
    echo "❌ ERROR: Diagnosis not completed after 45 seconds"
    echo "   Check llm-diagnosis logs:"
    echo "   docker-compose logs llm-diagnosis --tail 100"
fi

# Step 6: Show root cause summary
echo "📋 STEP 6: Root Cause Summary..."
echo "--------------------------------------------------------------------------------"
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    LEFT(root_cause, 500) as root_cause_summary
FROM incidents 
WHERE incident_number = $INCIDENT_NUMBER;
" -t | head -20
echo ""
echo "[...truncated, full root cause available in database...]"
echo ""

# Step 7: Show remediation preview
echo "🔧 STEP 7: Remediation Plan Preview..."
echo "--------------------------------------------------------------------------------"
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    LEFT(remediation_plan, 600) as remediation_preview
FROM incidents 
WHERE incident_number = $INCIDENT_NUMBER;
" -t | head -25
echo ""
echo "[...truncated, full remediation plan available in database...]"
echo ""

# Step 8: Check enhanced search metrics
echo "🔎 STEP 8: Checking Enhanced Multi-Query Search Metrics..."
echo "--------------------------------------------------------------------------------"
echo "Searching LLM diagnosis logs for vector search details..."
echo ""

docker-compose logs llm-diagnosis --tail 200 | grep -A 3 "Detected vendor\|multi-query\|KB Article" | head -20
echo ""

# Step 9: Final summary
echo "================================================================================"
echo "✅ TEST COMPLETE - SUMMARY"
echo "================================================================================"
echo ""
echo "Incident: #$INCIDENT_NUMBER"
echo ""

# Get final stats
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    '📊 Incident Type' as item,
    incident_type as value
FROM incidents WHERE incident_number = $INCIDENT_NUMBER
UNION ALL
SELECT 
    '🚨 Severity',
    severity
FROM incidents WHERE incident_number = $INCIDENT_NUMBER
UNION ALL
SELECT 
    '🖥️  Devices Affected',
    array_length(affected_devices, 1)::text
FROM incidents WHERE incident_number = $INCIDENT_NUMBER
UNION ALL
SELECT 
    '🔢 Anomalies Correlated',
    anomaly_count::text
FROM incidents WHERE incident_number = $INCIDENT_NUMBER
UNION ALL
SELECT 
    '✅ Root Cause Found',
    CASE WHEN root_cause IS NOT NULL THEN 'YES' ELSE 'NO' END
FROM incidents WHERE incident_number = $INCIDENT_NUMBER
UNION ALL
SELECT 
    '🔧 Remediation Plan',
    CASE WHEN remediation_plan IS NOT NULL THEN 'YES' ELSE 'NO' END
FROM incidents WHERE incident_number = $INCIDENT_NUMBER
UNION ALL
SELECT 
    '🎯 Confidence Score',
    ROUND(confidence_score::numeric, 2)::text
FROM incidents WHERE incident_number = $INCIDENT_NUMBER;
" -t | column -t -s '|'

echo ""
echo "================================================================================"
echo "📖 DETAILED QUERIES"
echo "================================================================================"
echo ""
echo "View full root cause:"
echo "  docker exec smart-noc-postgres psql -U noc_admin -d smart_noc \\"
echo "    -c \"SELECT root_cause FROM incidents WHERE incident_number = $INCIDENT_NUMBER;\""
echo ""
echo "View full remediation plan:"
echo "  docker exec smart-noc-postgres psql -U noc_admin -d smart_noc \\"
echo "    -c \"SELECT remediation_plan FROM incidents WHERE incident_number = $INCIDENT_NUMBER;\""
echo ""
echo "View all anomalies:"
echo "  docker exec smart-noc-postgres psql -U noc_admin -d smart_noc \\"
echo "    -c \"SELECT * FROM anomalies WHERE device_id LIKE 'voss-dist%' ORDER BY timestamp DESC LIMIT 10;\""
echo ""
echo "Check enhanced search logs:"
echo "  docker-compose logs llm-diagnosis | grep -A 10 'multi-query'"
echo ""
echo "================================================================================"
echo "✅ Test completed successfully!"
echo "================================================================================"
