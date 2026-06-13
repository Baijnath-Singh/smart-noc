#!/bin/bash
# Full End-to-End Test: Syslog → Enrichment → Anomaly → Correlation → Incident → LLM → Remediation

set -e

DEVICE_IP="10.139.38.188"  # EXOS device from inventory
PORT="2:88"
LOGSTASH_HOST="localhost"
LOGSTASH_PORT="5000"

echo "═══════════════════════════════════════════════════════════════════"
echo "  FULL E2E TEST: EXOS Device Enrichment → LLM EXOS Commands"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "📋 Test Plan:"
echo "  1. Generate 5 interface down events on same port (trigger correlation)"
echo "  2. Wait for correlation engine to create incident"
echo "  3. Wait for LLM diagnosis to process via Kafka"
echo "  4. Verify EXOS-specific commands in remediation plan"
echo ""

# Get initial incident count
echo "🔍 Step 1: Getting baseline incident count..."
INITIAL_COUNT=$(docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM incidents;")
echo "   Current incidents: $INITIAL_COUNT"
echo ""

# Generate multiple interface down events to trigger correlation
echo "🚀 Step 2: Generating 5 INTERFACE_DOWN events (Port $PORT on $DEVICE_IP)..."
for i in {1..5}; do
    TIMESTAMP=$(date -u +"%b %d %H:%M:%S")
    MESSAGE="<189>$TIMESTAMP $DEVICE_IP 06/13/2026 22:$(printf '%02d' $((10 + i))):$(printf '%02d' $i) <Warn:STP.Notif> Port $PORT link DOWN"
    
    echo "$MESSAGE" | nc -u -w1 $LOGSTASH_HOST $LOGSTASH_PORT
    echo "   [$i/5] Sent: Port $PORT link DOWN"
    sleep 2
done
echo "   ✓ All 5 events sent"
echo ""

# Wait for processing
echo "⏳ Step 3: Waiting 15 seconds for pipeline processing..."
echo "   (Logstash → Enrichment → Anomaly Detector → Correlation Engine)"
for i in {15..1}; do
    echo -ne "   Waiting: $i seconds...\r"
    sleep 1
done
echo ""
echo "   ✓ Processing window complete"
echo ""

# Check if new incident was created
echo "🔍 Step 4: Checking for new incident..."
FINAL_COUNT=$(docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM incidents;")
NEW_INCIDENTS=$((FINAL_COUNT - INITIAL_COUNT))

if [ $NEW_INCIDENTS -gt 0 ]; then
    echo "   ✓ NEW INCIDENT CREATED! ($NEW_INCIDENTS new incident(s))"
    
    # Get the latest incident details
    echo ""
    echo "📊 Step 5: Getting incident details..."
    docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -x -c "
        SELECT 
            incident_number,
            severity,
            status,
            affected_device_id,
            root_cause IS NOT NULL as has_root_cause,
            remediation_plan IS NOT NULL as has_remediation
        FROM incidents 
        ORDER BY created_at DESC 
        LIMIT 1;
    "
    
    # Get incident number
    INCIDENT_NUMBER=$(docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "SELECT incident_number FROM incidents ORDER BY created_at DESC LIMIT 1;")
    echo ""
    echo "   Incident Number: $INCIDENT_NUMBER"
    
else
    echo "   ⚠ No new incident created yet"
    echo "   This might mean:"
    echo "     - Correlation engine needs more time"
    echo "     - Events didn't meet correlation criteria"
    echo "     - Check correlation-engine logs for details"
fi
echo ""

# Wait for LLM diagnosis
echo "⏳ Step 6: Waiting 30 seconds for LLM diagnosis..."
for i in {30..1}; do
    echo -ne "   LLM processing: $i seconds...\r"
    sleep 1
done
echo ""
echo "   ✓ LLM diagnosis window complete"
echo ""

# Check LLM diagnosis results
echo "🔍 Step 7: Checking LLM diagnosis and enrichment..."
if [ $NEW_INCIDENTS -gt 0 ]; then
    # Check if root cause and remediation were generated
    docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
        SELECT 
            incident_number,
            CASE WHEN root_cause IS NOT NULL THEN '✓ DIAGNOSED' ELSE '⏳ PENDING' END as diagnosis_status,
            CASE WHEN remediation_plan IS NOT NULL THEN '✓ PLAN GENERATED' ELSE '⏳ PENDING' END as remediation_status
        FROM incidents 
        ORDER BY created_at DESC 
        LIMIT 1;
    "
    
    echo ""
    echo "🔍 Step 8: Checking device enrichment in anomaly data..."
    docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "
        SELECT 
            anomaly_data->'source_log'->>'device_vendor' as vendor,
            anomaly_data->'source_log'->>'device_family' as family,
            anomaly_data->'source_log'->>'device_cli_syntax' as cli_syntax
        FROM incident_anomalies 
        WHERE incident_id = (SELECT id FROM incidents ORDER BY created_at DESC LIMIT 1)
        LIMIT 1;
    "
    
    echo ""
    echo "🎯 Step 9: Extracting EXOS-specific commands from remediation plan..."
    docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "
        SELECT remediation_plan 
        FROM incidents 
        ORDER BY created_at DESC 
        LIMIT 1;
    " > /tmp/remediation_plan.json
    
    if [ -s /tmp/remediation_plan.json ] && [ "$(cat /tmp/remediation_plan.json | tr -d '[:space:]')" != "" ]; then
        echo "   ✓ Remediation plan exists!"
        echo ""
        echo "   Looking for EXOS-specific commands:"
        cat /tmp/remediation_plan.json | jq -r '.steps[]?.commands[]?' 2>/dev/null | grep -E "show port|enable port|disable port|show edp" || echo "   (parsing remediation plan...)"
    else
        echo "   ⏳ Remediation plan not yet generated"
    fi
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  TEST COMPLETE - Review results above"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "📋 Next steps to verify:"
echo "  1. Check LLM logs: docker logs smart-noc-llm-diagnosis | tail -50"
echo "  2. Check correlation logs: docker logs smart-noc-correlation-engine | tail -30"
echo "  3. View full remediation: SELECT remediation_plan FROM incidents WHERE incident_number = [NUMBER];"
echo ""
