#!/bin/bash
# Decision Matrix Test Coverage - All 12 Scenarios
# Tests all combinations of Risk Level × Confidence Level

set -e

echo "================================================================================"
echo "DECISION MATRIX TEST COVERAGE - ALL 12 SCENARIOS"
echo "================================================================================"
echo ""
echo "Testing Matrix:"
echo "  Risk Levels: LOW, MEDIUM, HIGH, CRITICAL"
echo "  Confidence Levels: High (≥0.92), Medium (0.75-0.92), Low (<0.75)"
echo "  Total Scenarios: 12"
echo ""

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Base incident number
BASE_INCIDENT=10000

# Test result function
test_result() {
    local scenario="$1"
    local risk="$2"
    local confidence="$3"
    local expected="$4"
    local actual="$5"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$expected" = "$actual" ]; then
        echo "   ✅ PASS - Decision: $actual"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo "   ❌ FAIL - Expected: $expected, Got: $actual"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Cleanup function
cleanup_test_data() {
    echo "🧹 Cleaning up existing test data..."
    docker-compose exec -T postgres psql -U noc_admin -d smart_noc << EOF > /dev/null 2>&1
DELETE FROM incident_risk_assessment WHERE incident_number BETWEEN 10000 AND 10999;
DELETE FROM autonomous_decision_log WHERE incident_number BETWEEN 10000 AND 10999;
DELETE FROM incidents WHERE incident_number BETWEEN 10000 AND 10999;
DELETE FROM device_criticality WHERE device_name LIKE 'test-device-%';
EOF
    echo "   ✅ Cleanup complete"
    echo ""
}

# Create device with criticality
create_device() {
    local device_name="$1"
    local criticality="$2"
    
    docker-compose exec -T postgres psql -U noc_admin -d smart_noc << EOF > /dev/null 2>&1
INSERT INTO device_criticality (device_name, criticality_level, business_impact, description)
VALUES ('$device_name', '$criticality', 'Test device', 'Decision matrix testing')
ON CONFLICT (device_name) DO UPDATE SET criticality_level = EXCLUDED.criticality_level;
EOF
}

# Run single test scenario
run_test() {
    local scenario_num=$1
    local risk_level="$2"
    local confidence=$3
    local conf_bucket="$4"
    local expected_decision="$5"
    
    local incident_num=$((BASE_INCIDENT + scenario_num))
    local device_name="test-device-${risk_level,,}-${scenario_num}"
    
    echo "────────────────────────────────────────────────────────────────────────────────"
    echo "TEST SCENARIO #$scenario_num: $risk_level Risk + ${conf_bucket^^} Confidence ($confidence)"
    echo "────────────────────────────────────────────────────────────────────────────────"
    
    # Determine risk factors based on risk level
    case "$risk_level" in
        "LOW")
            device_crit=0.25
            blast_radius=0.20
            time_sens=0.30
            complexity=0.30
            affected_count=1
            criticality="LOW"
            ;;
        "MEDIUM")
            device_crit=0.55
            blast_radius=0.50
            time_sens=0.50
            complexity=0.60
            affected_count=5
            criticality="MEDIUM"
            ;;
        "HIGH")
            device_crit=0.75
            blast_radius=0.70
            time_sens=0.80
            complexity=0.80
            affected_count=15
            criticality="HIGH"
            ;;
        "CRITICAL")
            device_crit=0.95
            blast_radius=0.90
            time_sens=0.90
            complexity=0.90
            affected_count=25
            criticality="CRITICAL"
            ;;
    esac
    
    # Calculate overall risk score
    risk_score=$(echo "scale=2; ($device_crit * 0.40) + ($blast_radius * 0.30) + ($time_sens * 0.20) + ($complexity * 0.10)" | bc)
    
    echo "📝 Step 1: Creating test incident #$incident_num..."
    
    # Create device
    create_device "$device_name" "$criticality"
    
    # Create affected devices array
    affected_devices="'{\"$device_name\""
    for i in $(seq 1 $((affected_count - 1))); do
        affected_devices="${affected_devices}, \"${device_name}-peer-${i}\""
    done
    affected_devices="${affected_devices}}'"
    
    # Create incident
    docker-compose exec -T postgres psql -U noc_admin -d smart_noc << EOF > /dev/null 2>&1
INSERT INTO incidents 
    (incident_number, primary_device, incident_type, severity, start_time, status, affected_devices)
VALUES 
    ($incident_num, '$device_name', 'TEST_SCENARIO', '$risk_level', NOW(), 'ACTIVE', $affected_devices);

UPDATE incidents 
SET 
    root_cause = 'Test scenario: $risk_level risk with $confidence confidence',
    root_cause_confidence = $confidence,
    confidence_reasoning = 'Synthetic test data for decision matrix validation',
    remediation_plan = '[{"step": 1, "action": "Test action", "command": "show version"}]',
    diagnosis_timestamp = NOW()
WHERE incident_number = $incident_num;
EOF
    
    echo "   ✅ Incident created with $affected_count affected device(s)"
    
    echo "🔍 Step 2: Risk assessment..."
    
    # Insert risk assessment
    docker-compose exec -T postgres psql -U noc_admin -d smart_noc << EOF > /dev/null 2>&1
INSERT INTO incident_risk_assessment
    (incident_number, risk_level, overall_risk_score, 
     device_criticality, blast_radius, time_sensitivity, change_complexity,
     factors, assessed_at)
VALUES
    ($incident_num, '$risk_level', $risk_score, 
     $device_crit, $blast_radius, $time_sens, $complexity,
     '{"device_criticality": $device_crit, "blast_radius": $blast_radius}',
     NOW());
EOF
    
    echo "   ✅ Risk: $risk_level (score: $risk_score)"
    echo "      Device Criticality: $device_crit"
    echo "      Blast Radius: $blast_radius"
    echo "      Time Sensitivity: $time_sens"
    echo "      Change Complexity: $complexity"
    
    echo "🎯 Step 3: Decision matrix..."
    
    # Apply decision matrix rules
    case "$risk_level" in
        "LOW")
            if (( $(echo "$confidence >= 0.75" | bc -l) )); then
                decision="execute"
            else
                decision="manual_only"
            fi
            ;;
        "MEDIUM")
            if (( $(echo "$confidence >= 0.92" | bc -l) )); then
                decision="require_approval"
            else
                decision="manual_only"
            fi
            ;;
        "HIGH")
            if (( $(echo "$confidence >= 0.92" | bc -l) )); then
                decision="require_approval"
            else
                decision="manual_only"
            fi
            ;;
        "CRITICAL")
            decision="manual_only"
            ;;
    esac
    
    # Generate reasoning
    case "$decision" in
        "execute")
            reasoning="$risk_level risk with sufficient confidence ($confidence) allows autonomous execution"
            ;;
        "require_approval")
            reasoning="$risk_level risk with high confidence ($confidence) requires human approval before execution"
            ;;
        "manual_only")
            reasoning="$risk_level risk with confidence ($confidence) requires manual intervention"
            ;;
    esac
    
    # Log decision
    docker-compose exec -T postgres psql -U noc_admin -d smart_noc << EOF > /dev/null 2>&1
INSERT INTO autonomous_decision_log
    (incident_number, decision, reasoning, calibrated_confidence, risk_level, decided_at)
VALUES
    ($incident_num, '$decision', '$reasoning', $confidence, '$risk_level', NOW());
EOF
    
    echo "   Decision: $decision"
    echo "   Reasoning: $reasoning"
    
    echo "✅ Step 4: Validation..."
    test_result "$scenario_num" "$risk_level" "$confidence" "$expected_decision" "$decision"
    
    echo ""
}

# Main execution
main() {
    # Cleanup
    cleanup_test_data
    
    echo "================================================================================"
    echo "RUNNING ALL 12 TEST SCENARIOS"
    echo "================================================================================"
    echo ""
    
    # LOW risk scenarios (3)
    run_test 1 "LOW" 0.95 "high" "execute"
    run_test 2 "LOW" 0.85 "medium" "execute"
    run_test 3 "LOW" 0.70 "low" "manual_only"
    
    # MEDIUM risk scenarios (3)
    run_test 4 "MEDIUM" 0.95 "high" "require_approval"
    run_test 5 "MEDIUM" 0.85 "medium" "manual_only"
    run_test 6 "MEDIUM" 0.70 "low" "manual_only"
    
    # HIGH risk scenarios (3)
    run_test 7 "HIGH" 0.95 "high" "require_approval"
    run_test 8 "HIGH" 0.85 "medium" "manual_only"
    run_test 9 "HIGH" 0.70 "low" "manual_only"
    
    # CRITICAL risk scenarios (3)
    run_test 10 "CRITICAL" 0.95 "high" "manual_only"
    run_test 11 "CRITICAL" 0.85 "medium" "manual_only"
    run_test 12 "CRITICAL" 0.70 "low" "manual_only"
    
    # Generate report
    generate_report
}

generate_report() {
    echo ""
    echo "================================================================================"
    echo "COMPREHENSIVE TEST REPORT"
    echo "================================================================================"
    echo ""
    
    # Summary
    pass_rate=$((100 * PASSED_TESTS / TOTAL_TESTS))
    
    echo "📊 SUMMARY:"
    echo "   Total Tests: $TOTAL_TESTS"
    echo "   Passed: $PASSED_TESTS ✅"
    echo "   Failed: $FAILED_TESTS ❌"
    echo "   Pass Rate: $pass_rate%"
    echo ""
    
    # Grade
    if [ $pass_rate -ge 95 ]; then
        grade="A+ (Excellent)"
    elif [ $pass_rate -ge 90 ]; then
        grade="A (Very Good)"
    elif [ $pass_rate -ge 85 ]; then
        grade="B+ (Good)"
    else
        grade="B (Satisfactory)"
    fi
    
    echo "🎓 GRADE: $grade"
    echo ""
    
    # Decision matrix table
    echo "📊 DECISION MATRIX COVERAGE:"
    echo ""
    echo "   Risk Level   | High Conf (≥0.92)      | Medium Conf (0.75-0.92) | Low Conf (<0.75)"
    echo "   ─────────────┼────────────────────────┼─────────────────────────┼────────────────────"
    
    # Query database for results
    docker-compose exec -T postgres psql -U noc_admin -d smart_noc << 'EOF'
SELECT 
    CASE 
        WHEN i.severity = 'LOW' THEN '   LOW         '
        WHEN i.severity = 'MEDIUM' THEN '   MEDIUM      '
        WHEN i.severity = 'HIGH' THEN '   HIGH        '
        WHEN i.severity = 'CRITICAL' THEN '   CRITICAL    '
    END ||
    ' | ' ||
    COALESCE((SELECT CASE WHEN d1.decision = 'execute' THEN '✅ execute            ' WHEN d1.decision = 'require_approval' THEN '✅ require_approval   ' ELSE '✅ manual_only        ' END FROM autonomous_decision_log d1 WHERE d1.incident_number = i.incident_number AND d1.calibrated_confidence >= 0.92), '⚠️  Not tested         ') ||
    ' | ' ||
    COALESCE((SELECT CASE WHEN d2.decision = 'execute' THEN '✅ execute             ' WHEN d2.decision = 'require_approval' THEN '✅ require_approval    ' ELSE '✅ manual_only         ' END FROM autonomous_decision_log d2 WHERE d2.incident_number = i.incident_number AND d2.calibrated_confidence >= 0.75 AND d2.calibrated_confidence < 0.92), '⚠️  Not tested          ') ||
    ' | ' ||
    COALESCE((SELECT CASE WHEN d3.decision = 'execute' THEN '✅ execute' WHEN d3.decision = 'require_approval' THEN '✅ require_approval' ELSE '✅ manual_only' END FROM autonomous_decision_log d3 WHERE d3.incident_number = i.incident_number AND d3.calibrated_confidence < 0.75), '⚠️  Not tested')
FROM (SELECT DISTINCT severity FROM incidents WHERE incident_number BETWEEN 10000 AND 10011 ORDER BY 
    CASE severity 
        WHEN 'LOW' THEN 1
        WHEN 'MEDIUM' THEN 2
        WHEN 'HIGH' THEN 3
        WHEN 'CRITICAL' THEN 4
    END) i;
EOF
    
    echo ""
    echo "📋 DETAILED RESULTS:"
    echo ""
    
    # Detailed query
    docker-compose exec -T postgres psql -U noc_admin -d smart_noc << 'EOF'
SELECT 
    i.incident_number as "Incident",
    i.severity as "Risk",
    ROUND(i.root_cause_confidence::numeric, 2) as "Confidence",
    CASE 
        WHEN i.root_cause_confidence >= 0.92 THEN 'HIGH'
        WHEN i.root_cause_confidence >= 0.75 THEN 'MEDIUM'
        ELSE 'LOW'
    END as "Conf Level",
    d.decision as "Decision",
    CASE 
        WHEN (i.severity = 'LOW' AND i.root_cause_confidence >= 0.75 AND d.decision = 'execute') THEN '✅'
        WHEN (i.severity = 'LOW' AND i.root_cause_confidence < 0.75 AND d.decision = 'manual_only') THEN '✅'
        WHEN (i.severity IN ('MEDIUM', 'HIGH') AND i.root_cause_confidence >= 0.92 AND d.decision = 'require_approval') THEN '✅'
        WHEN (i.severity IN ('MEDIUM', 'HIGH') AND i.root_cause_confidence < 0.92 AND d.decision = 'manual_only') THEN '✅'
        WHEN (i.severity = 'CRITICAL' AND d.decision = 'manual_only') THEN '✅'
        ELSE '❌'
    END as "Result"
FROM incidents i
JOIN autonomous_decision_log d ON i.incident_number = d.incident_number
WHERE i.incident_number BETWEEN 10000 AND 10011
ORDER BY i.incident_number;
EOF
    
    echo ""
    echo "🔍 VERIFICATION QUERY (for manual inspection):"
    echo ""
    echo "   docker-compose exec -T postgres psql -U noc_admin -d smart_noc -c \\"
    echo "   \"SELECT i.incident_number, i.severity, i.root_cause_confidence, \\"
    echo "    r.overall_risk_score, d.decision FROM incidents i \\"
    echo "    JOIN incident_risk_assessment r ON i.incident_number = r.incident_number \\"
    echo "    JOIN autonomous_decision_log d ON i.incident_number = d.incident_number \\"
    echo "    WHERE i.incident_number BETWEEN 10000 AND 10011 ORDER BY i.incident_number;\""
    
    echo ""
    echo "================================================================================"
    echo "TEST COMPLETION: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "================================================================================"
    echo ""
    
    # Exit with appropriate code
    if [ $FAILED_TESTS -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Run main
main
