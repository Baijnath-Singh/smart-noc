-- Create test incidents for safety framework testing
-- These are used by test_safety_framework.py

-- Insert test incidents if they don't exist
INSERT INTO incidents (incident_number, primary_device, incident_type, severity, status, start_time, correlation_method)
VALUES 
    (9001, 'access-sw-01', 'CONNECTIVITY_ISSUE', 'LOW', 'ACTIVE', NOW(), 'manual_test'),
    (9002, 'dist-sw-01', 'CONNECTIVITY_ISSUE', 'MEDIUM', 'ACTIVE', NOW(), 'manual_test'),
    (9003, 'dist-sw-02', 'CONNECTIVITY_ISSUE', 'HIGH', 'ACTIVE', NOW(), 'manual_test'),
    (9004, 'core-rtr-01', 'CONNECTIVITY_ISSUE', 'CRITICAL', 'ACTIVE', NOW(), 'manual_test'),
    (9100, 'test-switch-01', 'CONNECTIVITY_ISSUE', 'LOW', 'ACTIVE', NOW(), 'manual_test'),
    (9200, 'test-switch-02', 'BGP_FLAPPING', 'MEDIUM', 'ACTIVE', NOW(), 'manual_test'),
    (9301, 'access-sw-01', 'CONNECTIVITY_ISSUE', 'LOW', 'ACTIVE', NOW(), 'manual_test'),
    (9302, 'access-sw-02', 'CONNECTIVITY_ISSUE', 'LOW', 'ACTIVE', NOW(), 'manual_test'),
    (9303, 'dist-sw-01', 'BGP_FLAPPING', 'MEDIUM', 'ACTIVE', NOW(), 'manual_test'),
    (9304, 'dist-sw-02', 'BGP_FLAPPING', 'HIGH', 'ACTIVE', NOW(), 'manual_test'),
    (9305, 'core-rtr-01', 'BGP_FLAPPING', 'CRITICAL', 'ACTIVE', NOW(), 'manual_test'),
    (9306, 'access-sw-03', 'CONNECTIVITY_ISSUE', 'LOW', 'ACTIVE', NOW(), 'manual_test')
ON CONFLICT (incident_number) DO NOTHING;

-- Verify
SELECT COUNT(*) as test_incidents_created FROM incidents WHERE incident_number >= 9000;
