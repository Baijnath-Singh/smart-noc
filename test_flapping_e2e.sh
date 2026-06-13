#!/bin/bash
# Quick Flapping Test to Trigger Correlation → LLM

set -e

DEVICE_IP="10.139.38.188"
PORT="3:33"

echo "═══════════════════════════════════════════════════════════════════"
echo "  INTERFACE FLAPPING TEST - Trigger Correlation → LLM"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Get baseline
INITIAL_INCIDENTS=$(docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM incidents;")
INITIAL_ANOMALIES=$(docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM incident_anomalies;")

echo "📊 Baseline:"
echo "   Incidents: $INITIAL_INCIDENTS"
echo "   Anomalies: $INITIAL_ANOMALIES"
echo ""

# Send 8 alternating UP/DOWN events (triggers flapping detection)
echo "🚀 Sending 8 alternating UP/DOWN events (Port $PORT)..."
for i in {1..8}; do
    if [ $((i % 2)) -eq 1 ]; then
        STATE="DOWN"
    else
        STATE="UP"
    fi
    
    TIMESTAMP=$(date -u +"%b %d %H:%M:%S")
    MESSAGE="<189>$TIMESTAMP $DEVICE_IP $(date +"%m/%d/%Y %H:%M:%S") <Warn:STP.Notif> Port $PORT link $STATE"
    
    echo "$MESSAGE" | nc -u -w1 localhost 5000
    echo "   [$i/8] Port $PORT → $STATE"
    sleep 0.5
done

echo "   ✓ All 8 events sent (flapping pattern)"
echo ""

# Wait for detection
echo "⏳ Waiting 10 seconds for anomaly detection..."
sleep 10

# Check for new anomalies
NEW_ANOMALIES=$(docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM incident_anomalies WHERE created_at > NOW() - INTERVAL '2 minutes';")
echo "   New anomalies in last 2 min: $NEW_ANOMALIES"

if [ "$NEW_ANOMALIES" -gt "0" ]; then
    echo "   ✓ Anomaly detected!"
    
    echo ""
    echo "📋 Latest Anomaly Details:"
    docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -x -c "
        SELECT 
            anomaly_type,
            device_id,
            severity,
            anomaly_data->>'interface' as interface,
            anomaly_data->>'flap_count' as flap_count,
            anomaly_data->'source_log'->>'device_cli_syntax' as cli_syntax,
            anomaly_data->'source_log'->>'device_vendor' as vendor
        FROM incident_anomalies 
        WHERE created_at > NOW() - INTERVAL '2 minutes'
        ORDER BY created_at DESC 
        LIMIT 1;
    "
else
    echo "   ⚠ No anomalies detected yet"
fi

echo ""
echo "⏳ Waiting 20 seconds for correlation engine..."
sleep 20

# Check for new incidents
FINAL_INCIDENTS=$(docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM incidents WHERE created_at > NOW() - INTERVAL '3 minutes';")

if [ "$FINAL_INCIDENTS" -gt "0" ]; then
    echo "   ✓ NEW INCIDENT CREATED!"
    
    echo ""
    echo "📋 Incident Details:"
    docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -x -c "
        SELECT 
            incident_number,
            severity,
            affected_device_id,
            root_cause IS NOT NULL as has_diagnosis,
            remediation_plan IS NOT NULL as has_remediation
        FROM incidents 
        WHERE created_at > NOW() - INTERVAL '3 minutes'
        ORDER BY created_at DESC 
        LIMIT 1;
    "
    
    INCIDENT_NUM=$(docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "SELECT incident_number FROM incidents WHERE created_at > NOW() - INTERVAL '3 minutes' ORDER BY created_at DESC LIMIT 1;")
    
    echo ""
    echo "⏳ Waiting 40 seconds for LLM diagnosis (Incident $INCIDENT_NUM)..."
    sleep 40
    
    echo ""
    echo "🔍 Checking LLM Diagnosis Results..."
    docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -x -c "
        SELECT 
            incident_number,
            CASE WHEN root_cause IS NOT NULL THEN 'DIAGNOSED' ELSE 'PENDING' END as status,
            SUBSTRING(root_cause, 1, 100) as root_cause_preview,
            LENGTH(remediation_plan::text) as remediation_plan_size
        FROM incidents 
        WHERE incident_number = $INCIDENT_NUM;
    "
    
    # Check for EXOS commands
    echo ""
    echo "🎯 Looking for EXOS-Specific Commands in Remediation..."
    docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "
        SELECT remediation_plan 
        FROM incidents 
        WHERE incident_number = $INCIDENT_NUM;
    " > /tmp/remediation_check.json
    
    if grep -q "show port\|enable port\|disable port" /tmp/remediation_check.json 2>/dev/null; then
        echo "   ✓ EXOS commands found!"
        grep -o '"command"[^"]*"[^"]*"' /tmp/remediation_check.json | head -5
    else
        echo "   ⚠ No EXOS commands found yet (may still be processing)"
    fi
    
else
    echo "   ⚠ No incident created yet"
    echo "   (Correlation may need more time or more related anomalies)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  TEST COMPLETE"
echo "═══════════════════════════════════════════════════════════════════"
