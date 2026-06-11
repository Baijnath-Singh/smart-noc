#!/bin/bash
# Generate Test VLAN Trunk Incident
# This will create a new incident that will be diagnosed by the improved LLM system

echo "🔧 Generating test VLAN trunk misconfiguration incident..."

docker-compose exec -T postgres psql -U noc_admin -d smart_noc << 'EOF'
-- Clear any old test incident
DELETE FROM incidents WHERE incident_number = 999;

-- Create a realistic VLAN trunk incident
INSERT INTO incidents (
    incident_number,
    incident_type,
    severity,
    status,
    affected_device_count,
    affected_devices,
    primary_device,
    anomaly_count,
    start_time,
    correlation_method,
    impact_score
) VALUES (
    999,
    'CONNECTIVITY_ISSUE',
    'HIGH',
    'ACTIVE',
    2,
    '["core-switch-01", "access-switch-12"]'::jsonb,
    'core-switch-01',
    3,
    NOW() - INTERVAL '5 minutes',
    'temporal',
    8.5
);

-- Add correlated anomalies
INSERT INTO incident_anomalies (incident_id, anomaly_id, correlation_score)
SELECT 
    (SELECT id FROM incidents WHERE incident_number = 999),
    id,
    0.95
FROM anomalies 
WHERE device_name IN ('core-switch-01', 'access-switch-12')
ORDER BY detected_at DESC
LIMIT 3;

-- Publish to Kafka for LLM diagnosis
SELECT incident_number, incident_type, severity, primary_device 
FROM incidents 
WHERE incident_number = 999;

\echo ''
\echo '✅ Test incident #999 created!'
\echo ''
\echo 'To monitor diagnosis in real-time:'
\echo '  docker-compose logs -f llm-diagnosis | grep -E "999|Confidence"'
\echo ''
EOF

# Wait a moment then show the incident
sleep 2

echo ""
echo "📊 Incident Status:"
docker-compose exec -T postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    incident_number,
    incident_type,
    severity,
    CASE WHEN root_cause IS NOT NULL THEN 'DIAGNOSED' ELSE 'PENDING DIAGNOSIS' END as status,
    created_at
FROM incidents 
WHERE incident_number = 999;
"

echo ""
echo "⏳ Waiting for LLM diagnosis (may take 30-60 seconds)..."
echo ""
echo "To watch in real-time:"
echo "  docker-compose logs -f llm-diagnosis"
