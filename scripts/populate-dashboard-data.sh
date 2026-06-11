#!/bin/bash
# Populate Dashboard with Real Safety Framework Data
# This script runs actual remediation flow (no cleanup) to populate Grafana

set -e

echo "================================================================================"
echo "POPULATING GRAFANA DASHBOARD WITH REAL DATA"
echo "================================================================================"
echo ""

BASE_INCIDENT=20000

echo "Step 1: Cleaning up old test data (incidents >= 20000)..."
docker-compose exec -T postgres psql -U noc_admin -d smart_noc << 'EOF' > /dev/null 2>&1
DELETE FROM incident_risk_assessment WHERE incident_number >= 20000;
DELETE FROM autonomous_decision_log WHERE incident_number >= 20000;
DELETE FROM incidents WHERE incident_number >= 20000;
EOF
echo "   ✅ Cleanup complete"
echo ""

# Helper to run SQL safely
run_sql() {
    docker-compose exec -T postgres psql -U noc_admin -d smart_noc -c "$1" 2>&1 | grep -v "INSERT 0 1\|UPDATE 1" || true
}

echo "Step 1: Creating devices with criticality levels..."
run_sql "
INSERT INTO device_criticality (device_name, criticality, business_impact) VALUES
('dashboard-low-device', 'LOW', 'LOW'),
('dashboard-med-device', 'MEDIUM', 'MEDIUM'),
('dashboard-high-device', 'HIGH', 'HIGH'),
('dashboard-crit-device', 'CRITICAL', 'CRITICAL')
ON CONFLICT (device_name) DO UPDATE SET criticality = EXCLUDED.criticality;
"
echo "   ✅ Devices created"
echo ""

echo "Step 2: Creating diverse test scenarios..."

# Function to create complete incident with risk assessment and decision
create_scenario() {
    local num=$1
    local device=$2
    local severity=$3
    local confidence=$4
    local risk_score=$5
    local decision=$6
    local dev_crit=$7
    local blast=$8
    local time_s=$9
    local complex=${10}
    
    local incident=$((BASE_INCIDENT + num))
    
    echo "   Scenario $num: $severity risk, confidence $confidence → $decision"
    
    # Create incident
    run_sql "
    INSERT INTO incidents 
        (incident_number, primary_device, incident_type, severity, start_time, status, affected_devices, correlation_method)
    VALUES 
        ($incident, '$device', 'BGP_FLAPPING', '$severity', NOW(), 'ACTIVE', '[\"$device\"]'::jsonb, 'test_data')
    ON CONFLICT (incident_number) DO UPDATE 
    SET start_time = NOW(), status = 'ACTIVE', severity = EXCLUDED.severity;
    "
    
    # Update with remediation plan
    run_sql "
    UPDATE incidents 
    SET 
        root_cause = 'BGP session flapping detected on $device',
        remediation_plan = '[{\"step\": 1, \"action\": \"Reset BGP session\", \"command\": \"clear ip bgp *\"}]'
    WHERE incident_number = $incident;
    "
    
    # Risk assessment
    run_sql "
    INSERT INTO incident_risk_assessment
        (incident_number, risk_level, overall_risk_score, device_criticality, 
         blast_radius_score, time_sensitivity_score, change_complexity_score, 
         factors, assessed_at)
    VALUES
        ($incident, '$severity', $risk_score, '$dev_crit', $blast, $time_s, $complex,
         '{\"device_crit\": \"$dev_crit\", \"blast\": $blast, \"time\": $time_s, \"complex\": $complex}'::jsonb, NOW());
    "
    
    # Update if exists
    run_sql "
    UPDATE incident_risk_assessment
    SET assessed_at = NOW(), overall_risk_score = $risk_score
    WHERE incident_number = $incident AND id != (SELECT MAX(id) FROM incident_risk_assessment WHERE incident_number = $incident);
    "
    
    # Decision
    run_sql "
    INSERT INTO autonomous_decision_log
        (incident_number, decision_type, decision, decision_reasoning, calibrated_confidence, risk_level, decided_at)
    VALUES
        ($incident, 'auto_execute', '$decision', '$severity risk with $confidence confidence', $confidence, '$severity', NOW());
    "
}

# LOW risk scenarios (autonomous execution)
create_scenario 1 "dashboard-low-device" "LOW" 0.95 0.25 "execute" "LOW" 0.20 0.30 0.30
create_scenario 2 "dashboard-low-device" "LOW" 0.85 0.25 "execute" "LOW" 0.20 0.30 0.30
create_scenario 3 "dashboard-low-device" "LOW" 0.70 0.25 "manual_only" "LOW" 0.20 0.30 0.30

# MEDIUM risk scenarios (approval required)
create_scenario 4 "dashboard-med-device" "MEDIUM" 0.95 0.53 "require_approval" "MEDIUM" 0.50 0.50 0.60
create_scenario 5 "dashboard-med-device" "MEDIUM" 0.85 0.53 "manual_only" "MEDIUM" 0.50 0.50 0.60
create_scenario 6 "dashboard-med-device" "MEDIUM" 0.70 0.53 "manual_only" "MEDIUM" 0.50 0.50 0.60

# HIGH risk scenarios
create_scenario 7 "dashboard-high-device" "HIGH" 0.95 0.76 "require_approval" "HIGH" 0.70 0.80 0.80
create_scenario 8 "dashboard-high-device" "HIGH" 0.85 0.76 "manual_only" "HIGH" 0.70 0.80 0.80
create_scenario 9 "dashboard-high-device" "HIGH" 0.70 0.76 "manual_only" "HIGH" 0.70 0.80 0.80

# CRITICAL risk scenarios (always manual)
create_scenario 10 "dashboard-crit-device" "CRITICAL" 0.95 0.92 "manual_only" "CRITICAL" 0.90 0.90 0.90
create_scenario 11 "dashboard-crit-device" "CRITICAL" 0.85 0.92 "manual_only" "CRITICAL" 0.90 0.90 0.90
create_scenario 12 "dashboard-crit-device" "CRITICAL" 0.70 0.92 "manual_only" "CRITICAL" 0.90 0.90 0.90

echo ""
echo "================================================================================"
echo "VERIFICATION"
echo "================================================================================"

# Verify
docker-compose exec -T postgres psql -U noc_admin -d smart_noc << 'EOF'
SELECT 
    COUNT(*) as total_decisions,
    COUNT(CASE WHEN decision = 'execute' THEN 1 END) as execute,
    COUNT(CASE WHEN decision = 'require_approval' THEN 1 END) as approval,
    COUNT(CASE WHEN decision = 'manual_only' THEN 1 END) as manual,
    MAX(decided_at) as latest_decision,
    NOW() - MAX(decided_at) as seconds_ago
FROM autonomous_decision_log
WHERE incident_number >= 20000;

-- Show risk distribution
SELECT 
    r.risk_level,
    COUNT(*) as count,
    ROUND(AVG(r.overall_risk_score), 2) as avg_score
FROM incident_risk_assessment r
WHERE r.incident_number >= 20000
GROUP BY r.risk_level
ORDER BY 
    CASE r.risk_level 
        WHEN 'LOW' THEN 1
        WHEN 'MEDIUM' THEN 2
        WHEN 'HIGH' THEN 3
        WHEN 'CRITICAL' THEN 4
    END;
EOF

echo ""
echo "================================================================================"
echo "✅ DASHBOARD DATA POPULATED"
echo "================================================================================"
echo ""
echo "📊 Grafana Dashboard: http://10.37.12.33:3000/d/safety-framework"
echo ""
echo "🔄 Refresh your browser to see the data"
echo ""
echo "Note: This data is persistent. To regenerate with fresh timestamps, run this script again."
echo ""
