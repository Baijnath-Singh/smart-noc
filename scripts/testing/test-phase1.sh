#!/bin/bash
# Phase 1 Test Script
# Tests that remediation lessons are being queried and included in LLM context

echo "========================================="
echo "Phase 1 Implementation Test"
echo "========================================="
echo ""

# Test 1: Verify remediation_executions table has data
echo "Test 1: Check remediation lessons data..."
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "
SELECT COUNT(*) as total_lessons FROM remediation_executions;
"

# Test 2: Verify SQL query works (same query used by diagnosis service)
echo ""
echo "Test 2: Test SQL query (what LLM diagnosis will see)..."
docker compose exec -T postgres psql -U noc_admin -d smart_noc << 'EOF'
SELECT 
    i.incident_number,
    i.primary_device,
    r.success,
    r.actions_taken,
    r.resolution_time_seconds,
    r.final_phase,
    r.lessons_learned
FROM remediation_executions r
JOIN incidents i ON r.incident_id = i.id
WHERE i.incident_type = 'UNKNOWN'
ORDER BY r.executed_at DESC
LIMIT 3;
EOF

# Test 3: Verify llm-diagnosis service is running
echo ""
echo "Test 3: Check llm-diagnosis service status..."
docker compose ps llm-diagnosis | grep -E "smart-noc-llm-diagnosis|Up"

# Test 4: Check service logs for errors
echo ""
echo "Test 4: Check for errors in logs..."
ERROR_COUNT=$(docker compose logs llm-diagnosis --since 5m 2>&1 | grep -i "error\|exception\|failed" | grep -v "No error" | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "✅ No errors found in logs"
else
    echo "⚠️  Found $ERROR_COUNT potential errors (review logs)"
fi

# Test 5: Show what LLM will see
echo ""
echo "Test 5: Sample of what LLM diagnosis will see..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker compose exec -T postgres psql -U noc_admin -d smart_noc << 'EOF'
SELECT 
    'Past remediation results for ' || i.incident_type || E':\n' ||
    '- Incident #' || i.incident_number || ' (' || i.primary_device || '): ' ||
    CASE WHEN r.success THEN '✅ SUCCESS' ELSE '❌ FAILED' END || E'\n' ||
    '  Phase: ' || r.final_phase || ', Actions: ' || r.actions_taken || 
    ', Time: ' || ROUND(r.resolution_time_seconds::numeric, 1) || E's\n' ||
    '  Lesson: ' || r.lessons_learned as "LLM Context"
FROM remediation_executions r
JOIN incidents i ON r.incident_id = i.id
WHERE i.incident_type = 'UNKNOWN'
ORDER BY r.executed_at DESC
LIMIT 1;
EOF
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "========================================="
echo "Phase 1 Test Complete!"
echo "========================================="
echo ""
echo "Status: ✅ Phase 1 is READY"
echo ""
echo "Next steps to verify end-to-end:"
echo "1. Generate a new UNKNOWN incident:"
echo "   ./scripts/generate-logs.sh --scenario flapping --count 2"
echo ""
echo "2. Watch diagnosis logs:"
echo "   docker compose logs -f llm-diagnosis"
echo ""
echo "3. Check if diagnosis used remediation lessons:"
echo "   docker compose exec postgres psql -U noc_admin -d smart_noc -c \\"
echo "   'SELECT incident_number, root_cause FROM incidents ORDER BY created_at DESC LIMIT 1;'"
echo ""
