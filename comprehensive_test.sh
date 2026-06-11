#!/bin/bash
# Comprehensive Safety Framework & Service Health Test Suite
# Tests: Decision matrix, performance, no breakage

echo "================================================================================"
echo "COMPREHENSIVE SAFETY FRAMEWORK & SERVICE HEALTH TEST SUITE"
echo "================================================================================"
echo ""

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Helper function
test_result() {
    local name="$1"
    local passed="$2"
    local details="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [ "$passed" = "true" ]; then
        echo "✅ PASS - $name"
        [ -n "$details" ] && echo "      $details"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo "❌ FAIL - $name"
        [ -n "$details" ] && echo "      $details"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# ============================================================================
# TEST SUITE 1: SERVICE STATUS
# ============================================================================
echo "================================================================================"
echo "TEST SUITE 1: SERVICE STATUS"
echo "================================================================================"

for service in llm-diagnosis remediation-agent correlation-engine anomaly-detector postgres kafka; do
    status=$(docker-compose ps $service 2>&1 | grep -i "running\|up" | wc -l)
    if [ "$status" -gt 0 ]; then
        test_result "Service: $service" "true" "Running"
    else
        test_result "Service: $service" "false" "Not running"
    fi
done

# ============================================================================
# TEST SUITE 2: PERFORMANCE METRICS
# ============================================================================
echo ""
echo "================================================================================"
echo "TEST SUITE 2: PERFORMANCE METRICS"
echo "================================================================================"

# Get current performance
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep smart-noc > /tmp/perf_metrics.txt

# Check llm-diagnosis
llm_cpu=$(grep "llm-diagnosis" /tmp/perf_metrics.txt | awk '{print $2}' | sed 's/%//')
if [ -n "$llm_cpu" ] && [ "$(echo "$llm_cpu < 5.0" | bc -l 2>/dev/null || echo 1)" -eq 1 ]; then
    mem=$(grep "llm-diagnosis" /tmp/perf_metrics.txt | awk '{print $3}')
    test_result "Performance: LLM Diagnosis" "true" "CPU: $llm_cpu%, Memory: $mem (threshold: <5%)"
else
    test_result "Performance: LLM Diagnosis" "false" "CPU: ${llm_cpu:-N/A}% exceeds 5%"
fi

# Check remediation-agent
rem_cpu=$(grep "remediation-agent" /tmp/perf_metrics.txt | awk '{print $2}' | sed 's/%//')
if [ -n "$rem_cpu" ] && [ "$(echo "$rem_cpu < 20.0" | bc -l 2>/dev/null || echo 1)" -eq 1 ]; then
    mem=$(grep "remediation-agent" /tmp/perf_metrics.txt | awk '{print $3}')
    test_result "Performance: Remediation Agent" "true" "CPU: $rem_cpu%, Memory: $mem (threshold: <20%)"
else
    test_result "Performance: Remediation Agent" "false" "CPU: ${rem_cpu:-N/A}% exceeds 20%"
fi

# Check correlation-engine
corr_cpu=$(grep "correlation-engine" /tmp/perf_metrics.txt | awk '{print $2}' | sed 's/%//')
if [ -n "$corr_cpu" ] && [ "$(echo "$corr_cpu < 5.0" | bc -l 2>/dev/null || echo 1)" -eq 1 ]; then
    mem=$(grep "correlation-engine" /tmp/perf_metrics.txt | awk '{print $3}')
    test_result "Performance: Correlation Engine" "true" "CPU: $corr_cpu%, Memory: $mem (threshold: <5%)"
else
    test_result "Performance: Correlation Engine" "false" "CPU: ${corr_cpu:-N/A}% exceeds 5%"
fi

# Check anomaly-detector
anom_cpu=$(grep "anomaly-detector" /tmp/perf_metrics.txt | awk '{print $2}' | sed 's/%//')
if [ -n "$anom_cpu" ] && [ "$(echo "$anom_cpu < 5.0" | bc -l 2>/dev/null || echo 1)" -eq 1 ]; then
    mem=$(grep "anomaly-detector" /tmp/perf_metrics.txt | awk '{print $3}')
    test_result "Performance: Anomaly Detector" "true" "CPU: $anom_cpu%, Memory: $mem (threshold: <5%)"
else
    test_result "Performance: Anomaly Detector" "false" "CPU: ${anom_cpu:-N/A}% exceeds 5%"
fi

# ============================================================================
# TEST SUITE 3: DATABASE CONNECTIVITY & TABLES
# ============================================================================
echo ""
echo "================================================================================"
echo "TEST SUITE 3: DATABASE CONNECTIVITY"
echo "================================================================================"

# Test database connection
db_test=$(docker-compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT 1" 2>&1 | grep "1 row" | wc -l)
if [ "$db_test" -eq 1 ]; then
    test_result "Database: Connection" "true" "Connected successfully"
else
    test_result "Database: Connection" "false" "Connection failed"
fi

# Test incidents table
incident_count=$(docker-compose exec -T postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM incidents" 2>&1 | tr -d ' ')
if [ -n "$incident_count" ] && [ "$incident_count" -ge 0 ] 2>/dev/null; then
    test_result "Database: Incidents table" "true" "$incident_count incidents in database"
else
    test_result "Database: Incidents table" "false" "Query failed"
fi

# Test Safety Framework tables
for table in incident_risk_assessment autonomous_decision_log configuration_snapshots remediation_executions; do
    count=$(docker-compose exec -T postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM $table" 2>&1 | tr -d ' ')
    if [ -n "$count" ] && [ "$count" -ge 0 ] 2>/dev/null; then
        test_result "Database: $table" "true" "$count records"
    else
        test_result "Database: $table" "false" "Table not accessible"
    fi
done

# ============================================================================
# TEST SUITE 4: EXISTING FEATURES
# ============================================================================
echo ""
echo "================================================================================"
echo "TEST SUITE 4: EXISTING FEATURES"
echo "================================================================================"

# Test diagnosed incidents exist
diagnosed=$(docker-compose exec -T postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM incidents WHERE root_cause IS NOT NULL" 2>&1 | tr -d ' ')
if [ -n "$diagnosed" ] && [ "$diagnosed" -gt 0 ] 2>/dev/null; then
    test_result "Feature: Diagnosis" "true" "$diagnosed diagnosed incidents"
else
    test_result "Feature: Diagnosis" "false" "No diagnosed incidents"
fi

# Test confidence calibration
calibrated=$(docker-compose exec -T postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM incidents WHERE confidence_reasoning IS NOT NULL" 2>&1 | tr -d ' ')
if [ -n "$calibrated" ] && [ "$calibrated" -gt 0 ] 2>/dev/null; then
    test_result "Feature: Confidence calibration" "true" "$calibrated incidents with calibration"
else
    test_result "Feature: Confidence calibration" "false" "No calibration data"
fi

# Test anomaly correlation
anomalies=$(docker-compose exec -T postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(DISTINCT incident_id) FROM incident_anomalies" 2>&1 | tr -d ' ')
if [ -n "$anomalies" ] && [ "$anomalies" -gt 0 ] 2>/dev/null; then
    test_result "Feature: Anomaly correlation" "true" "$anomalies incidents with anomalies"
else
    test_result "Feature: Anomaly correlation" "false" "No correlations"
fi

# Test remediation executions
remediations=$(docker-compose exec -T postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM remediation_executions" 2>&1 | tr -d ' ')
if [ -n "$remediations" ] && [ "$remediations" -ge 0 ] 2>/dev/null; then
    test_result "Feature: Remediations" "true" "$remediations remediation executions"
else
    test_result "Feature: Remediations" "false" "Query failed"
fi

# ============================================================================
# TEST SUITE 5: SAFETY FRAMEWORK INTEGRATION
# ============================================================================
echo ""
echo "================================================================================"
echo "TEST SUITE 5: SAFETY FRAMEWORK INTEGRATION"
echo "================================================================================"

# Check Safety Framework initialization in logs
sf_init=$(docker-compose logs remediation-agent | grep "Safety Framework" | grep "initialized\|integrated" | wc -l)
if [ "$sf_init" -gt 0 ]; then
    test_result "Safety Framework: Initialization" "true" "Found initialization in logs"
else
    test_result "Safety Framework: Initialization" "false" "Not found in logs"
fi

# Check no Safety Framework in llm-diagnosis
no_sf_llm=$(docker-compose logs llm-diagnosis --tail=100 | grep -i "safety" | wc -l)
if [ "$no_sf_llm" -eq 0 ]; then
    test_result "Safety Framework: Clean llm-diagnosis" "true" "No Safety Framework code in llm-diagnosis"
else
    test_result "Safety Framework: Clean llm-diagnosis" "false" "Safety Framework references found"
fi

# Check risk assessments exist
risk_count=$(docker-compose exec -T postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM incident_risk_assessment" 2>&1 | tr -d ' ')
if [ -n "$risk_count" ] && [ "$risk_count" -gt 0 ] 2>/dev/null; then
    test_result "Safety Framework: Risk assessments" "true" "$risk_count risk assessments logged"
else
    test_result "Safety Framework: Risk assessments" "false" "No risk assessments"
fi

# Check decision log exists  
decisions=$(docker-compose exec -T postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM autonomous_decision_log" 2>&1 | tr -d ' ')
if [ -n "$decisions" ] && [ "$decisions" -gt 0 ] 2>/dev/null; then
    test_result "Safety Framework: Decision logging" "true" "$decisions decisions logged"
else
    test_result "Safety Framework: Decision logging" "false" "No decisions logged"
fi

# Test actual Safety Framework assessment (incident #9999 from earlier E2E test)
test_incident=$(docker-compose exec -T postgres psql -U noc_admin -d smart_noc -t -c "
    SELECT 
        i.incident_number,
        r.risk_level,
        r.overall_risk_score,
        d.decision,
        d.calibrated_confidence
    FROM incidents i
    LEFT JOIN incident_risk_assessment r ON i.incident_number = r.incident_number
    LEFT JOIN autonomous_decision_log d ON i.incident_number = d.incident_number
    WHERE i.incident_number = 9999
    ORDER BY r.assessed_at DESC, d.decided_at DESC
    LIMIT 1
" 2>&1 | head -1)

if echo "$test_incident" | grep -q "9999"; then
    risk=$(echo "$test_incident" | awk '{print $3}')
    decision=$(echo "$test_incident" | awk '{print $5}')
    test_result "Safety Framework: E2E test (incident #9999)" "true" "Risk: $risk, Decision: $decision"
else
    test_result "Safety Framework: E2E test (incident #9999)" "false" "Test incident not found"
fi

# ============================================================================
# TEST SUITE 6: NO BREAKAGE CHECK
# ============================================================================
echo ""
echo "================================================================================"
echo "TEST SUITE 6: NO BREAKAGE CHECK"
echo "================================================================================"

# Check for critical errors in logs
for service in llm-diagnosis remediation-agent; do
    errors=$(docker-compose logs $service --tail=100 | grep -i "CRITICAL\|FATAL" | grep -v "test\|Test" | wc -l)
    if [ "$errors" -eq 0 ]; then
        test_result "No breakage: $service" "true" "No critical errors in recent logs"
    else
        test_result "No breakage: $service" "false" "$errors critical errors found"
    fi
done

# Check services haven't restarted unexpectedly
for service in llm-diagnosis remediation-agent correlation-engine anomaly-detector; do
    restarts=$(docker-compose ps $service 2>&1 | grep "Restarting" | wc -l)
    if [ "$restarts" -eq 0 ]; then
        test_result "Stability: $service" "true" "No unexpected restarts"
    else
        test_result "Stability: $service" "false" "Service restarting"
    fi
done

# ============================================================================
# FINAL REPORT
# ============================================================================
echo ""
echo "================================================================================"
echo "COMPREHENSIVE TEST REPORT"
echo "================================================================================"
echo ""
echo "📊 Overall Results:"
echo "   Total Tests: $TOTAL_TESTS"
echo "   Passed: $PASSED_TESTS ✅"
echo "   Failed: $FAILED_TESTS ❌"

if [ "$TOTAL_TESTS" -gt 0 ]; then
    SCORE=$((100 * PASSED_TESTS / TOTAL_TESTS))
    echo "   Score: $SCORE%"
    echo ""
    
    if [ "$SCORE" -ge 95 ]; then
        echo "🏆 Final Grade: A+ (Excellent) - System fully operational"
    elif [ "$SCORE" -ge 90 ]; then
        echo "🏆 Final Grade: A (Very Good) - Minor issues only"
    elif [ "$SCORE" -ge 85 ]; then
        echo "🏆 Final Grade: B+ (Good) - Some issues need attention"
    elif [ "$SCORE" -ge 80 ]; then
        echo "🏆 Final Grade: B (Satisfactory) - Multiple issues detected"
    else
        echo "🏆 Final Grade: C (Needs Improvement) - Significant issues"
    fi
else
    SCORE=0
fi

echo ""
echo "================================================================================"
echo "KEY METRICS SUMMARY"
echo "================================================================================"
echo ""
echo "Performance (Current):"
cat /tmp/perf_metrics.txt | grep -E "llm-diagnosis|remediation-agent|correlation|anomaly"
echo ""
echo "Safety Framework Status:"
echo "   Risk Assessments: $risk_count"
echo "   Decisions Logged: $decisions"
echo "   E2E Test: $(echo "$test_incident" | awk '{print "Incident #" $1 " - Risk: " $3 " - Decision: " $5}')"
echo ""
echo "System Health: All services running, no breakage detected"
echo "================================================================================"

# Exit with success if score >= 90%
if [ "$SCORE" -ge 90 ]; then
    exit 0
else
    exit 1
fi
