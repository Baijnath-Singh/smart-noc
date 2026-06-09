-- Create a test BGP connectivity incident to demonstrate vector-enhanced diagnosis
INSERT INTO incidents (
    incident_type, 
    severity, 
    status, 
    affected_device_count, 
    affected_devices, 
    primary_device, 
    anomaly_count, 
    start_time, 
    correlation_method, 
    correlation_confidence, 
    impact_score, 
    incident_metadata
) VALUES (
    'CONNECTIVITY_ISSUE', 
    'CRITICAL', 
    'ACTIVE', 
    1, 
    '[{"device_id": "core-router-02", "anomaly_count": 5}]'::jsonb, 
    'core-router-02', 
    5, 
    NOW(), 
    'device_correlation', 
    85.0, 
    8.5, 
    '{"bgp_neighbor": "10.0.1.2", "bgp_state": "Down", "affected_routes": "192.168.10.0/24", "route_flapping": true, "peer_as": 65001}'::jsonb
) 
RETURNING incident_number, incident_type, severity;
