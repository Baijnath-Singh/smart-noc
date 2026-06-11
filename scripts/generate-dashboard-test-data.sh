#!/bin/bash
# Generate Persistent Test Data for Grafana Dashboard
# This data will NOT be cleaned up and will remain visible

set -e

echo "================================================================================"
echo "GENERATING PERSISTENT TEST DATA FOR GRAFANA DASHBOARD"
echo "================================================================================"
echo ""

# Use higher incident numbers to avoid conflicts
BASE_INCIDENT=20000

echo "📝 Creating 10 test incidents with decisions..."
echo ""

# Create diverse test scenarios
create_test_incident() {
    local num=$1
    local risk=$2
    local confidence=$3
    local decision=$4
    
    local incident=$((BASE_INCIDENT + num))
    local device="dashboard-test-device-$num"
    
    echo "Creating incident #$incident: $risk risk, confidence $confidence → $decision"
    
    # Device criticality based on risk
    case "$risk" in
        "LOW") crit_level="LOW"; dev_crit=0.25; blast=0.20; time_s=0.30; complex=0.30; affected=1 ;;
        "MEDIUM") crit_level="MEDIUM"; dev_crit=0.55; blast=0.50; time_s=0.50; complex=0.60; affected=5 ;;
        "HIGH") crit_level="HIGH"; dev_crit=0.75; blast=0.70; time_s=0.80; complex=0.80; affected=15 ;;
        "CRITICAL") crit_level="CRITICAL"; dev_crit=0.95; blast=0.90; time_s=0.90; complex=0.90; affected=25 ;;
    esac
    
    risk_score=$(echo "scale=2; ($dev_crit * 0.40) + ($blast * 0.30) + ($time_s * 0.20) + ($complex * 0.10)" | bc)
    
    # Create device
    docker-compose exec -T postgres psql -U noc_admin -d smart_noc << EOF > /dev/null 2>&1
INSERT INTO device_criticality (device_name, criticality_level, business_impact, description)
VALUES ('$device', '$crit_level', 'Dashboard test device', 'Persistent test data')
ON CONFLICT (device_name) DO UPDATE SET criticality_level = EXCLUDED.criticality_level;
EOF
    
    # Create incident
    docker-compose exec -T postgres psql -U noc_admin -d smart_noc << EOF > /dev/null 2>&1
INSERT INTO incidents 
    (incident_number, primary_device, incident_type, severity, start_time, status, affected_devices)
VALUES 
    ($incident, '$device', 'DASHBOARD_TEST', '$risk', NOW(), 'ACTIVE', '{\"$device\"}')
ON CONFLICT (incident_number) DO UPDATE SET start_time = NOW();

UPDATE incidents 
SET 
    root_cause = 'Dashboard test: $risk risk with $confidence confidence',
    root_cause_confidence = $confidence,
    confidence_reasoning = 'Persistent test data for Grafana dashboard visibility',
    remediation_plan = '[{"step": 1, "action": "Test action", "command": "show version"}]',
    diagnosis_timestamp = NOW()
WHERE incident_number = $incident;
EOF
    
    # Create risk assessment
    docker-compose exec -T postgres psql -U noc_admin -d smart_noc << EOF > /dev/null 2>&1
INSERT INTO incident_risk_assessment
    (incident_number, risk_level, overall_risk_score, device_criticality, blast_radius, 
     time_sensitivity, change_complexity, factors, assessed_at)
VALUES
    ($incident, '$risk', $risk_score, $dev_crit, $blast, $time_s, $complex,
     '{"device_criticality": $dev_crit, "blast_radius": $blast}', NOW())
ON CONFLICT (incident_number) DO UPDATE SET assessed_at = NOW();
EOF
    
    # Create decision
    docker-compose exec -T postgres psql -U noc_admin -d smart_noc << EOF > /dev/null 2>&1
INSERT INTO autonomous_decision_log
    (incident_number, decision, reasoning, calibrated_confidence, risk_level, decided_at)
VALUES
    ($incident, '$decision', 'Dashboard test: $risk risk with $confidence confidence', 
     $confidence, '$risk', NOW())
ON CONFLICT (incident_number) DO UPDATE SET decided_at = NOW();
EOF
    
    echo "   ✅ Created incident #$incident"
}

# Generate 10 diverse test scenarios
create_test_incident 1 "LOW" 0.95 "execute"
create_test_incident 2 "LOW" 0.85 "execute"
create_test_incident 3 "LOW" 0.65 "manual_only"
create_test_incident 4 "MEDIUM" 0.95 "require_approval"
create_test_incident 5 "MEDIUM" 0.85 "manual_only"
create_test_incident 6 "MEDIUM" 0.70 "manual_only"
create_test_incident 7 "HIGH" 0.95 "require_approval"
create_test_incident 8 "HIGH" 0.80 "manual_only"
create_test_incident 9 "CRITICAL" 0.95 "manual_only"
create_test_incident 10 "CRITICAL" 0.70 "manual_only"

echo ""
echo "================================================================================"
echo "VERIFICATION"
echo "================================================================================"

# Verify data
docker-compose exec -T postgres psql -U noc_admin -d smart_noc << 'EOF'
SELECT 
    COUNT(*) as total_test_incidents,
    COUNT(CASE WHEN decision = 'execute' THEN 1 END) as execute,
    COUNT(CASE WHEN decision = 'require_approval' THEN 1 END) as approval,
    COUNT(CASE WHEN decision = 'manual_only' THEN 1 END) as manual
FROM autonomous_decision_log
WHERE incident_number >= 20000;
EOF

echo ""
echo "================================================================================"
echo "✅ PERSISTENT TEST DATA CREATED"
echo "================================================================================"
echo ""
echo "📊 Dashboard should now show data at:"
echo "   http://10.37.12.33:3000/d/safety-framework"
echo ""
echo "🔄 Refresh your browser (Ctrl+R or F5)"
echo ""
echo "Note: This data is persistent and will remain until manually deleted"
echo "To delete: docker-compose exec -T postgres psql -U noc_admin -d smart_noc -c"
echo "  \"DELETE FROM incidents WHERE incident_number >= 20000;\""
echo ""
echo "================================================================================"
